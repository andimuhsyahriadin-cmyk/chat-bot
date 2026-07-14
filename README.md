# 🤖 TELEGRAM USERBOT DENGAN GEMINI 3.1 AI - INDONESIA FOKUS

README diperbarui: perbaikan instruksi, env, dan fallback generation.

Perubahan utama di branch: `improve/fallback-and-ai-logic`

Perbaikan yang dibuat:
- bot.py sekarang membaca konfigurasi REPLY_DELAY_MIN / REPLY_DELAY_MAX, REST_DURATION_MIN / REST_DURATION_MAX, dan SILENCE_THRESHOLD dari `.env`.
- Bot akan menghasilkan (atau memuat) pool fallback berukuran besar (>=5000 frasa) secara otomatis ke `data/fallback_phrases.json` saat pertama kali dijalankan.
- Ditambahkan logika analisis ringan (intent + tone) untuk memilih fallback yang relevan ketika Gemini gagal/timeout/atau menghasilkan non-Indonesia.
- Smart-open (self-chat) sekarang mencoba memilih opening yang relevan berdasar kata kunci percakapan terakhir.
- README: perbaikan URL clone dan instruksi singkat.


## Quick start

```bash
git clone https://github.com/andimuhsyahriadin-cmyk/chat-bot.git
cd chat-bot

python -m venv .venv
source .venv/bin/activate  # atau di Termux: source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# edit .env: set TELEGRAM_API_ID, TELEGRAM_API_HASH, GEMINI_API_KEY, TARGET_GROUP, INDONESIA_TOPIC_ID
# optional: adjust REPLY_DELAY_MIN, REPLY_DELAY_MAX, REST_DURATION_MIN, REST_DURATION_MAX, SILENCE_THRESHOLD

python bot.py
```

## Env vars penting (lihat .env.example)
- TELEGRAM_API_ID (int)
- TELEGRAM_API_HASH
- GEMINI_API_KEY
- TARGET_GROUP (nama grup atau id yang diterima Telethon)
- INDONESIA_TOPIC_ID (int)
- REPLY_DELAY_MIN / REPLY_DELAY_MAX (detik)
- REST_DURATION_MIN / REST_DURATION_MAX (detik)
- SILENCE_THRESHOLD (detik)

Catatan: ketika pertama kali dijalankan, bot akan membuat `data/fallback_phrases.json` jika belum ada — proses ini cepat dan hanya dilakukan sekali.

## Notes
- Perubahan dibuat di branch `improve/fallback-and-ai-logic`. Setelah review, saya dapat membuat PR ke `main` jika Anda setuju.
- Fallback pool dibuat programmatically dan persisten di `data/fallback_phrases.json` supaya repo tidak membengkak.
