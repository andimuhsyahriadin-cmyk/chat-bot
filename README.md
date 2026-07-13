# 🤖 TELEGRAM USERBOT DENGAN GEMINI 3.1 AI - INDONESIA FOKUS 🇮🇩

## 📌 OVERVIEW

Bot ini adalah **Userbot Telegram Indonesia-Only** yang:
- ✅ **HANYA BALAS DI TOPIC INDONESIA (#26251)**
- ✅ **STRICT BAHASA INDONESIA** - Tidak balas bahasa lain
- ✅ Balas **EXACTLY 3 MESSAGES** dengan delay 15-30 detik antar chat
- ✅ **REST 1:50 - 2:10** setelah balas (humanize)
- ✅ **BUKA PERCAKAPAN** jika grup sepi > 60 detik
- ✅ Menggunakan **Gemini 3.1 AI** untuk respons natural
- ✅ **INSTANT MESSAGE SEND** - Real-time di group
- ✅ **MUDAH DIJALANKAN DI TERMUX** (single file)

---

## 🔒 FITUR KEAMANAN INDONESIA

### 1. **Strict Topic Filtering**
```
✅ Hanya terima message dari TOPIC_ID #26251
❌ Reject message dari topic lain atau global
```

### 2. **Language Detection**
```python
# Bot detects:
- ✅ Indonesian (Bahasa Indonesia)
- ❌ English
- ❌ Arabic / Persian
- ❌ Cyrillic (Russian, dsb)
- ❌ Chinese / Japanese / Korean
```

Jika user chat bahasa lain → **SKIP LANGSUNG**

### 3. **AI System Prompts - FORCED INDONESIA**
```
"PENTING: HANYA balas dalam BAHASA INDONESIA"
"WAJIB gunakan Bahasa Indonesia dalam semua reply"
"Jangan berpindah ke bahasa lain apapun"
```

Jika AI menghasilkan bahasa lain → Gunakan fallback Indonesia

### 4. **Fallback Responses - GUARANTEED INDONESIA**
```
"Wkwk setuju" "Haha iya" "Iyaa" "Amen" "Betul"
```

---

## 🚀 SETUP TERMUX

### 1. Install Python & Dependencies
```bash
pkg update && pkg upgrade
pkg install python git
```

### 2. Clone Repository
```bash
git clone https://github.com/adinsaja726-netizen/Chat-tele.git
cd Chat-tele
```

### 3. Install Requirements
```bash
pip install -r requirements.txt
```

### 4. Setup Configuration (.env)
```bash
cp .env.example .env
nano .env
```

**Isi .env dengan:**
```env
TELEGRAM_API_ID=1234567
TELEGRAM_API_HASH=your_api_hash
GEMINI_API_KEY=your_gemini_key
TARGET_GROUP=interlinkIDchat
INDONESIA_TOPIC_ID=26251
```

**Untuk mendapatkan API credentials:**
- Telegram API: https://my.telegram.org/
- Gemini API Key: https://aistudio.google.com/app/apikey

### 5. Run Bot
```bash
python bot.py
```

---

## 📊 LOGIC BOT - 3-CHAT CYCLE

### Skenario: 5 pesan masuk dalam waktu singkat (HANYA dari #26251)

```
[19:00:00] BOT START ✅

[19:00:05] 💬 MESSAGE 1 - Budi: "Halo bro"
[19:00:05] [DISPLAY] Topic #26251 ✅ Bahasa Indonesia ✅
[19:00:05] 📦 Queue: 1 messages

[19:00:10] 💬 MESSAGE 2 - Andi: "Apa kabar?"
[19:00:10] [DISPLAY] Topic #26251 ✅ Bahasa Indonesia ✅
[19:00:10] 📦 Queue: 2 messages

[19:00:15] 💬 MESSAGE 3 - Citra: "Sepi yah"
[19:00:15] [DISPLAY] Topic #26251 ✅ Bahasa Indonesia ✅
[19:00:15] 📦 Queue: 3 messages
[19:00:15] ⚠️ Queue >= 3, TRIGGER CYCLE!

════════════════════════════════════════════════════════════
🤖 CYCLE: Balas 3 Messages (Indonesia Only) 🇮🇩
════════════════════════════════════════════════════════════

[19:00:15] 🤔 Replying to Budi... (22s typing)
[19:00:37] ✅ [REPLY/AI] Wkwk iya bro, gimana kabar?

[19:00:37] 🤔 Replying to Andi... (18s typing)
[19:00:55] ✅ [REPLY/AI] Alhamdulillah sehat bro

[19:00:55] 🤔 Replying to Citra... (25s typing)
[19:01:20] ✅ [REPLY/AI] Iya bro sepi, gas ngobrol!

════════════════════════════════════════════════════════════
✅ CYCLE COMPLETE
════════════════════════════════════════════════════════════

[19:01:20] ⏸️ RESTING for 1m 55s
[19:03:15] 🌅 BOT WOKE UP

[19:03:15] Check: Grup sepi > 60s? NO!
   → Continue monitoring

[19:03:20] 💬 MESSAGE 4 - Doni: "Wkwk iya"
[19:03:20] [DISPLAY] Topic #26251 ✅ Bahasa Indonesia ✅
[19:03:20] 📦 Queue: 1 messages

[19:03:25] 💬 MESSAGE 5 - Eka: "Gas lanjut"
[19:03:25] [DISPLAY] Topic #26251 ✅ Bahasa Indonesia ✅
[19:03:25] 📦 Queue: 2 messages

(Tunggu message ke-3 untuk trigger cycle...)
```

---

## 🔍 FILTERING LOGIC

### Message di-SKIP jika:

1. **❌ Wrong Topic**
   ```
   Pesan dari topic lain atau global
   LOG: "Skipped: Wrong topic X (should be 26251)"
   ```

2. **❌ Non-Indonesian Language**
   ```
   Bahasa: English, Arabic, Russian, Chinese, dll
   LOG: "Skipped non-Indonesian from User: text..."
   ```

3. **❌ Skip Keywords**
   ```
   Keywords: admin, moderator, warning, bot, report, spam, banned
   ```

4. **❌ Bot Messages**
   ```
   Message dari bot lain
   ```

5. **❌ Terlalu Pendek**
   ```
   < 3 karakter
   ```

### Message di-TERIMA jika:

✅ Dari topic #26251  
✅ Bahasa Indonesia  
✅ Tidak ada skip keywords  
✅ Dari user (bukan bot)  
✅ Minimal 3 karakter  

---

## ⚙️ KONFIGURASI

Edit di `.env`:

```env
# Delay antar reply dalam cycle (15-30 detik)
REPLY_DELAY_MIN=15
REPLY_DELAY_MAX=30

# Rest period (1:50 - 2:10 = 110-130 detik)
REST_DURATION_MIN=110
REST_DURATION_MAX=130

# Smart open trigger (60 detik sepi)
SILENCE_THRESHOLD=60
```

---

## 📊 STATISTICS

Bot menampilkan stats saat shutdown:

```
📊 BOT STATISTICS
═════════════════════════════════════════
⏱️  Uptime: 2d 3h 45m 30s
📨 Messages Received: 150
✅ Messages Replied: 45
🚫 Messages Skipped: 105
⏸️  Reply Rate: 30.0%
🔄 Cycles Completed: 15
⚠️  Errors: 2
═════════════════════════════════════════
```

---

## 📝 LOGGING

Semua aktivitas di-log ke `logs/userbot.log`:

```
2026-07-13 19:00:05 - INFO - BOT STARTING - INDONESIA FOKUS
2026-07-13 19:00:10 - INFO - [INDONESIA] Reply to Budi: Wkwk iya bro
2026-07-13 19:00:55 - INFO - [INDONESIA] Smart opening sent: Woi pada ngapain nih?
2026-07-13 19:03:26 - WARNING - Skipped non-Indonesian from User: some non-ID text
```

---

## 🛡️ SECURITY

- ✅ **Credentials di .env** (tidak hardcoded)
- ✅ **Strict topic filtering** (hanya #26251)
- ✅ **Language detection** (hanya Indonesian)
- ✅ **Skip keywords** (admin, moderator, dll)
- ✅ **Skip bot messages**
- ✅ **Graceful shutdown** (Ctrl+C = instant exit)
- ✅ **Error handling** (jangan crash)
- ✅ **Instant message send** (real-time di group)

---

## 🔧 TROUBLESHOOTING

### Bot tidak balas pesan

**Solusi checklist:**
1. Check `.env` - pastikan TOPIC_ID benar (#26251)
2. Check console output - apakah ada `🚫 Skip (non-Indonesian)`?
3. Pastikan message dari grup yang benar
4. Pastikan message dalam Bahasa Indonesia
5. Check queue size: `📦 Queue: X messages`
6. Check logs: `cat logs/userbot.log`

### Bot balas bahasa selain Indonesia

**Ini berarti:**
- AI menghasilkan bahasa lain (bug Gemini)
- Bot akan detect & gunakan fallback Indonesia
- Check log: `AI generated non-Indonesian text`

---

## ⚡ QUICK START

```bash
# Clone
git clone https://github.com/adansaja721-arch/telegram-userbot-enhanced.git
cd telegram-userbot-enhanced

# Setup
pip install -r requirements.txt
cp .env.example .env
nano .env  # Isi credentials

# Run
python bot.py
```

---

## 🎯 PENTING

**Bot ini WAJIB:**
- ✅ Hanya di grup Indonesia
- ✅ Hanya balas dari topic #26251
- ✅ Hanya gunakan Bahasa Indonesia
- ✅ Tidak follow link global
- ✅ Tidak berpindah ke bahasa lain

**Jika melanggar → Bot auto-skip message tersebut**

---

**Made with ❤️ untuk Indonesia 🇮🇩**
