"""
Enhanced bot.py (main updated)
- Enforces replies to be exactly 2-3 words only (both AI and fallback)
- Ensures fallback generator produces only 2-3 word phrases
- Validation updated: Gemini outputs must be 2-3 words; otherwise retry -> fallback
"""

import asyncio
import random
import signal
import sys
import os
import logging
import time
import json
from datetime import datetime, timedelta
from collections import deque, Counter
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

# Readable behavior config (from .env, with safe defaults)
DELAY_MIN = int(os.getenv('REPLY_DELAY_MIN', '15'))
DELAY_MAX = int(os.getenv('REPLY_DELAY_MAX', '30'))
REST_MIN = int(os.getenv('REST_DURATION_MIN', '110'))
REST_MAX = int(os.getenv('REST_DURATION_MAX', '130'))
SILENCE = int(os.getenv('SILENCE_THRESHOLD', '60'))

# Safety clamps
if DELAY_MIN < 0: DELAY_MIN = 15
if DELAY_MAX < DELAY_MIN: DELAY_MAX = DELAY_MIN + 1
if REST_MIN < 10: REST_MIN = 110
if REST_MAX < REST_MIN: REST_MAX = REST_MIN + 10
if SILENCE < 5: SILENCE = 60

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
    'ai_replies': 0,
    'fallback_replies': 0,
    'errors': 0,
    'ai_errors': 0,
    'start_time': datetime.now()
}

# Skip keywords
SKIP_KEYWORDS = ['admin', 'moderator', 'warning', '[bot]', 'report', 'spam', 'banned', 'kick', 'mute']

# Fallback management
FALLBACK_PATH = os.path.join('data', 'fallback_phrases.json')
fallback_by_category = {}
all_fallbacks = []
recent_used = deque(maxlen=300)  # avoid recent repeats
MIN_FALLBACK_POOL = 5000

# Helper utils

def count_words(text):
    return len(text.split())

# ==================== BANNER & UTIL ====================

def print_banner():
    print(f"\n{C.CYAN}{C.BOLD}" + "="*80)
    print(f"        🤖 TELEGRAM USERBOT DENGAN GEMINI 3.1 FLASH-LITE AI 🇮🇩")
    print(f"        PRIORITAS GEMINI API 100% • Fallback DB EMERGENCY ONLY")
    print(f"="*80 + f"{C.RESET}\n")


def validate_config():
    errors = []
    if API_ID == 0:
        errors.append("TELEGRAM_API_ID tidak dikonfigurasi")
    if API_HASH == 'change_me':
        errors.append("TELEGRAM_API_HASH tidak dikonfigurasi")
    if GEMINI_KEY == 'change_me' or not GEMINI_KEY:
        errors.append("GEMINI_API_KEY tidak dikonfigurasi")
    return errors


def get_uptime():
    uptime = datetime.now() - stats['start_time']
    days = uptime.days
    hours, remainder = divmod(uptime.seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{days}d {hours}h {minutes}m {seconds}s"


def print_stats():
    uptime = get_uptime()
    received = stats['messages_received']
    replied = stats['messages_replied']
    skipped = stats['messages_skipped']
    ai_count = stats['ai_replies']
    fallback_count = stats['fallback_replies']
    rate = (replied / max(received, 1)) * 100
    
    print(f"\n{C.BOLD}{C.CYAN}{'='*80}{C.RESET}")
    print(f"{C.BOLD}📊 BOT STATISTICS{C.RESET}")
    print(f"{C.BOLD}{C.CYAN}{'='*80}{C.RESET}")
    print(f"{C.GREEN}⏱️  Uptime:{C.RESET} {uptime}")
    print(f"{C.GREEN}📨 Messages Received:{C.RESET} {received}")
    print(f"{C.GREEN}✅ Messages Replied:{C.RESET} {replied}")
    print(f"{C.GREEN}   🤖 via Gemini AI:{C.RESET} {ai_count}")
    print(f"{C.GREEN}   📚 via Fallback DB:{C.RESET} {fallback_count}")
    print(f"{C.GREEN}💬 Self Chats:{C.RESET} {stats['self_chats']}")
    print(f"{C.GREEN}🚫 Messages Skipped:{C.RESET} {skipped}")
    print(f"{C.GREEN}⏸️  Reply Rate:{C.RESET} {rate:.1f}%")
    print(f"{C.GREEN}🔄 Cycles Completed:{C.RESET} {stats['cycles_completed']}")
    print(f"{C.GREEN}🤖 AI Success Rate:{C.RESET} {(ai_count/max(replied, 1)*100):.1f}%")
    print(f"{C.GREEN}⚠️  Total Errors:{C.RESET} {stats['errors']}")
    print(f"{C.BOLD}{C.CYAN}{'='*80}{C.RESET}\n")

# ==================== LANGUAGE DETECTION ====================

def detect_language(text):
    """Simple heuristic to detect if text likely Indonesian"""
    indonesian_words = [
        'apa', 'siapa', 'dimana', 'kapan', 'bagaimana', 'kenapa', 'berapa',
        'ya', 'yah', 'yaudah', 'lah', 'dong', 'sih', 'kali', 'nih', 'tuh',
        'ini', 'itu', 'saya', 'kamu', 'dia', 'kami', 'kalian', 'kita',
        'dan', 'atau', 'tapi', 'bukan', 'juga', 'pun', 'kalau', 'kalo',
        'di', 'ke', 'dari', 'untuk', 'sama', 'ada', 'tidak', 'jadi', 'dulu',
        'bro', 'mas', 'bang', 'kak', 'dek', 'om', 'mbak', 'pak', 'ibu', 'ente',
        'aja', 'udah', 'gak', 'ga', 'ngga', 'nggak', 'enggak', 'gakk',
        'gimana', 'gini', 'gitu', 'cuman', 'wkwk', 'haha', 'hehe', 'njir',
        'lo', 'gue', 'elu', 'klo', 'yang', 'sih', 'kok', 'soal'
    ]
    
    text_lower = text.lower()
    words = text_lower.split()
    if not words:
        return False
    indo_count = sum(1 for word in words if any(indo_word in word for indo_word in indonesian_words))
    if indo_count / len(words) > 0.22:
        return True
    # Check for other script presence (Arabic, Cyrillic, CJK)
    if any('\u0600' <= c <= '\u06FF' for c in text) or any('\u0400' <= c <= '\u04FF' for c in text):
        return False
    if any('\u4E00' <= c <= '\u9FFF' for c in text) or any('\u3040' <= c <= '\u309F' for c in text):
        return False
    if any('\uAC00' <= c <= '\uD7AF' for c in text):
        return False
    return indo_count > 0

# ==================== TOPIC ID DETECTION ====================

def get_message_topic_id(message):
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

# ==================== FALLBACK GENERATION/LOADING ====================

def generate_fallback_pool(target_total=MIN_FALLBACK_POOL):
    """Generate a diverse Indonesian fallback pool programmatically and persist to disk.
    Ensure each phrase is 2-3 words only.
    """
    os.makedirs('data', exist_ok=True)
    categories = {
        'agreement': {
            'prefix': ['', 'Haha', 'Wkwk', 'Iya', 'Bener', 'Setuju', 'Yup', 'Iya deh', 'Betul'],
            'core': ['iya', 'setuju', 'bener', 'betul', 'sama', 'sepakat', 'oke'],
            'suffix': ['', 'banget', 'bro', 'nih']
        },
        'humor': {
            'prefix': ['Wkwk', 'Haha', 'Njir', 'Waduh', 'Hahaha', 'Ngakak'],
            'core': ['kocak', 'gokil', 'gila', 'parah', 'konyol', 'absurd'],
            'suffix': ['', 'banget', 'bro']
        },
        'question': {
            'prefix': ['', 'Eh', 'Woi', 'Asli'],
            'core': ['apa', 'gimana', 'kenapa', 'siapa', 'dimana', 'kapan', 'kok'],
            'suffix': ['', 'nih', 'ya']
        },
        'support': {
            'prefix': ['', 'Semangat', 'Kuat', 'Bisa kok', 'Ayo', 'Sikat'],
            'core': ['bro', 'teman', 'sobat', 'kalian', 'kita'],
            'suffix': ['', 'ya']
        },
        'surprise': {
            'prefix': ['', 'Wah', 'Astaga', 'Waduh', 'Gila'],
            'core': ['beneran', 'serius', 'lho', 'gak nyangka'],
            'suffix': ['', '!']
        },
        'opening': {
            'prefix': ['', 'Woi', 'Halo', 'Yo', 'Gas', 'Siapa'],
            'core': ['ada', 'apa', 'ide', 'cerita', 'lagi'],
            'suffix': ['', 'nih', '?']
        },
        'smalltalk': {
            'prefix': ['', 'Eh', 'Hmm', 'Hehe', 'Oh'],
            'core': ['lagi', 'makan', 'ngopi', 'kerja', 'libur', 'nongkrong'],
            'suffix': ['', 'ya', '?']
        }
    }

    generated = {k: set() for k in categories}
    per_cat = max(300, target_total // max(1, len(categories)))

    for cat, parts in categories.items():
        attempts = 0
        while len(generated[cat]) < per_cat and attempts < per_cat * 20:
            p = random.choice(parts['prefix']).strip()
            c = random.choice(parts['core']).strip()
            s = random.choice(parts['suffix']).strip()
            # Try forms that yield 2-3 words: (prefix core), (core suffix), (prefix core suffix)
            forms = []
            if p and c:
                forms.append(f"{p} {c}".strip())
            if c and s:
                forms.append(f"{c} {s}".strip())
            if p and c and s:
                forms.append(f"{p} {c} {s}".strip())
            if not forms:
                attempts += 1
                continue
            phrase = random.choice(forms)
            phrase = phrase.replace(' ?', '?').replace(' !', '!').strip()
            wc = count_words(phrase)
            if 2 <= wc <= 3 and len(phrase) <= 60:
                generated[cat].add(phrase)
            attempts += 1

    # Flatten and ensure total target
    all_phrases = []
    for cat, s in generated.items():
        for p in s:
            all_phrases.append({'category': cat, 'text': p})

    # If still not enough, expand by combining core two-words forms
    core_pool = [item['text'] for item in all_phrases]
    while len(all_phrases) < target_total:
        a = random.choice(core_pool) if core_pool else 'Iya bro'
        b = random.choice(core_pool) if core_pool else 'Siap ya'
        # try to merge into 2-3 words by picking parts
        parts_a = a.split()
        parts_b = b.split()
        candidate_words = (parts_a + parts_b)[:3]
        candidate = ' '.join(candidate_words)
        if 2 <= count_words(candidate) <= 3 and candidate not in [x['text'] for x in all_phrases]:
            all_phrases.append({'category': 'mixed', 'text': candidate})
        else:
            # fallback small generated variant
            alternative = (a.split()[0] + ' ' + (b.split()[0] if len(b.split())>0 else 'ya')).strip()
            if 2 <= count_words(alternative) <=3 and alternative not in [x['text'] for x in all_phrases]:
                all_phrases.append({'category': 'mixed', 'text': alternative})

    # Persist to JSON grouped by category
    grouped = {}
    for item in all_phrases:
        grouped.setdefault(item['category'], []).append(item['text'])

    with open(FALLBACK_PATH, 'w', encoding='utf-8') as f:
        json.dump(grouped, f, ensure_ascii=False, indent=2)

    return grouped


def load_or_create_fallback():
    global fallback_by_category, all_fallbacks
    if os.path.exists(FALLBACK_PATH):
        try:
            with open(FALLBACK_PATH, 'r', encoding='utf-8') as f:
                fallback_by_category = json.load(f)
        except Exception as e:
            logger.warning(f"Failed to load fallback file, regenerating: {e}")
            fallback_by_category = generate_fallback_pool(MIN_FALLBACK_POOL)
    else:
        logger.info("Fallback file not found — generating large pool (this may take a few seconds)...")
        fallback_by_category = generate_fallback_pool(MIN_FALLBACK_POOL)

    # flatten
    all_fallbacks = []
    for k, lst in fallback_by_category.items():
        all_fallbacks.extend(lst)
    # Filter to 2-3 word phrases only (safety)
    all_fallbacks = [p for p in all_fallbacks if 2 <= count_words(p) <= 3]
    random.shuffle(all_fallbacks)
    logger.info(f"Fallback pool loaded: {len(all_fallbacks)} phrases across {len(fallback_by_category)} categories")

# ==================== INTENT & SENTIMENT (LIGHTWEIGHT) ====================

INTENT_KEYWORDS = {
    'question': ['apa', 'kenapa', 'gimana', 'gak', 'kok', 'siapa', 'dimana', 'kapan', '?'],
    'agreement': ['setuju', 'iya', 'betul', 'bener', 'sepakat', 'sama', 'yup', 'yoi'],
    'humor': ['wkwk', 'haha', 'ngakak', 'kocak', 'gokil', 'konyol'],
    'support': ['semangat', 'sukses', 'bisa', 'kuat', 'ayo'],
    'surprise': ['astaga', 'waduh', 'woi', 'lho', 'serius'],
    'opening': ['halo', 'woi', 'gas', 'siapa'],
    'smalltalk': ['lagi', 'makan', 'ngopi', 'libur', 'kerja']
}

POSITIVE_WORDS = ['baik', 'bagus', 'mantap', 'oke', 'ok', 'siap', 'ya', 'iya', 'betul']
NEGATIVE_WORDS = ['gak', 'tidak', 'nggak', 'gatau', 'ga', 'capek', 'bingung']


def analyze_intent_and_tone(text, context_messages=None):
    txt = text.lower()
    scores = Counter()
    for intent, keys in INTENT_KEYWORDS.items():
        for k in keys:
            if k in txt:
                scores[intent] += 1
    if '?' in text:
        scores['question'] += 1
    pos = sum(1 for w in POSITIVE_WORDS if w in txt)
    neg = sum(1 for w in NEGATIVE_WORDS if w in txt)
    if context_messages:
        combined = ' '.join(m['text'].lower() for m in context_messages[-5:])
        for k in INTENT_KEYWORDS.keys():
            if k in combined:
                scores[k] += 0
    if scores:
        intent = scores.most_common(1)[0][0]
        if intent in fallback_by_category:
            return intent
    if pos > neg and pos > 0:
        return 'agreement' if 'agreement' in fallback_by_category else 'support'
    if neg > pos and neg > 0:
        return 'support' if 'support' in fallback_by_category else 'neutral'
    return 'neutral'


def select_fallback_for(text, context_messages=None):
    intent = analyze_intent_and_tone(text, context_messages)
    candidates = []
    if intent in fallback_by_category:
        candidates = list(fallback_by_category.get(intent, []))
    if not candidates:
        candidates = list(all_fallbacks)
    candidates = [p for p in candidates if 2 <= count_words(p) <= 3]
    if not candidates:
        candidates = [p for p in all_fallbacks if 2 <= count_words(p) <= 3]
    attempts = 0
    while attempts < 30 and candidates:
        choice = random.choice(candidates)
        if choice not in recent_used:
            recent_used.append(choice)
            return choice, intent
        attempts += 1
    choice = random.choice(candidates) if candidates else ('Iya bro', 'neutral')
    recent_used.append(choice)
    return choice, intent

# ==================== AI ENGINE - GEMINI FOKUS ====================

def generate_ai_response(sender_name, user_text, context_messages=None, retry=0):
    if retry > 3:
        logger.warning(f"AI failed {retry}x, selecting fallback by analysis")
        fallback, cat = select_fallback_for(user_text, context_messages)
        return fallback, True, f"FALLBACK:{cat}"

    try:
        context = ''
        if context_messages and len(context_messages) > 0:
            recent = context_messages[-4:]
            context = 'Chat context:\n'
            for msg in recent:
                short_text = msg['text'][:80]
                context += f"{msg['sender']}: {short_text}\n"
            context += '\n'

        system_prompt = (
            "Kamu adalah teman grup Indonesia yang responsive dan natural.\n"
            "WAJIB HANYA Bahasa Indonesia, SINGKAT: 2-3 KATA. VARIASI.\n"
            "Jangan ulang-ulang frasa yang sama terus."
        )

        prompt = f"""{context}{sender_name}: {user_text[:200]}

Balas singkat (2-3 kata) yang natural dan relevan:"""

        logger.debug(f"🤖 Requesting Gemini (retry {retry})...")

        response = ai_client.models.generate_content(
            model='gemini-3.1-flash-lite',
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
                temperature=0.85,
                max_output_tokens=30,
                top_p=0.95,
                top_k=40,
                timeout=10.0
            )
        )

        if response and getattr(response, 'text', None):
            reply_text = response.text.strip()
            reply_text = reply_text.replace('**', '').replace('__', '').replace('```', '')
            reply_text = reply_text.replace('"', '').replace("'", '').strip()
            reply_text = ' '.join(reply_text.split())
            if reply_text.startswith('Balas:') or reply_text.startswith('Reply:'):
                reply_text = reply_text.split(':', 1)[1].strip()
            word_count = count_words(reply_text)
            logger.debug(f"Gemini returned ({word_count} words): {reply_text}")
            # Validate Indonesian & length: enforce 2-3 words
            if not detect_language(reply_text):
                logger.warning("Gemini returned non-Indonesian text — retrying with AI")
                stats['ai_errors'] += 1
                time.sleep(1)
                return generate_ai_response(sender_name, user_text, context_messages, retry + 1)
            if 2 <= word_count <= 3 and len(reply_text) < 140:
                logger.info(f"✅ [GEMINI] {sender_name}: '{reply_text}'")
                return reply_text, False, 'GEMINI'
            else:
                logger.warning(f"Gemini output invalid (words={word_count}) — retrying")
                stats['ai_errors'] += 1
                time.sleep(1)
                return generate_ai_response(sender_name, user_text, context_messages, retry + 1)
        else:
            logger.warning("Empty response from Gemini — retrying")
            stats['ai_errors'] += 1
            time.sleep(1)
            return generate_ai_response(sender_name, user_text, context_messages, retry + 1)

    except Exception as e:
        error_msg = str(e)
        logger.warning(f"Gemini error (attempt {retry+1}): {error_msg[:120]}")
        if any(x in error_msg.lower() for x in ['500', '503', 'timeout', 'deadline', 'temporarily', 'rate limit', 'unauth']):
            stats['ai_errors'] += 1
            time.sleep(2 + retry)
            return generate_ai_response(sender_name, user_text, context_messages, retry + 1)
        logger.error(f"Gemini failed: {error_msg[:200]}")
        stats['errors'] += 1

    # final fallback
    logger.warning("Using fallback pool due to Gemini failure")
    fallback, cat = select_fallback_for(user_text, context_messages)
    return fallback, True, f"FALLBACK:{cat}"

# ==================== MESSAGE HANDLING ====================

@client.on(events.NewMessage(chats=TARGET_GROUP))
async def handle_message(event):
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
        sender_name = sender.first_name or 'Unknown'
        user_text = event.message.text or ''
        if not user_text or len(user_text.strip()) < 3:
            stats['messages_skipped'] += 1
            return
        timestamp = datetime.now().strftime('%H:%M:%S')
        print(f"{C.YELLOW}[{timestamp}] {C.BOLD}{sender_name}{C.RESET}: {user_text}")
        if not detect_language(user_text):
            print(f"   {C.RED}└─ 🚫 Skip (non-Indonesian){C.RESET}")
            logger.info(f"Skipped non-Indonesian from {sender_name}")
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
        print(f"   {C.MAGENTA}└─ 📦 Queue: {queue_size}/3 (Topic: #{TOPIC_ID}){C.RESET}")
        current_time = datetime.now()
        time_since_last_cycle = (current_time - last_cycle_time).total_seconds()
        if queue_size >= 3 and not is_processing and time_since_last_cycle > 5:
            asyncio.create_task(start_reply_cycle())
    except Exception as e:
        logger.error(f"Error handling message: {e}")
        stats['errors'] += 1

# ==================== REPLY CYCLE LOGIC ====================

async def start_reply_cycle():
    global is_processing, message_queue, last_activity, last_cycle_time
    if is_processing or len(message_queue) < 3:
        return
    is_processing = True
    last_cycle_time = datetime.now()
    try:
        selected = message_queue[:3]
        print(f"\n{C.BOLD}{C.BLUE}{'='*80}{C.RESET}")
        print(f"{C.BOLD}🤖 CYCLE: Balas 3 Messages (GEMINI AI)🇮🇩{C.RESET}")
        print(f"{C.BOLD}{C.BLUE}{'='*80}{C.RESET}\n")
        context_for_ai = []
        for msg in message_queue:
            context_for_ai.append({'sender': msg['sender_name'], 'text': msg['text']})
        for idx, msg in enumerate(selected, 1):
            if should_exit:
                print(f"{C.YELLOW}[EXIT] Stopping cycle...{C.RESET}")
                break
            sender_name = msg['sender_name']
            user_text = msg['text']
            event = msg['event']
            try:
                reply_text, is_fallback, source = generate_ai_response(
                    sender_name, user_text, context_for_ai
                )
                if not is_fallback:
                    stats['ai_replies'] += 1
                else:
                    stats['fallback_replies'] += 1
                delay = random.randint(DELAY_MIN, DELAY_MAX)
                source_emoji = '🤖' if source == 'GEMINI' else '📚'
                print(f"   {C.CYAN}└─ {source_emoji}[{source}] Reply (delay {delay}s){C.RESET}")
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
                        logger.warning(f"Reply failed: {send_error}")
                        try:
                            await client.send_message(TARGET_GROUP, reply_text, reply_to=TOPIC_ID)
                        except Exception as fallback_error:
                            logger.error(f"Send failed: {fallback_error}")
                            raise
                    print(f"   {C.GREEN}└─ ✅ Sent: {reply_text}{C.RESET}")
                    stats['messages_replied'] += 1
                    last_activity = datetime.now()
                    logger.info(f"[{source}] Balas ke {sender_name}: {reply_text}")
            except Exception as e:
                logger.error(f"Error replying to {sender_name}: {e}")
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
        print(f"{C.YELLOW}⏸️  REST {minutes}m {seconds}s (Ctrl+C exit){C.RESET}")
        for _ in range(rest_duration):
            if should_exit:
                print(f"{C.YELLOW}[EXIT] Rest interrupted{C.RESET}\n")
                break
            await asyncio.sleep(1)
        if not should_exit:
            print(f"{C.GREEN}🌅 WOKE UP{C.RESET}\n")
            if len(message_queue) >= 3:
                print(f"{C.CYAN}Queue ada, cycle baru...{C.RESET}")
                await start_reply_cycle()
            else:
                time_silent = (datetime.now() - last_activity).total_seconds()
                if time_silent > SILENCE:
                    print(f"{C.YELLOW}[SMART OPEN] Sepi {int(time_silent)}s, buka chat...{C.RESET}")
                    await smart_open()
    except Exception as e:
        logger.error(f"Error in reply cycle: {e}")
        stats['errors'] += 1
    finally:
        is_processing = False

# ==================== SMART OPENING ====================

async def smart_open():
    try:
        if should_exit:
            return
        opening = None
        if len(message_queue) >= 1:
            ctx = message_queue[-3:]
            words = ' '.join(m['text'] for m in ctx).lower().split()
            common = Counter([w for w in words if len(w) > 2])
            if common:
                keyword = common.most_common(1)[0][0]
                candidates = [p for p in all_fallbacks if keyword in p and 2 <= count_words(p) <= 3]
                if candidates:
                    opening = random.choice(candidates)
        if not opening:
            opening, cat = select_fallback_for('opening')
            if 2 > count_words(opening) or count_words(opening) > 3:
                opening, cat = select_fallback_for('opening')
        await client.send_message(TARGET_GROUP, opening, reply_to=TOPIC_ID)
        print(f"{C.GREEN}📢 [SELF-CHAT] {opening}{C.RESET}\n")
        logger.info(f"[SELF-CHAT] Sent: {opening}")
        global last_activity
        last_activity = datetime.now()
        stats['self_chats'] += 1
    except Exception as e:
        logger.error(f"Self chat failed: {e}")

async def smart_opening_task():
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
    global should_exit
    logger.warning(f"Signal {signum} - instant shutdown...")
    print(f"\n{C.RED}🛑 INSTANT EXIT{C.RESET}\n")
    should_exit = True
    sys.exit(0)

# ==================== MAIN ====================

async def main():
    print_banner()
    errors = validate_config()
    if errors:
        print(f"{C.RED}❌ CONFIG ERRORS:{C.RESET}")
        for e in errors:
            print(f"   {C.RED}✗ {e}{C.RESET}")
        sys.exit(1)

    load_or_create_fallback()

    logger.info("BOT STARTING - PRIORITAS GEMINI AI")
    logger.info(f"Target: {TARGET_GROUP} | Topic: #{TOPIC_ID}")
    logger.info("Model: Gemini 3.1 Flash-Lite (PRIMARY)")
    logger.info("Fallback: Generated pool (EMERGENCY ONLY)")

    try:
        print(f"{C.GREEN}🔌 Connecting to Telegram...{C.RESET}")
        await client.start()
        logger.info("✅ Connected successfully!")
        print(f"{C.GREEN}✅ USERBOT ACTIVE - GEMINI AI MODE 🤖🇮🇩{C.RESET}\n")
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
        print(f"{C.GREEN}✅ Shutdown complete{C.RESET}\n")

# ==================== ENTRY POINT ====================

if __name__ == '__main__':
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    try:
        with client:
            client.loop.run_until_complete(main())
    except KeyboardInterrupt:
        print(f"{C.RED}🛑 EXIT{C.RESET}\n")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        print(f"{C.RED}❌ Fatal: {e}{C.RESET}")
