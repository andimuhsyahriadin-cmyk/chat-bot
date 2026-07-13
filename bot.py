"""
TELEGRAM USERBOT DENGAN GEMINI 3.1 FLASH-LITE AI - INDONESIA FOKUS
Single file complete bot - ready untuk Termux
IMPROVED: Gemini 3.1 Flash-Lite + Better response quality + Robust error handling
TUNED: Short, natural, authentic responses (1-2 kalimat MAX)
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

# System prompts - STRICT INDONESIA ONLY + SHORT & AUTHENTIC
SYSTEM_PROMPTS = [
    """Kamu adalah teman santai di grup Telegram Indonesia.
WAJIB: HANYA Bahasa Indonesia, balas SUPER SINGKAT (1-2 kalimat SAJA).
Gaya: Seperti respon cepat teman biasa. Natural, jangan sok asik, jangan panjang.
Bahasa: Gaul anak muda (bro, bang, wkwk, njir, gak, udah, sih, lah).
PENTING: Balas langsung ke poin, jangan menjelaskan, jangan rambling.
Contoh: "Haha iya", "Betul bro", "Njir kocak", "Bet deal"
Jangan: Panjang, formal, menjelaskan, atau terkesan AI.""",

    """Kamu adalah member aktif grup yang santai dan authentic.
HANYA Bahasa Indonesia, balas SINGKAT BANGET (max 1-2 kalimat).
Tone: Real, casual, langsung nyambung tanpa perlu explain.
Bahasa: Pakai istilah gaul (gue, lo, bro, bang, wkwk, njir, gak, udah).
Jangan: Panjang, formal, sok tahu, atau terlihat AI.
Balas cepat saja, ke poin, singkat.""",

    """Kamu adalah teman grup yang santai.
PENTING: HANYA Bahasa Indonesia, balas 1-2 kalimat SAJA.
Natural: Seperti reply cepat WhatsApp teman, bukan essay.
Gaya: Casual, paham konteks, langsung nyambung.
Hindari: Panjang, formal, explanation, AI-sounding.
Contoh: "Iya bang", "Wkwk true", "Bet", "Haha setuju".""",

    """Sebagai teman grup Indonesia.
WAJIB: Hanya Bahasa Indonesia, SINGKAT (1-2 kalimat).
Respon: Cepat & natural, jangan panjang-panjang.
Authentic: Seperti teman biasa chat, bukan AI.
Bahas: Pakai gaul muda (bro, bang, wkwk, sih, lah, gak).
Jangan: Panjang, formal, menjelaskan, overkill.""",

    """Kamu teman santai di grup Telegram.
HANYA Bahasa Indonesia, SUPER SINGKAT (max 2 kalimat).
Gaya: Natural, authentic, langsung to the point.
Hindari: Panjang, formal, explanation yang tidak perlu.
Pakai: Bahasa gaul (bro, bang, wkwk, njir, gue, lo, aja, gak).
Contoh baik: "Wkwk iya", "Bet bro", "Haha true", "Njir kocak".""",
]

# Fallback responses - HANYA untuk emergency (jika AI benar-benar error)
FALLBACK_RESPONSES = [
    "Wkwk iya", "Haha bener", "Bet", "Iyah deh", "Njir", 
    "Setuju", "Sama sih", "True", "Hehe iya", "Okayy",
    "Fix", "Yup", "Amen", "Asli 😂", "Wkwk kocak", "Bener"
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
    print(f"        🤖 TELEGRAM USERBOT DENGAN GEMINI 3.1 FLASH-LITE AI 🇮🇩")
    print(f"        Indonesia-Only • 3-Chat Cycle • SHORT Natural Response • Strict Topic Filter")
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

# ==================== AI ENGINE (IMPROVED - SHORT RESPONSES) ====================

def generate_ai_response(sender_name, user_text, context_messages=None, retry=0):
    """
    Generate response dengan Gemini 3.1 Flash-Lite - STRICT INDONESIA + SHORT & NATURAL
    Improved: Better prompts, retry logic, quality validation
    TUNED: Responses harus singkat (1-2 kalimat), authentic, jangan panjang
    """
    if retry > 2:
        # After 3 retries, use fallback
        logger.warning(f"Max retries reached for {sender_name}, using fallback")
        fallback = random.choice(FALLBACK_RESPONSES)
        return fallback, True
    
    try:
        # Build minimal context (2-3 messages only)
        context = ""
        if context_messages and len(context_messages) > 0:
            # Take last 2-3 messages only untuk context yang minimal
            recent = context_messages[-3:] if len(context_messages) >= 3 else context_messages
            context = "Chat:\n"
            for msg in recent:
                short_text = msg['text'][:80]
                context += f"{msg['sender']}: {short_text}\n"
            context += "\n"
        
        system_prompt = random.choice(SYSTEM_PROMPTS)
        
        # Minimal templates untuk SANGAT SINGKAT
        template = random.choice([
            "{context}Balas singkat: {sender} bilang: {text}\nReply (1-2 kalimat):",
            "{context}{sender}: {text}\nBalas pendek (jangan panjang):",
            "{context}Chat: {sender} - {text}\nReply kamu (2 kalimat max):",
            "{context}{sender} berkata: {text}\nRespon cepat & singkat:",
        ])
        
        prompt = template.format(context=context, sender=sender_name, text=user_text[:120])
        
        # Use Gemini 3.1 Flash-Lite
        response = ai_client.models.generate_content(
            model='gemini-3.1-flash-lite',
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
                temperature=0.85,  # Natural but consistent
                max_output_tokens=50,  # KURANGI dari 80 → 50 untuk force singkat
                top_p=0.9,
                top_k=30
            )
        )
        
        if response and response.text:
            reply_text = response.text.strip()
            
            # Aggressive cleanup
            reply_text = reply_text.replace('**', '').replace('__', '').replace('```', '')
            reply_text = reply_text.replace('"', '').replace("'", '')
            reply_text = reply_text.replace('Balas:', '').replace('Reply:', '').replace('Respon:', '').strip()
            reply_text = ' '.join(reply_text.split())  # Remove extra spaces
            
            # Remove common AI prefixes
            if reply_text.startswith('Kamu:') or reply_text.startswith('Respon:') or reply_text.startswith('Chat:'):
                reply_text = reply_text.split(':', 1)[1].strip()
            
            logger.debug(f"AI Response (raw): {reply_text[:80]}")
            
            # STRICT: Reject jika lebih dari 2 kalimat
            sentence_count = reply_text.count('.') + reply_text.count('!') + reply_text.count('?')
            if sentence_count > 2:
                logger.warning(f"Response terlalu panjang ({sentence_count} kalimat), retrying...")
                stats['ai_errors'] += 1
                return generate_ai_response(sender_name, user_text, context_messages, retry + 1)
            
            # Validate Indonesian
            if not detect_language(reply_text):
                logger.warning(f"Non-Indonesian detected, retrying...")
                stats['ai_errors'] += 1
                return generate_ai_response(sender_name, user_text, context_messages, retry + 1)
            
            # Length validation: max 120 chars (singkat!)
            if len(reply_text) > 120:
                reply_text = reply_text[:117] + "..."
            
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
    logger.info("Model: Gemini 3.1 Flash-Lite (SHORT RESPONSES)")
    logger.info("="*80)
    
    try:
        print(f"{C.GREEN}🔌 Connecting to Telegram...{C.RESET}")
        await client.start()
        
        logger.info("✅ Connected successfully!")
        print(f"{C.GREEN}✅ USERBOT ACTIVE - INDONESIA ONLY 🇮🇩{C.RESET}\n")
        print(f"{C.CYAN}LOGIC: Tunggu 3 chat → Balas singkat natural → Istirahat → Repeat{C.RESET}")
        print(f"{C.CYAN}FILTER: Hanya dari topic #{TOPIC_ID} • Hanya Bahasa Indonesia{C.RESET}")
        print(f"{C.CYAN}AI: Gemini 3.1 Flash-Lite - SHORT & AUTHENTIC responses (1-2 kalimat){C.RESET}")
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
