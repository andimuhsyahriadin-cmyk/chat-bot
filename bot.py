"""
TELEGRAM USERBOT DENGAN GEMINI 3.1 FLASH-LITE AI - INDONESIA FOKUS
Single file complete bot - ready untuk Termux
IMPROVED: Ultra SHORT responses (2-3 kata) + Context Aware + Diverse Responses
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

# Bot behavior
DELAY_MIN = 15
DELAY_MAX = 30
REST_MIN = 110
REST_MAX = 130
SILENCE = 60

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
message_queue = []
last_activity = datetime.now()
should_exit = False
is_processing = False
last_cycle_time = datetime.now()

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

# ==================== DIVERSE RESPONSE LIBRARY ====================

# Opening messages - diversified (2-3 kata)
OPENING_MESSAGES = [
    "Woi sepi banget", "Gimana kabar bro?", "Ada yang seru?", "Gas ngobrol",
    "Ayo dong lanjut", "Siapa punya ide?", "Cerita donk temen", "Gas lah bro",
    "Wkwk sepi nih", "Update donk gaes", "Apa kabar semua?", "Ada berita gak?",
    "Halo semua", "Apa yang baru?", "Sedang apa?", "Yuk chat santai",
]

# DIVERSIFIED RESPONSE POOL - berbagai tipe jawaban alami (2-3 kata)
AGREEMENT_RESPONSES = [
    "Haha iya", "Wkwk bener", "Bet bro", "Iyah deh", "Setuju banget",
    "Sama sih", "True true", "Hehe iya", "Okayy bro", "Bener banget",
    "Amin", "Yesss bro", "Indeed bro", "Bener", "Setuju", "Iya kok",
    "Totally agree", "Bener kok", "Sip sip", "Yep yep", "Mantul", "Beneran",
]

HUMOROUS_RESPONSES = [
    "Njir kocak", "Wkwk gila", "Gila banget", "Kocak parah", "Njir parah",
    "Lucu banget", "Gokil bro", "Srek wkwk", "Anjirrr", "Gawkwk", "Kaco bro",
    "Ngakak bro", "Wkwk ngakak", "Haha ngakak", "Parah ini", "Aduh bro",
    "Wkwk asli", "Gila asli", "Lucu gila", "Parah bener", "Haha asli",
]

SURPRISED_RESPONSES = [
    "Waduh bro", "Asli gak?", "Beneran nih?", "Serius bro?", "Asli gaes?",
    "Kok bisa?", "Gimana ini?", "Waduh", "Wah wah", "Astaga", "Mampus bro",
    "Sumpah bro?", "Jadi gini?", "Apa nih?", "Enak aja", "Yakin kah?",
]

SUPPORTIVE_RESPONSES = [
    "Kuat bro", "Semangat", "Bisa kok", "Yakin bisa", "Go go", "Push terus",
    "Gasss", "Ayuuu", "Kamu bisa", "Lancar bro", "Sehat selalu", "Mantap",
    "Sukses bro", "Hebat bro", "Keren deh", "Gampang kok", "Bisa donk",
]

CURIOUS_RESPONSES = [
    "Apa sih?", "Gimana?", "Siapa itu?", "Kapan tuh?", "Mana nih?", "Kenapa?",
    "Cerita dong", "Lanjut", "Terus apa?", "Trus?", "Yang mana?", "Siapa nih?",
    "Pakai apa?", "Berapa?", "Dimana?", "Bagaimana?", "Info dong", "Kasih tau",
]

REJECTION_RESPONSES = [
    "Gak deh", "Nah gak", "Nope bro", "Jangan bro", "Lainnya", "Gak jadi",
    "Skip aja", "Ngilir", "Gawl", "Nggak kuat", "Malas bro", "Nanti deh",
    "Gak bisa", "Gak tahu", "Gak suka", "Nope nope", "Lahhh", "Enggak",
]

# VERY DIVERSE CONTEXT-AWARE SYSTEM PROMPTS
SYSTEM_PROMPTS = [
    """Kamu adalah teman grup Indonesia yang natural, gaul, dan responsive.
PENTING: Balas HANYA Bahasa Indonesia dengan 2-3 KATA SAJA.
JENIS JAWABAN: Sesuaikan dengan topik pesan - jangan selalu "gas ngobrol" / "gas poll"
- Jika agreement → Gunakan: "Haha iya", "Bener banget", "Setuju"
- Jika humor → Gunakan: "Njir kocak", "Wkwk gila", "Gokil bro"
- Jika surprise → Gunakan: "Asli gak?", "Waduh bro", "Kok bisa?"
- Jika curious → Gunakan: "Cerita dong", "Trus apa?", "Gimana nih?"
- Jika support → Gunakan: "Semangat bro", "Kuat deh", "Sukses kamu"
HINDARI: Selalu "gas ngobrol", monoton jawaban, no rambling.""",

    """Kamu member grup yang super responsive dan natural.
WAJIB: Bahasa Indonesia, 2-3 KATA MAKSIMAL, DIVERSE jawaban.
BACA KONTEKS: Jangan asal balas, pahami maksud pesan user dulu
- User setuju? → Agree: "Iyah", "Bener", "Sama"
- User cerita lucu? → Humor: "Wkwk", "Njir", "Hahaha"
- User tanya? → Question: "Apa sih?", "Gimana?", "Siapa?"
- User share motivasi? → Support: "Semangat", "Kuat", "Pasti bisa"
JANGAN MONOTON! Variasikan jawaban, jangan selalu "gas".""",

    """Teman grup yang flair, punya personality, responsif.
HANYA Bahasa Indonesia, 2-3 KATA SAJA, CONTEXT AWARE.
STRATEGI JAWAB:
1. Baca konteks pesan (jangan langsung balas)
2. Sesuaikan tone dengan pesan (tidak selalu "gas")
3. Variasikan jawaban (50+ pilihan jawaban berbeda)
4. Natural dan authentic (seperti teman biasa)
CONTOH BURUK: "gas ngobrol" "gas poll" (monoton!)
CONTOH BAGUS: Varies by context - "Bener", "Wkwk", "Gimana?", "Semangat".""",

    """Member grup super responsive dan natural banget.
WAJIB: Bahasa Indonesia, 2-3 KATA, DIVERSIFIED RESPONSE.
RULE PENTING:
- JANGAN MONOTON! Tidak boleh selalu "gas ngobrol"
- BACA PESAN dulu sebelum balas
- SESUAIKAN TONE dengan konteks
- VARIASIKAN JAWABAN dari berbagai kategori
Tone mapping:
  * Setuju → Agreement pool
  * Lucu → Humor pool
  * Heran → Surprised pool
  * Penasaran → Curious pool
  * Semangat → Support pool
HASILNYA: Natural, diverse, no repetition.""",

    """Teman grup yang punya taste, personality, responsive.
HANYA Bahasa Indonesia, MAX 3 KATA, AWARE OF CONTEXT.
JANGAN: Monoton "gas" terus
HARUS: Variasi tone sesuai pesan user
- Pesan positif → Agree/Support: "Iya", "Semangat", "Mantap"
- Pesan lucu → Humor: "Wkwk", "Kocak", "Ngakak"
- Pesan tanya → Curious: "Apa?", "Gimana?", "Cerita"
- Pesan shocking → Surprise: "Asli?", "Waduh", "Kok bisa?"
HASIL: Terasa real, natural, gaul tapi smart.""",
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

# ==================== CONTEXT DETECTION ====================

def detect_message_type(text):
    """Detect type of message to response appropriately"""
    text_lower = text.lower()
    
    # Question detection
    if any(q in text_lower for q in ['?', 'apa', 'siapa', 'gimana', 'kapan', 'dimana', 'kenapa', 'berapa', 'bagaimana']):
        return 'question'
    
    # Positive/agreement detection
    if any(p in text_lower for p in ['iya', 'bener', 'setuju', 'agree', 'yes', 'yup', 'betul', 'benar', 'ok', 'oke']):
        return 'agreement'
    
    # Humor/joke detection
    if any(h in text_lower for h in ['haha', 'wkwk', 'hehe', 'lol', 'kocak', 'lucu', 'ngakak', 'gila', 'gokil', 'keren', 'srek']):
        return 'humor'
    
    # Surprise detection
    if any(s in text_lower for s in ['!', 'waduh', 'wah', 'asli', 'kok bisa', 'gimana', 'astaga', 'gila', 'mampus', 'apa nih']):
        return 'surprise'
    
    # Negative/rejection
    if any(n in text_lower for n in ['gak', 'tidak', 'nah', 'jangan', 'no', 'nope', 'enggak']):
        return 'rejection'
    
    # Support/motivation
    if any(s in text_lower for s in ['semangat', 'gasss', 'yuk', 'ayoo', 'push', 'kuat', 'go', 'susah', 'berat']):
        return 'support'
    
    return 'neutral'

# ==================== RESPONSE SELECTOR ====================

def select_diverse_response(message_type):
    """Select response based on message type - DIVERSE!"""
    type_map = {
        'question': CURIOUS_RESPONSES,
        'agreement': AGREEMENT_RESPONSES,
        'humor': HUMOROUS_RESPONSES,
        'surprise': SURPRISED_RESPONSES,
        'rejection': REJECTION_RESPONSES,
        'support': SUPPORTIVE_RESPONSES,
        'neutral': AGREEMENT_RESPONSES + HUMOROUS_RESPONSES + CURIOUS_RESPONSES,  # Mix all
    }
    
    pool = type_map.get(message_type, AGREEMENT_RESPONSES)
    return random.choice(pool)

# ==================== HELPER FUNCTIONS ====================

def print_banner():
    """Print bot banner"""
    print(f"\n{C.CYAN}{C.BOLD}" + "="*80)
    print(f"        🤖 TELEGRAM USERBOT DENGAN GEMINI 3.1 FLASH-LITE AI 🇮🇩")
    print(f"        DIVERSE RESPONSES • Context Aware • 2-3 KATA • Indonesia-Only")
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

# ==================== AI ENGINE (DIVERSE + CONTEXT AWARE) ====================

def generate_ai_response(sender_name, user_text, context_messages=None, retry=0):
    """
    Generate DIVERSE response (2-3 kata) dengan context awareness
    """
    if retry > 2:
        # Fallback dengan diversification
        msg_type = detect_message_type(user_text)
        fallback = select_diverse_response(msg_type)
        return fallback, True
    
    try:
        # Detect message type untuk better context
        msg_type = detect_message_type(user_text)
        
        # Build minimal context
        context = ""
        if context_messages and len(context_messages) > 0:
            recent = context_messages[-2:] if len(context_messages) >= 2 else context_messages
            context = "Chat:\n"
            for msg in recent:
                short_text = msg['text'][:60]
                context += f"{msg['sender']}: {short_text}\n"
            context += "\n"
        
        system_prompt = random.choice(SYSTEM_PROMPTS)
        
        # Context-aware template
        type_hint = f"(Tipe: {msg_type})"
        template = random.choice([
            "{context}{sender}: {text}\n{hint}\nBalas 2-3 kata varied:",
            "{context}Balas natural:\n{sender}: {text}\n{hint}",
            "{context}{sender} berkata: {text}\n{hint}\nReply cepat:",
        ])
        
        prompt = template.format(context=context, sender=sender_name, text=user_text[:100], hint=type_hint)
        
        response = ai_client.models.generate_content(
            model='gemini-3.1-flash-lite',
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
                temperature=0.95,  # Higher untuk diversity
                max_output_tokens=30,
                top_p=0.9,
                top_k=25
            )
        )
        
        if response and response.text:
            reply_text = response.text.strip()
            
            # Cleanup
            reply_text = reply_text.replace('**', '').replace('__', '').replace('```', '')
            reply_text = reply_text.replace('"', '').replace("'", '').replace('Balas:', '').strip()
            reply_text = ' '.join(reply_text.split())
            
            if reply_text.startswith('Kamu:') or reply_text.startswith('Respon:'):
                reply_text = reply_text.split(':', 1)[1].strip()
            
            logger.debug(f"AI Response [{msg_type}]: {reply_text[:60]}")
            
            # STRICT validation
            word_count = count_words(reply_text)
            if word_count > 5 or word_count < 1:
                logger.warning(f"Response invalid ({word_count} kata), retrying...")
                stats['ai_errors'] += 1
                return generate_ai_response(sender_name, user_text, context_messages, retry + 1)
            
            # Language check
            if not detect_language(reply_text):
                logger.warning(f"Non-Indonesian detected, retrying...")
                stats['ai_errors'] += 1
                return generate_ai_response(sender_name, user_text, context_messages, retry + 1)
            
            # Length
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
    
    # Final fallback dengan diversity
    logger.warning(f"AI generation failed, using diverse fallback")
    msg_type = detect_message_type(user_text)
    fallback = select_diverse_response(msg_type)
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
        print(f"{C.BOLD}🤖 CYCLE: Balas 3 Messages (DIVERSE)🇮🇩{C.RESET}")
        print(f"{C.BOLD}{C.BLUE}{'='*80}{C.RESET}\n")
        
        context_for_ai = []
        for msg in message_queue:
            context_for_ai.append({
                'sender': msg['sender_name'],
                'text': msg['text']
            })
        
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
    """Send diverse opening message"""
    try:
        if should_exit:
            return
        
        msg = random.choice(OPENING_MESSAGES)
        await client.send_message(TARGET_GROUP, msg, reply_to=TOPIC_ID)
        print(f"{C.GREEN}📢 [SELF-CHAT] {msg}{C.RESET}\n")
        logger.info(f"[SELF-CHAT] Sent: {msg}")
        
        global last_activity
        last_activity = datetime.now()
        stats['self_chats'] += 1
    except Exception as e:
        logger.error(f"Self chat failed: {e}")

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
            
            if len(message_queue) >= 3 and not is_processing:
                asyncio.create_task(start_reply_cycle())
            
            time_silent = (datetime.now() - last_activity).total_seconds()
            if time_silent > SILENCE and not is_processing and len(message_queue) == 0:
                asyncio.create_task(smart_open())
        
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"Task error: {e}")

# ==================== SIGNAL HANDLING ====================

def signal_handler(signum, frame):
    """Handle Ctrl+C"""
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
    logger.info("Model: Gemini 3.1 Flash-Lite (DIVERSE CONTEXT-AWARE)")
    logger.info("="*80)
    
    try:
        print(f"{C.GREEN}🔌 Connecting to Telegram...{C.RESET}")
        await client.start()
        
        logger.info("✅ Connected successfully!")
        print(f"{C.GREEN}✅ USERBOT ACTIVE - INDONESIA ONLY 🇮🇩{C.RESET}\n")
        print(f"{C.CYAN}LOGIC: Tunggu 3 chat → Balas diverse/context-aware → Istirahat{C.RESET}")
        print(f"{C.CYAN}FILTER: Hanya dari topic #{TOPIC_ID} • Hanya Bahasa Indonesia{C.RESET}")
        print(f"{C.CYAN}AI: Gemini 3.1 Flash-Lite - DIVERSE responses sesuai konteks (2-3 kata){C.RESET}")
        print(f"{C.CYAN}SELF-CHAT: Auto kirim jika sepi 60+ detik{C.RESET}")
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
