"""
Newsletter Feedback and Analytics Module
Tracks user reactions, edits, and engagement metrics
"""
from datetime import datetime, UTC
from typing import Dict, Optional
import difflib
from supabase_client import get_supabase_client

def record_feedback(newsletter_id: str, user_id: str, reaction: str, edited_content: Optional[str] = None, original_content: Optional[str] = None) -> bool:
    """
    Record user feedback on newsletter
    reaction: 'thumbs_up', 'thumbs_down', 'accepted', 'rejected'
    """
    from supabase_client import get_supabase_client
    
    try:
        supabase = get_supabase_client()
        
        feedback_data = {
            "newsletter_id": newsletter_id,
            "user_id": user_id,
            "reaction": reaction,
            "created_at": datetime.now(UTC).isoformat()
        }
        
        # If content was edited, calculate diff
        if edited_content and original_content:
            diff_summary = calculate_diff_summary(original_content, edited_content)
            feedback_data["edit_diff"] = diff_summary
            feedback_data["was_edited"] = True
        else:
            feedback_data["was_edited"] = False
        
        response = supabase.table("newsletter_feedback").insert(feedback_data).execute()
        
        # Update newsletter status
        if reaction in ['accepted', 'thumbs_up']:
            supabase.table("newsletters").update({
                "status": "accepted",
                "accepted_at": datetime.now(UTC).isoformat()
            }).eq("id", newsletter_id).execute()
        
        return bool(response.data)
    except Exception as e:
        print(f"Error recording feedback: {e}")
        return False

def calculate_diff_summary(original: str, edited: str) -> Dict:
    """Calculate summary of edits made to newsletter"""
    original_lines = original.split('\n')
    edited_lines = edited.split('\n')
    
    # Use difflib to find differences
    diff = list(difflib.unified_diff(original_lines, edited_lines, lineterm=''))
    
    additions = sum(1 for line in diff if line.startswith('+') and not line.startswith('+++'))
    deletions = sum(1 for line in diff if line.startswith('-') and not line.startswith('---'))
    
    # Calculate edit ratio
    original_words = len(original.split())
    edited_words = len(edited.split())
    
    return {
        "lines_added": additions,
        "lines_deleted": deletions,
        "original_word_count": original_words,
        "edited_word_count": edited_words,
        "edit_ratio": round(abs(edited_words - original_words) / max(original_words, 1), 2)
    }

def get_feedback_stats(user_id: str, days: int = 30) -> Dict:
    """Get feedback statistics for user"""
    from supabase_client import get_supabase_client
    from datetime import timedelta
    
    try:
        supabase = get_supabase_client()
        
        # Get feedback from last N days
        since_date = (datetime.now(UTC) - timedelta(days=days)).isoformat()
        
        response = supabase.table("newsletter_feedback").select("*").eq("user_id", user_id).gte("created_at", since_date).execute()
        
        if not response.data:
            return {
                "total_newsletters": 0,
                "acceptance_rate": 0,
                "avg_edit_ratio": 0,
                "thumbs_up": 0,
                "thumbs_down": 0
            }
        
        feedbacks = response.data
        
        # Calculate stats
        total = len(feedbacks)
        accepted = sum(1 for f in feedbacks if f.get('reaction') in ['accepted', 'thumbs_up'])
        thumbs_up = sum(1 for f in feedbacks if f.get('reaction') == 'thumbs_up')
        thumbs_down = sum(1 for f in feedbacks if f.get('reaction') == 'thumbs_down')
        
        # Calculate average edit ratio
        edited_feedbacks = [f for f in feedbacks if f.get('was_edited') and f.get('edit_diff')]
        avg_edit_ratio = 0
        if edited_feedbacks:
            edit_ratios = [f['edit_diff'].get('edit_ratio', 0) for f in edited_feedbacks if isinstance(f.get('edit_diff'), dict)]
            avg_edit_ratio = round(sum(edit_ratios) / len(edit_ratios), 2) if edit_ratios else 0
        
        return {
            "total_newsletters": total,
            "acceptance_rate": round((accepted / total) * 100, 1) if total > 0 else 0,
            "avg_edit_ratio": avg_edit_ratio,
            "thumbs_up": thumbs_up,
            "thumbs_down": thumbs_down,
            "avg_review_time": "< 20 min"  # Placeholder for future tracking
        }
    except Exception as e:
        print(f"Error fetching feedback stats: {e}")
        return {}

def track_engagement_metrics(newsletter_id: str, metric_type: str, value: float) -> bool:
    """
    Track engagement metrics for newsletter
    metric_type: 'open_rate', 'click_rate', 'reply_rate'
    """
    from supabase_client import get_supabase_client
    
    try:
        supabase = get_supabase_client()
        
        metric_data = {
            "newsletter_id": newsletter_id,
            "metric_type": metric_type,
            "value": value,
            "recorded_at": datetime.now(UTC).isoformat()
        }
        
        response = supabase.table("newsletter_metrics").insert(metric_data).execute()
        
        return bool(response.data)
    except Exception as e:
        print(f"Error tracking metric: {e}")
        return False

def get_engagement_analytics(user_id: str, days: int = 30) -> Dict:
    """Get engagement analytics for user's newsletters"""
    from supabase_client import get_supabase_client
    from datetime import timedelta
    
    try:
        supabase = get_supabase_client()
        
        # Get newsletters from last N days
        since_date = (datetime.now(UTC) - timedelta(days=days)).isoformat()
        
        newsletters_response = supabase.table("newsletters").select("id").eq("user_id", user_id).gte("created_at", since_date).execute()
        
        if not newsletters_response.data:
            return {
                "avg_open_rate": 0,
                "avg_click_rate": 0,
                "trend": "no_data"
            }
        
        newsletter_ids = [n['id'] for n in newsletters_response.data]
        
        # Get metrics for these newsletters
        metrics_response = supabase.table("newsletter_metrics").select("*").in_("newsletter_id", newsletter_ids).execute()
        
        if not metrics_response.data:
            return {
                "avg_open_rate": 0,
                "avg_click_rate": 0,
                "trend": "no_data"
            }
        
        metrics = metrics_response.data
        
        # Calculate averages
        open_rates = [m['value'] for m in metrics if m['metric_type'] == 'open_rate']
        click_rates = [m['value'] for m in metrics if m['metric_type'] == 'click_rate']
        
        avg_open_rate = round(sum(open_rates) / len(open_rates), 1) if open_rates else 0
        avg_click_rate = round(sum(click_rates) / len(click_rates), 1) if click_rates else 0
        
        # Determine trend (simplified)
        trend = "stable"
        if len(open_rates) >= 2:
            recent_avg = sum(open_rates[-3:]) / min(len(open_rates[-3:]), 3)
            older_avg = sum(open_rates[:-3]) / max(len(open_rates[:-3]), 1) if len(open_rates) > 3 else recent_avg
            
            if recent_avg > older_avg * 1.1:
                trend = "improving"
            elif recent_avg < older_avg * 0.9:
                trend = "declining"
        
        return {
            "avg_open_rate": avg_open_rate,
            "avg_click_rate": avg_click_rate,
            "total_sent": len(newsletter_ids),
            "trend": trend
        }
    except Exception as e:
        print(f"Error fetching analytics: {e}")
        return {}

# ============================================================================
# TIME TRACKING FUNCTIONS (NEW - Added for PDF requirement)
# ============================================================================

def start_review_timer(newsletter_id: str, user_id: str) -> bool:
    """Start timer when user begins reviewing a draft"""
    try:
        supabase = get_supabase_client()
        
        timer_data = {
            "newsletter_id": newsletter_id,
            "user_id": user_id,
            "started_at": datetime.now(UTC).isoformat(),
            "status": "active"
        }
        
        # Check if timer exists
        existing = supabase.table("review_timers").select("*").eq("newsletter_id", newsletter_id).eq("user_id", user_id).execute()
        
        if existing.data and len(existing.data) > 0:
            supabase.table("review_timers").update({
                "started_at": datetime.now(UTC).isoformat(),
                "status": "active"
            }).eq("newsletter_id", newsletter_id).eq("user_id", user_id).execute()
        else:
            supabase.table("review_timers").insert(timer_data).execute()
        
        print(f"⏱️ Review timer started")
        return True
    except Exception as e:
        print(f"Error starting timer: {e}")
        return False


def stop_review_timer(newsletter_id: str, user_id: str, action: str = "sent"):
    """Stop timer and return duration in minutes"""
    try:
        supabase = get_supabase_client()
        
        response = supabase.table("review_timers").select("*").eq("newsletter_id", newsletter_id).eq("user_id", user_id).eq("status", "active").execute()
        
        if not response.data or len(response.data) == 0:
            return None
        
        timer = response.data[0]
        started_at = datetime.fromisoformat(timer['started_at'].replace('Z', '+00:00'))
        ended_at = datetime.now(UTC)
        
        duration_minutes = round((ended_at - started_at).total_seconds() / 60, 2)
        
        supabase.table("review_timers").update({
            "ended_at": ended_at.isoformat(),
            "duration_minutes": duration_minutes,
            "action": action,
            "status": "completed"
        }).eq("id", timer['id']).execute()
        
        print(f"⏱️ Review completed in {duration_minutes} min")
        return duration_minutes
    except Exception as e:
        print(f"Error stopping timer: {e}")
        return None


def get_average_review_time(user_id: str, days: int = 30):
    """Get review time statistics"""
    try:
        supabase = get_supabase_client()
        from datetime import timedelta
        
        since_date = (datetime.now(UTC) - timedelta(days=days)).isoformat()
        
        response = supabase.table("review_timers").select("*").eq("user_id", user_id).eq("status", "completed").gte("started_at", since_date).execute()
        
        if not response.data:
            return {
                "avg_time_minutes": 0,
                "total_reviews": 0,
                "under_target_count": 0,
                "success_rate": 0
            }
        
        durations = [t['duration_minutes'] for t in response.data if t.get('duration_minutes')]
        
        if not durations:
            return {
                "avg_time_minutes": 0,
                "total_reviews": 0,
                "under_target_count": 0,
                "success_rate": 0
            }
        
        under_target = sum(1 for d in durations if d <= 20)
        
        return {
            "avg_time_minutes": round(sum(durations) / len(durations), 2),
            "total_reviews": len(durations),
            "under_target_count": under_target,
            "success_rate": round((under_target / len(durations)) * 100, 1)
        }
    except Exception as e:
        print(f"Error getting review stats: {e}")
        return {}


# ============================================================================
# EDIT TRACKING FUNCTIONS (NEW - Added for PDF requirement)
# ============================================================================

def save_edit_history(newsletter_id: str, user_id: str, original: str, edited: str):
    """Save edit history with diff analysis"""
    try:
        supabase = get_supabase_client()
        
        # Calculate edit metrics
        metrics = calculate_edit_metrics(original, edited)
        
        edit_data = {
            "newsletter_id": newsletter_id,
            "user_id": user_id,
            "original_content": original[:1000],  # Store first 1000 chars
            "edited_content": edited[:1000],
            "edit_metrics": metrics,
            "created_at": datetime.now(UTC).isoformat()
        }
        
        response = supabase.table("edit_history").insert(edit_data).execute()
        
        if response.data:
            print(f"✅ Edit saved - Ratio: {metrics.get('edit_ratio', 0)*100:.1f}%")
            return True
        return False
    except Exception as e:
        print(f"Error saving edit: {e}")
        return False


def calculate_edit_metrics(original: str, edited: str):
    """Calculate detailed edit metrics"""
    try:
        import difflib
        
        original_words = original.split()
        edited_words = edited.split()
        
        # Calculate similarity
        similarity = difflib.SequenceMatcher(None, original, edited).ratio()
        edit_ratio = 1 - similarity
        
        # Categorize severity
        if edit_ratio < 0.05:
            severity = "minimal"
        elif edit_ratio < 0.15:
            severity = "minor"
        elif edit_ratio < 0.30:
            severity = "moderate"
        else:
            severity = "major"
        
        return {
            "original_word_count": len(original_words),
            "edited_word_count": len(edited_words),
            "similarity_ratio": round(similarity, 3),
            "edit_ratio": round(edit_ratio, 3),
            "severity": severity
        }
    except Exception as e:
        print(f"Error calculating metrics: {e}")
        return {}


def get_edit_patterns(user_id: str, days: int = 30):
    """Analyze user's editing patterns"""
    try:
        supabase = get_supabase_client()
        from datetime import timedelta
        
        since_date = (datetime.now(UTC) - timedelta(days=days)).isoformat()
        
        response = supabase.table("edit_history").select("edit_metrics").eq("user_id", user_id).gte("created_at", since_date).execute()
        
        if not response.data:
            return {
                "total_edits": 0,
                "avg_edit_ratio": 0,
                "improvement_trend": "no_data"
            }
        
        edits = response.data
        edit_ratios = [e['edit_metrics'].get('edit_ratio', 0) for e in edits if isinstance(e.get('edit_metrics'), dict)]
        
        if not edit_ratios:
            return {
                "total_edits": 0,
                "avg_edit_ratio": 0,
                "improvement_trend": "no_data"
            }
        
        avg_ratio = sum(edit_ratios) / len(edit_ratios)
        
        # Trend analysis
        if len(edit_ratios) >= 5:
            recent_avg = sum(edit_ratios[-3:]) / 3
            older_avg = sum(edit_ratios[:-3]) / len(edit_ratios[:-3])
            
            if recent_avg < older_avg * 0.9:
                trend = "improving"
            elif recent_avg > older_avg * 1.1:
                trend = "declining"
            else:
                trend = "stable"
        else:
            trend = "insufficient_data"
        
        return {
            "total_edits": len(edits),
            "avg_edit_ratio": round(avg_ratio, 3),
            "improvement_trend": trend
        }
    except Exception as e:
        print(f"Error analyzing patterns: {e}")
        return {}