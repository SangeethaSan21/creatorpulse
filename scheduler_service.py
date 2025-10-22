"""
Background Scheduler Service for CreatorPulse
Runs scheduled newsletter generation and delivery
"""
import schedule
import time
from datetime import datetime, UTC
from supabase_client import get_supabase_client
from content_aggregator import parse_multiple_feeds, extract_trends
from draft_generator import generate_newsletter_with_ai
from email_service import send_newsletter_email
from models import save_newsletter, get_user_sources
import os
from dotenv import load_dotenv

load_dotenv()

def check_and_send_scheduled_newsletters():
    """
    Check for users with active schedules and send newsletters
    """
    print(f"\n{'='*60}")
    print(f"⏰ Running scheduled check at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}\n")
    
    try:
        supabase = get_supabase_client()
        
        # Get all active schedules
        response = supabase.table("scheduled_deliveries").select("*").eq("is_active", True).execute()
        
        if not response.data:
            print("📭 No active schedules found")
            return
        
        schedules = response.data
        print(f"📬 Found {len(schedules)} active schedule(s)")
        
        current_time = datetime.now().strftime('%H:%M')
        
        for schedule_data in schedules:
            user_id = schedule_data['user_id']
            schedule_time = schedule_data['schedule_time'][:5]  # Get HH:MM only
            
            print(f"\n🔍 Checking schedule for user {user_id}")
            print(f"   Scheduled time: {schedule_time}")
            print(f"   Current time: {current_time}")
            
            # Check if it's time to send (within 1-minute window)
            if schedule_time == current_time:
                print(f"✅ Time match! Generating newsletter...")
                generate_and_send_newsletter(user_id, schedule_data)
            else:
                print(f"⏭️  Not time yet (scheduled: {schedule_time}, current: {current_time})")
                
    except Exception as e:
        print(f"❌ Error in scheduled check: {e}")
        import traceback
        traceback.print_exc()


def generate_and_send_newsletter(user_id: str, schedule_data: dict):
    """
    Generate newsletter draft and send it to the USER for review
    (NOT to their subscribers - user reviews and sends manually)
    """
    try:
        supabase = get_supabase_client()
        
        # Get user email
        user_response = supabase.table("users").select("email").eq("id", user_id).single().execute()
        if not user_response.data:
            print(f"❌ User {user_id} not found")
            return
        
        user_email = user_response.data['email']
        print(f"📧 Generating DRAFT newsletter for review by {user_email}")
        
        # Get user's sources
        user_sources = get_user_sources(user_id)
        rss_feeds = [source['url'] for source in user_sources if source.get('type') in ['rss_feed', 'rss']]
        
        if not rss_feeds:
            print(f"⚠️  No RSS feeds configured for user {user_id}")
            return
        
        print(f"📡 Found {len(rss_feeds)} RSS feeds")
        
        # Parse feeds
        articles = parse_multiple_feeds(rss_feeds, max_articles_per_feed=5)
        
        if not articles:
            print(f"⚠️  No articles found from feeds")
            return
        
        print(f"📰 Found {len(articles)} articles")
        
        # Extract trends
        trends = extract_trends(articles)
        print(f"🔥 Extracted {len(trends)} trends")
        
        # Generate newsletter with AI
        groq_api_key = os.getenv("GROQ_API_KEY")
        if not groq_api_key:
            print(f"❌ GROQ_API_KEY not configured")
            return
        
        title = f"Daily Digest - {datetime.now().strftime('%B %d, %Y')}"
        topic = "Technology & Innovation"
        tone = "Professional"
        
        print(f"🤖 Generating AI newsletter...")
        content = generate_newsletter_with_ai(
            articles=articles,
            trends=trends,
            title=title,
            topic=topic,
            tone=tone,
            api_key=groq_api_key,
        )
        
        # Save newsletter
        newsletter_data = {
            "user_id": user_id,
            "title": title,
            "content": content,
            "status": "draft",
            "trends": str(trends),
            "topic": topic,
            "tone": tone,
            "created_at": datetime.now(UTC).isoformat()
        }
        
        saved_id = save_newsletter(newsletter_data)
        
        if not saved_id:
            print(f"❌ Failed to save newsletter")
            return
        
        print(f"💾 Newsletter saved with ID: {saved_id}")
        
        # Send email
        subject = f"📰 {title}"
        
        print(f"📤 Sending email to {user_email}...")
        success = send_newsletter_email(
            recipient_email=user_email,
            subject=subject,
            html_content=content
        )
        
        if success:
            print(f"✅ Newsletter sent successfully!")
            
            # Update schedule's last_delivered_at
            supabase.table("scheduled_deliveries").update({
                "last_delivered_at": datetime.now(UTC).isoformat()
            }).eq("user_id", user_id).execute()
            
            # Update newsletter status
            from models import update_newsletter
            update_newsletter(saved_id, {
                "status": "sent",
                "sent_at": datetime.now(UTC).isoformat()
            }, user_id)
            
            print(f"🎉 Scheduled delivery completed for {user_email}")
        else:
            print(f"❌ Failed to send email")
            
    except Exception as e:
        print(f"❌ Error generating/sending newsletter: {e}")
        import traceback
        traceback.print_exc()


def run_scheduler():
    """
    Run the scheduler service
    """
    print("\n" + "="*60)
    print("🚀 CreatorPulse Scheduler Service Starting...")
    print("="*60)
    
    # Schedule checks every minute
    schedule.every(1).minutes.do(check_and_send_scheduled_newsletters)
    
    print("\n⏰ Scheduler running - checking every minute")
    print("   Press Ctrl+C to stop\n")
    
    # Run immediately on start
    check_and_send_scheduled_newsletters()
    
    # Keep running
    while True:
        schedule.run_pending()
        time.sleep(30)  # Check every 30 seconds


if __name__ == "__main__":
    try:
        run_scheduler()
    except KeyboardInterrupt:
        print("\n\n🛑 Scheduler stopped by user")
    except Exception as e:
        print(f"\n\n❌ Scheduler crashed: {e}")
        import traceback
        traceback.print_exc()