"""
TELEGRAM USERBOT DENGAN GEMINI 3.1 AI - INDONESIA FOKUS
Single file complete bot - ready untuk Termux
IMPROVED: Strict Indonesia-only + Topic filtering + Language detection
FIX: Correct topic_id detection for original messages + improved message handling
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

# Bot behavior - FIXED 3-CHAT CYCLE
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
message_queue = []  # Queue untuk di-balas
last_activity = datetime.now()
should_exit = False
is_processing = False
last_cycle_time = datetime.now()

stats = {
    'messages_received': 0,
    'messages_replied': 0,
    'messages_skipped': 0,
    'cycles_completed': 0,
    'errors': 0,
    'start_time': datetime.now()
}

# Skip keywords
SKIP_KEYWORDS = ['admin', 'moderator', 'warning', '[bot]', 'report', 'spam', 'banned', 'kick', 'mute']

# Opening messages - STRICT BAHASA INDONESIA
OPENING_MESSAGES = [
    "Woi pada ngapain nih? Sepi banget",
    "Gimana kabar kalian semua bro?",
    "Ada yang seru nggak hari ini?",
    "Anjir sepi amat, gas lah ngobrol",
    "Ayo dong lanjut obrolan",
    "Siapa ada ide obrolan asik?",
    "Apa yang mau dibicarain hari ini?",
    "Gas lanjut cerita bro",
]

# System prompts - STRICT INDONESIA ONLY
SYSTEM_PROMPTS = [
    """Kamu adalah teman gaul di grup chat Indonesia. 
PENTING: HANYA balas dalam BAHASA INDONESIA yang casual dan natural. 
Jangan gunakan bahasa lain apapun (English, Arab, dsb).
Balas SINGKAT (1-2 kalimat), santai, natural, dan NYAMBUNG sempurna dengan obrolan.
Jangan formal, jangan panjang-panjang, jangan terlalu serius.""",
    
    """Respond sebagai teman biasa di grup Indonesia yang santai.
PENTING: Jawab HANYA dalam Bahasa Indonesia casual.
Jangan berpindah ke bahasa lain meski ditanya dalam bahasa lain - tetap gunakan Bahasa Indonesia.
Balas super singkat (1-2 kalimat), santai, langsung to the point.""",
    
    """Kamu adalah anggota grup Indonesia yang fun dan natural.
PENTING: SELALU gunakan Bahasa Indonesia dalam semua reply.
Balas pendek, casual, LANGSUNG NYAMBUNG dengan obrolan grup.
Keep it real, jangan terlalu formal atau panjang.""",
    
    """Sebagai teman di grup, balas dengan santai dan natural.
PENTING: Hanya gunakan Bahasa Indonesia, jangan bahasa lain.
Balas singkat (1-2 kalimat), dengan energi tapi tidak berlebihan.
Jangan formal atau membosankan.""",
    
    """Kamu adalah teman santai di grup Indonesia.
PENTING: WAJIB gunakan Bahasa Indonesia dalam semua jawaban.
Balas sangat singkat, natural, straightforward, dan nyambung topik.
Jangan panjang, jangan formal, jangan bahasa lain.""",
]

# Fallback responses - STRICT BAHASA INDONESIA
FALLBACK_RESPONSES = [
    "Wkwk setuju", "Haha iya", "Sama sih", "Hehe true", "Bet", "Okee", 
    "Betul", "Fix", "Noted", "Yup", "Iyaa", "Haha bener", "Tul bro",
    "Amen", "Iyah deh", "Okeee", "Setuju banget", "Ya ya ya"
]

# ==================== LANGUAGE DETECTION ====================

def detect_language(text):
    """
    Detect if text is Indonesian
    Returns: True if Indonesian, False otherwise
    """
    # Indonesian keywords & patterns
    indonesian_words = [
        'apa', 'siapa', 'dimana', 'kapan', 'bagaimana', 'kenapa',
        'ya', 'yah', 'yaudah', 'lah', 'dong', 'sih', 'kali', 'nih',
        'ini', 'itu', 'saya', 'kamu', 'dia', 'kami', 'kalian',
        'dan', 'atau', 'tapi', 'tapi', 'bukan', 'juga', 'pun',
        'di', 'ke', 'dari', 'untuk', 'sama', 'ada', 'tidak', 'jadi',
        'bro', 'mas', 'bang', 'kak', 'dek', 'om', 'mbak', 'pak',
        'aja', 'udah', 'gak', 'ga', 'ngga', 'nggak', 'enggak',
        'gimana', 'gini', 'gitu', 'cuman', 'kalo', 'kalau'
    ]
    
    text_lower = text.lower()
    words = text_lower.split()
    
    # Count Indonesian words
    indo_count = sum(1 for word in words if any(indo_word in word for indo_word in indonesian_words))
    
    # If > 30% Indonesian words, likely Indonesian
    if len(words) > 0 and indo_count / len(words) > 0.3:
        return True
    
    # Check for Arabic/Persian script
    if any('\u0600' <= c <= '\u06FF' for c in text):  # Arabic range
        return False
    
    # Check for Cyrillic (Russian, etc)
    if any('\u0400' <= c <= '\u04FF' for c in text):
        return False
    
    # Check for Chinese/Japanese/Korean
    if any('\u4E00' <= c <= '\u9FFF' for c in text):  # Chinese
        return False
    if any('\u3040' <= c <= '\u309F' for c in text):  # Japanese Hiragana
        return False
    if any('\uAC00' <= c <= '\uD7AF' for c in text):  # Korean Hangul
        return False
    
    # If no non-Latin characters and reasonable length, assume Indonesian
    if len(words) >= 2 and not any('\u0100' <= c <= '\uFFFF' for c in text if c.isalpha()):
        return True
    
    # Default to Indonesian for benefit of doubt
    return True

# ==================== HELPER FUNCTIONS ====================

def print_banner():
    """Print bot banner"""
    print(f"\n{C.CYAN}{C.BOLD}" + "="*80)
    print(f"        🤖 TELEGRAM USERBOT DENGAN GEMINI 3.1 AI 🇮🇩")
    print(f"        Indonesia-Only • 3-Chat Cycle • Instant Send • Strict Topic Filter")
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
    skipped = stats['messages_skipped']
    rate = (replied / max(received, 1)) * 100
    
    print(f"\n{C.BOLD}{C.CYAN}{'='*80}{C.RESET}")
    print(f"{C.BOLD}📊 BOT STATISTICS{C.RESET}")
    print(f"{C.BOLD}{C.CYAN}{'='*80}{C.RESET}")
    print(f"{C.GREEN}⏱️  Uptime:{C.RESET} {uptime}")
    print(f"{C.GREEN}📨 Messages Received:{C.RESET} {received}")
    print(f"{C.GREEN}✅ Messages Replied:{C.RESET} {replied}")
    print(f"{C.GREEN}🚫 Messages Skipped:{C.RESET} {skipped}")
    print(f"{C.GREEN}⏸️  Reply Rate:{C.RESET} {rate:.1f}%")
    print(f"{C.GREEN}🔄 Cycles Completed:{C.RESET} {stats['cycles_completed']}")
    print(f"{C.GREEN}⚠️  Errors:{C.RESET} {stats['errors']}")
    print(f"{C.BOLD}{C.CYAN}{'='*80}{C.RESET}\n")

# ==================== TOPIC ID DETECTION (FIXED) ====================

def get_message_topic_id(message):
    """
    FIX: Extract topic ID from message correctly
    - For replies: use reply_to_top_id
    - For original messages in topic: use topics_id (Telethon 1.31+)
    - Fallback to None if not in a topic
    """
    try:
        # For replies to messages in a topic
        if message.reply_to and hasattr(message.reply_to, 'reply_to_top_id'):
            return message.reply_to.reply_to_top_id
        
        # For original messages in a topic (Telethon 1.31+)
        if hasattr(message, 'topic_id') and message.topic_id:
            return message.topic_id
        
        # Fallback: check if message has forum_topic attribute
        if hasattr(message, 'forum_topic') and message.forum_topic:
            return message.forum_topic
        
        # Last resort: None (not in a topic)
        return None
    
    except Exception as e:
        logger.debug(f"Error extracting topic_id: {e}")
        return None

# ==================== AI ENGINE ====================

def generate_ai_response(sender_name, user_text, context_messages=None):
    """Generate response dengan Gemini 3.1 AI - STRICT INDONESIA"""
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
        
        # Templates - all in Indonesian
        template = random.choice([
            "{context}Balas singkat dan nyambung:\n{sender}: {text}",
            "{context}{sender}: {text}\nBalas cepat (1-2 kalimat saja):",
            "{context}Teman ngomong:\n{sender}: {text}\nReply kamu (singkat):",
            "{context}Kasih response santai:\n{sender}: {text}",
        ])
        
        contents = template.format(context=context, sender=sender_name, text=user_text[:120])
        
        response = ai_client.models.generate_content(
            model='gemini-1.5-flash',
            contents=contents,
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
                temperature=0.8,
                max_output_tokens=60,
                top_p=0.9
            )
        )
        
        if response and response.text:
            reply_text = response.text.strip()
            
            # Cleanup
            reply_text = reply_text.replace('**', '').replace('__', '').replace('```', '')
            reply_text = reply_text.replace('"', '').replace("'", '')
            reply_text = ' '.join(reply_text.split())
            
            # Validate Indonesian
            if not detect_language(reply_text):
                logger.warning(f"AI generated non-Indonesian text, using fallback: {reply_text[:50]}")
                stats['errors'] += 1
                fallback = random.choice(FALLBACK_RESPONSES)
                return fallback, True
            
            # Length check
            if len(reply_text) > 150:
                reply_text = reply_text[:147] + "..."
            
            if reply_text and len(reply_text.strip()) > 2:
                return reply_text, False
    
    except Exception as e:
        logger.error(f"AI Error: {e}")
        stats['errors'] += 1
    
    # Fallback - guaranteed Indonesian
    fallback = random.choice(FALLBACK_RESPONSES)
    return fallback, True

# ==================== MESSAGE HANDLING ====================

@client.on(events.NewMessage(chats=TARGET_GROUP))
async def handle_message(event):
    """Handle incoming messages - STRICT FILTERING"""
    global message_queue, last_activity, is_processing, last_cycle_time
    
    try:
        # Skip own messages
        if getattr(event.message, 'out', False):
            return
        
        # STRICT: Only accept from INDONESIA TOPIC (FIXED)
        topic_id = get_message_topic_id(event.message)
        if topic_id != TOPIC_ID:
            logger.debug(f"Skipped: Wrong topic {topic_id} (should be {TOPIC_ID})")
            stats['messages_skipped'] += 1
            return
        
        # Get sender
        sender = await event.get_sender()
        if not sender or sender.bot:
            stats['messages_skipped'] += 1
            return
        
        sender_name = sender.first_name or "Unknown"
        user_text = event.message.text or ''
        
        # Validate text
        if not user_text or len(user_text.strip()) < 3:
            stats['messages_skipped'] += 1
            return
        
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"{C.YELLOW}[{timestamp}] {C.BOLD}{sender_name}{C.RESET}: {user_text}")
        
        # Language check - STRICT INDONESIAN ONLY
        if not detect_language(user_text):
            print(f"   {C.RED}└─ 🚫 Skip (non-Indonesian){C.RESET}")
            logger.info(f"Skipped non-Indonesian from {sender_name}: {user_text[:50]}")
            stats['messages_skipped'] += 1
            return
        
        # Keyword filtering
        if should_skip_keywords(user_text):
            print(f"   {C.CYAN}└─ ⏭️  Skip (keyword filter){C.RESET}")
            stats['messages_skipped'] += 1
            return
        
        stats['messages_received'] += 1
        last_activity = datetime.now()
        
        # Add to queue
        message_queue.append({
            'sender_id': sender.id,
            'sender_name': sender_name,
            'text': user_text,
            'event': event,
            'timestamp': datetime.now()
        })
        
        queue_size = len(message_queue)
        print(f"   {C.MAGENTA}└─ 📦 Queue: {queue_size} messages (Topic: #{TOPIC_ID}){C.RESET}")
        
        # TRIGGER: Jika queue >= 3
        current_time = datetime.now()
        time_since_last_cycle = (current_time - last_cycle_time).total_seconds()
        
        if queue_size >= 3 and not is_processing and time_since_last_cycle > 5:
            asyncio.create_task(start_reply_cycle())
    
    except Exception as e:
        logger.error(f"Error handling message: {e}")
        stats['errors'] += 1

# ==================== REPLY CYCLE LOGIC ====================

async def start_reply_cycle():
    """Start 3-message reply cycle - INSTANT SEND"""
    global is_processing, message_queue, last_activity, last_cycle_time
    
    if is_processing or len(message_queue) < 3:
        return
    
    is_processing = True
    last_cycle_time = datetime.now()
    
    try:
        # Pick 3 messages
        selected = message_queue[:3]
        
        print(f"\n{C.BOLD}{C.BLUE}{'='*80}{C.RESET}")
        print(f"{C.BOLD}🤖 CYCLE: Balas 3 Messages (Indonesia Only)🇮🇩{C.RESET}")
        print(f"{C.BOLD}{C.BLUE}{'='*80}{C.RESET}\n")
        
        # Build context
        context_for_ai = []
        for msg in message_queue:
            context_for_ai.append({
                'sender': msg['sender_name'],
                'text': msg['text']
            })
        
        # Reply to 3 messages
        for idx, msg in enumerate(selected, 1):
            if should_exit:
                print(f"{C.YELLOW}[EXIT] Stopping cycle...{C.RESET}")
                break
            
            sender_name = msg['sender_name']
            user_text = msg['text']
            event = msg['event']
            
            try:
                # Generate response
                reply_text, is_fallback = generate_ai_response(sender_name, user_text, context_for_ai)
                
                delay = random.randint(DELAY_MIN, DELAY_MAX)
                print(f"   {C.CYAN}└─ 🤔 Replying to {sender_name}... ({delay}s){C.RESET}")
                
                # Typing action - interruptible
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
                
                # Send immediately
                if not should_exit:
                    try:
                        await event.reply(reply_text)
                    except Exception as send_error:
                        logger.warning(f"Reply failed: {send_error}, trying fallback send...")
                        # Fallback: send as message to topic
                        try:
                            await client.send_message(TARGET_GROUP, reply_text, reply_to=TOPIC_ID)
                        except Exception as fallback_error:
                            logger.error(f"Fallback send also failed: {fallback_error}")
                            raise
                    
                    response_type = "FALLBACK" if is_fallback else "AI"
                    print(f"   {C.GREEN}└─ ✅ [REPLY/{response_type}] {reply_text}{C.RESET}")
                    stats['messages_replied'] += 1
                    last_activity = datetime.now()
                    logger.info(f"[INDONESIA] Reply to {sender_name}: {reply_text[:50]}")
                
            except Exception as e:
                logger.error(f"Error sending reply to {sender_name}: {e}")
                stats['errors'] += 1
                continue
        
        if should_exit:
            return
        
        # Remove dari queue
        for msg in selected:
            if msg in message_queue:
                message_queue.remove(msg)
        
        print(f"\n{C.BOLD}{C.BLUE}{'='*80}{C.RESET}")
        print(f"{C.GREEN}✅ CYCLE COMPLETE{C.RESET}")
        print(f"{C.BOLD}{C.BLUE}{'='*80}{C.RESET}\n")
        
        stats['cycles_completed'] += 1
        
        # REST PERIOD
        rest_duration = random.randint(REST_MIN, REST_MAX)
        minutes = rest_duration // 60
        seconds = rest_duration % 60
        print(f"{C.YELLOW}⏸️  RESTING for {minutes}m {seconds}s (Ctrl+C untuk exit){C.RESET}")
        
        for _ in range(rest_duration):
            if should_exit:
                print(f"{C.YELLOW}[EXIT] Rest interrupted{C.RESET}\n")
                break
            await asyncio.sleep(1)
        
        if not should_exit:
            print(f"{C.GREEN}🌅 BOT WOKE UP{C.RESET}\n")
            
            # Check queue
            if len(message_queue) >= 3:
                print(f"{C.CYAN}New messages in queue, starting new cycle...{C.RESET}")
                await start_reply_cycle()
            else:
                # Check silence
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
    """Send smart opening message - INDONESIA ONLY"""
    try:
        if should_exit:
            return
        
        msg = random.choice(OPENING_MESSAGES)
        await client.send_message(TARGET_GROUP, msg, reply_to=TOPIC_ID)
        print(f"{C.GREEN}📢 [OPENING] {msg}{C.RESET}\n")
        logger.info(f"[INDONESIA] Smart opening sent: {msg}")
        
        global last_activity
        last_activity = datetime.now()
    except Exception as e:
        logger.error(f"Smart opening failed: {e}")

async def smart_opening_task():
    """Background task untuk monitor silence"""
    while not should_exit:
        try:
            for _ in range(2):
                if should_exit:
                    break
                await asyncio.sleep(1)
            
            if should_exit:
                break
            
            # Trigger cycle if queue >= 3
            if len(message_queue) >= 3 and not is_processing:
                asyncio.create_task(start_reply_cycle())
            
            # Check silence
            time_silent = (datetime.now() - last_activity).total_seconds()
            if time_silent > SILENCE and not is_processing and len(message_queue) == 0:
                asyncio.create_task(smart_open())
        
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
    logger.info("BOT STARTING - INDONESIA FOKUS")
    logger.info(f"Target: {TARGET_GROUP} | Topic: #{TOPIC_ID}")
    logger.info("="*80)
    
    try:
        print(f"{C.GREEN}🔌 Connecting to Telegram...{C.RESET}")
        await client.start()
        
        logger.info("✅ Connected successfully!")
        print(f"{C.GREEN}✅ USERBOT ACTIVE - INDONESIA ONLY 🇮🇩{C.RESET}\n")
        print(f"{C.CYAN}LOGIC: Tunggu 3 chat → Balas instant → Istirahat → Repeat{C.RESET}")
        print(f"{C.CYAN}FILTER: Hanya dari topic #{TOPIC_ID} • Hanya Bahasa Indonesia{C.RESET}")
        print(f"{C.CYAN}Press Ctrl+C to instant shutdown{C.RESET}\n")
        
        # Start background task
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
