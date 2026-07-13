"""
TELEGRAM USERBOT DENGAN GEMINI 3.1 FLASH-LITE AI - INDONESIA FOKUS
Single file complete bot - ready untuk Termux
IMPROVED: Ultra SHORT responses (2-3 kata) + Self-initiated chat + Strict filtering
"""

import asyncio
import random
import signal
import sys
import os
import logging
import time
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
last_self_chat_time = datetime.now()

stats = {
    'messages_received': 0,
    'messages_replied': 0,
    'messages_skipped': 0,
    'self_chats': 0,
    'cycles_completed': 0,
    'errors': 0,
    'ai_errors': 0,
    'start_time': datetime.now()
}

# Skip keywords
SKIP_KEYWORDS = ['admin', 'moderator', 'warning', '[bot]', 'report', 'spam', 'banned', 'kick', 'mute']

# Ultra short opening messages (2-3 kata) - STRICT BAHASA INDONESIA
OPENING_MESSAGES = [
    "Woi sepi banget",
    "Gimana kabar bro?",
    "Ada yang seru?",
    "Gas ngobrol",
    "Ayo dong lanjut",
    "Siapa punya ide?",
    "Cerita donk temen",
    "Gas lah bro",
    "Wkwk sepi nih",
    "Update donk gaes",
    "Apa kabar semua?",
    "Ada berita gak?",
]

# Ultra short responses (2-3 kata SAJA!)
ULTRA_SHORT_RESPONSES = [
    "Haha iya", "Wkwk bener", "Bet bro", "Iyah deh", "Njir kocak",
    "Setuju banget", "Sama sih", "True true", "Hehe iya", "Okayy",
    "Fix lah", "Yup yup", "Amen", "Asli kocak", "Wkwk pas", "Bener bro",
    "Haha ngakak", "Wkwk iya", "Gila banget", "Gokil bro", "Njir parah",
    "Anjirrr", "Aduh bro", "Parah ini", "Keren banget", "Srek wkwk",
]

# System prompts - FORCE ULTRA SHORT (2-3 KATA)
SYSTEM_PROMPTS = [
    """Kamu adalah teman grup Indonesia yang sangat santai.
WAJIB: HANYA Bahasa Indonesia, balas ULTRA SINGKAT (2-3 KATA SAJA).
Gaya: Seperti respon cepat WhatsApp, super natural, jangan panjang.
Bahasa: Gaul padat (bro, bang, wkwk, njir, bet, iya, bener, yup).
PENTING: Maksimal 2-3 kata, langsung poin, no explanation, authentic.
Contoh BAIK: "Haha iya", "Bet bro", "Wkwk kocak", "Iyah deh"
Contoh BURUK: "Saya setuju", "Itu benar", "Sangat lucu", "Menurut saya".""",

    """Kamu member grup yang super chill.
HANYA Bahasa Indonesia, MAKSIMAL 3 KATA.
Style: Pendek, natural, casual, jangan formal sama sekali.
Kata: Pakai slang (bro, bang, iya, bener, wkwk, njir, gak, bet).
WAJIB: 2-3 kata saja, langsung, authentic, no AI-sounding.""",

    """Teman grup Indonesia yang santai banget.
PENTING: HANYA Bahasa Indonesia, 2-3 KATA MAKSIMAL.
Natural: Seperti chat WhatsApp biasa temen, super singkat.
Gaya: Casual, paham konteks, authentic, jangan panjang.
Hindari: Formal, panjang, explanation, AI-like.""",

    """Member aktif grup yang natural.
HANYA Bahasa Indonesia, SUPER SINGKAT (max 3 kata).
Respon: Cepat, natural, authentic, langsung to the point.
Bahasa: Gaul muda (bro, bang, iya, wkwk, bet, njir, amen).
Jangan: Panjang, formal, explanation, terlihat AI.""",

    """Teman santai di grup.
WAJIB: Bahasa Indonesia, 2-3 KATA SAJA.
Gaya: Super natural, authentic, casual, jangan overthink.
Contoh: "Haha iya", "Wkwk bener", "Bet", "Iyah", "Njir"
Jangan: Panjang, formal, AI-sounding, explanation.""",
]

# ==================== LANGUAGE DETECTION ====================

def detect_language(text):
    """Detect if text is Indonesian"""
    indonesian_words = [
        'apa', 'siapa', 'dimana', 'kapan', 'bagaimana', 'kenapa', 'berapa',
        'ya', 'yah', 'yaudah', 'lah', 'dong', 'sih', 'kali', 'nih', 'tuh',
        'ini', 'itu', 'saya', 'kamu', 'dia', 'kami', 'kalian', 'kita',
        'dan', 'atau', 'tapi', 'bukan', 'juga', 'pun', 'kalau', 'kalo',
        'di', 'ke', 'dari', 'untuk', 'sama', 'ada', 'tidak', 'jadi', 'dulu',
        'bro', 'mas', 'bang', 'kak', 'dek', 'om', 'mbak', 'pak', 'ibu', 'ente',
        'aja', 'udah', 'gak', 'ga', 'ngga', 'nggak', 'enggak', 'gakk',
        'gimana', 'gini', 'gitu', 'cuman', 'wkwk', 'haha', 'hehe', 'njir',
        'be', 'bet', 'lo', 'gue', 'elu', 'klo', 'yang', 'sih', 'kok', 'soal'
    ]
    
    text_lower = text.lower()
    words = text_lower.split()
    
    indo_count = sum(1 for word in words if any(indo_word in word.lower() for indo_word in indonesian_words))
    
    if len(words) > 0 and indo_count / len(words) > 0.25:
        return True
    
    if any('\u0600' <= c <= '\u06FF' for c in text) or any('\u0400' <= c <= '\u04FF' for c in text):
        return False
    if any('\u4E00' <= c <= '\u9FFF' for c in text) or any('\u3040' <= c <= '\u309F' for c in text):
        return False
    if any('\uAC00' <= c <= '\uD7AF' for c in text):
        return False
    
    return True

# ==================== HELPER FUNCTIONS ====================

def print_banner():
    """Print bot banner"""
    print(f"\n{C.CYAN}{C.BOLD}" + "="*80)
    print(f"        🤖 TELEGRAM USERBOT DENGAN GEMINI 3.1 FLASH-LITE AI 🇮🇩")
    print(f"        ULTRA SHORT (2-3 KATA) • Self-Chat • Indonesia-Only • Strict Filter")
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

def count_words(text):
    """Count words in text"""
    return len(text.split())

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
    print(f"{C.GREEN}💬 Self Chats:{C.RESET} {stats['self_chats']}")
    print(f"{C.GREEN}🚫 Messages Skipped:{C.RESET} {skipped}")
    print(f"{C.GREEN}⏸️  Reply Rate:{C.RESET} {rate:.1f}%")
    print(f"{C.GREEN}🔄 Cycles Completed:{C.RESET} {stats['cycles_completed']}")
    print(f"{C.GREEN}🤖 AI Errors:{C.RESET} {stats['ai_errors']}")
    print(f"{C.GREEN}⚠️  Total Errors:{C.RESET} {stats['errors']}")
    print(f"{C.BOLD}{C.CYAN}{'='*80}{C.RESET}\n")

# ==================== TOPIC ID DETECTION ====================

def get_message_topic_id(message):
    """Extract topic ID from message correctly"""
    try:
        if message.reply_to and hasattr(message.reply_to, 'reply_to_top_id'):
            return message.reply_to.reply_to_top_id
        
        if hasattr(message, 'topic_id') and message.topic_id:
            return message.topic_id
        
        if hasattr(message, 'forum_topic') and message.forum_topic:
            return message.forum_topic
        
        return None
    
    except Exception as e:
        logger.debug(f"Error extracting topic_id: {e}")
        return None

# ==================== AI ENGINE (ULTRA SHORT) ====================

def generate_ai_response(sender_name, user_text, context_messages=None, retry=0):
    """
    Generate ULTRA SHORT response (2-3 kata SAJA)
    """
    if retry > 2:
        fallback = random.choice(ULTRA_SHORT_RESPONSES)
        return fallback, True
    
    try:
        # Minimal context
        context = ""
        if context_messages and len(context_messages) > 0:
            recent = context_messages[-2:] if len(context_messages) >= 2 else context_messages
            context = "Chat:\n"
            for msg in recent:
                short_text = msg['text'][:60]
                context += f"{msg['sender']}: {short_text}\n"
            context += "\n"
        
        system_prompt = random.choice(SYSTEM_PROMPTS)
        
        # Force ultra short templates
        template = random.choice([
            "{context}{sender}: {text}\nBalas (2-3 kata max):",
            "{context}Balas singkat:\n{sender}: {text}",
            "{context}{sender} bilang: {text}\nReply cepat (3 kata):",
        ])
        
        prompt = template.format(context=context, sender=sender_name, text=user_text[:100])
        
        response = ai_client.models.generate_content(
            model='gemini-3.1-flash-lite',
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
                temperature=0.8,
                max_output_tokens=30,  # SUPER PENDEK (dari 50 → 30)
                top_p=0.85,
                top_k=20
            )
        )
        
        if response and response.text:
            reply_text = response.text.strip()
            
            # Aggressive cleanup
            reply_text = reply_text.replace('**', '').replace('__', '').replace('```', '')
            reply_text = reply_text.replace('"', '').replace("'", '').replace('Balas:', '').strip()
            reply_text = ' '.join(reply_text.split())
            
            if reply_text.startswith('Kamu:') or reply_text.startswith('Respon:') or reply_text.startswith('Chat:'):
                reply_text = reply_text.split(':', 1)[1].strip()
            
            logger.debug(f"AI Response: {reply_text[:60]}")
            
            # STRICT VALIDATION: max 5 kata (2-3 preferred)
            word_count = count_words(reply_text)
            if word_count > 5:
                logger.warning(f"Response terlalu panjang ({word_count} kata), retrying...")
                stats['ai_errors'] += 1
                return generate_ai_response(sender_name, user_text, context_messages, retry + 1)
            
            # Validate Indonesian
            if not detect_language(reply_text):
                logger.warning(f"Non-Indonesian detected, retrying...")
                stats['ai_errors'] += 1
                return generate_ai_response(sender_name, user_text, context_messages, retry + 1)
            
            # Length: max 50 chars (sangat singkat)
            if len(reply_text) > 50:
                reply_text = reply_text[:47] + "..."
            
            if reply_text and len(reply_text.strip()) > 1:
                logger.debug(f"✅ Valid: {reply_text}")
                return reply_text, False
            else:
                stats['ai_errors'] += 1
                return generate_ai_response(sender_name, user_text, context_messages, retry + 1)
    
    except Exception as e:
        error_msg = str(e)
        logger.error(f"AI Error (attempt {retry + 1}): {error_msg[:100]}")
        
        if '500' in error_msg or '503' in error_msg or 'timeout' in error_msg.lower():
            logger.info(f"Transient error, retrying...")
            time.sleep(2)
            stats['ai_errors'] += 1
            return generate_ai_response(sender_name, user_text, context_messages, retry + 1)
        
        stats['errors'] += 1
        stats['ai_errors'] += 1
    
    # Final fallback
    logger.warning(f"AI generation failed after retries, using fallback")
    fallback = random.choice(ULTRA_SHORT_RESPONSES)
    return fallback, True

# ==================== MESSAGE HANDLING ====================

@client.on(events.NewMessage(chats=TARGET_GROUP))
async def handle_message(event):
    """Handle incoming messages - STRICT FILTERING"""
    global message_queue, last_activity, is_processing, last_cycle_time
    
    try:
        if getattr(event.message, 'out', False):
            return
        
        topic_id = get_message_topic_id(event.message)
        if topic_id != TOPIC_ID:
            logger.debug(f"Skipped: Wrong topic {topic_id} (should be {TOPIC_ID})")
            stats['messages_skipped'] += 1
            return
        
        sender = await event.get_sender()
        if not sender or sender.bot:
            stats['messages_skipped'] += 1
            return
        
        sender_name = sender.first_name or "Unknown"
        user_text = event.message.text or ''
        
        if not user_text or len(user_text.strip()) < 3:
            stats['messages_skipped'] += 1
            return
        
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"{C.YELLOW}[{timestamp}] {C.BOLD}{sender_name}{C.RESET}: {user_text}")
        
        if not detect_language(user_text):
            print(f"   {C.RED}└─ 🚫 Skip (non-Indonesian){C.RESET}")
            logger.info(f"Skipped non-Indonesian from {sender_name}: {user_text[:50]}")
            stats['messages_skipped'] += 1
            return
        
        if should_skip_keywords(user_text):
            print(f"   {C.CYAN}└─ ⏭️  Skip (keyword filter){C.RESET}")
            stats['messages_skipped'] += 1
            return
        
        stats['messages_received'] += 1
        last_activity = datetime.now()
        
        message_queue.append({
            'sender_id': sender.id,
            'sender_name': sender_name,
            'text': user_text,
            'event': event,
            'timestamp': datetime.now()
        })
        
        queue_size = len(message_queue)
        print(f"   {C.MAGENTA}└─ 📦 Queue: {queue_size} messages (Topic: #{TOPIC_ID}){C.RESET}")
        
        current_time = datetime.now()
        time_since_last_cycle = (current_time - last_cycle_time).total_seconds()
        
        if queue_size >= 3 and not is_processing and time_since_last_cycle > 5:
            asyncio.create_task(start_reply_cycle())
    
    except Exception as e:
        logger.error(f"Error handling message: {e}")
        stats['errors'] += 1

# ==================== REPLY CYCLE LOGIC ====================

async def start_reply_cycle():
    """Start 3-message reply cycle"""
    global is_processing, message_queue, last_activity, last_cycle_time
    
    if is_processing or len(message_queue) < 3:
        return
    
    is_processing = True
    last_cycle_time = datetime.now()
    
    try:
        selected = message_queue[:3]
        
        print(f"\n{C.BOLD}{C.BLUE}{'='*80}{C.RESET}")
        print(f"{C.BOLD}🤖 CYCLE: Balas 3 Messages (ULTRA SHORT)🇮🇩{C.RESET}")
        print(f"{C.BOLD}{C.BLUE}{'='*80}{C.RESET}\n")
        
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
                reply_text, is_fallback = generate_ai_response(sender_name, user_text, context_for_ai)
                
                delay = random.randint(DELAY_MIN, DELAY_MAX)
                response_type = "FALLBACK" if is_fallback else "AI"
                print(f"   {C.CYAN}└─ 🤔 Replying to {sender_name}... ({delay}s typing){C.RESET}")
                
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
                    try:
                        await event.reply(reply_text)
                    except Exception as send_error:
                        logger.warning(f"Reply failed: {send_error}, trying fallback...")
                        try:
                            await client.send_message(TARGET_GROUP, reply_text, reply_to=TOPIC_ID)
                        except Exception as fallback_error:
                            logger.error(f"Fallback send failed: {fallback_error}")
                            raise
                    
                    print(f"   {C.GREEN}└─ ✅ [REPLY/{response_type}] {reply_text}{C.RESET}")
                    stats['messages_replied'] += 1
                    last_activity = datetime.now()
                    logger.info(f"[INDONESIA] Reply to {sender_name}: {reply_text}")
            
            except Exception as e:
                logger.error(f"Error sending reply to {sender_name}: {e}")
                stats['errors'] += 1
                continue
        
        if should_exit:
            return
        
        for msg in selected:
            if msg in message_queue:
                message_queue.remove(msg)
        
        print(f"\n{C.BOLD}{C.BLUE}{'='*80}{C.RESET}")
        print(f"{C.GREEN}✅ CYCLE COMPLETE{C.RESET}")
        print(f"{C.BOLD}{C.BLUE}{'='*80}{C.RESET}\n")
        
        stats['cycles_completed'] += 1
        
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
            
            if len(message_queue) >= 3:
                print(f"{C.CYAN}New messages in queue, starting new cycle...{C.RESET}")
                await start_reply_cycle()
            else:
                time_silent = (datetime.now() - last_activity).total_seconds()
                if time_silent > SILENCE:
                    print(f"{C.YELLOW}[SMART OPEN] Sepi {int(time_silent)}s, buka obrolan...{C.RESET}")
                    await smart_open()
    
    except Exception as e:
        logger.error(f"Error in reply cycle: {e}")
        stats['errors'] += 1
    
    finally:
        is_processing = False

# ==================== SMART OPENING + SELF CHAT ====================

async def smart_open():
    """Send ultra short opening message (2-3 kata)"""
    try:
        if should_exit:
            return
        
        msg = random.choice(OPENING_MESSAGES)
        await client.send_message(TARGET_GROUP, msg, reply_to=TOPIC_ID)
        print(f"{C.GREEN}📢 [SELF-CHAT] {msg}{C.RESET}\n")
        logger.info(f"[SELF-CHAT] Sent: {msg}")
        
        global last_activity, last_self_chat_time
        last_activity = datetime.now()
        last_self_chat_time = datetime.now()
        stats['self_chats'] += 1
    except Exception as e:
        logger.error(f"Self chat failed: {e}")

async def smart_opening_task():
    """Background task untuk monitor silence + self-chat"""
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
            
            # Check silence and maybe self-chat
            time_silent = (datetime.now() - last_activity).total_seconds()
            if time_silent > SILENCE and not is_processing and len(message_queue) == 0:
                asyncio.create_task(smart_open())
        
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"Task error: {e}")

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
    logger.info("Model: Gemini 3.1 Flash-Lite (ULTRA SHORT 2-3 KATA)")
    logger.info("="*80)
    
    try:
        print(f"{C.GREEN}🔌 Connecting to Telegram...{C.RESET}")
        await client.start()
        
        logger.info("✅ Connected successfully!")
        print(f"{C.GREEN}✅ USERBOT ACTIVE - INDONESIA ONLY 🇮🇩{C.RESET}\n")
        print(f"{C.CYAN}LOGIC: Tunggu 3 chat → Balas ultra short → Istirahat → Repeat{C.RESET}")
        print(f"{C.CYAN}FILTER: Hanya dari topic #{TOPIC_ID} • Hanya Bahasa Indonesia{C.RESET}")
        print(f"{C.CYAN}AI: Gemini 3.1 Flash-Lite - ULTRA SHORT responses (2-3 kata){C.RESET}")
        print(f"{C.CYAN}SELF-CHAT: Auto kirim pesan jika sepi 60+ detik{C.RESET}")
        print(f"{C.CYAN}Press Ctrl+C to instant shutdown{C.RESET}\n")
        
        smart_task = asyncio.create_task(smart_opening_task())
        
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
