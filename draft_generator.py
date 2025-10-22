import os
from groq import Groq
from datetime import datetime
from typing import List, Dict, Optional
import json
import re
from style_trainer import get_style_profile, generate_style_prompt


def generate_newsletter_with_ai(
    articles: List[Dict],
    trends: List[Dict],
    title: str,
    topic: str,
    tone: str,
    api_key: str,
    user_id: Optional[str] = None,
    max_articles: int = 6
) -> str:
    """
    Generate a concise, scannable AI newsletter (industry standard format).
    """

    client = Groq(api_key=api_key)

    # Merge title + topic naturally
    combined_title = f"{title.strip()} {topic.strip()}" if topic.lower() not in title.lower() else title.strip()

    rss_articles = [a for a in articles if a.get('source') not in ['Twitter', 'YouTube']]
    twitter_posts = [a for a in articles if a.get('source') == 'Twitter']
    youtube_videos = [a for a in articles if a.get('source') == 'YouTube']

    print(f"\n📊 Content Breakdown: RSS={len(rss_articles)}, Twitter={len(twitter_posts)}, YouTube={len(youtube_videos)}")
    print(f"🎯 Target max_articles: {max_articles}")

    if len(rss_articles) < 1:
        print("⚠️ No RSS articles found, using template-only mode")
        return create_template_only_newsletter(
            combined_title, topic, tone, rss_articles, twitter_posts, youtube_videos, trends
        )

    # ✅ Process articles
    articles_to_process = rss_articles[:max_articles]
    print(f"\n🔄 Processing {len(articles_to_process)} articles...")

    # ✅ IMPROVED: Generate SHORT, scannable summaries (2-3 sentences)
    article_summaries = []
    
    for i, article in enumerate(articles_to_process, 1):
        print(f"🧠 Summarizing article {i}/{len(articles_to_process)}: {article['title'][:60]}...")

        # ✅ NEW: Short summary prompt (not essay)
        summary_prompt = f"""
You are a professional newsletter editor. Write a CONCISE 2-3 sentence summary of this article.

Article Title: {article['title']}
Article Text: {article['summary']}

Requirements:
- Maximum 3 sentences (50-80 words total)
- First sentence: What happened
- Second sentence: Why it matters
- Third sentence (optional): Key implication
- {tone} tone
- No fluff, no filler phrases
- Get straight to the point

Write ONLY the summary, nothing else.
"""

        try:
            response = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": "You write concise, punchy newsletter summaries. No essays. Maximum 3 sentences."},
                    {"role": "user", "content": summary_prompt}
                ],
                temperature=0.4,
                max_tokens=150  # ✅ REDUCED from 900 to 150 (forces brevity)
            )

            summary = response.choices[0].message.content.strip()
            article_summaries.append(summary)
            print(f"  ✅ Summary {i} generated ({len(summary)} chars)")
            
        except Exception as e:
            print(f"  ❌ Error generating summary for article {i}: {e}")
            # Fallback: Use first 2 sentences of original summary
            fallback = '. '.join(article['summary'].split('.')[:2]) + '.'
            article_summaries.append(fallback)

    print(f"\n✅ Generated {len(article_summaries)} concise summaries")

    # ✅ IMPROVED: Short intro (50-100 words)
    trend_titles = ", ".join([t["trend_title"] for t in trends[:3]]) if trends else "key topics"

    intro_prompt = f"""
Write a brief 50-75 word welcome paragraph for the newsletter "{combined_title}".

Include:
- Quick welcome
- Today's focus: {trend_titles}
- {tone} tone

Keep it SHORT and punchy. No lengthy explanations.
"""

    intro_response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": "You write concise newsletter intros. Maximum 75 words."},
            {"role": "user", "content": intro_prompt}
        ],
        temperature=0.5,
        max_tokens=150  # ✅ REDUCED from 400
    )

    intro = intro_response.choices[0].message.content.strip()

    # ✅ IMPROVED: Short conclusion (2-3 sentences)
    conclusion_prompt = f"""
Write a brief 2-3 sentence closing for "{combined_title}".

Include:
- Thanks for reading
- Invitation to stay tuned
- {tone} tone

Maximum 40 words.
"""

    conclusion_response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": "You write brief, friendly newsletter conclusions. Maximum 3 sentences."},
            {"role": "user", "content": conclusion_prompt}
        ],
        temperature=0.4,
        max_tokens=80  # ✅ REDUCED from 250
    )

    conclusion = conclusion_response.choices[0].message.content.strip()

    print(f"✅ Newsletter generated successfully. Intro + {len(article_summaries)} summaries + conclusion")

    # ✅ Send to HTML builder (NO duplicate "Full Articles" section)
    return create_html_newsletter_v3(
        title=combined_title,
        topic=topic,
        tone=tone,
        intro=intro,
        article_summaries=article_summaries,
        conclusion=conclusion,
        rss_articles=articles_to_process,
        twitter_posts=twitter_posts[:3],
        youtube_videos=youtube_videos[:3],
        trends=trends[:5],
    )


def create_template_only_newsletter(
    title: str,
    topic: str,
    tone: str,
    rss_articles: List[Dict],
    twitter_posts: List[Dict],
    youtube_videos: List[Dict],
    trends: List[Dict],
) -> str:
    """Create newsletter WITHOUT AI - only uses provided content."""

    intro = f"Welcome to {title}! Today we're covering {len(rss_articles)} articles"
    if twitter_posts:
        intro += f", {len(twitter_posts)} tweets"
    if youtube_videos:
        intro += f", and {len(youtube_videos)} videos"
    intro += f" in {topic}."

    conclusion = f"Thanks for reading! Stay tuned for more {topic} updates."

    return create_html_newsletter_v3(
        title=title,
        topic=topic,
        tone=tone,
        intro=intro,
        article_summaries=[],
        conclusion=conclusion,
        rss_articles=rss_articles,
        twitter_posts=twitter_posts,
        youtube_videos=youtube_videos,
        trends=trends,
    )


# ✅ NEW HTML GENERATOR (Concise, scannable format)
def create_html_newsletter_v3(
    title: str,
    topic: str,
    tone: str,
    intro: str,
    article_summaries: List[str],
    conclusion: str,
    rss_articles: List[Dict],
    twitter_posts: List[Dict],
    youtube_videos: List[Dict],
    trends: List[Dict],
) -> str:
    """
    Create HTML newsletter - CONCISE, SCANNABLE format.
    Industry standard: No duplicate content, short summaries.
    """

    print(f"\n🎨 HTML Generation:")
    print(f"  - Concise summaries: {len(article_summaries)}")
    print(f"  - RSS Articles: {len(rss_articles)}")
    print(f"  - Twitter Posts: {len(twitter_posts)}")
    print(f"  - YouTube Videos: {len(youtube_videos)}")
    print(f"  - Trends: {len(trends)}")

    # --- Trends Section ---
    trends_html = ""
    if trends:
        trends_html = """
            <section style="padding: 20px 0;">
                <h2 style="color: #3b82f6; margin-bottom: 15px; font-size: 20px;">🔥 Trending Today</h2>
                <div style="background: #f0f9ff; padding: 15px; border-radius: 8px; border-left: 4px solid #3b82f6;">
        """
        trend_items = []
        for trend in trends[:3]:
            trend_items.append(f"<strong>{trend['trend_title']}</strong>")
        
        trends_html += f"<p style='margin: 0; color: #1e293b;'>Key topics today: {', '.join(trend_items)}</p>"
        trends_html += """
                </div>
            </section>
        """

    # ✅ MAIN SECTION: Articles with SHORT summaries (NO DUPLICATES)
    articles_html = ""
    if rss_articles and article_summaries:
        articles_html = f"""
            <section style="padding: 20px 0;">
                <h2 style="color: #1e293b; margin-bottom: 20px; font-size: 22px; border-bottom: 2px solid #e2e8f0; padding-bottom: 10px;">📰 Today's Top Stories</h2>
        """
        
        for i, (article, summary) in enumerate(zip(rss_articles, article_summaries), 1):
            articles_html += f"""
                <article style="margin-bottom: 25px; padding-bottom: 20px; border-bottom: 1px solid #e2e8f0;">
                    <h3 style="margin: 0 0 8px 0; font-size: 18px; line-height: 1.4;">
                        <a href="{article['link']}" target="_blank" style="color: #1e293b; text-decoration: none;">
                            {i}. {article['title']}
                        </a>
                    </h3>
                    <p style="color: #64748b; margin: 0 0 10px 0; font-size: 13px;">
                        📍 {article['source']} · 📅 {article['published'][:15]}
                    </p>
                    <p style="color: #475569; margin: 0 0 10px 0; line-height: 1.6; font-size: 15px;">
                        {summary}
                    </p>
                    <a href="{article['link']}" target="_blank" style="color: #3b82f6; text-decoration: none; font-weight: 600; font-size: 14px;">
                        Read full story →
                    </a>
                </article>
            """
        
        articles_html += "</section>"

    # --- Twitter Section (Compact) ---
    twitter_html = ""
    if twitter_posts:
        twitter_html = """
            <section style="padding: 20px 0;">
                <h2 style="color: #1da1f2; margin-bottom: 15px; font-size: 20px;">🐦 From Twitter</h2>
        """
        for tweet in twitter_posts:
            engagement = tweet.get("engagement", {})
            likes = engagement.get("likes", 0)
            twitter_html += f"""
                <div style="background: #f8fafc; padding: 15px; margin-bottom: 15px; border-radius: 8px; border-left: 3px solid #1da1f2;">
                    <p style="color: #64748b; margin: 0 0 8px 0; font-size: 13px;">
                        <strong>{tweet['author']}</strong> · {tweet['published'][:15]}
                    </p>
                    <p style="color: #1e293b; margin: 0; line-height: 1.5; font-size: 15px;">
                        {tweet['summary'][:200]}{'...' if len(tweet['summary']) > 200 else ''}
                    </p>
                    <p style="color: #64748b; margin: 8px 0 0 0; font-size: 13px;">
                        ❤️ {likes} · <a href="{tweet['link']}" style="color: #1da1f2; text-decoration: none;">View tweet →</a>
                    </p>
                </div>
            """
        twitter_html += "</section>"

    # --- YouTube Section (Compact) ---
    youtube_html = ""
    if youtube_videos:
        youtube_html = """
            <section style="padding: 20px 0;">
                <h2 style="color: #ff0000; margin-bottom: 15px; font-size: 20px;">🎥 Watch This</h2>
        """
        for video in youtube_videos:
            youtube_html += f"""
                <div style="background: #fef2f2; padding: 15px; margin-bottom: 15px; border-radius: 8px; border-left: 3px solid #ff0000;">
                    <h3 style="margin: 0 0 8px 0; font-size: 16px;">
                        <a href="{video['link']}" target="_blank" style="color: #1e293b; text-decoration: none;">
                            🎬 {video['title']}
                        </a>
                    </h3>
                    <p style="color: #64748b; margin: 0 0 10px 0; font-size: 13px;">
                        📺 {video['author']} · {video['published'][:15]}
                    </p>
                    <a href="{video['link']}" target="_blank" style="display: inline-block; padding: 6px 12px; background: #ff0000; color: white; text-decoration: none; border-radius: 4px; font-size: 13px;">
                        ▶️ Watch Now
                    </a>
                </div>
            """
        youtube_html += "</section>"

    # --- FINAL HTML ---
    html = f"""
        <div style="max-width: 600px; margin: 0 auto; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; color: #333; background: #ffffff;">
            
            <!-- Header -->
            <header style="text-align: center; padding: 30px 20px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white;">
                <h1 style="margin: 0 0 5px 0; font-size: 26px; font-weight: 700;">{title}</h1>
                <p style="margin: 0; font-size: 14px; opacity: 0.9;">
                    {topic} · {datetime.now().strftime('%B %d, %Y')}
                </p>
            </header>

            <!-- Intro -->
            <section style="padding: 25px 20px 15px 20px;">
                <p style="color: #1e293b; line-height: 1.6; margin: 0; font-size: 15px;">
                    {intro}
                </p>
            </section>

            <!-- Trends -->
            <div style="padding: 0 20px;">
                {trends_html}
            </div>

            <!-- Main Articles -->
            <div style="padding: 0 20px;">
                {articles_html}
            </div>

            <!-- Twitter -->
            <div style="padding: 0 20px;">
                {twitter_html}
            </div>

            <!-- YouTube -->
            <div style="padding: 0 20px;">
                {youtube_html}
            </div>

            <!-- Conclusion -->
            <section style="padding: 20px; background: #f8fafc; margin: 20px 20px 0 20px; border-radius: 8px;">
                <p style="color: #475569; line-height: 1.6; margin: 0; font-size: 14px; text-align: center;">
                    {conclusion}
                </p>
            </section>

            <!-- Footer -->
            <footer style="text-align: center; padding: 20px; color: #94a3b8; font-size: 12px;">
                <p style="margin: 0;">CreatorPulse · {datetime.now().strftime('%B %d, %Y')}</p>
            </footer>
        </div>
    """
    return html