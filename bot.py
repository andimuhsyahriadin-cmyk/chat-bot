"""
TELEGRAM USERBOT DENGAN GEMINI 3.1 AI
Single file complete bot - ready untuk Termux
IMPROVED: Smart deep reply detection + Intelligent context-aware responses
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
stats = {
    'messages_received': 0,
    'messages_replied': 0,
    'errors': 0,
    'rest_sessions': 0,
    'start_time': datetime.now()
}

# Skip keywords
SKIP_KEYWORDS = ['admin', 'moderator', 'warning', '[bot]', 'report', 'spam', 'banned']

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
    "Kamu temen gaul. Balas pendek, santai, nyambung sama obrolan.",
    "Jadi temen yang fun dan natural. Jangan formal atau membosankan.",
    "Respond seperti teman yang lagi santai di grup. Keep it real.",
    "Balas dengan energi dan sedikit humor. Jangan terlalu panjang.",
    "Ngobrol seperti teman biasa. Santai, natural, dan straightforward.",
]

# Fallback responses
FALLBACK_RESPONSES = ["Wkwk setuju", "Haha true", "Sama sih", "Hehe iya", "Bet", "Noted", "Okee"]

# ==================== HELPER FUNCTIONS ====================

def print_banner():
    """Print bot banner"""
    print(f"\n{C.CYAN}{C.BOLD}" + "="*80)
    print(f"        🤖 TELEGRAM USERBOT DENGAN GEMINI 3.1 AI 🤖")
    print(f"        Smart Reply • Intelligent Rest • Real-time Monitoring")
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
    IMPROVED: Check if deep reply (reply to reply) dengan logic yang lebih akurat
    Deep reply = pesan yang reply ke pesan lain (bukan top-level)
    Logic:
    1. Jika tidak ada reply_to → top-level (return False)
    2. Jika reply_to ada, cek apakah itu reply to thread/topic → top-level (return False)
    3. Jika reply to pesan spesifik (reply_to_msg_id ada) → deep reply (return True)
    """
    if not message.reply_to:
        return False
    
    # Check if ini reply to thread/topic (reply_to_top_id)
    reply_to_top = getattr(message.reply_to, 'reply_to_top_id', None)
    if reply_to_top:
        # Ada reply_to_top_id tapi bukan nested = top-level di thread
        return False
    
    # Check if ini actual reply ke pesan lain
    reply_to_msg = getattr(message.reply_to, 'reply_to_msg_id', None)
    return reply_to_msg is not None

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
    print(f"{C.GREEN}⚠️  Errors:{C.RESET} {stats['errors']}")
    print(f"{C.GREEN}😴 Rest Sessions:{C.RESET} {stats['rest_sessions']}")
    print(f"{C.BOLD}{C.CYAN}{'='*80}{C.RESET}\n")

# ==================== AI ENGINE ====================

def generate_ai_response(sender_name, user_text, context_messages=None):
    """
    IMPROVED: Generate response menggunakan Gemini 3.1 AI dengan context awareness
    context_messages: List of recent messages untuk context yang lebih baik
    """
    try:
        # Build context dari recent messages
        context = ""
        if context_messages:
            context = "Konteks obrolan terakhir:\n"
            for msg in context_messages[-3:]:  # Last 3 messages
                context += f"- {msg['sender']}: {msg['text']}\n"
            context += "\n"
        
        # Pick random system prompt dan template
        system_prompt = random.choice(SYSTEM_PROMPTS)
        template = random.choice([
            "{context}Balas gaul Indonesia sesuai konteks:\n{sender}: {text}",
            "{context}Respond in casual Indonesian:\n{sender}: {text}",
            "{context}Komentar santai:\n{sender}: {text}",
        ])
        
        contents = template.format(context=context, sender=sender_name, text=user_text)
        
        # Call Gemini 3.1 Flash Lite dengan temperature tinggi untuk variasi
        response = ai_client.models.generate_content(
            model='gemini-3.1-flash-lite',
            contents=contents,
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
                temperature=0.88,
                max_output_tokens=75
            )
        )
        
        if response and response.text:
            reply_text = response.text.strip()
            # Cleanup markdown formatting
            reply_text = reply_text.replace('**', '').replace('__', '').replace('```', '')
            reply_text = ' '.join(reply_text.split())
            if len(reply_text) > 150:
                reply_text = reply_text[:147] + "..."
            return reply_text, False
    
    except Exception as e:
        logger.error(f"AI Error: {e}")
        stats['errors'] += 1
    
    # Fallback
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
        
        sender_name = sender.first_name or "Unknown"
        user_text = event.message.text or ''
        
        # Validate text
        if not user_text or len(user_text.strip()) < 3:
            return
        
        # Display message (SEMUA CHAT DITAMPILKAN!)
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"{C.YELLOW}[{timestamp}] {C.BOLD}{sender_name}{C.RESET}: {user_text}")
        
        stats['messages_received'] += 1
        last_activity = datetime.now()
        
        # Check conditions
        if is_deep_reply(event.message):
            print(f"   {C.CYAN}└─ ⏭️ Skip (deep reply){C.RESET}")
            return
        
        if should_skip_keywords(user_text):
            print(f"   {C.CYAN}└─ ⏭️ Skip (keyword){C.RESET}")
            return
        
        # Add to buffer
        messages_buffer.append({
            'sender_id': sender.id,
            'sender_name': sender_name,
            'text': user_text,
            'event': event
        })
        
        print(f"   {C.MAGENTA}└─ 📦 Buffer: {len(messages_buffer)} messages{C.RESET}")
        
        # Check if should trigger reply
        if len(messages_buffer) >= MIN_REPLY and not is_replying:
            await reply_sequence()
    
    except Exception as e:
        logger.error(f"Error handling message: {e}")
        stats['errors'] += 1

# ==================== REPLY SEQUENCE ====================

async def reply_sequence():
    """
    Reply sequence dengan improved context awareness:
    1. Pilih random 1-3 messages dari buffer
    2. Reply dengan delay 30-45s random per reply
    3. Show typing indicator
    4. Rest 1:50-2:20
    5. Buka percakapan jika sepi
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
        
        # Select random messages
        selected = random.sample(messages_buffer, reply_count)
        
        print(f"\n{C.BOLD}{C.BLUE}{'='*80}{C.RESET}")
        print(f"{C.BOLD}🤖 REPLYING TO {reply_count} MESSAGES{C.RESET}")
        print(f"{C.BOLD}{C.BLUE}{'='*80}{C.RESET}\n")
        
        # Build context dari previous messages di buffer
        context_for_ai = []
        for msg in messages_buffer:
            context_for_ai.append({
                'sender': msg['sender_name'],
                'text': msg['text']
            })
        
        # Reply to each message
        for idx, msg in enumerate(selected, 1):
            sender_name = msg['sender_name']
            user_text = msg['text']
            event = msg['event']
            
            # Generate response dengan context
            reply_text, is_fallback = generate_ai_response(sender_name, user_text, context_for_ai)
            
            # Random typing time
            typing_time = random.randint(DELAY_MIN, DELAY_MAX)
            print(f"   {C.CYAN}└─ 🤔 Thinking... ({typing_time}s){C.RESET}")
            
            # Show typing action
            try:
                async with client.action(TARGET_GROUP, 'typing'):
                    await asyncio.sleep(typing_time)
            except:
                await asyncio.sleep(typing_time)
            
            # Send reply
            await event.reply(reply_text)
            print(f"   {C.GREEN}└─ ✅ [REPLY] {reply_text}{C.RESET}")
            
            stats['messages_replied'] += 1
            last_activity = datetime.now()
            
            logger.info(f"Reply #{idx}/{reply_count} sent")
            
            # Delay before next reply (jika bukan last)
            if idx < reply_count:
                next_delay = random.randint(DELAY_MIN, DELAY_MAX)
                await asyncio.sleep(next_delay)
        
        print(f"\n{C.BOLD}{C.BLUE}{'='*80}{C.RESET}")
        print(f"{C.GREEN}✅ ALL REPLIES SENT{C.RESET}")
        print(f"{C.BOLD}{C.BLUE}{'='*80}{C.RESET}\n")
        
        # Remove replied messages dari buffer
        for msg in selected:
            messages_buffer.remove(msg)
        
        # Rest period
        rest_duration = random.randint(REST_MIN, REST_MAX)
        minutes = rest_duration // 60
        seconds = rest_duration % 60
        print(f"{C.YELLOW}⏸️  BOT RESTING for {minutes}m {seconds}s{C.RESET}")
        
        logger.info(f"Bot resting for {rest_duration} seconds")
        stats['rest_sessions'] += 1
        
        await asyncio.sleep(rest_duration)
        
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
        msg = random.choice(OPENING_MESSAGES)
        await client.send_message(TARGET_GROUP, msg, reply_to=TOPIC_ID)
        print(f"{C.GREEN}📢 [OPENING] {msg}{C.RESET}")
        logger.info(f"Smart opening sent: {msg}")
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
        
        # Start smart opening task
        smart_task = asyncio.create_task(smart_opening_task())
        
        # Run until disconnected
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
        print(f"{C.GREEN}✅ Bot shutdown{C.RESET}\n")

# ==================== ENTRY POINT ====================

def signal_handler(signum, frame):
    """Handle Ctrl+C"""
    global should_exit
    logger.warning("Received signal, shutting down...")
    should_exit = True

if __name__ == '__main__':
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        with client:
            client.loop.run_until_complete(main())
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        print(f"{C.RED}❌ Fatal error: {e}{C.RESET}")
