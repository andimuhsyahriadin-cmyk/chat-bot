"""
TELEGRAM USERBOT DENGAN GEMINI 3.1 AI - INDONESIA FOKUS
Single file complete bot - ready untuk Termux
IMPROVED: Gemini 3.1 Pro + Better response quality + Robust error handling
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

stats = {
    'messages_received': 0,
    'messages_replied': 0,
    'messages_skipped': 0,
    'cycles_completed': 0,
    'errors': 0,
    'ai_errors': 0,
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
    "Wkwk sepi nih, temen?",
    "Gaes ada update terbaru?",
]

# System prompts - STRICT INDONESIA ONLY + NATURAL
SYSTEM_PROMPTS = [
    """Kamu adalah teman gaul muda di grup chat Telegram Indonesia. 
WAJIB PENTING: HANYA balas dalam BAHASA INDONESIA yang casual, natural, dan spontan.
Gaya: Seperti ngobrol santai dengan teman sendiri. Pakai bahasa gaul muda (bro, bang, wkwk, njir, anjir, dll).
Respon: SINGKAT (1-3 kalimat max), langsung nyambung, paham konteks, ngga formal, pakai emoji sesekali.
Jangan: Bahasa Inggris, formal, panjang-panjang, robot-robot, atau terkesan AI.
Contoh baik: "Wkwk bener banget", "Njir kocak", "Haha bet, gue setuju", "Iyah deh broo"
Contoh buruk: "Ya, saya setuju", "Menurut saya itu benar", "Sangat menyenangkan".""",

    """Kamu adalah member aktif grup Telegram Indonesia yang fun, humor, dan natural.
PENTING: Balas HANYA dalam Bahasa Indonesia gaul, jangan bahasa lain apapun.
Suara: Santai, friendly, paham obrolan, bisa nyambung dengan baik.
Panjang: Max 1-3 kalimat, singkat tapi meaningful, emotional intelligence tinggi.
Gaya: Pakai bro/bang/mas, emoji, bahasa gaul muda (gak, udah, sih, lah, dong, dll).
Hindari: English, formal, panjang, membosankan, terlihat AI.""",

    """Kamu adalah teman baik di grup chat yang santai dan fun.
WAJIB: Jawab HANYA Bahasa Indonesia yang casual dan gaul.
Tone: Seurii teman curhat, humor, paham konteks, bisa bercanda.
Format: 1-2 kalimat, langsung poin, energik tapi santai.
Bahasa: Pakai istilah anak muda (wkwk, njir, bang, bro, gak, sih, lah).
Jangan: Bahasa Inggris, formal berlebihan, terlalu serius, atau jelas-jelas AI.""",

    """Sebagai anggota grup Telegram Indonesia yang akrab dan fun.
PENTING: Respon HANYA dalam Bahasa Indonesia yang natural & casual.
Gaya: Seperti teman dekat yang ngobrol santai, humor, paham mood.
Panjang: Singkat banget (1-3 kalimat), tapi kena banget, nyambung sempurna.
Bahasa: Gaul muda, pakai slang (wkwk, haha, njir, gue, lo, aja, udah, gak).
Jangan: Bahasa selain Indonesia, AI-sounding, formal, atau panjang-panjang.""",

    """Kamu adalah teman gaul di grup Indonesia yang memahami humor lokal.
WAJIB: Balas HANYA Bahasa Indonesia casual & fun, bukan bahasa lain.
Karakter: Santai, funny, bisa ngerti konteks, bisa bercanda.
Output: Maksimal 3 kalimat, langsung ke point, pakai emoji boleh.
Bahasa: Indonesian gaul muda (bro, bang, wkwk, njir, sih, lah, dong, gak).
Hindari: English, formal, panjang, AI-like, serius-serius.""",
]

# Fallback responses - HANYA untuk emergency (jika AI benar-benar error)
FALLBACK_RESPONSES = [
    "Wkwk iya", "Haha bener", "Bet broo", "Iyah deh", "Njir kocak", 
    "Setuju banget", "Sama sih", "True true", "Hehe iya", "Okayy",
    "Fix lah", "Noted", "Yup yup", "Amen", "Asli 😂", "Wkwk pas banget"
]

# ==================== LANGUAGE DETECTION ====================

def detect_language(text):
    """
    Detect if text is Indonesian (improved accuracy)
    Returns: True if Indonesian, False otherwise
    """
    # Indonesian keywords & common words
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
    
    # Count Indonesian words
    indo_count = sum(1 for word in words if any(indo_word in word.lower() for indo_word in indonesian_words))
    
    # If > 25% Indonesian words, likely Indonesian (lowered threshold)
    if len(words) > 0 and indo_count / len(words) > 0.25:
        return True
    
    # Check for Arabic/Persian script
    if any('\u0600' <= c <= '\u06FF' for c in text):
        return False
    
    # Check for Cyrillic (Russian, etc)
    if any('\u0400' <= c <= '\u04FF' for c in text):
        return False
    
    # Check for Chinese/Japanese/Korean
    if any('\u4E00' <= c <= '\u9FFF' for c in text):  # Chinese
        return False
    if any('\u3040' <= c <= '\u309F' for c in text):  # Japanese Hiragana
        return False
    if any('\u3400' <= c <= '\u4DBF' for c in text):  # CJK Extension A
        return False
    if any('\uAC00' <= c <= '\uD7AF' for c in text):  # Korean Hangul
        return False
    
    # If mostly Latin and reasonable length, assume Indonesian
    if len(words) >= 1:
        return True
    
    return True

# ==================== HELPER FUNCTIONS ====================

def print_banner():
    """Print bot banner"""
    print(f"\n{C.CYAN}{C.BOLD}" + "="*80)
    print(f"        🤖 TELEGRAM USERBOT DENGAN GEMINI 3.1 AI 🇮🇩")
    print(f"        Indonesia-Only • 3-Chat Cycle • Natural Response • Strict Topic Filter")
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
    print(f"{C.GREEN}🤖 AI Errors:{C.RESET} {stats['ai_errors']}")
    print(f"{C.GREEN}⚠️  Total Errors:{C.RESET} {stats['errors']}")
    print(f"{C.BOLD}{C.CYAN}{'='*80}{C.RESET}\n")

# ==================== TOPIC ID DETECTION ====================

def get_message_topic_id(message):
    """
    Extract topic ID from message correctly
    - For replies: use reply_to_top_id
    - For original messages in topic: use topic_id
    - Fallback to None if not in a topic
    """
    try:
        # For replies to messages in a topic
        if message.reply_to and hasattr(message.reply_to, 'reply_to_top_id'):
            return message.reply_to.reply_to_top_id
        
        # For original messages in a topic
        if hasattr(message, 'topic_id') and message.topic_id:
            return message.topic_id
        
        # Fallback: check forum_topic
        if hasattr(message, 'forum_topic') and message.forum_topic:
            return message.forum_topic
        
        return None
    
    except Exception as e:
        logger.debug(f"Error extracting topic_id: {e}")
        return None

# ==================== AI ENGINE (IMPROVED) ====================

def generate_ai_response(sender_name, user_text, context_messages=None, retry=0):
    """
    Generate response dengan Gemini 3.1 Pro - STRICT INDONESIA + NATURAL
    Improved: Better prompts, retry logic, quality validation
    """
    if retry > 2:
        # After 3 retries, use fallback
        logger.warning(f"Max retries reached for {sender_name}, using fallback")
        fallback = random.choice(FALLBACK_RESPONSES)
        return fallback, True
    
    try:
        # Build context
        context = ""
        if context_messages and len(context_messages) > 0:
            # Take last 3-5 messages for context
            recent = context_messages[-5:] if len(context_messages) >= 5 else context_messages
            context = "Obrolan sebelumnya:\n"
            for msg in recent:
                short_text = msg['text'][:100]
                context += f"• {msg['sender']}: {short_text}\n"
            context += "\n"
        
        system_prompt = random.choice(SYSTEM_PROMPTS)
        
        # Better templates untuk Gemini 3.1
        template = random.choice([
            "{context}Sekarang {sender} berkata: {text}\nBales singkat dan casual:",
            "{context}{sender}: {text}\nReply kamu (natural, singkat, 1-2 kalimat):",
            "{context}Temen ngobrol:\n{sender}: {text}\nKamu: (respon santai 1-2 kalimat)",
            "{context}Chat grup:\n{sender}: {text}\nBalas cepat seperti teman biasa:",
            "{context}Terbaru:\n{sender}: {text}\nRespon kamu (casual & natural):",
        ])
        
        prompt = template.format(context=context, sender=sender_name, text=user_text[:150])
        
        # Use Gemini 3.1 Pro (or Flash as fallback)
        response = ai_client.models.generate_content(
            model='gemini-3.1-pro-latest',  # Primary: Pro
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
                temperature=0.9,  # Lebih tinggi untuk natural
                max_output_tokens=80,  # Slightly more room for natural responses
                top_p=0.95,
                top_k=40
            )
        )
        
        if response and response.text:
            reply_text = response.text.strip()
            
            # Cleanup formatting
            reply_text = reply_text.replace('**', '').replace('__', '').replace('```', '')
            reply_text = reply_text.replace('"', '').replace("'", '')
            reply_text = reply_text.replace('Balas:', '').replace('Reply:', '').strip()
            reply_text = ' '.join(reply_text.split())  # Remove extra spaces
            
            # Remove common AI prefixes
            if reply_text.startswith('Kamu:') or reply_text.startswith('Respon:'):
                reply_text = reply_text.split(':', 1)[1].strip()
            
            logger.debug(f"AI Response (raw): {reply_text[:80]}")
            
            # Validate Indonesian
            if not detect_language(reply_text):
                logger.warning(f"Non-Indonesian detected, retrying...")
                stats['ai_errors'] += 1
                return generate_ai_response(sender_name, user_text, context_messages, retry + 1)
            
            # Length validation
            if len(reply_text) > 200:
                reply_text = reply_text[:197] + "..."
            
            # Quality check: not too short, not empty
            if reply_text and len(reply_text.strip()) > 2:
                logger.debug(f"✅ Valid response: {reply_text[:60]}")
                return reply_text, False
            else:
                logger.warning(f"Response too short, retrying...")
                stats['ai_errors'] += 1
                return generate_ai_response(sender_name, user_text, context_messages, retry + 1)
    
    except Exception as e:
        error_msg = str(e)
        logger.error(f"AI Error (attempt {retry + 1}): {error_msg[:100]}")
        
        # Retry if it's a transient error
        if '500' in error_msg or '503' in error_msg or 'timeout' in error_msg.lower():
            logger.info(f"Transient error, retrying...")
            time.sleep(2)  # Wait before retry
            stats['ai_errors'] += 1
            return generate_ai_response(sender_name, user_text, context_messages, retry + 1)
        
        stats['errors'] += 1
        stats['ai_errors'] += 1
    
    # Final fallback
    logger.warning(f"AI generation failed after retries, using fallback")
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
        
        # STRICT: Only accept from INDONESIA TOPIC
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
        
        # Build context from entire queue
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
                # Generate response with retry logic
                reply_text, is_fallback = generate_ai_response(sender_name, user_text, context_for_ai)
                
                delay = random.randint(DELAY_MIN, DELAY_MAX)
                response_type = "FALLBACK" if is_fallback else "AI"
                print(f"   {C.CYAN}└─ 🤔 Replying to {sender_name}... ({delay}s typing){C.RESET}")
                
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
                        logger.warning(f"Reply failed: {send_error}, trying fallback...")
                        try:
                            await client.send_message(TARGET_GROUP, reply_text, reply_to=TOPIC_ID)
                        except Exception as fallback_error:
                            logger.error(f"Fallback send failed: {fallback_error}")
                            raise
                    
                    print(f"   {C.GREEN}└─ ✅ [REPLY/{response_type}] {reply_text}{C.RESET}")
                    stats['messages_replied'] += 1
                    last_activity = datetime.now()
                    logger.info(f"[INDONESIA] Reply to {sender_name}: {reply_text[:70]}")
                
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
    logger.info("Model: Gemini 3.1 Pro Latest")
    logger.info("="*80)
    
    try:
        print(f"{C.GREEN}🔌 Connecting to Telegram...{C.RESET}")
        await client.start()
        
        logger.info("✅ Connected successfully!")
        print(f"{C.GREEN}✅ USERBOT ACTIVE - INDONESIA ONLY 🇮🇩{C.RESET}\n")
        print(f"{C.CYAN}LOGIC: Tunggu 3 chat → Balas natural → Istirahat → Repeat{C.RESET}")
        print(f"{C.CYAN}FILTER: Hanya dari topic #{TOPIC_ID} • Hanya Bahasa Indonesia{C.RESET}")
        print(f"{C.CYAN}AI: Gemini 3.1 Pro dengan natural response{C.RESET}")
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
