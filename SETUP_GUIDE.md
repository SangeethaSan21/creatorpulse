# CreatorPulse - Complete Setup Guide

## Table of Contents
1. [Prerequisites](#prerequisites)
2. [Initial Setup](#initial-setup)
3. [Supabase Configuration](#supabase-configuration)
4. [External Services Setup](#external-services-setup)
5. [Local Development](#local-development)
6. [Production Deployment](#production-deployment)
7. [Troubleshooting](#troubleshooting)

---

## Prerequisites

### System Requirements
- Python 3.9 or higher
- 2GB RAM minimum
- Internet connection
- Git installed

### Accounts Needed
- Supabase (free tier available)
- Groq (free tier available)
- Gmail account (for SMTP)
- GitHub (optional, for version control)

---

## Initial Setup

### Step 1: Clone Repository

```bash
git clone https://github.com/yourusername/creatorpulse.git
cd creatorpulse
```

### Step 2: Create Virtual Environment

```bash
# macOS / Linux
python3 -m venv venv
source venv/bin/activate

# Windows
python -m venv venv
venv\Scripts\activate
```

### Step 3: Install Dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### Step 4: Create Environment File

```bash
cp .env.example .env
```

---

## Supabase Configuration

### Step 1: Create Supabase Project

1. Go to https://supabase.com
2. Click "Start Your Project"
3. Sign up with email or GitHub
4. Create new project:
   - Name: "creatorpulse"
   - Database password: (save securely)
   - Region: (closest to your location)
5. Wait for project to initialize (2-3 minutes)

### Step 2: Get API Keys

In Supabase dashboard:
1. Go to **Settings → API**
2. Copy these values to `.env`:
   - **Project URL** → `SUPABASE_URL`
   - **Anon Public Key** → `SUPABASE_KEY`

### Step 3: Create Database Schema

In Supabase, go to **SQL Editor** and execute this SQL:

```sql
-- ============================================================================
-- USERS TABLE
-- ============================================================================
CREATE TABLE IF NOT EXISTS users (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  email VARCHAR UNIQUE NOT NULL,
  username VARCHAR UNIQUE NOT NULL,
  display_name VARCHAR,
  name VARCHAR,
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);

-- ============================================================================
-- USER SOURCES TABLE
-- ============================================================================
CREATE TABLE IF NOT EXISTS user_sources (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  name VARCHAR NOT NULL,
  url VARCHAR NOT NULL,
  type VARCHAR NOT NULL CHECK (type IN ('rss_feed', 'newsletter', 'blog', 'twitter_handle', 'twitter_hashtag', 'youtube_channel')),
  category VARCHAR DEFAULT 'General',
  active BOOLEAN DEFAULT true,
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW(),
  UNIQUE(user_id, url)
);

-- ============================================================================
-- NEWSLETTERS TABLE
-- ============================================================================
CREATE TABLE IF NOT EXISTS newsletters (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  title VARCHAR NOT NULL,
  content TEXT,
  status VARCHAR DEFAULT 'draft' CHECK (status IN ('draft', 'sent', 'published')),
  trends JSONB,
  topic VARCHAR,
  tone VARCHAR,
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW(),
  sent_at TIMESTAMP,
  published_at TIMESTAMP
);

-- ============================================================================
-- NEWSLETTER FEEDBACK TABLE
-- ============================================================================
CREATE TABLE IF NOT EXISTS newsletter_feedback (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  newsletter_id UUID NOT NULL REFERENCES newsletters(id) ON DELETE CASCADE,
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  reaction VARCHAR NOT NULL CHECK (reaction IN ('thumbs_up', 'thumbs_down', 'accepted', 'rejected')),
  edit_diff JSONB,
  was_edited BOOLEAN DEFAULT false,
  created_at TIMESTAMP DEFAULT NOW()
);

-- ============================================================================
-- SCHEDULED DELIVERIES TABLE
-- ============================================================================
CREATE TABLE IF NOT EXISTS scheduled_deliveries (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
  schedule_time TIME DEFAULT '08:00:00',
  timezone VARCHAR DEFAULT 'UTC',
  delivery_method VARCHAR DEFAULT 'email' CHECK (delivery_method IN ('email', 'telegram', 'both')),
  is_active BOOLEAN DEFAULT true,
  last_delivered_at TIMESTAMP,
  telegram_chat_id VARCHAR,
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);

-- ============================================================================
-- STYLE PROFILES TABLE
-- ============================================================================
CREATE TABLE IF NOT EXISTS user_style_profiles (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
  style_profile JSONB,
  custom_prompt TEXT,
  updated_at TIMESTAMP DEFAULT NOW()
);

-- ============================================================================
-- EDIT HISTORY TABLE
-- ============================================================================
CREATE TABLE IF NOT EXISTS edit_history (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  newsletter_id UUID NOT NULL REFERENCES newsletters(id) ON DELETE CASCADE,
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  original_content TEXT,
  edited_content TEXT,
  edit_metrics JSONB,
  created_at TIMESTAMP DEFAULT NOW()
);

-- ============================================================================
-- REVIEW TIMERS TABLE
-- ============================================================================
CREATE TABLE IF NOT EXISTS review_timers (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  newsletter_id UUID NOT NULL REFERENCES newsletters(id) ON DELETE CASCADE,
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  started_at TIMESTAMP NOT NULL,
  ended_at TIMESTAMP,
  duration_minutes DECIMAL(10,2),
  action VARCHAR,
  status VARCHAR DEFAULT 'active' CHECK (status IN ('active', 'completed')),
  created_at TIMESTAMP DEFAULT NOW()
);

-- ============================================================================
-- SOCIAL POSTS TABLE
-- ============================================================================
CREATE TABLE IF NOT EXISTS social_posts (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  newsletter_id UUID REFERENCES newsletters(id) ON DELETE CASCADE,
  platform VARCHAR NOT NULL CHECK (platform IN ('twitter', 'linkedin')),
  content TEXT,
  posts JSONB,
  status VARCHAR DEFAULT 'draft' CHECK (status IN ('draft', 'posted')),
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);

-- ============================================================================
-- NEWSLETTER METRICS TABLE
-- ============================================================================
CREATE TABLE IF NOT EXISTS newsletter_metrics (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  newsletter_id UUID NOT NULL REFERENCES newsletters(id) ON DELETE CASCADE,
  metric_type VARCHAR NOT NULL,
  value DECIMAL(10,2),
  recorded_at TIMESTAMP DEFAULT NOW()
);

-- ============================================================================
-- CREATE INDEXES FOR PERFORMANCE
-- ============================================================================
CREATE INDEX idx_user_sources_user_id ON user_sources(user_id);
CREATE INDEX idx_newsletters_user_id ON newsletters(user_id);
CREATE INDEX idx_newsletters_created_at ON newsletters(created_at DESC);
CREATE INDEX idx_newsletter_feedback_newsletter_id ON newsletter_feedback(newsletter_id);
CREATE INDEX idx_newsletter_feedback_user_id ON newsletter_feedback(user_id);
CREATE INDEX idx_scheduled_deliveries_user_id ON scheduled_deliveries(user_id);
CREATE INDEX idx_edit_history_newsletter_id ON edit_history(newsletter_id);
CREATE INDEX idx_social_posts_user_id ON social_posts(user_id);

-- ============================================================================
-- ENABLE ROW LEVEL SECURITY (RLS)
-- ============================================================================
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_sources ENABLE ROW LEVEL SECURITY;
ALTER TABLE newsletters ENABLE ROW LEVEL SECURITY;
ALTER TABLE newsletter_feedback ENABLE ROW LEVEL SECURITY;
ALTER TABLE scheduled_deliveries ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_style_profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE edit_history ENABLE ROW LEVEL SECURITY;
ALTER TABLE review_timers ENABLE ROW LEVEL SECURITY;
ALTER TABLE social_posts ENABLE ROW LEVEL SECURITY;
ALTER TABLE newsletter_metrics ENABLE ROW LEVEL SECURITY;

-- ============================================================================
-- RLS POLICIES - Users can only access their own data
-- ============================================================================

-- Users table
CREATE POLICY "Users can only access their own data"
  ON users FOR SELECT USING (id = auth.uid());

-- User sources
CREATE POLICY "Users can only access their own sources"
  ON user_sources FOR ALL USING (user_id = auth.uid());

-- Newsletters
CREATE POLICY "Users can only access their own newsletters"
  ON newsletters FOR ALL USING (user_id = auth.uid());

-- Feedback
CREATE POLICY "Users can only access their own feedback"
  ON newsletter_feedback FOR ALL USING (user_id = auth.uid());

-- Scheduled deliveries
CREATE POLICY "Users can only access their own schedules"
  ON scheduled_deliveries FOR ALL USING (user_id = auth.uid());

-- Style profiles
CREATE POLICY "Users can only access their own style profiles"
  ON user_style_profiles FOR ALL USING (user_id = auth.uid());

-- Edit history
CREATE POLICY "Users can only access their own edits"
  ON edit_history FOR ALL USING (user_id = auth.uid());

-- Review timers
CREATE POLICY "Users can only access their own timers"
  ON review_timers FOR ALL USING (user_id = auth.uid());

-- Social posts
CREATE POLICY "Users can only access their own social posts"
  ON social_posts FOR ALL USING (user_id = auth.uid());

-- Newsletter metrics
CREATE POLICY "Users can only access their own metrics"
  ON newsletter_metrics FOR SELECT USING (
    newsletter_id IN (SELECT id FROM newsletters WHERE user_id = auth.uid())
  );
```

4. Click "Run" to execute the schema

### Step 4: Enable Authentication

1. Go to **Authentication → Providers** in Supabase
2. Enable "Email" (should be default)
3. Go to **Settings → Auth** and configure:
   - Site URL: `http://localhost:8501` (development)
   - Redirect URLs: Add your production URL later

---

## External Services Setup

### Groq API Setup

1. Go to https://console.groq.com
2. Sign up (free account)
3. Go to **API Keys**
4. Create new API key
5. Copy to `.env`:
   ```
   GROQ_API_KEY=gsk_your_key_here
   ```

### Gmail SMTP Configuration

**Step 1: Enable 2-Factor Authentication**

1. Go to https://myaccount.google.com/security
2. Scroll to "2-Step Verification"
3. Click "Enable"
4. Follow the prompts

**Step 2: Generate App Password**

1. Go to https://myaccount.google.com/apppasswords
2. Select:
   - App: "Mail"
   - Device: "Other (Custom name)"
   - Type: "CreatorPulse"
3. Click "Generate"
4. Google shows 16-character password
5. Copy the password (no spaces)
6. Add to `.env`:
   ```
   SENDER_EMAIL=your-email@gmail.com
   SENDER_EMAIL_PASSWORD=abcd efgh ijkl mnop
   ```

**Troubleshooting Email:**
- If you don't see "App passwords" option, enable 2FA first
- Make sure to copy the password exactly (with spaces)
- Use your full Gmail address (with @gmail.com)

### Telegram Bot Setup (Optional)

1. Open Telegram app
2. Search for **@BotFather**
3. Send `/newbot`
4. Follow prompts:
   - Bot name: "CreatorPulse Bot"
   - Username: "yourname_creatorpulse_bot"
5. BotFather sends you the bot token
6. Copy to `.env`:
   ```
   TELEGRAM_BOT_TOKEN=your_bot_token_here
   ```
7. Search for your bot in Telegram and send `/start`
8. In app, go to Settings → Telegram to get your Chat ID

### YouTube API Setup (Optional)

1. Go to https://console.cloud.google.com
2. Create new project
3. Enable **YouTube Data API v3**
4. Create API key under **Credentials**
5. Copy to `.env`:
   ```
   YOUTUBE_API_KEY=your_key_here
   ```

---

## Local Development

### Step 1: Verify All Environment Variables

Check that `.env` contains at minimum:
```
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_KEY=eyJ...
GROQ_API_KEY=gsk_...
```

### Step 2: Start the Application

```bash
streamlit run app.py
```

You'll see:
```
  You can now view your Streamlit app in your browser.

  Local URL: http://localhost:8501
```

### Step 3: Create Your Account

1. Go to http://localhost:8501
2. Click "Create Account" tab
3. Sign up with email and password
4. Log in

### Step 4: Configure Sources

1. Go to **Settings** tab
2. Test email (if configured):
   - Click "Send Test Email"
   - Check your inbox
3. Go to **RSS Sources** tab
4. Add your first source:
   - Select "TechCrunch"
   - Click "Add Source"

### Step 5: Generate First Newsletter

1. Go to **Create Newsletter** tab
2. Fill in:
   - Title: "My First Newsletter"
   - Topic: "Technology"
   - Tone: "Professional"
3. Click "Generate Newsletter"
4. Review the AI draft
5. Send or download

### Step 6: Test Style Training

1. Go to **Style Trainer** tab
2. Paste or upload 3-5 past newsletters
3. Click "Analyze & Save"
4. Next newsletters will match your style

---

## Production Deployment

### Option 1: Heroku Deployment

**Prerequisites:**
- Heroku account (free tier available)
- Heroku CLI installed

**Steps:**

1. Create `Procfile` in root:
```
web: streamlit run app.py --server.port=$PORT --server.address=0.0.0.0
```

2. Create `.streamlit/config.toml`:
```toml
[server]
port = 8501
headless = true

[client]
showErrorDetails = false
```

3. Deploy:
```bash
heroku login
heroku create creatorpulse-app
heroku config:set SUPABASE_URL=your_url
heroku config:set SUPABASE_KEY=your_key
heroku config:set GROQ_API_KEY=your_key
heroku config:set SENDER_EMAIL=your_email
heroku config:set SENDER_EMAIL_PASSWORD=your_password
git push heroku main
```

4. View logs:
```bash
heroku logs --tail
```

### Option 2: Railway Deployment

1. Push code to GitHub
2. Go to https://railway.app
3. Connect GitHub repo
4. Add environment variables in dashboard
5. Deploy

### Option 3: Render Deployment

1. Push code to GitHub
2. Go to https://render.com
3. Create "New Web Service"
4. Connect GitHub repo
5. Configure:
   - Build: `pip install -r requirements.txt`
   - Start: `streamlit run app.py`
6. Add environment variables
7. Deploy

### Background Scheduler in Production

The app includes a built-in background scheduler that:
- Runs every minute
- Checks `scheduled_deliveries` table
- Generates and sends newsletters via email/Telegram

It works automatically - no additional setup needed.

To verify it's running:
- Check app logs for "Background scheduler thread started"
- Scheduled newsletters should arrive at set time

---

## Troubleshooting

### Supabase Connection Failed

**Error:** "Failed to connect to Supabase"

**Solutions:**
1. Verify `SUPABASE_URL` and `SUPABASE_KEY` in `.env`
2. Check internet connection
3. Ensure Supabase project is active
4. Restart app

### Email Not Sending

**Error:** "Email not configured" or "SMTPAuthenticationError"

**Solutions:**
1. Verify `SENDER_EMAIL` and `SENDER_EMAIL_PASSWORD` in `.env`
2. Ensure Gmail 2FA is enabled
3. Use app password (16 chars), not regular password
4. No spaces in password
5. Restart app after changing `.env`

### No Articles Fetching

**Error:** "Could not fetch articles from any sources"

**Solutions:**
1. Verify RSS URLs are valid and accessible
2. Test RSS feed in browser
3. Check internet connection
4. Look for rate limiting errors (Google Trends)
5. Wait 60 seconds before retrying

### Scheduler Not Running

**Error:** Newsletters not arriving at scheduled time

**Solutions:**
1. Verify schedule time matches current time
2. Check timezone setting
3. Look for errors in Streamlit logs
4. Restart app
5. Verify email is configured (if using email delivery)

### Style Profile Not Loading

**Error:** "No active writing style profile found"

**Solutions:**
1. Upload at least 3 past newsletters
2. Use TXT or MD file format
3. Separate newsletters with `---`
4. Check for SQL errors in Supabase logs

### Python Import Errors

**Error:** "ModuleNotFoundError: No module named..."

**Solution:**
```bash
pip install -r requirements.txt --force-reinstall --no-cache-dir
```

### Port Already in Use

**Error:** "Address already in use"

**Solutions:**
```bash
# Kill process on port 8501
lsof -ti:8501 | xargs kill -9  # macOS/Linux

# Or use different port
streamlit run app.py --server.port 8502
```

---

## Security Checklist

- [ ] Never commit `.env` to version control
- [ ] Use `.env.example` as template
- [ ] Enable Supabase RLS on all tables
- [ ] Rotate API keys every 90 days
- [ ] Use app passwords for Gmail (not regular password)
- [ ] Enable 2FA on Gmail and Supabase accounts
- [ ] Monitor API usage to detect abuse
- [ ] Keep dependencies updated: `pip list --outdated`

---

## Support

- Documentation: See README.md
- Issues: GitHub Issues
- Email: support@creatorpulse.ai

**Version:** 1.0.0
**Last Updated:** January 2025
