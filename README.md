# CreatorPulse - Complete Project Documentation

## Table of Contents
1. [Project Overview](#project-overview)
2. [Tech Stack](#tech-stack)
3. [Architecture](#architecture)
4. [Setup Guide](#setup-guide)
5. [README](#readme)
6. [Database Schema](#database-schema)
7. [API Documentation](#api-documentation)
8. [Deployment Guide](#deployment-guide)

---

## Project Overview

**CreatorPulse** is an AI-powered newsletter curation platform that aggregates content from multiple sources (RSS, Twitter, YouTube), generates trend insights, and produces AI-drafted newsletters ready for user review and distribution.

### Key Features
- Multi-source content aggregation (RSS, Twitter, YouTube)
- AI-powered trend detection with Google Trends integration
- Intelligent newsletter generation with style training
- Writing style analysis and voice matching
- Scheduled newsletter delivery (Email + Telegram)
- Comprehensive analytics and feedback tracking
- Social media post generation (Twitter threads, LinkedIn)
- Edit history and performance metrics

### Business Metrics
- Target: Draft acceptance rate ≥ 70%
- Target: Review time ≤ 20 minutes
- Target: Engagement uplift ≥ 2x baseline

---

## Tech Stack

### Frontend
- **Framework**: Streamlit (Python)
- **Styling**: Custom CSS (TailwindCSS concepts)
- **Charts**: Recharts, Chart.js
- **Components**: shadcn/ui

### Backend
- **Language**: Python 3.9+
- **Web Framework**: Streamlit
- **Task Scheduling**: APScheduler, Schedule
- **API Client**: Groq (LLM), Supabase (Database)

### AI/ML
- **LLM**: Groq Llama 3.3 70B (via API)
- **Trend Detection**: Google Trends API (pytrends)
- **Web Scraping**: Nitter (Twitter), YouTube API
- **Feed Parsing**: feedparser

### Database
- **Primary**: Supabase (PostgreSQL)
- **Auth**: Supabase Auth
- **Real-time**: Supabase Realtime (optional)

### External Services
- **Email**: Gmail SMTP
- **Messaging**: Telegram Bot API
- **Scraping**: Firecrawl (optional), Twitter Scraper
- **Content Parsing**: feedparser, BeautifulSoup

### Deployment
- **Hosting**: Heroku / Railway / Render / AWS EC2
- **Background Jobs**: APScheduler (on-process)
- **Monitoring**: Sentry (optional)

### Development Tools
- **Version Control**: Git
- **Package Manager**: pip
- **Environment**: python-dotenv
- **Testing**: pytest (optional)

---

## Architecture

### High-Level Flow

```
User Input
    ↓
[Source Management] (RSS, Twitter, YouTube)
    ↓
[Content Aggregator] → [Trend Detector]
    ↓
[Style Profile Retrieval]
    ↓
[AI Newsletter Generator]
    ↓
[Draft Review & Editing]
    ↓
[Scheduler] → [Email/Telegram Delivery]
    ↓
[Feedback System] → [Analytics]
```

### Module Organization

```
creatorpulse/
├── app.py                      # Main Streamlit app
├── auth.py                     # Authentication (Supabase)
├── content_aggregator.py       # RSS, Twitter, YouTube scraping
├── draft_generator.py          # AI newsletter generation (Groq)
├── email_service.py            # Email + Telegram delivery
├── feedback_system.py          # User feedback & analytics
├── models.py                   # Database models (CRUD)
├── style_trainer.py            # Writing style analysis
├── social_media_generator.py   # Social post generation
├── supabase_client.py          # Shared Supabase instance
├── scheduler_service.py        # Background task scheduler
├── utils.py                    # Helper functions
├── requirements.txt            # Python dependencies
├── .env.example                # Environment template
├── .streamlit/config.toml       # Streamlit config
└── README.md                   # Project documentation
```

### Database Schema (Key Tables)

```sql
-- Users
users:
  - id (UUID, PK)
  - email (VARCHAR)
  - username (VARCHAR, UNIQUE)
  - created_at (TIMESTAMP)

-- Content Sources
user_sources:
  - id (UUID, PK)
  - user_id (UUID, FK)
  - name (VARCHAR)
  - url (VARCHAR)
  - type (ENUM: rss_feed, twitter_handle, twitter_hashtag, youtube_channel)
  - category (VARCHAR)
  - active (BOOLEAN)
  - created_at (TIMESTAMP)

-- Newsletters
newsletters:
  - id (UUID, PK)
  - user_id (UUID, FK)
  - title (VARCHAR)
  - content (TEXT/HTML)
  - status (ENUM: draft, sent, published)
  - trends (JSONB)
  - topic (VARCHAR)
  - tone (VARCHAR)
  - created_at (TIMESTAMP)

-- Feedback
newsletter_feedback:
  - id (UUID, PK)
  - newsletter_id (UUID, FK)
  - user_id (UUID, FK)
  - reaction (ENUM: thumbs_up, thumbs_down)
  - created_at (TIMESTAMP)

-- Scheduling
scheduled_deliveries:
  - id (UUID, PK)
  - user_id (UUID, FK)
  - schedule_time (TIME)
  - timezone (VARCHAR)
  - delivery_method (ENUM: email, telegram, both)
  - is_active (BOOLEAN)
  - last_delivered_at (TIMESTAMP)

-- Style Profiles
user_style_profiles:
  - id (UUID, PK)
  - user_id (UUID, FK)
  - style_profile (JSONB)
  - custom_prompt (TEXT)
  - updated_at (TIMESTAMP)

-- Edits & Analytics
edit_history:
  - id (UUID, PK)
  - newsletter_id (UUID, FK)
  - user_id (UUID, FK)
  - original_content (TEXT)
  - edited_content (TEXT)
  - edit_metrics (JSONB)
  - created_at (TIMESTAMP)

review_timers:
  - id (UUID, PK)
  - newsletter_id (UUID, FK)
  - user_id (UUID, FK)
  - started_at (TIMESTAMP)
  - ended_at (TIMESTAMP)
  - duration_minutes (DECIMAL)
  - status (ENUM: active, completed)

social_posts:
  - id (UUID, PK)
  - user_id (UUID, FK)
  - newsletter_id (UUID, FK)
  - platform (ENUM: twitter, linkedin)
  - content (TEXT)
  - posts (JSONB)
  - status (ENUM: draft, posted)
  - created_at (TIMESTAMP)
```

---

## Setup Guide

### Prerequisites
- Python 3.9 or higher
- Git
- Supabase account (free tier available)
- Groq API key (free tier available)
- Gmail account (for SMTP)
- Telegram account (for bot delivery)

### Step 1: Clone Repository

```bash
git clone https://github.com/yourusername/creatorpulse.git
cd creatorpulse
```

### Step 2: Create Virtual Environment

```bash
# macOS/Linux
python3 -m venv venv
source venv/bin/activate

# Windows
python -m venv venv
venv\Scripts\activate
```

### Step 3: Install Dependencies

```bash
pip install -r requirements.txt
```

### Step 4: Set Up Environment Variables

```bash
cp .env.example .env
```

Edit `.env` with your credentials:

```env
# Supabase
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-anon-key

# AI/LLM
GROQ_API_KEY=your-groq-api-key

# Email Configuration
SENDER_EMAIL=your-email@gmail.com
SENDER_EMAIL_PASSWORD=your-app-password

# Telegram (Optional)
TELEGRAM_BOT_TOKEN=your-bot-token

# YouTube API (Optional)
YOUTUBE_API_KEY=your-youtube-api-key

# Environment
ENVIRONMENT=development
```

### Step 5: Set Up Supabase Database

1. Create a new Supabase project
2. Navigate to SQL Editor
3. Execute the SQL schema (see Database Schema section)
4. Enable Row Level Security (RLS) for all tables

### Step 6: Run Application

```bash
streamlit run app.py
```

Access at: http://localhost:8501

### Step 7: Create Account & Configure

1. Sign up with email
2. Go to Settings tab
3. Configure email (Gmail SMTP with App Password)
4. Optional: Set up Telegram bot
5. Add RSS/content sources
6. Upload past newsletters for style training

---

## README

# CreatorPulse - AI-Powered Newsletter Curator

Turn hours of research into minutes of curation. CreatorPulse aggregates your content sources, detects emerging trends, and generates AI-drafted newsletters ready to send.

## Features

- **Multi-Source Aggregation**: Combine RSS feeds, Twitter, YouTube, and newsletters
- **Trend Detection**: Real-time spike detection using Google Trends
- **AI Newsletter Generation**: Groq Llama 3.3 powered drafts
- **Writing Style Training**: AI learns your voice from past newsletters
- **Scheduled Delivery**: Automated morning newsletter generation
- **Email + Telegram**: Flexible delivery options
- **Edit Tracking**: Version history with diff visualization
- **Performance Analytics**: Track open rates, CTR, review times
- **Social Media**: Convert newsletters into Twitter threads or LinkedIn posts

## Quick Start

### 1. Prerequisites

```
Python 3.9+
Supabase account (free)
Groq API key (free)
Gmail account
```

### 2. Installation

```bash
git clone https://github.com/yourusername/creatorpulse.git
cd creatorpulse
python -m venv venv
source venv/bin/activate  # or: venv\Scripts\activate (Windows)
pip install -r requirements.txt
```

### 3. Configuration

```bash
cp .env.example .env
# Edit .env with your credentials
streamlit run app.py
```

### 4. First Run

1. Sign up for account
2. Add content sources (Settings tab)
3. Upload past newsletters for style training
4. Generate your first newsletter

## Key Workflows

### Generate Newsletter

1. Click "Create Newsletter"
2. Select title, topic, tone
3. Click "Generate Newsletter"
4. Review AI draft
5. Edit if needed
6. Send via email or save

### Schedule Daily Delivery

1. Go to "Scheduler" tab
2. Set delivery time and timezone
3. Choose email or Telegram
4. Save schedule
5. Background scheduler sends drafts each morning

### Train Writing Style

1. Go to "Style Trainer" tab
2. Upload 3-10 past newsletters
3. Click "Analyze & Save"
4. AI learns your voice automatically

## Environment Variables

```env
# Required
SUPABASE_URL=
SUPABASE_KEY=
GROQ_API_KEY=

# Email (optional but recommended)
SENDER_EMAIL=
SENDER_EMAIL_PASSWORD=

# Telegram (optional)
TELEGRAM_BOT_TOKEN=

# YouTube (optional)
YOUTUBE_API_KEY=
```

## Database

Uses Supabase PostgreSQL with automatic schema creation. Supports:
- Row-level security
- Real-time subscriptions
- Automated backups

## Performance Targets

- Newsletter review time: ≤ 20 minutes
- Draft acceptance rate: ≥ 70%
- Engagement uplift: ≥ 2x baseline

## Troubleshooting

### Email Not Sending

1. Check `.env` has SENDER_EMAIL and SENDER_EMAIL_PASSWORD
2. Verify Gmail App Password (not regular password)
3. Enable "Less secure apps" if needed
4. Check console for error messages

### No Articles Fetching

1. Verify RSS URLs are valid
2. Check internet connection
3. Ensure Supabase is connected
4. Look for 403 rate limit errors

### Scheduler Not Running

1. Check `scheduler_thread_started` in logs
2. Ensure time is set correctly
3. Verify timezone setting

## API Rate Limits

- Google Trends: ~200 requests/day
- YouTube: 10,000 units/day (free tier)
- Groq: Varies by plan
- Twitter: See Nitter limits

Recommendations:
- Cache results where possible
- Batch requests
- Use delays between API calls

## Future Roadmap

- Beehiiv/Substack API integration
- Browser extension for content clipping
- Multi-language newsletter generation
- Advanced analytics dashboard
- API endpoint for external apps
- Team collaboration features
- Custom publication branding

## Support

For issues, questions, or feature requests:
- GitHub Issues: [project-issues]
- Email: support@creatorpulse.ai
- Documentation: [docs-site]

## License

MIT License - See LICENSE file

## Contributing

Contributions welcome! Please:
1. Fork the repository
2. Create feature branch
3. Commit changes
4. Push and create pull request

---

## Database Schema

See complete schema in SETUP_GUIDE.md (Supabase section)

---

## API Documentation

### Content Aggregator

```python
# Fetch from RSS
articles = parse_rss_feed(url, max_articles=8)

# Fetch from all sources
articles = aggregate_all_sources(
    rss_feeds=['url1', 'url2'],
    twitter_handles=['handle1'],
    twitter_hashtags=['hashtag1'],
    youtube_channels=['channel1']
)

# Detect trends
trends = detect_trending_topics(articles, use_google_trends=True)
```

### Newsletter Generation

```python
content = generate_newsletter_with_ai(
    articles=articles,
    trends=trends,
    title="Daily Digest",
    topic="Technology",
    tone="Professional",
    api_key=GROQ_API_KEY,
    user_id=user_id,
    max_articles=6
)
```

### Email Delivery

```python
send_newsletter_email(
    recipient_email="user@example.com",
    subject="Your Daily Newsletter",
    html_content=content
)

send_test_email(recipient_email="user@example.com")
```

### Telegram Delivery

```python
send_newsletter_via_telegram(
    chat_id="123456789",
    newsletter_title="Daily Digest",
    newsletter_content=html_content
)

send_test_telegram(chat_id="123456789")
```

### Analytics

```python
# Feedback stats
stats = get_feedback_stats(user_id, days=30)

# Engagement analytics
analytics = get_engagement_analytics(user_id, days=30)

# Review time tracking
time_stats = get_average_review_time(user_id, days=30)

# Edit patterns
edit_patterns = get_edit_patterns(user_id, days=30)
```

---

## Deployment Guide

### Local Development

```bash
streamlit run app.py
```

Access at `http://localhost:8501`

### Production Deployment

#### Option 1: Heroku

```bash
# Install Heroku CLI
# Login
heroku login

# Create app
heroku create creatorpulse

# Set environment variables
heroku config:set SUPABASE_URL=xxx
heroku config:set SUPABASE_KEY=xxx
heroku config:set GROQ_API_KEY=xxx
# ... (add all env vars)

# Create Procfile
echo "web: streamlit run app.py --server.port=\$PORT" > Procfile

# Deploy
git push heroku main
```

#### Option 2: Railway

```bash
# Install Railway CLI
# Login
railway login

# Initialize project
railway init

# Add environment variables via dashboard
# Deploy
railway up
```

#### Option 3: Render

1. Push code to GitHub
2. Connect GitHub repo to Render
3. Add environment variables
4. Deploy

#### Background Scheduler

The app includes a built-in background scheduler. For production:

```python
# scheduler_thread_started in session_state
# Runs every minute checking scheduled_deliveries table
# Sends newsletters via email or Telegram
```

### Monitoring

Add Sentry for error tracking:

```python
import sentry_sdk
sentry_sdk.init("your-sentry-dsn")
```

### Database Backups

Supabase provides:
- Daily automated backups
- Point-in-time recovery
- Export to CSV

---

## Performance Optimization

### Caching Strategies

```python
# Cache feed results for 1 hour
@cache
def parse_rss_feed(url):
    ...

# Cache AI responses
cache.set(f"newsletter_{user_id}", content, ttl=3600)
```

### Database Query Optimization

```python
# Use indexes on frequently queried columns
# user_id, created_at, newsletter_id

# Batch operations
supabase.table("feedback").insert(batch_data).execute()

# Use pagination for large result sets
response = supabase.table("newsletters").select("*").limit(20).offset(0)
```

### API Rate Limiting

```python
# Implement exponential backoff
import time
for attempt in range(max_retries):
    try:
        response = api.call()
        break
    except RateLimitError:
        time.sleep(2 ** attempt)
```

---

## Security Best Practices

### Environment Variables

- Never commit `.env` to version control
- Use `.env.example` as template
- Rotate API keys regularly

### Database

- Enable Row Level Security (RLS)
- Use service role key only for backend
- Restrict user queries via policies

### API Keys

- Store in environment variables only
- Never expose in frontend
- Use short-lived tokens where possible

### Email

- Use app passwords, not regular passwords
- Enable 2FA on Gmail account
- Monitor for unauthorized access

---

## Troubleshooting Guide

### Common Issues

**Email not configured error**
- Set SENDER_EMAIL and SENDER_EMAIL_PASSWORD
- Use Gmail app password (16 chars, no spaces)
- Restart app after changing .env

**Supabase connection failed**
- Verify SUPABASE_URL and SUPABASE_KEY
- Check internet connection
- Ensure Supabase project is running

**No articles fetching**
- Verify RSS URLs are accessible
- Check Google rate limiting
- Add delays between requests

**Scheduler not triggering**
- Confirm schedule time matches current time
- Check timezone setting
- Look for errors in Streamlit logs

**Style profile not loading**
- Upload at least 3 past newsletters
- Check file format (TXT or MD)
- Verify JSONB storage in database

---

## Contributing

To contribute:

1. Fork repository
2. Create feature branch: `git checkout -b feature/amazing-feature`
3. Commit changes: `git commit -m 'Add amazing feature'`
4. Push to branch: `git push origin feature/amazing-feature`
5. Open Pull Request

## Support & Contact

- Email: support@creatorpulse.ai
- GitHub Issues: [project-issues]
- Documentation: [docs-site]
- Twitter: [@creatorpulse]

---

**Last Updated**: January 2025
**Version**: 1.0.0
**Status**: Production Ready
