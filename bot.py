"""
TELEGRAM USERBOT DENGAN GEMINI 3.1 AI
Single file complete bot - ready untuk Termux
IMPROVED: Fast shutdown + Dual buffer system + Independent messages
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
deep_reply_buffer = []
is_replying = False
last_activity = datetime.now()
should_exit = False
active_tasks = set()

stats = {
    'messages_received': 0,
    'messages_replied': 0,
    'independent_messages': 0,
    'deep_replies_converted': 0,
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

# System prompts
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
    print(f"        Smart Reply • Independent Messages • Fast Shutdown • Active Bot")
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

def get_reply_depth(message):
    """
    Check kedalaman reply chain
    Return: 0 = top-level, 1+ = deep reply
    """
    if not message.reply_to:
        return 0
    
    current = message.reply_to
    reply_to_msg = getattr(current, 'reply_to_msg_id', None)
    
    if reply_to_msg:
        return 2  # Deep nested
    
    return 1

def is_truly_top_level(message):
    """Check if message is truly top-level"""
    return not message.reply_to

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
    independent = stats['independent_messages']
    rate = ((replied + independent) / max(received, 1)) * 100
    
    print(f"\n{C.BOLD}{C.CYAN}{'='*80}{C.RESET}")
    print(f"{C.BOLD}📊 BOT STATISTICS{C.RESET}")
    print(f"{C.BOLD}{C.CYAN}{'='*80}{C.RESET}")
    print(f"{C.GREEN}⏱️  Uptime:{C.RESET} {uptime}")
    print(f"{C.GREEN}📨 Messages Received:{C.RESET} {received}")
    print(f"{C.GREEN}✅ Direct Replies:{C.RESET} {replied}")
    print(f"{C.GREEN}💬 Independent Messages:{C.RESET} {independent}")
    print(f"{C.GREEN}⏸️  Activity Rate:{C.RESET} {rate:.1f}%")
    print(f"{C.GREEN}🔄 Deep Replies Converted:{C.RESET} {stats['deep_replies_converted']}")
    print(f"{C.GREEN}⚠️  Errors:{C.RESET} {stats['errors']}")
    print(f"{C.GREEN}😴 Rest Sessions:{C.RESET} {stats['rest_sessions']}")
    print(f"{C.BOLD}{C.CYAN}{'='*80}{C.RESET}\n")

# ==================== AI ENGINE ====================

def generate_ai_response(sender_name, user_text, context_messages=None, is_independent=False):
    """Generate response dengan Gemini 3.1 AI"""
    try:
        context = ""
        if context_messages and len(context_messages) > 0:
            recent = context_messages[-4:]
            context = "Konteks obrolan terakhir:\n"
            for msg in recent:
                short_text = msg['text'][:80]
                context += f"- {msg['sender']}: {short_text}\n"
            context += "\n"
        
        system_prompt = random.choice(SYSTEM_PROMPTS)
        
        if is_independent:
            template = random.choice([
                "{context}Kasih komentar santai tentang topik ini:\n{text}",
                "{context}Sekarang kamu bilang:\n{text}\nJawab singkat (1-2 kalimat):",
                "{context}Ada topik: {text}\nKamu bilang apa?",
            ])
            contents = template.format(context=context, text=user_text[:120])
        else:
            template = random.choice([
                "{context}Balas singkat dan nyambung:\n{sender}: {text}",
                "{context}{sender}: {text}\nBalas cepat (1-2 kalimat):",
                "{context}Teman ngomong:\n{sender}: {text}\nReply kamu:",
            ])
            contents = template.format(context=context, sender=sender_name, text=user_text[:120])
        
        response = ai_client.models.generate_content(
            model='gemini-3.1-flash-lite',
            contents=contents,
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
                temperature=0.85,
                max_output_tokens=60,
                top_p=0.9
            )
        )
        
        if response and response.text:
            reply_text = response.text.strip()
            reply_text = reply_text.replace('**', '').replace('__', '').replace('```', '')
            reply_text = reply_text.replace('"', '').replace("'", '')
            reply_text = ' '.join(reply_text.split())
            
            if len(reply_text) > 150:
                reply_text = reply_text[:147] + "..."
            
            if reply_text and len(reply_text.strip()) > 2:
                return reply_text, False
    
    except Exception as e:
        logger.error(f"AI Error: {e}")
        stats['errors'] += 1
    
    fallback = random.choice(FALLBACK_RESPONSES)
    return fallback, True

# ==================== MESSAGE HANDLING ====================

@client.on(events.NewMessage(chats=TARGET_GROUP))
async def handle_message(event):
    """Handle incoming messages"""
    global messages_buffer, deep_reply_buffer, last_activity, is_replying
    
    try:
        if getattr(event.message, 'out', False):
            return
        
        if event.message.reply_to:
            reply_to_top = getattr(event.message.reply_to, 'reply_to_top_id', None)
            if reply_to_top and reply_to_top != TOPIC_ID:
                return
        
        sender = await event.get_sender()
        if not sender or sender.bot:
            return
        
        sender_name = sender.first_name or "Unknown"
        user_text = event.message.text or ''
        
        if not user_text or len(user_text.strip()) < 3:
            return
        
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"{C.YELLOW}[{timestamp}] {C.BOLD}{sender_name}{C.RESET}: {user_text}")
        
        stats['messages_received'] += 1
        last_activity = datetime.now()
        
        reply_depth = get_reply_depth(event.message)
        is_top_level = is_truly_top_level(event.message)
        
        if should_skip_keywords(user_text):
            print(f"   {C.CYAN}└─ ⏭️  Skip (keyword filter){C.RESET}")
            return
        
        if is_top_level:
            print(f"   {C.GREEN}└─ 📌 Top-level message (akan di-reply){C.RESET}")
            messages_buffer.append({
                'sender_id': sender.id,
                'sender_name': sender_name,
                'text': user_text,
                'event': event,
                'timestamp': datetime.now(),
                'type': 'direct_reply'
            })
        else:
            print(f"   {C.CYAN}└─ 💬 Deep reply (akan dijawab sebagai independent message){C.RESET}")
            deep_reply_buffer.append({
                'sender_id': sender.id,
                'sender_name': sender_name,
                'text': user_text,
                'timestamp': datetime.now(),
                'type': 'independent'
            })
            stats['deep_replies_converted'] += 1
        
        buffer_size = len(messages_buffer) + len(deep_reply_buffer)
        print(f"   {C.MAGENTA}└─ 📦 Total buffer: {len(messages_buffer)} direct + {len(deep_reply_buffer)} independent{C.RESET}")
        
        trigger_count = MIN_REPLY + random.randint(0, 1)
        if buffer_size >= trigger_count and not is_replying:
            task = asyncio.create_task(reply_sequence())
            active_tasks.add(task)
            task.add_done_callback(active_tasks.discard)
    
    except Exception as e:
        logger.error(f"Error handling message: {e}")
        stats['errors'] += 1

# ==================== REPLY SEQUENCE ====================

async def reply_sequence():
    """Reply sequence dengan fast shutdown support"""
    global is_replying, messages_buffer, deep_reply_buffer, last_activity
    
    if is_replying or (not messages_buffer and not deep_reply_buffer):
        return
    
    is_replying = True
    
    try:
        direct_count = min(random.randint(MIN_REPLY, MAX_REPLY), len(messages_buffer))
        independent_count = min(random.randint(0, 2), len(deep_reply_buffer))
        
        total_replies = direct_count + independent_count
        
        if total_replies == 0:
            return
        
        print(f"\n{C.BOLD}{C.BLUE}{'='*80}{C.RESET}")
        print(f"{C.BOLD}🤖 REPLYING: {direct_count} direct + {independent_count} independent{C.RESET}")
        print(f"{C.BOLD}{C.BLUE}{'='*80}{C.RESET}\n")
        
        context_for_ai = []
        for msg in messages_buffer + deep_reply_buffer:
            context_for_ai.append({
                'sender': msg['sender_name'],
                'text': msg['text']
            })
        
        # === PHASE 1: Direct Replies ===
        if direct_count > 0 and not should_exit:
            selected_direct = random.sample(messages_buffer, direct_count)
            
            for idx, msg in enumerate(selected_direct, 1):
                if should_exit:
                    print(f"{C.YELLOW}[SHUTDOWN] Stopping replies...{C.RESET}")
                    break
                
                sender_name = msg['sender_name']
                user_text = msg['text']
                event = msg['event']
                
                try:
                    reply_text, is_fallback = generate_ai_response(sender_name, user_text, context_for_ai, is_independent=False)
                    
                    typing_time = random.randint(DELAY_MIN, DELAY_MAX)
                    print(f"   {C.CYAN}└─ 🤔 Replying to {sender_name}... ({typing_time}s){C.RESET}")
                    
                    try:
                        async with client.action(TARGET_GROUP, 'typing'):
                            # Cancel sleep jika should_exit
                            for _ in range(typing_time):
                                if should_exit:
                                    break
                                await asyncio.sleep(1)
                    except:
                        for _ in range(typing_time):
                            if should_exit:
                                break
                            await asyncio.sleep(1)
                    
                    if not should_exit:
                        await event.reply(reply_text)
                        response_type = "FALLBACK" if is_fallback else "AI"
                        print(f"   {C.GREEN}└─ ✅ [REPLY/{response_type}] {reply_text}{C.RESET}")
                        stats['messages_replied'] += 1
                        last_activity = datetime.now()
                    
                    if idx < direct_count and not should_exit:
                        next_delay = random.randint(DELAY_MIN, DELAY_MAX)
                        for _ in range(next_delay):
                            if should_exit:
                                break
                            await asyncio.sleep(1)
                
                except Exception as e:
                    logger.error(f"Error sending direct reply: {e}")
                    stats['errors'] += 1
            
            for msg in selected_direct:
                if msg in messages_buffer:
                    messages_buffer.remove(msg)
        
        # === PHASE 2: Independent Messages ===
        if independent_count > 0 and not should_exit:
            selected_independent = random.sample(deep_reply_buffer, independent_count)
            
            for idx, msg in enumerate(selected_independent, 1):
                if should_exit:
                    print(f"{C.YELLOW}[SHUTDOWN] Stopping independent messages...{C.RESET}")
                    break
                
                sender_name = msg['sender_name']
                user_text = msg['text']
                
                try:
                    reply_text, is_fallback = generate_ai_response(sender_name, user_text, context_for_ai, is_independent=True)
                    
                    typing_time = random.randint(DELAY_MIN, DELAY_MAX)
                    print(f"   {C.CYAN}└─ 💬 Typing independent message... ({typing_time}s){C.RESET}")
                    
                    try:
                        async with client.action(TARGET_GROUP, 'typing'):
                            for _ in range(typing_time):
                                if should_exit:
                                    break
                                await asyncio.sleep(1)
                    except:
                        for _ in range(typing_time):
                            if should_exit:
                                break
                            await asyncio.sleep(1)
                    
                    if not should_exit:
                        await client.send_message(TARGET_GROUP, reply_text, reply_to=TOPIC_ID)
                        response_type = "FALLBACK" if is_fallback else "AI"
                        print(f"   {C.GREEN}└─ ✅ [INDEPENDENT/{response_type}] {reply_text}{C.RESET}")
                        stats['independent_messages'] += 1
                        last_activity = datetime.now()
                    
                    if idx < independent_count and not should_exit:
                        next_delay = random.randint(DELAY_MIN, DELAY_MAX)
                        for _ in range(next_delay):
                            if should_exit:
                                break
                            await asyncio.sleep(1)
                
                except Exception as e:
                    logger.error(f"Error sending independent message: {e}")
                    stats['errors'] += 1
            
            for msg in selected_independent:
                if msg in deep_reply_buffer:
                    deep_reply_buffer.remove(msg)
        
        if not should_exit:
            print(f"\n{C.BOLD}{C.BLUE}{'='*80}{C.RESET}")
            print(f"{C.GREEN}✅ BATCH COMPLETE{C.RESET}")
            print(f"{C.BOLD}{C.BLUE}{'='*80}{C.RESET}\n")
            
            rest_duration = random.randint(REST_MIN, REST_MAX)
            minutes = rest_duration // 60
            seconds = rest_duration % 60
            print(f"{C.YELLOW}⏸️  BOT RESTING for {minutes}m {seconds}s (Ctrl+C untuk exit){C.RESET}")
            
            stats['rest_sessions'] += 1
            
            # Sleep dengan interrupt support
            for _ in range(rest_duration):
                if should_exit:
                    print(f"{C.YELLOW}[SHUTDOWN] Interrupted rest period{C.RESET}\n")
                    break
                await asyncio.sleep(1)
            
            if not should_exit:
                print(f"{C.GREEN}🌅 BOT WOKE UP - Ready for next batch!{C.RESET}\n")
                
                time_silent = (datetime.now() - last_activity).total_seconds()
                if time_silent > SILENCE and not messages_buffer and not deep_reply_buffer:
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
            for _ in range(20):
                if should_exit:
                    break
                await asyncio.sleep(1)
            
            if should_exit:
                break
            
            time_silent = (datetime.now() - last_activity).total_seconds()
            
            if time_silent > SILENCE and not is_replying and not messages_buffer and not deep_reply_buffer:
                await smart_open()
        
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"Smart opening task error: {e}")

# ==================== SIGNAL HANDLING ====================

def signal_handler(signum, frame):
    """Handle Ctrl+C - Fast shutdown"""
    global should_exit
    logger.warning(f"Received signal {signum}, initiating fast shutdown...")
    print(f"\n{C.YELLOW}🛑 SHUTDOWN SIGNAL - Stopping bot...{C.RESET}\n")
    should_exit = True

# ==================== MAIN ====================

async def main():
    """Main bot function"""
    print_banner()
    
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
        print(f"{C.CYAN}Press Ctrl+C to shutdown (fast mode){C.RESET}\n")
        
        smart_task = asyncio.create_task(smart_opening_task())
        active_tasks.add(smart_task)
        smart_task.add_done_callback(active_tasks.discard)
        
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
