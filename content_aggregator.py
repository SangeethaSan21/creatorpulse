import feedparser
import requests
from datetime import datetime, timedelta
from collections import Counter
import re
from typing import List, Dict, Optional
import os
import requests

def validate_rss_feed(url: str) -> bool:
    """Validate if URL is a working RSS feed"""
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            # Try to parse as RSS
            feed = feedparser.parse(response.content)
            return len(feed.entries) > 0
        return False
    except Exception:
        return False

def parse_rss_feed(rss_url: str, max_articles: int = 8) -> List[Dict]:
    """Fetch articles from RSS feed and return structured data"""
    try:
        print(f"\n📡 Parsing feed: {rss_url}")
        feed = feedparser.parse(rss_url)
        articles = []

        if hasattr(feed, 'bozo') and feed.bozo:
            print(f"⚠️ Warning: Possibly malformed RSS feed: {rss_url}")

        print(f"  Found {len(feed.entries)} total entries in feed")

        for i, entry in enumerate(feed.entries[:max_articles]):
            # Clean and extract article data
            article = {
                "title": getattr(entry, "title", "Untitled"),
                "link": getattr(entry, "link", ""),
                "summary": clean_html(getattr(entry, "summary", "")),
                "published": format_publish_date(getattr(entry, "published", "")),
                "author": getattr(entry, "author", "Unknown"),
                "source": getattr(feed.feed, "title", "Unknown Source"),
                "tags": extract_tags(entry)
            }
            
            # Only add articles with valid title and link
            if article["title"] and article["link"]:
                articles.append(article)
                print(f"  ✅ Article {i+1}: {article['title'][:60]}...")
            else:
                print(f"  ❌ Skipped article {i+1}: missing title or link")

        print(f"  📊 Extracted {len(articles)} valid articles from {rss_url}")
        return articles
    except Exception as e:
        print(f"❌ Error parsing RSS feed {rss_url}: {e}")
        import traceback
        traceback.print_exc()
        return []

def parse_multiple_feeds(rss_urls: List[str], max_articles_per_feed: int = 5) -> List[Dict]:
    """Parse multiple RSS feeds and combine results"""
    print(f"\n🔄 Parsing {len(rss_urls)} RSS feeds...")
    all_articles = []
    
    for url in rss_urls:
        try:
            articles = parse_rss_feed(url, max_articles_per_feed)
            all_articles.extend(articles)
            print(f"✅ {url}: Added {len(articles)} articles")
        except Exception as e:
            print(f"❌ Failed to parse {url}: {e}")
            continue
    
    print(f"\n📊 Total articles before deduplication: {len(all_articles)}")
    
    # Remove duplicates based on title similarity
    unique_articles = remove_duplicate_articles(all_articles)
    
    print(f"📊 Total articles after deduplication: {len(unique_articles)}")
    
    # Sort by publication date (most recent first)
    unique_articles.sort(key=lambda x: parse_date(x.get("published", "")), reverse=True)
    
    return unique_articles

def remove_duplicate_articles(articles: List[Dict]) -> List[Dict]:
    """Remove duplicate articles based on title similarity AND source type"""
    print(f"\n🔍 Deduplication process:")
    print(f"  Input: {len(articles)} articles")
    
    unique_articles = []
    seen_keys = set()
    removed_count = 0
    
    for i, article in enumerate(articles):
        # Get title, source, and link
        title = article.get("title", "")
        source = article.get("source", "")
        link = article.get("link", "")
        
        # Clean title for comparison
        title_key = clean_title_for_comparison(title)
        
        # ✅ IMPROVED: Use link as primary unique identifier
        if link:
            unique_key = link  # Links are always unique
        else:
            # Fallback to title + source if no link
            unique_key = f"{title_key}|{source}"
        
        if unique_key not in seen_keys:
            seen_keys.add(unique_key)
            unique_articles.append(article)
            print(f"  ✅ Keeping article {i+1}: {title[:50]}... (source: {source})")
        else:
            removed_count += 1
            print(f"  ❌ Removing duplicate {i+1}: {title[:50]}... (source: {source})")
    
    print(f"\n  Summary: Kept {len(unique_articles)}, Removed {removed_count} duplicates")
    return unique_articles
    
def clean_title_for_comparison(title: str) -> str:
    """Clean title for duplicate detection"""
    # Remove common words and normalize
    title = re.sub(r'[^\w\s]', '', title.lower())
    title = ' '.join(title.split()[:5])  # Take first 5 words
    return title

def extract_trends(articles: List[Dict], max_trends: int = 5) -> List[Dict]:
    """Extract trending topics from articles"""
    if not articles:
        return []
    
    # Extract keywords from titles and summaries
    all_text = []
    for article in articles:
        all_text.append(article.get("title", ""))
        all_text.append(article.get("summary", ""))
    
    # Simple keyword extraction (could be enhanced with NLP)
    keywords = extract_keywords_from_text(" ".join(all_text))
    
    trends = []
    for i, (keyword, count) in enumerate(keywords.most_common(max_trends)):
        if len(keyword) > 3 and count > 1:  # Filter short words and low frequency
            # Find representative article for this trend
            representative_article = find_representative_article(articles, keyword)
            
            trend = {
                "trend_title": keyword.title(),
                "explainer": generate_trend_explanation(keyword, count, articles),
                "source_link": representative_article.get("link", "#") if representative_article else "#",
                "frequency": count,
                "related_articles": [a for a in articles if keyword.lower() in (a.get("title", "") + " " + a.get("summary", "")).lower()][:3]
            }
            trends.append(trend)
    
    return trends

def extract_keywords_from_text(text: str) -> Counter:
    """Extract keywords from text using simple NLP techniques"""
    # Common stop words to exclude
    stop_words = {
        'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with',
        'by', 'is', 'are', 'was', 'were', 'be', 'been', 'have', 'has', 'had', 'do', 'does',
        'did', 'will', 'would', 'could', 'should', 'may', 'might', 'can', 'this', 'that',
        'these', 'those', 'i', 'you', 'he', 'she', 'it', 'we', 'they', 'new', 'more', 'most',
        'also', 'get', 'go', 'make', 'see', 'know', 'think', 'take', 'come', 'say', 'use'
    }
    
    # Clean and tokenize
    words = re.findall(r'\b[a-zA-Z]{3,}\b', text.lower())
    
    # Filter out stop words and count
    filtered_words = [word for word in words if word not in stop_words]
    
    return Counter(filtered_words)

def find_representative_article(articles: List[Dict], keyword: str) -> Optional[Dict]:
    """Find the most representative article for a given keyword"""
    best_article = None
    best_score = 0
    
    for article in articles:
        title = article.get("title", "").lower()
        summary = article.get("summary", "").lower()
        content = f"{title} {summary}"
        
        # Simple scoring based on keyword frequency and position
        score = content.count(keyword.lower())
        if keyword.lower() in title:
            score += 2  # Bonus for title presence
        
        if score > best_score:
            best_score = score
            best_article = article
    
    return best_article

def generate_trend_explanation(keyword: str, frequency: int, articles: List[Dict]) -> str:
    """Generate an explanation for a trending topic"""
    explanations = [
        f"'{keyword.title()}' appears frequently across {frequency} recent articles, indicating growing interest in this topic.",
        f"This trend around '{keyword.title()}' has been mentioned {frequency} times in recent content.",
        f"'{keyword.title()}' is gaining traction with {frequency} mentions across various sources."
    ]
    return explanations[0]

def clean_html(html_content: str) -> str:
    """Remove HTML tags and clean content"""
    if not html_content:
        return ""
    
    # Remove HTML tags
    clean_text = re.sub(r'<[^>]+>', '', html_content)
    
    # Clean up whitespace
    clean_text = re.sub(r'\s+', ' ', clean_text).strip()
    
    # Limit length
    if len(clean_text) > 300:
        clean_text = clean_text[:300] + "..."
    
    return clean_text

def format_publish_date(date_str: str) -> str:
    """Format publication date to readable format"""
    if not date_str:
        return "Recently"
    
    try:
        # Parse the date string (feedparser usually provides parsed dates)
        if hasattr(date_str, 'strftime'):
            return date_str.strftime("%B %d, %Y")
        else:
            return str(date_str)
    except Exception:
        return "Recently"

def parse_date(date_str: str) -> datetime:
    """Parse date string to datetime object for sorting (timezone-aware)"""
    try:
        if not date_str or date_str == "Recently":
            # Return timezone-aware datetime
            from datetime import timezone
            return datetime.now(timezone.utc)
        
        # Try different date formats
        formats = [
            "%a, %d %b %Y %H:%M:%S %z",  # Has timezone
            "%a, %d %b %Y %H:%M:%S %Z",  # Has timezone
            "%Y-%m-%dT%H:%M:%S%z",       # Has timezone
            "%Y-%m-%d %H:%M:%S",         # No timezone
            "%B %d, %Y"                  # No timezone
        ]
        
        parsed_date = None
        
        for fmt in formats:
            try:
                parsed_date = datetime.strptime(str(date_str), fmt)
                break
            except ValueError:
                continue
        
        if not parsed_date:
            from datetime import timezone
            return datetime.now(timezone.utc)
        
        # If the parsed date is timezone-naive, make it timezone-aware (assume UTC)
        if parsed_date.tzinfo is None:
            from datetime import timezone
            parsed_date = parsed_date.replace(tzinfo=timezone.utc)
        
        return parsed_date
        
    except Exception:
        from datetime import timezone
        return datetime.now(timezone.utc)

def extract_tags(entry) -> List[str]:
    """Extract tags/categories from RSS entry"""
    tags = []
    
    if hasattr(entry, 'tags'):
        for tag in entry.tags:
            if hasattr(tag, 'term'):
                tags.append(tag.term)
    
    if hasattr(entry, 'category'):
        tags.append(entry.category)
    
    return tags[:5]  # Limit to 5 tags

# ============================================================================
# GOOGLE TRENDS INTEGRATION (NEW - Added for enhanced trend detection)
# ============================================================================

def get_google_trends_data(keywords: List[str], timeframe: str = 'now 7-d'):
    """Get Google Trends data for keywords"""
    try:
        from pytrends.request import TrendReq
        
        pytrends = TrendReq(hl='en-US', tz=360)
        keywords = keywords[:5]  # Limit to 5
        
        print(f"🔍 Fetching Google Trends for: {', '.join(keywords)}")
        
        pytrends.build_payload(keywords, cat=0, timeframe=timeframe, geo='', gprop='')
        interest_df = pytrends.interest_over_time()
        
        if interest_df.empty:
            return {}
        
        trends_data = {}
        
        for keyword in keywords:
            if keyword in interest_df.columns:
                values = interest_df[keyword].values
                
                current = int(values[-1]) if len(values) > 0 else 0
                avg = int(values.mean()) if len(values) > 0 else 0
                
                # Calculate direction
                if len(values) >= 2:
                    recent = values[-3:].mean() if len(values) >= 3 else values[-1]
                    older = values[:-3].mean() if len(values) > 3 else values[0]
                    
                    if recent > older * 1.2:
                        direction = "rising"
                    elif recent < older * 0.8:
                        direction = "falling"
                    else:
                        direction = "stable"
                else:
                    direction = "unknown"
                
                trends_data[keyword] = {
                    "current_interest": current,
                    "avg_interest": avg,
                    "direction": direction,
                    "is_trending": current > avg * 1.2
                }
        
        return trends_data
    except ImportError:
        print("⚠️ pytrends not installed. Run: pip install pytrends")
        return {}
    except Exception as e:
        print(f"Error fetching Google Trends: {e}")
        return {}


def detect_trending_topics(articles: List[Dict], use_google_trends: bool = True):
    """Enhanced trend detection with Google Trends"""
    try:
        # First do local analysis
        local_trends = extract_trends(articles, max_trends=10)
        
        if not local_trends or not use_google_trends:
            return local_trends[:5]
        
        # Get keywords
        keywords = [trend['trend_title'].lower() for trend in local_trends[:5]]
        
        # Get Google Trends data
        google_data = get_google_trends_data(keywords)
        
        # Enhance trends
        enhanced = []
        for trend in local_trends:
            keyword = trend['trend_title'].lower()
            
            enhanced_trend = {
                **trend,
                "source": "local+google" if keyword in google_data else "local"
            }
            
            if keyword in google_data:
                gt = google_data[keyword]
                enhanced_trend.update({
                    "google_interest": gt['current_interest'],
                    "direction": gt['direction'],
                    "is_google_trending": gt['is_trending']
                })
            
            enhanced.append(enhanced_trend)
        
        # Sort by Google interest if available
        enhanced.sort(
            key=lambda x: (
                x.get('google_interest', 0),
                x.get('frequency', 0)
            ),
            reverse=True
        )
        
        return enhanced[:5]
    except Exception as e:
        print(f"Error in enhanced trends: {e}")
        return extract_trends(articles, max_trends=5)

# ============================================================================
# TWITTER SCRAPING INTEGRATION (NEW - For Twitter as content source)
# ============================================================================

def scrape_twitter_handle(handle: str, max_tweets: int = 10) -> List[Dict]:
    """Scrape recent tweets from a Twitter handle"""
    try:
        from ntscraper import Nitter
        
        print(f"🐦 Scraping tweets from @{handle}...")
        
        scraper = Nitter(log_level=1, skip_instance_check=False)
        tweets_data = scraper.get_tweets(handle, mode='user', number=max_tweets)
        
        if not tweets_data or 'tweets' not in tweets_data:
            print(f"⚠️ No tweets found for @{handle}")
            return []
        
        articles = []
        for tweet in tweets_data['tweets']:
            article = {
                "title": f"Tweet by @{handle}",
                "link": tweet.get('link', f"https://twitter.com/{handle}"),
                "summary": clean_tweet_text(tweet.get('text', '')),
                "published": format_tweet_date(tweet.get('date', '')),
                "author": f"@{handle}",
                "source": "Twitter",
                "engagement": {
                    "likes": tweet.get('stats', {}).get('likes', 0),
                    "retweets": tweet.get('stats', {}).get('retweets', 0),
                    "replies": tweet.get('stats', {}).get('comments', 0)
                },
                "tags": extract_hashtags_from_tweet(tweet.get('text', ''))
            }
            articles.append(article)
        
        print(f"✅ Scraped {len(articles)} tweets from @{handle}")
        return articles
        
    except Exception as e:
        print(f"Error scraping Twitter handle @{handle}: {e}")
        return []


def scrape_twitter_hashtag(hashtag: str, max_tweets: int = 10) -> List[Dict]:
    """Scrape recent tweets from a hashtag"""
    try:
        from ntscraper import Nitter
        
        hashtag = hashtag.lstrip('#')
        print(f"🐦 Scraping tweets for #{hashtag}...")
        
        scraper = Nitter(log_level=1, skip_instance_check=False)
        tweets_data = scraper.get_tweets(hashtag, mode='hashtag', number=max_tweets)
        
        if not tweets_data or 'tweets' not in tweets_data:
            print(f"⚠️ No tweets found for #{hashtag}")
            return []
        
        articles = []
        for tweet in tweets_data['tweets']:
            article = {
                "title": f"Tweet about #{hashtag}",
                "link": tweet.get('link', f"https://twitter.com/hashtag/{hashtag}"),
                "summary": clean_tweet_text(tweet.get('text', '')),
                "published": format_tweet_date(tweet.get('date', '')),
                "author": tweet.get('user', {}).get('name', 'Unknown'),
                "source": f"Twitter - #{hashtag}",
                "engagement": {
                    "likes": tweet.get('stats', {}).get('likes', 0),
                    "retweets": tweet.get('stats', {}).get('retweets', 0),
                    "replies": tweet.get('stats', {}).get('comments', 0)
                },
                "tags": extract_hashtags_from_tweet(tweet.get('text', ''))
            }
            articles.append(article)
        
        print(f"✅ Scraped {len(articles)} tweets for #{hashtag}")
        return articles
        
    except Exception as e:
        print(f"Error scraping hashtag #{hashtag}: {e}")
        return []


def clean_tweet_text(text: str) -> str:
    """Clean tweet text (remove URLs, extra whitespace)"""
    if not text:
        return ""
    
    text = re.sub(r'http\S+|www\S+', '', text)
    text = re.sub(r'\s+', ' ', text).strip()
    
    if len(text) > 280:
        text = text[:280] + "..."
    
    return text


def format_tweet_date(date_str: str) -> str:
    """Format tweet date to readable format"""
    if not date_str:
        return "Recently"
    
    try:
        for fmt in ['%b %d, %Y · %I:%M %p', '%Y-%m-%d %H:%M:%S', '%a %b %d %H:%M:%S %z %Y']:
            try:
                dt = datetime.strptime(date_str, fmt)
                return dt.strftime("%B %d, %Y")
            except ValueError:
                continue
        
        return date_str
    except Exception:
        return "Recently"


def extract_hashtags_from_tweet(text: str) -> List[str]:
    """Extract hashtags from tweet text"""
    if not text:
        return []
    
    hashtags = re.findall(r'#(\w+)', text)
    return hashtags[:5]


# ============================================================================
# YOUTUBE SCRAPING INTEGRATION
# ============================================================================

def scrape_youtube_channel_with_api(channel_id: str, max_videos: int = 10) -> List[Dict]:
    """Scrape videos using official YouTube Data API v3"""
    try:
        api_key = os.getenv("YOUTUBE_API_KEY")
        
        if not api_key:
            print("⚠️ YOUTUBE_API_KEY not found in .env file")
            return []
        
        channel_id = channel_id.strip()
        
        if 'youtube.com' in channel_id or 'youtu.be' in channel_id:
            if '/@' in channel_id:
                channel_id = '@' + channel_id.split('/@')[-1].split('/')[0].split('?')[0]
            elif '/channel/' in channel_id:
                channel_id = channel_id.split('/channel/')[-1].split('/')[0].split('?')[0]
            elif '/c/' in channel_id:
                channel_id = channel_id.split('/c/')[-1].split('/')[0].split('?')[0]
        
        print(f"📺 Fetching YouTube videos using API for: {channel_id}")
        
        actual_channel_id = channel_id
        
        if channel_id.startswith('@'):
            search_url = "https://www.googleapis.com/youtube/v3/search"
            search_params = {
                "part": "snippet",
                "q": channel_id,
                "type": "channel",
                "maxResults": 1,
                "key": api_key
            }
            
            search_response = requests.get(search_url, params=search_params, timeout=10)
            search_data = search_response.json()
            
            if 'error' in search_data:
                print(f"❌ YouTube API Error: {search_data['error']['message']}")
                return []
            
            if 'items' not in search_data or len(search_data['items']) == 0:
                print(f"⚠️ Channel not found: {channel_id}")
                return []
            
            actual_channel_id = search_data['items'][0]['id']['channelId']
            print(f"  ✅ Found channel ID: {actual_channel_id}")
        
        videos_url = "https://www.googleapis.com/youtube/v3/search"
        videos_params = {
            "part": "snippet",
            "channelId": actual_channel_id,
            "maxResults": max_videos,
            "order": "date",
            "type": "video",
            "key": api_key
        }
        
        videos_response = requests.get(videos_url, params=videos_params, timeout=10)
        videos_data = videos_response.json()
        
        if 'error' in videos_data:
            print(f"❌ YouTube API Error: {videos_data['error']['message']}")
            return []
        
        if 'items' not in videos_data or len(videos_data['items']) == 0:
            print(f"⚠️ No videos found for channel")
            return []
        
        articles = []
        for item in videos_data['items']:
            video_id = item['id']['videoId']
            snippet = item['snippet']
            
            try:
                pub_date = datetime.fromisoformat(snippet['publishedAt'].replace('Z', '+00:00'))
                published = pub_date.strftime("%B %d, %Y")
            except:
                published = snippet['publishedAt']
            
            article = {
                "title": snippet['title'],
                "link": f"https://www.youtube.com/watch?v={video_id}",
                "summary": snippet['description'][:300] + "..." if len(snippet['description']) > 300 else snippet['description'],
                "published": published,
                "author": snippet['channelTitle'],
                "source": "YouTube",
                "video_id": video_id,
                "thumbnail": snippet['thumbnails']['high']['url'] if 'high' in snippet['thumbnails'] else snippet['thumbnails']['default']['url'],
                "tags": []
            }
            articles.append(article)
        
        print(f"✅ Fetched {len(articles)} videos via YouTube API")
        return articles
        
    except Exception as e:
        print(f"❌ YouTube API error: {e}")
        import traceback
        traceback.print_exc()
        return []


# ============================================================================
# UNIFIED CONTENT AGGREGATOR
# ============================================================================

def aggregate_all_sources(
    rss_feeds: List[str] = None,
    twitter_handles: List[str] = None,
    twitter_hashtags: List[str] = None,
    youtube_channels: List[str] = None,
    max_per_source: int = 5
) -> List[Dict]:
    """Aggregate content from ALL sources: RSS, Twitter, YouTube"""
    print("\n" + "="*70)
    print("🚀 CONTENT AGGREGATION STARTED")
    print("="*70)
    
    all_articles = []
    
    # 1. Fetch RSS feeds
    if rss_feeds:
        print(f"\n📡 Fetching {len(rss_feeds)} RSS feeds...")
        for feed_url in rss_feeds:
            try:
                articles = parse_rss_feed(feed_url, max_per_source)
                all_articles.extend(articles)
                print(f"  ✅ {feed_url}: {len(articles)} articles")
            except Exception as e:
                print(f"  ❌ {feed_url}: {e}")
    
    # 2. Fetch Twitter handles
    if twitter_handles:
        print(f"\n🐦 Fetching {len(twitter_handles)} Twitter handles...")
        for handle in twitter_handles:
            try:
                tweets = scrape_twitter_handle(handle, max_per_source)
                all_articles.extend(tweets)
                print(f"  ✅ @{handle}: {len(tweets)} tweets")
            except Exception as e:
                print(f"  ❌ @{handle}: {e}")
    
    # 3. Fetch Twitter hashtags
    if twitter_hashtags:
        print(f"\n#️⃣ Fetching {len(twitter_hashtags)} Twitter hashtags...")
        for hashtag in twitter_hashtags:
            try:
                tweets = scrape_twitter_hashtag(hashtag, max_per_source)
                all_articles.extend(tweets)
                print(f"  ✅ #{hashtag}: {len(tweets)} tweets")
            except Exception as e:
                print(f"  ❌ #{hashtag}: {e}")
    
    # 4. Fetch YouTube channels
    if youtube_channels:
        print(f"\n📺 Fetching {len(youtube_channels)} YouTube channels...")
        for channel in youtube_channels:
            try:
                videos = scrape_youtube_channel_with_api(channel, max_per_source)
                all_articles.extend(videos)
                print(f"  ✅ {channel}: {len(videos)} videos")
            except Exception as e:
                print(f"  ❌ {channel}: {e}")
    
    print(f"\n📊 Total articles collected: {len(all_articles)}")
    
    # Remove duplicates
    unique_articles = remove_duplicate_articles(all_articles)
    
    # Sort by publication date
    unique_articles.sort(key=lambda x: parse_date(x.get("published", "")), reverse=True)
    
    print("\n" + "="*70)
    print(f"✅ AGGREGATION COMPLETE: {len(unique_articles)} unique articles")
    print("="*70 + "\n")
    
    return unique_articles