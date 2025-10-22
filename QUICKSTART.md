# CreatorPulse - Quick Start Guide

Get CreatorPulse running in 5 minutes with minimal setup.

## Prerequisites (1 minute)

- Python 3.9+ installed
- Terminal/Command Prompt access
- 3 free API accounts (2 minutes to create):
  1. Supabase (https://supabase.com) - Free
  2. Groq (https://console.groq.com) - Free
  3. Gmail account (existing) - Free

---

## Installation (3 minutes)

### 1. Clone & Setup

```bash
git clone https://github.com/yourusername/creatorpulse.git
cd creatorpulse

# Create virtual environment
python -m venv venv

# Activate
# macOS/Linux:
source venv/bin/activate
# Windows:
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Create Environment File

```bash
cp .env.example .env
```

### 3. Get Your API Keys (2 minutes)

**Supabase:**
1. Go to https://supabase.com → Create Project
2. Go to Settings → API
3. Copy `Project URL` and `Anon Public Key`
4. Paste into `.env`:
```
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_KEY=eyJ...
```

**Groq:**
1. Go to https://console.groq.com
2. Sign up (free)
3. Create API key
4. Paste into `.env`:
```
GROQ_API_KEY=gsk_...
```

**Gmail (Optional but Recommended):**
1. Go to https://myaccount.google.com/security
2. Enable 2-Factor Auth
3. Go to https://myaccount.google.com/apppasswords
4. Generate app password
5. Paste into `.env`:
```
SENDER_EMAIL=your@gmail.com
SENDER_EMAIL_PASSWORD=abcd efgh ijkl mnop
```

### 4. Create Database

1. In Supabase, go to **SQL Editor**
2. Click "New Query"
3. Copy entire SQL from [SETUP_GUIDE.md Database Schema section](SETUP_GUIDE.md#step-3-create-database-schema)
4. Paste and click "Run"

---

## Launch (< 1 minute)

```bash
streamlit run app.py
```

Open your browser: **http://localhost:8501**

---

## First Run Checklist

1. **Sign Up**
   - Create account with email

2. **Test Email** (if configured)
   - Settings tab → "Send Test Email"

3. **Add Content Source**
   - RSS Sources tab
   - Select "TechCrunch" 
   - Click "Add Source"

4. **Generate Newsletter**
   - Create Newsletter tab
   - Title: "My First Newsletter"
   - Topic: "Technology"
   - Click "Generate Newsletter"

5. **Review & Send**
   - Review AI draft
   - Click "Send Email" or "Download"

---

## Common Tasks

### Add RSS Feed

1. Go to **RSS Sources** tab
2. Enter URL: `https://example.com/feed.xml`
3. Click "Add Source"

### Schedule Daily Newsletter

1. Go to **Scheduler** tab
2. Set time: 8:00 AM
3. Timezone: Your timezone
4. Delivery: Email or Telegram
5. Click "Save Schedule"

### Train Your Writing Style

1. Go to **Style Trainer** tab
2. Upload 3-5 past newsletters
3. Click "Analyze & Save"
4. Done! AI learns your voice

### Add Telegram Bot (Optional)

1. Open Telegram
2. Search for @BotFather
3. Send `/newbot`
4. Follow prompts
5. Copy bot token to `.env`:
```
TELEGRAM_BOT_TOKEN=123456:ABC...
```
6. Find your bot and send `/start`

---

## File Structure

```
creatorpulse/
├── app.py                    # Main app
├── requirements.txt          # Dependencies
├── .env                      # Your credentials (DON'T commit!)
├── .env.example             # Template
├── README.md                # Full documentation
├── SETUP_GUIDE.md           # Detailed setup
├── DEPLOYMENT.md            # Production deployment
├── auth.py                  # Login/signup
├── models.py                # Database
├── content_aggregator.py    # RSS/Twitter/YouTube
├── draft_generator.py       # AI newsletter
├── email_service.py         # Email/Telegram
├── style_trainer.py         # Writing style
└── .streamlit/
    └── config.toml          # Streamlit config
```

---

## Environment Variables Explained

**REQUIRED (Must have):**
- `SUPABASE_URL` - Your Supabase project URL
- `SUPABASE_KEY` - Supabase anon key
- `GROQ_API_KEY` - Groq AI API key

**RECOMMENDED (Should have):**
- `SENDER_EMAIL` - Your Gmail address
- `SENDER_EMAIL_PASSWORD` - Gmail app password

**OPTIONAL:**
- `TELEGRAM_BOT_TOKEN` - Telegram bot token (for messenger delivery)
- `YOUTUBE_API_KEY` - YouTube API key (to fetch videos)

---

## Troubleshooting

### "Supabase client not initialized"
- Check `SUPABASE_URL` and `SUPABASE_KEY` in `.env`
- Verify Supabase project is active
- Restart app

### "No articles fetching"
- Add valid RSS URL in RSS Sources tab
- Try popular feed: `https://techcrunch.com/feed/`
- Check internet connection

### "Email not sending"
- Set `SENDER_EMAIL` and `SENDER_EMAIL_PASSWORD` in `.env`
- Use Gmail app password (16 chars, no spaces)
- Enable Gmail 2-Factor Auth first
- Restart app

### "Error on page load"
```bash
# Check for Python errors
streamlit run app.py --logger.level=debug
```

### "Port 8501 already in use"
```bash
# Use different port
streamlit run app.py --server.port 8502
```

---

## Next Steps

1. Read full [README.md](README.md) for complete documentation
2. See [SETUP_GUIDE.md](SETUP_GUIDE.md) for detailed configuration
3. Follow [DEPLOYMENT.md](DEPLOYMENT.md) to deploy to production
4. Check [API Documentation](README.md#api-documentation) for extending

---

## Key Features at a Glance

- ✅ **Multi-source aggregation** - RSS, Twitter, YouTube
- ✅ **AI newsletter generation** - Powered by Groq Llama 3.3
- ✅ **Writing style training** - AI learns your voice
- ✅ **Scheduled delivery** - Automatic morning newsletters
- ✅ **Email & Telegram** - Multiple delivery options
- ✅ **Analytics** - Track engagement & performance
- ✅ **Social media** - Convert to Twitter threads/LinkedIn posts
- ✅ **Edit tracking** - Version history with diffs

---

## Support

- Full docs: See README.md, SETUP_GUIDE.md, DEPLOYMENT.md
- Issues: GitHub Issues
- Email: support@creatorpulse.ai

---

## What You Can Do Now

**Immediately:**
- Generate AI-drafted newsletters
- Add RSS feeds from any source
- Schedule daily newsletter delivery
- Send via email or Telegram
- Track newsletter analytics

**Next:**
- Add Twitter handles/hashtags as sources
- Add YouTube channels
- Train AI on your writing style
- Convert newsletters to social posts
- Deploy to production

---

Happy newsletter creating! 🚀

---

**Version:** 1.0.0
**Time to First Newsletter:** ~5 minutes
**Difficulty:** Beginner-friendly
