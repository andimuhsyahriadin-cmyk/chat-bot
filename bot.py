"""
TELEGRAM USERBOT DENGAN GEMINI 3.1 AI
Single file complete bot - ready untuk Termux
IMPROVED: Smart deep reply detection + Intelligent context-aware responses + Graceful shutdown
"""

import asyncio
import random
import signal
import sys
import os
import logging
from datetime import datetime, timedelta
from collections import defaultdict
from dotenv import load_dotenv
from telethon import TelegramClient, events
from telethon.tl.types import MessageActionChatDeleteUser, MessageActionChatAddUser
from google import genai
from google.genai import types

# ==================== LOAD ENV ====================
load_dotenv()

API_ID = int(os.getenv('TELEGRAM_API_ID', '0'))
API_HASH = os.getenv('TELEGRAM_API_HASH', 'change_me')
GEMINI_KEY = os.getenv('GEMINI_API_KEY', 'change_me')
TARGET_GROUP = os.getenv('TARGET_GROUP', 'interlinkIDchat')
TOPIC_ID = int(os.getenv('INDONESIA_TOPIC_ID', '26251'))

# Bot behavior
MIN_REPLY = int(os.getenv('MIN_MESSAGES_REPLY', '1'))
MAX_REPLY = int(os.getenv('MAX_MESSAGES_REPLY', '3'))
REST_MIN = int(os.getenv('REST_DURATION_MIN', '110'))
REST_MAX = int(os.getenv('REST_DURATION_MAX', '140'))
DELAY_MIN = int(os.getenv('REPLY_DELAY_MIN', '30'))
DELAY_MAX = int(os.getenv('REPLY_DELAY_MAX', '45'))
SILENCE = int(os.getenv('SILENCE_THRESHOLD', '60'))

# ==================== COLORS ====================
class C:
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    RESET = '\033[0m'
    BOLD = '\033[1m'

# ==================== LOGGING ====================
os.makedirs('logs', exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/userbot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('userbot')

# ==================== GLOBALS ====================
client = TelegramClient('session_indo', API_ID, API_HASH)
ai_client = genai.Client(api_key=GEMINI_KEY)

# State
messages_buffer = []
is_replying = False
last_activity = datetime.now()
should_exit = False
shutdown_event = asyncio.Event()
active_tasks = set()

stats = {
    'messages_received': 0,
    'messages_replied': 0,
    'deep_replies_skipped': 0,
    'errors': 0,
    'rest_sessions': 0,
    'start_time': datetime.now()
}

# Skip keywords
SKIP_KEYWORDS = ['admin', 'moderator', 'warning', '[bot]', 'report', 'spam', 'banned', 'kick', 'mute']

# Opening messages
OPENING_MESSAGES = [
    "Woi pada ngapain nih? Sepi banget",
    "Gimana kabar kalian semua bro?",
    "Ada yang seru nggak hari ini?",
    "Anjir sepi amat, gas lah ngobrol",
    "Ayo dong lanjut obrolan",
    "Siapa ada ide obrolan asik?",
]

# System prompts (variation untuk hindari deteksi bot)
SYSTEM_PROMPTS = [
    "Kamu adalah teman gaul di grup chat. PENTING: Balas SANGAT pendek (1-2 kalimat max), santai, natural, dan nyambung sempurna dengan obrolan. Jangan panjang-panjang. Jangan formal.",
    "Jadi teman yang fun dan natural dalam grup. Balas super singkat, santai, dan langsung to the point. Keep it real dan ga membosankan.",
    "Respond seperti teman yang lagi santai di grup Telegram. Balas pendek, casual, dan LANGSUNG NYAMBUNG dengan apa yang mereka bilang. No over-thinking.",
    "Balas dengan energi dan sedikit humor, tapi SINGKAT. Hanya 1-2 kalimat. Jangan terlalu panjang atau formal.",
    "Ngobrol seperti teman biasa dalam grup. Santai, natural, straightforward, dan sangat singkat. Langsung nyambung topik.",
]

# Fallback responses
FALLBACK_RESPONSES = ["Wkwk setuju", "Haha true", "Sama sih", "Hehe iya", "Bet", "Okee", "Betul", "Fix", "Noted"]

# ==================== HELPER FUNCTIONS ====================

def print_banner():
    """Print bot banner"""
    print(f"\n{C.CYAN}{C.BOLD}" + "="*80)
    print(f"        🤖 TELEGRAM USERBOT DENGAN GEMINI 3.1 AI 🤖")
    print(f"        Smart Reply • Deep Reply Detection • Context-Aware • Graceful Shutdown")
    print(f"="*80 + f"{C.RESET}\n")

def validate_config():
    """Validate config"""
    errors = []
    if API_ID == 0:
        errors.append("TELEGRAM_API_ID tidak dikonfigurasi")
    if API_HASH == 'change_me':
        errors.append("TELEGRAM_API_HASH tidak dikonfigurasi")
    if GEMINI_KEY == 'change_me':
        errors.append("GEMINI_API_KEY tidak dikonfigurasi")
    return errors

def get_topic_id(message):
    """Get topic ID dari message"""
    if not message.reply_to:
        return None
    reply_to_top = getattr(message.reply_to, 'reply_to_top_id', None)
    return reply_to_top or getattr(message.reply_to, 'reply_to_msg_id', None)

def is_deep_reply(message):
    """
    IMPROVED: Detect deep reply dengan logic yang akurat
    
    Deep reply = reply yang reply ke pesan tertentu (bukan top-level)
    
    Return True jika:
    - reply_to_msg_id ada (reply ke msg spesifik, bukan thread)
    - dan BUKAN reply ke top-level comment
    """
    if not message.reply_to:
        return False
    
    # Check if ini reply to thread (reply_to_top_id)
    reply_to_top = getattr(message.reply_to, 'reply_to_top_id', None)
    
    # Check if ini actual reply ke pesan spesifik
    reply_to_msg = getattr(message.reply_to, 'reply_to_msg_id', None)
    
    # Deep reply = has reply_to_msg_id tapi BUKAN reply to top comment
    if reply_to_msg and not reply_to_top:
        return True
    
    # Jika ada both, berarti nested/deep
    if reply_to_msg and reply_to_top:
        return True
    
    return False

def should_skip_keywords(text):
    """Check skip keywords"""
    text_lower = text.lower()
    for keyword in SKIP_KEYWORDS:
        if keyword.lower() in text_lower:
            return True
    return False

def get_uptime():
    """Get uptime"""
    uptime = datetime.now() - stats['start_time']
    days = uptime.days
    hours, remainder = divmod(uptime.seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{days}d {hours}h {minutes}m {seconds}s"

def print_stats():
    """Print statistics"""
    uptime = get_uptime()
    received = stats['messages_received']
    replied = stats['messages_replied']
    rate = (replied / max(received, 1)) * 100
    
    print(f"\n{C.BOLD}{C.CYAN}{'='*80}{C.RESET}")
    print(f"{C.BOLD}📊 BOT STATISTICS{C.RESET}")
    print(f"{C.BOLD}{C.CYAN}{'='*80}{C.RESET}")
    print(f"{C.GREEN}⏱️  Uptime:{C.RESET} {uptime}")
    print(f"{C.GREEN}📨 Messages Received:{C.RESET} {received}")
    print(f"{C.GREEN}✅ Messages Replied:{C.RESET} {replied}")
    print(f"{C.GREEN}⏸️  Reply Rate:{C.RESET} {rate:.1f}%")
    print(f"{C.GREEN}🚫 Deep Replies Skipped:{C.RESET} {stats['deep_replies_skipped']}")
    print(f"{C.GREEN}⚠️  Errors:{C.RESET} {stats['errors']}")
    print(f"{C.GREEN}😴 Rest Sessions:{C.RESET} {stats['rest_sessions']}")
    print(f"{C.BOLD}{C.CYAN}{'='*80}{C.RESET}\n")

# ==================== AI ENGINE ====================

def generate_ai_response(sender_name, user_text, context_messages=None):
    """
    IMPROVED: Generate response dengan Gemini 3.1 AI yang SMART
    - Context-aware dari recent messages
    - Smart reply detection untuk nyambung obrolan
    - Fallback jika Gemini error
    
    Args:
        sender_name: Nama pengirim pesan
        user_text: Text dari pesan
        context_messages: List of recent messages untuk context
    
    Returns:
        tuple(reply_text, is_fallback)
    """
    try:
        # Build context dari recent messages untuk AI understand obrolan
        context = ""
        if context_messages and len(context_messages) > 0:
            # Ambil last 4 messages untuk context yang natural
            recent = context_messages[-4:]
            context = "Konteks obrolan terakhir:\n"
            for msg in recent:
                short_text = msg['text'][:80]  # Truncate long messages
                context += f"- {msg['sender']}: {short_text}\n"
            context += "\n"
        
        # Pick random system prompt untuk variation
        system_prompt = random.choice(SYSTEM_PROMPTS)
        
        # Template yang lebih natural
        template = random.choice([
            "{context}Balas singkat dan nyambung:\n{sender}: {text}\nJawab cepat dalam 1-2 kalimat:",
            "{context}Sekarang giliran kamu reply. Balas santai dan langsung nyambung:\n{sender}: {text}",
            "{context}Teman ngomong:\n{sender}: {text}\nKamu reply (singkat & natural):",
        ])
        
        contents = template.format(
            context=context,
            sender=sender_name,
            text=user_text[:120]  # Truncate untuk efficiency
        )
        
        # Call Gemini 3.1 Flash Lite
        response = ai_client.models.generate_content(
            model='gemini-3.1-flash-lite',
            contents=contents,
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
                temperature=0.85,  # Sedikit lebih tinggi untuk variation
                max_output_tokens=60,  # Lebih pendek = lebih natural
                top_p=0.9
            )
        )
        
        if response and response.text:
            reply_text = response.text.strip()
            
            # Cleanup formatting
            reply_text = reply_text.replace('**', '').replace('__', '').replace('```', '')
            reply_text = reply_text.replace('"', '').replace("'", '')
            reply_text = ' '.join(reply_text.split())
            
            # Final length check
            if len(reply_text) > 150:
                reply_text = reply_text[:147] + "..."
            
            # Validasi: harus ada text, jangan terlalu pendek
            if reply_text and len(reply_text.strip()) > 2:
                return reply_text, False
    
    except Exception as e:
        logger.error(f"AI Error: {e}")
        stats['errors'] += 1
    
    # Fallback jika AI gagal
    fallback = random.choice(FALLBACK_RESPONSES)
    return fallback, True

# ==================== MESSAGE HANDLING ====================

@client.on(events.NewMessage(chats=TARGET_GROUP))
async def handle_message(event):
    """Handle incoming messages dengan improved logic"""
    global messages_buffer, last_activity, is_replying
    
    try:
        # Skip own messages
        if getattr(event.message, 'out', False):
            return
        
        # Skip wrong topic
        if get_topic_id(event.message) != TOPIC_ID:
            return
        
        # Get sender info
        sender = await event.get_sender()
        if not sender:
            return
        
        # Skip bot messages
        if sender.bot:
            return
        
        sender_name = sender.first_name or "Unknown"
        user_text = event.message.text or ''
        
        # Validate text
        if not user_text or len(user_text.strip()) < 3:
            return
        
        # Display message
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"{C.YELLOW}[{timestamp}] {C.BOLD}{sender_name}{C.RESET}: {user_text}")
        
        stats['messages_received'] += 1
        last_activity = datetime.now()
        
        # Check if deep reply - IMPROVED LOGIC
        if is_deep_reply(event.message):
            print(f"   {C.CYAN}└─ ⏭️  Skip (deep reply to specific message){C.RESET}")
            stats['deep_replies_skipped'] += 1
            return
        
        # Skip keywords
        if should_skip_keywords(user_text):
            print(f"   {C.CYAN}└─ ⏭️  Skip (keyword filter){C.RESET}")
            return
        
        # Add to buffer
        messages_buffer.append({
            'sender_id': sender.id,
            'sender_name': sender_name,
            'text': user_text,
            'event': event,
            'timestamp': datetime.now()
        })
        
        print(f"   {C.MAGENTA}└─ 📦 Buffer: {len(messages_buffer)} messages{C.RESET}")
        
        # Check if should trigger reply
        if len(messages_buffer) >= MIN_REPLY and not is_replying:
            # Create task dan track
            task = asyncio.create_task(reply_sequence())
            active_tasks.add(task)
            task.add_done_callback(active_tasks.discard)
    
    except Exception as e:
        logger.error(f"Error handling message: {e}")
        stats['errors'] += 1

# ==================== REPLY SEQUENCE ====================

async def reply_sequence():
    """
    Reply sequence dengan improved context awareness dan graceful handling:
    1. Pilih random 1-3 messages dari buffer
    2. Build context dari previous messages
    3. Reply dengan delay 30-45s random per reply
    4. Show typing indicator
    5. Rest 1:50-2:20
    6. Buka percakapan jika sepi
    """
    global is_replying, messages_buffer, last_activity
    
    if is_replying or not messages_buffer:
        return
    
    is_replying = True
    
    try:
        # Determine jumlah replies
        reply_count = random.randint(MIN_REPLY, MAX_REPLY)
        if len(messages_buffer) < reply_count:
            reply_count = len(messages_buffer)
        
        # Select random messages untuk reply
        selected = random.sample(messages_buffer, reply_count)
        
        print(f"\n{C.BOLD}{C.BLUE}{'='*80}{C.RESET}")
        print(f"{C.BOLD}🤖 REPLYING TO {reply_count} MESSAGES{C.RESET}")
        print(f"{C.BOLD}{C.BLUE}{'='*80}{C.RESET}\n")
        
        # Build context dari ALL messages di buffer untuk AI understanding
        context_for_ai = []
        for msg in messages_buffer:
            context_for_ai.append({
                'sender': msg['sender_name'],
                'text': msg['text']
            })
        
        # Reply to each message
        for idx, msg in enumerate(selected, 1):
            # Check if should exit
            if should_exit:
                print(f"{C.YELLOW}⚠️  Shutdown signal received, stopping replies...{C.RESET}")
                break
            
            sender_name = msg['sender_name']
            user_text = msg['text']
            event = msg['event']
            
            try:
                # Generate response dengan context
                reply_text, is_fallback = generate_ai_response(sender_name, user_text, context_for_ai)
                
                # Random typing time
                typing_time = random.randint(DELAY_MIN, DELAY_MAX)
                print(f"   {C.CYAN}└─ 🤔 Thinking... ({typing_time}s){C.RESET}")
                
                # Show typing action dengan cancel support
                try:
                    async with client.action(TARGET_GROUP, 'typing'):
                        await asyncio.sleep(typing_time)
                except:
                    await asyncio.sleep(typing_time)
                
                # Send reply
                await event.reply(reply_text)
                response_type = "FALLBACK" if is_fallback else "AI"
                print(f"   {C.GREEN}└─ ✅ [{response_type}] {reply_text}{C.RESET}")
                
                stats['messages_replied'] += 1
                last_activity = datetime.now()
                
                logger.info(f"Reply #{idx}/{reply_count} sent ({response_type})")
                
                # Delay before next reply (jika bukan last)
                if idx < reply_count and not should_exit:
                    next_delay = random.randint(DELAY_MIN, DELAY_MAX)
                    await asyncio.sleep(next_delay)
            
            except Exception as e:
                logger.error(f"Error sending reply #{idx}: {e}")
                stats['errors'] += 1
                continue
        
        print(f"\n{C.BOLD}{C.BLUE}{'='*80}{C.RESET}")
        print(f"{C.GREEN}✅ REPLY BATCH COMPLETE{C.RESET}")
        print(f"{C.BOLD}{C.BLUE}{'='*80}{C.RESET}\n")
        
        # Remove replied messages dari buffer
        for msg in selected:
            if msg in messages_buffer:
                messages_buffer.remove(msg)
        
        # Rest period (skip if should_exit)
        if not should_exit:
            rest_duration = random.randint(REST_MIN, REST_MAX)
            minutes = rest_duration // 60
            seconds = rest_duration % 60
            print(f"{C.YELLOW}⏸️  BOT RESTING for {minutes}m {seconds}s{C.RESET}")
            
            logger.info(f"Bot resting for {rest_duration} seconds")
            stats['rest_sessions'] += 1
            
            try:
                await asyncio.sleep(rest_duration)
            except asyncio.CancelledError:
                logger.warning("Rest period interrupted")
                return
            
            print(f"{C.GREEN}🌅 BOT WOKE UP - Ready for next batch!{C.RESET}\n")
            
            # After wake up - check if silent
            time_silent = (datetime.now() - last_activity).total_seconds()
            if time_silent > SILENCE and not messages_buffer:
                print(f"{C.YELLOW}[SMART OPEN] Grup sepi {int(time_silent)}s, buka obrolan...{C.RESET}")
                await smart_open()
    
    except Exception as e:
        logger.error(f"Error in reply sequence: {e}")
        stats['errors'] += 1
    
    finally:
        is_replying = False

# ==================== SMART OPENING ====================

async def smart_open():
    """Send smart opening message"""
    try:
        if should_exit:
            return
        
        msg = random.choice(OPENING_MESSAGES)
        await client.send_message(TARGET_GROUP, msg, reply_to=TOPIC_ID)
        print(f"{C.GREEN}📢 [OPENING] {msg}{C.RESET}")
        logger.info(f"Smart opening sent: {msg}")
        
        global last_activity
        last_activity = datetime.now()
    except Exception as e:
        logger.error(f"Smart opening failed: {e}")

async def smart_opening_task():
    """Background task untuk monitor silence"""
    while not should_exit:
        try:
            await asyncio.sleep(20)
            
            # Check silence
            time_silent = (datetime.now() - last_activity).total_seconds()
            
            if time_silent > SILENCE and not is_replying and not messages_buffer:
                await smart_open()
                await asyncio.sleep(5)
        
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"Smart opening task error: {e}")
            await asyncio.sleep(5)

# ==================== GRACEFUL SHUTDOWN ====================

async def graceful_shutdown():
    """Graceful shutdown - wait for active tasks"""
    global should_exit
    should_exit = True
    
    print(f"\n{C.YELLOW}{C.BOLD}🛑 GRACEFUL SHUTDOWN INITIATED{C.RESET}")
    print(f"{C.YELLOW}Waiting for active tasks to complete...{C.RESET}\n")
    
    # Wait for any active reply task
    if is_replying:
        print(f"{C.YELLOW}Waiting for current reply to finish...{C.RESET}")
        timeout = 30
        for i in range(timeout):
            if not is_replying:
                break
            await asyncio.sleep(1)
            if i % 5 == 0:
                print(f"{C.YELLOW}Still waiting... ({timeout - i}s timeout){C.RESET}")
    
    # Wait for other tasks
    if active_tasks:
        print(f"{C.YELLOW}Waiting for {len(active_tasks)} background task(s)...{C.RESET}")
        await asyncio.gather(*active_tasks, return_exceptions=True)
    
    print(f"{C.GREEN}✅ All tasks completed{C.RESET}")

def signal_handler(signum, frame):
    """Handle Ctrl+C"""
    logger.warning(f"Received signal {signum}, initiating graceful shutdown...")
    global should_exit
    should_exit = True

# ==================== MAIN ====================

async def main():
    """Main bot function"""
    print_banner()
    
    # Validate config
    errors = validate_config()
    if errors:
        print(f"{C.RED}❌ CONFIG ERRORS:{C.RESET}")
        for e in errors:
            print(f"   {C.RED}✗ {e}{C.RESET}")
        sys.exit(1)
    
    logger.info("="*80)
    logger.info("BOT STARTING")
    logger.info("="*80)
    
    try:
        print(f"{C.GREEN}🔌 Connecting to Telegram...{C.RESET}")
        await client.start()
        
        logger.info("✅ Connected successfully!")
        print(f"{C.GREEN}✅ USERBOT ACTIVE - LISTENING FOR MESSAGES{C.RESET}\n")
        print(f"{C.CYAN}Press Ctrl+C to gracefully shutdown{C.RESET}\n")
        
        # Start smart opening task
        smart_task = asyncio.create_task(smart_opening_task())
        active_tasks.add(smart_task)
        smart_task.add_done_callback(active_tasks.discard)
        
        # Run until disconnected or shutdown
        await client.run_until_disconnected()
    
    except KeyboardInterrupt:
        logger.warning("Interrupted by user")
        print(f"\n{C.YELLOW}⚠️ Interrupted by user{C.RESET}")
    
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        print(f"{C.RED}❌ Error: {e}{C.RESET}")
    
    finally:
        print_stats()
        logger.info("Bot shutdown")
        print(f"{C.GREEN}✅ Bot shutdown complete{C.RESET}\n")

# ==================== ENTRY POINT ====================

if __name__ == '__main__':
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        with client:
            client.loop.run_until_complete(main())
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        print(f"{C.RED}❌ Fatal error: {e}{C.RESET}")
