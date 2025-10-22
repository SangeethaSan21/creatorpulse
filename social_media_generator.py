"""
Social Media Post Generator for CreatorPulse
Converts newsletter content into platform-optimized social posts
"""
from typing import List, Dict, Optional
from datetime import datetime, UTC
import re

def generate_social_posts(
    newsletter_content: str,
    articles: List[Dict],
    trends: List[Dict],
    platform: str,
    api_key: str,
    tone: str = "Professional"
) -> Dict:
    """
    Generate social media posts from newsletter content
    
    Args:
        newsletter_content: Full newsletter HTML/text
        articles: List of article dicts
        trends: List of trend dicts
        platform: 'twitter' or 'linkedin'
        api_key: Groq API key
        tone: Writing tone
    
    Returns:
        Dict with generated posts and metadata
    """
    try:
        from groq import Groq
        client = Groq(api_key=api_key)
        
        # Clean newsletter content for AI processing
        clean_content = clean_html_for_ai(newsletter_content)
        
        # Prepare context
        articles_summary = prepare_articles_summary(articles[:5])  # Top 5 articles
        trends_summary = prepare_trends_summary(trends[:3])  # Top 3 trends
        
        if platform == "twitter":
            posts = generate_twitter_thread(
                client, clean_content, articles_summary, trends_summary, tone
            )
        elif platform == "linkedin":
            posts = generate_linkedin_post(
                client, clean_content, articles_summary, trends_summary, tone
            )
        else:
            return {"error": "Unsupported platform"}
        
        return posts
        
    except Exception as e:
        print(f"Error generating social posts: {e}")
        return {"error": str(e)}


def generate_twitter_thread(
    client, content: str, articles: str, trends: str, tone: str
) -> Dict:
    """Generate a Twitter/X thread (multiple tweets)"""
    
    prompt = f"""
    Create a Twitter/X thread from this newsletter content. Follow these rules STRICTLY:
    
    RULES:
    - Each tweet must be UNDER 280 characters (including spaces)
    - Create 4-6 tweets total
    - First tweet: Hook that grabs attention
    - Middle tweets: Key insights (one per tweet)
    - Last tweet: Call-to-action
    - Use emojis sparingly (1-2 per tweet max)
    - Tone: {tone}
    - Number each tweet (1/, 2/, 3/, etc.)
    
    Newsletter Summary:
    {content[:500]}
    
    Key Articles:
    {articles}
    
    Trending Topics:
    {trends}
    
    Generate the thread now. Format each tweet on a new line starting with the number.
    """
    
    try:
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {
                    "role": "system",
                    "content": "You are a social media expert who creates engaging Twitter threads. Keep tweets under 280 characters."
                },
                {"role": "user", "content": prompt}
            ],
            max_tokens=1000,
            temperature=0.7
        )
        
        thread_text = completion.choices[0].message.content
        
        # Parse into individual tweets
        tweets = parse_twitter_thread(thread_text)
        
        # Validate length
        tweets = [truncate_tweet(t) for t in tweets]
        
        return {
            "platform": "twitter",
            "posts": tweets,
            "full_text": thread_text,
            "char_counts": [len(t) for t in tweets],
            "created_at": datetime.now(UTC).isoformat()
        }
        
    except Exception as e:
        print(f"Error generating Twitter thread: {e}")
        return {"error": str(e)}


def generate_linkedin_post(
    client, content: str, articles: str, trends: str, tone: str
) -> Dict:
    """Generate a LinkedIn post (single long-form post)"""
    
    prompt = f"""
    Create a LinkedIn post from this newsletter content. Follow these rules:
    
    RULES:
    - Length: 1200-1500 characters (LinkedIn sweet spot)
    - Structure: Hook → Key insights → Call-to-action
    - Use line breaks for readability
    - Professional tone but engaging
    - Include 3-5 relevant hashtags at the end
    - Tone: {tone}
    
    Newsletter Summary:
    {content[:600]}
    
    Key Articles:
    {articles}
    
    Trending Topics:
    {trends}
    
    Generate the LinkedIn post now.
    """
    
    try:
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {
                    "role": "system",
                    "content": "You are a LinkedIn content strategist who creates engaging professional posts."
                },
                {"role": "user", "content": prompt}
            ],
            max_tokens=1200,
            temperature=0.7
        )
        
        post_text = completion.choices[0].message.content
        
        # Extract hashtags
        hashtags = extract_hashtags(post_text)
        
        return {
            "platform": "linkedin",
            "posts": [post_text],  # Single post
            "full_text": post_text,
            "char_count": len(post_text),
            "hashtags": hashtags,
            "created_at": datetime.now(UTC).isoformat()
        }
        
    except Exception as e:
        print(f"Error generating LinkedIn post: {e}")
        return {"error": str(e)}


def clean_html_for_ai(html_content: str) -> str:
    """Remove HTML tags and clean content"""
    # Remove HTML tags
    clean = re.sub(r'<[^>]+>', '', html_content)
    # Clean whitespace
    clean = re.sub(r'\s+', ' ', clean).strip()
    # Limit length
    return clean[:1000]


def prepare_articles_summary(articles: List[Dict]) -> str:
    """Prepare articles for AI context"""
    summaries = []
    for i, article in enumerate(articles[:5], 1):
        summary = f"{i}. {article.get('title', 'Untitled')} - {article.get('summary', 'No summary')[:100]}"
        summaries.append(summary)
    return "\n".join(summaries)


def prepare_trends_summary(trends: List[Dict]) -> str:
    """Prepare trends for AI context"""
    summaries = []
    for i, trend in enumerate(trends[:3], 1):
        summary = f"{i}. {trend.get('trend_title', 'Unknown')} - {trend.get('explainer', 'No explanation')[:100]}"
        summaries.append(summary)
    return "\n".join(summaries)


def parse_twitter_thread(thread_text: str) -> List[str]:
    """Parse AI-generated thread into individual tweets"""
    # Split by common patterns: "1/", "2.", "Tweet 1:", etc.
    patterns = [
        r'\d+[/\.]',  # 1/, 2., etc.
        r'Tweet \d+:',
        r'\n\n'
    ]
    
    tweets = []
    current_tweet = ""
    
    for line in thread_text.split('\n'):
        line = line.strip()
        if not line:
            continue
        
        # Check if line starts a new tweet
        is_new_tweet = False
        for pattern in patterns:
            if re.match(pattern, line):
                is_new_tweet = True
                # Remove the numbering
                line = re.sub(r'^\d+[/\.\)]\s*', '', line)
                line = re.sub(r'^Tweet \d+:\s*', '', line)
                break
        
        if is_new_tweet and current_tweet:
            tweets.append(current_tweet.strip())
            current_tweet = line
        else:
            current_tweet += " " + line
    
    # Add last tweet
    if current_tweet:
        tweets.append(current_tweet.strip())
    
    # Fallback: if parsing failed, split by double newlines
    if len(tweets) == 0:
        tweets = [t.strip() for t in thread_text.split('\n\n') if t.strip()]
    
    return tweets[:6]  # Max 6 tweets


def truncate_tweet(tweet: str, max_length: int = 280) -> str:
    """Ensure tweet is under character limit"""
    if len(tweet) <= max_length:
        return tweet
    
    # Truncate and add ellipsis
    return tweet[:max_length-3] + "..."


def extract_hashtags(text: str) -> List[str]:
    """Extract hashtags from text"""
    return re.findall(r'#\w+', text)


def save_social_post(post_data: Dict, user_id: str, newsletter_id: Optional[str] = None) -> bool:
    """Save generated social post to database"""
    from supabase_client import get_supabase_client
    
    try:
        supabase = get_supabase_client()
        
        data = {
            "user_id": user_id,
            "newsletter_id": newsletter_id,
            "platform": post_data.get("platform"),
            "content": post_data.get("full_text"),
            "posts": post_data.get("posts"),  # Array of tweets or single post
            "status": "draft",
            "created_at": datetime.now(UTC).isoformat()
        }
        
        response = supabase.table("social_posts").insert(data).execute()
        
        if response.data:
            print(f"✅ Social post saved!")
            return True
        return False
        
    except Exception as e:
        print(f"Error saving social post: {e}")
        return False


def get_user_social_posts(user_id: str, platform: Optional[str] = None) -> List[Dict]:
    """Get saved social posts for user"""
    from supabase_client import get_supabase_client
    
    try:
        supabase = get_supabase_client()
        
        query = supabase.table("social_posts").select("*").eq("user_id", user_id)
        
        if platform:
            query = query.eq("platform", platform)
        
        response = query.order("created_at", desc=True).execute()
        
        return response.data or []
        
    except Exception as e:
        print(f"Error fetching social posts: {e}")
        return []


# ============================================================================
# TWITTER API INTEGRATION (Optional - requires API keys)
# ============================================================================

def post_to_twitter(tweets: List[str], api_credentials: Dict) -> bool:
    """
    Post thread to Twitter/X using API v2
    Requires: tweepy library and Twitter API credentials
    """
    try:
        import tweepy
        
        # Authenticate
        client = tweepy.Client(
            consumer_key=api_credentials.get("consumer_key"),
            consumer_secret=api_credentials.get("consumer_secret"),
            access_token=api_credentials.get("access_token"),
            access_token_secret=api_credentials.get("access_token_secret")
        )
        
        # Post thread
        previous_tweet_id = None
        
        for i, tweet in enumerate(tweets):
            if i == 0:
                # First tweet
                response = client.create_tweet(text=tweet)
                previous_tweet_id = response.data['id']
            else:
                # Reply to previous tweet
                response = client.create_tweet(
                    text=tweet,
                    in_reply_to_tweet_id=previous_tweet_id
                )
                previous_tweet_id = response.data['id']
        
        print(f"✅ Posted {len(tweets)} tweets to Twitter!")
        return True
        
    except ImportError:
        print("❌ tweepy not installed. Run: pip install tweepy")
        return False
    except Exception as e:
        print(f"❌ Error posting to Twitter: {e}")
        return False


def post_to_linkedin(content: str, api_credentials: Dict) -> bool:
    """
    Post to LinkedIn using their API
    Requires: LinkedIn API credentials
    """
    try:
        import requests
        
        access_token = api_credentials.get("access_token")
        person_urn = api_credentials.get("person_urn")
        
        url = "https://api.linkedin.com/v2/ugcPosts"
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
            "X-Restli-Protocol-Version": "2.0.0"
        }
        
        payload = {
            "author": f"urn:li:person:{person_urn}",
            "lifecycleState": "PUBLISHED",
            "specificContent": {
                "com.linkedin.ugc.ShareContent": {
                    "shareCommentary": {
                        "text": content
                    },
                    "shareMediaCategory": "NONE"
                }
            },
            "visibility": {
                "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"
            }
        }
        
        response = requests.post(url, headers=headers, json=payload)
        
        if response.status_code == 201:
            print("✅ Posted to LinkedIn!")
            return True
        else:
            print(f"❌ LinkedIn API error: {response.status_code}")
            return False
        
    except Exception as e:
        print(f"❌ Error posting to LinkedIn: {e}")
        return False