"""
TELEGRAM USERBOT DENGAN GEMINI 3.1 AI - ADVANCED VERSION
Single file complete bot - ready untuk Termux
IMPROVED: Smart 3-message cycle + Conversational replies + Smart conversation tracking
"""

import asyncio
import random
import signal
import sys
import os
import logging
from datetime import datetime, timedelta
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

# Bot behavior - FIXED CYCLE
DELAY_MIN = 15  # Delay antar reply dalam cycle
DELAY_MAX = 30
REST_MIN = 110  # 1:50
REST_MAX = 130  # 2:10
SILENCE = 60    # Open jika sepi 60 detik

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
cycle_count = 0  # Cycle 1, 2, 3, 4... (1-3 untuk first batch, 4-6 untuk replies)
message_queue = []  # Queue untuk di-balas nanti
last_activity = datetime.now()
should_exit = False
is_processing = False

# Tracking conversation
conversation_state = {
    'pending_replies': [],  # Chat yang menunggu balasan
    'cycle_position': 0     # Posisi di cycle (1-3 atau reset)
}

stats = {
    'messages_received': 0,
    'messages_replied': 0,
    'cycles_completed': 0,
    'errors': 0,
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
    "Kamu adalah teman gaul di grup chat. Balas SINGKAT (1-2 kalimat), santai, natural, dan nyambung sempurna. Jangan formal.",
    "Jadi teman yang fun dan natural. Balas super singkat, santai, langsung to the point.",
    "Respond seperti teman santai di Telegram. Balas pendek, casual, LANGSUNG NYAMBUNG.",
    "Balas dengan energi tapi SINGKAT. 1-2 kalimat max. Jangan panjang.",
    "Ngobrol seperti teman biasa. Santai, natural, straightforward, sangat singkat.",
]

# Fallback responses
FALLBACK_RESPONSES = ["Wkwk setuju", "Haha true", "Sama sih", "Hehe iya", "Bet", "Okee", "Betul", "Fix", "Noted"]

# ==================== HELPER FUNCTIONS ====================

def print_banner():
    """Print bot banner"""
    print(f"\n{C.CYAN}{C.BOLD}" + "="*80)
    print(f"        🤖 TELEGRAM USERBOT DENGAN GEMINI 3.1 AI 🤖")
    print(f"        3-Chat Cycle • Smart Replies • Instant Exit • Active Conversations")
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
    print(f"{C.GREEN}🔄 Cycles Completed:{C.RESET} {stats['cycles_completed']}")
    print(f"{C.GREEN}⚠️  Errors:{C.RESET} {stats['errors']}")
    print(f"{C.BOLD}{C.CYAN}{'='*80}{C.RESET}\n")

# ==================== AI ENGINE ====================

def generate_ai_response(sender_name, user_text, context_messages=None):
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
    global message_queue, last_activity, conversation_state
    
    try:
        if getattr(event.message, 'out', False):
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
        
        if should_skip_keywords(user_text):
            print(f"   {C.CYAN}└─ ⏭️  Skip (keyword filter){C.RESET}")
            return
        
        # Tambah ke queue
        message_queue.append({
            'sender_id': sender.id,
            'sender_name': sender_name,
            'text': user_text,
            'event': event,
            'timestamp': datetime.now()
        })
        
        queue_size = len(message_queue)
        print(f"   {C.MAGENTA}└─ 📦 Queue: {queue_size} messages{C.RESET}")
        
        # Trigger reply jika queue >= 3
        if queue_size >= 3 and not is_processing:
            await start_reply_cycle()
    
    except Exception as e:
        logger.error(f"Error handling message: {e}")
        stats['errors'] += 1

# ==================== REPLY CYCLE LOGIC ====================

async def start_reply_cycle():
    """Start 3-message reply cycle"""
    global is_processing, message_queue, last_activity
    
    if is_processing or len(message_queue) < 3:
        return
    
    is_processing = True
    
    try:
        # Pilih 3 message dari queue
        selected = message_queue[:3]
        
        print(f"\n{C.BOLD}{C.BLUE}{'='*80}{C.RESET}")
        print(f"{C.BOLD}🤖 CYCLE: Balas 3 Messages{C.RESET}")
        print(f"{C.BOLD}{C.BLUE}{'='*80}{C.RESET}\n")
        
        # Build context
        context_for_ai = []
        for msg in message_queue:
            context_for_ai.append({
                'sender': msg['sender_name'],
                'text': msg['text']
            })
        
        # Balas ketiga message dengan delay
        for idx, msg in enumerate(selected, 1):
            if should_exit:
                print(f"{C.YELLOW}[EXIT] Stopping cycle...{C.RESET}")
                break
            
            sender_name = msg['sender_name']
            user_text = msg['text']
            event = msg['event']
            
            try:
                reply_text, is_fallback = generate_ai_response(sender_name, user_text, context_for_ai)
                
                delay = random.randint(DELAY_MIN, DELAY_MAX)
                print(f"   {C.CYAN}└─ 🤔 Replying to {sender_name}... ({delay}s){C.RESET}")
                
                try:
                    async with client.action(TARGET_GROUP, 'typing'):
                        for _ in range(delay):
                            if should_exit:
                                break
                            await asyncio.sleep(1)
                except:
                    for _ in range(delay):
                        if should_exit:
                            break
                        await asyncio.sleep(1)
                
                if not should_exit:
                    await event.reply(reply_text)
                    response_type = "FALLBACK" if is_fallback else "AI"
                    print(f"   {C.GREEN}└─ ✅ [REPLY/{response_type}] {reply_text}{C.RESET}")
                    stats['messages_replied'] += 1
                    last_activity = datetime.now()
                
            except Exception as e:
                logger.error(f"Error sending reply: {e}")
                stats['errors'] += 1
        
        if should_exit:
            return
        
        # Remove dari queue
        message_queue[:3] = []
        
        print(f"\n{C.BOLD}{C.BLUE}{'='*80}{C.RESET}")
        print(f"{C.GREEN}✅ CYCLE COMPLETE{C.RESET}")
        print(f"{C.BOLD}{C.BLUE}{'='*80}{C.RESET}\n")
        
        stats['cycles_completed'] += 1
        
        # REST PERIOD
        rest_duration = random.randint(REST_MIN, REST_MAX)
        minutes = rest_duration // 60
        seconds = rest_duration % 60
        print(f"{C.YELLOW}⏸️  RESTING for {minutes}m {seconds}s (Ctrl+C untuk exit){C.RESET}")
        
        # Interruptible sleep
        for _ in range(rest_duration):
            if should_exit:
                print(f"{C.YELLOW}[EXIT] Rest interrupted{C.RESET}\n")
                break
            await asyncio.sleep(1)
        
        if not should_exit:
            print(f"{C.GREEN}🌅 BOT WOKE UP{C.RESET}\n")
            
            # Check jika ada queue yang masuk selama rest
            if len(message_queue) >= 3:
                print(f"{C.CYAN}New messages in queue, starting new cycle...{C.RESET}")
                await start_reply_cycle()
            else:
                # Check silence untuk smart open
                time_silent = (datetime.now() - last_activity).total_seconds()
                if time_silent > SILENCE:
                    print(f"{C.YELLOW}[SMART OPEN] Sepi {int(time_silent)}s, buka obrolan...{C.RESET}")
                    await smart_open()
    
    except Exception as e:
        logger.error(f"Error in reply cycle: {e}")
        stats['errors'] += 1
    
    finally:
        is_processing = False

# ==================== SMART OPENING ====================

async def smart_open():
    """Send smart opening message"""
    try:
        if should_exit:
            return
        
        msg = random.choice(OPENING_MESSAGES)
        await client.send_message(TARGET_GROUP, msg, reply_to=TOPIC_ID)
        print(f"{C.GREEN}📢 [OPENING] {msg}{C.RESET}\n")
        logger.info(f"Smart opening sent: {msg}")
        
        global last_activity
        last_activity = datetime.now()
    except Exception as e:
        logger.error(f"Smart opening failed: {e}")

async def smart_opening_task():
    """Background task untuk monitor silence dan trigger cycle"""
    while not should_exit:
        try:
            # Check setiap 5 detik
            for _ in range(5):
                if should_exit:
                    break
                await asyncio.sleep(1)
            
            if should_exit:
                break
            
            # Jika queue >= 3 dan tidak sedang process, trigger cycle
            if len(message_queue) >= 3 and not is_processing:
                await start_reply_cycle()
            
            # Check silence
            time_silent = (datetime.now() - last_activity).total_seconds()
            if time_silent > SILENCE and not is_processing and len(message_queue) == 0:
                await smart_open()
        
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"Smart opening task error: {e}")

# ==================== SIGNAL HANDLING ====================

def signal_handler(signum, frame):
    """Handle Ctrl+C - INSTANT EXIT"""
    global should_exit
    logger.warning(f"Received signal {signum}, instant shutdown...")
    print(f"\n{C.RED}🛑 INSTANT SHUTDOWN{C.RESET}\n")
    should_exit = True
    # Force exit
    sys.exit(0)

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
        print(f"{C.CYAN}LOGIC: Tunggu 3 chat, balas dengan delay, istirahat, repeat{C.RESET}")
        print(f"{C.CYAN}Press Ctrl+C to instant shutdown{C.RESET}\n")
        
        # Start smart opening task
        smart_task = asyncio.create_task(smart_opening_task())
        
        # Run
        await client.run_until_disconnected()
    
    except KeyboardInterrupt:
        logger.warning("Interrupted by user")
    
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
    except KeyboardInterrupt:
        print(f"{C.RED}🛑 INSTANT EXIT{C.RESET}\n")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        print(f"{C.RED}❌ Fatal error: {e}{C.RESET}")
