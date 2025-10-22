from supabase_client import get_supabase_client
from typing import List, Dict, Optional

def fetch_newsletters(user_id: str) -> List[Dict]:
    """Fetch all newsletters for a specific user"""
    supabase = get_supabase_client()
    
    if not supabase:
        return []
    
    try:
        response = supabase.table("newsletters").select("*").eq("user_id", user_id).order("created_at", desc=True).execute()
        return response.data or []
    except Exception as e:
        print(f"Error fetching newsletters: {e}")
        return []

def save_newsletter(newsletter_data: Dict) -> str:
    """Save a newsletter to the database and return the ID"""
    supabase = get_supabase_client()
    
    if not supabase:
        print("Supabase client not initialized")
        return None
    
    try:
        # Ensure user_id is included before saving
        if "user_id" not in newsletter_data or not newsletter_data["user_id"]:
            print("❌ Missing user_id in newsletter data")
            return None

        print("🧩 Newsletter insert payload:", newsletter_data)
        
        response = supabase.table("newsletters").insert(newsletter_data).execute()
        
        if response.data and len(response.data) > 0:
            newsletter_id = response.data[0].get('id')
            print(f"✅ Newsletter saved successfully! ID: {newsletter_id}")
            return newsletter_id
        else:
            print("❌ No data returned from insert")
            return None
            
    except Exception as e:
        print(f"❌ Error saving newsletter: {e}")
        return None

def update_newsletter(newsletter_id: str, updates: Dict, user_id: str) -> bool:
    """Update an existing newsletter"""
    supabase = get_supabase_client()
    
    if not supabase:
        return False
    
    try:
        response = supabase.table("newsletters").update(updates).eq("id", newsletter_id).eq("user_id", user_id).execute()
        return bool(response.data)
    except Exception as e:
        print(f"Error updating newsletter: {e}")
        return False

def delete_newsletter(newsletter_id: str, user_id: str) -> bool:
    """Delete a newsletter (with user verification)"""
    supabase = get_supabase_client()
    
    if not supabase:
        print("Supabase client not initialized")
        return False
    
    try:
        # Delete with user verification to ensure RLS compliance
        response = supabase.table("newsletters").delete().eq("id", newsletter_id).eq("user_id", user_id).execute()
        
        if response.data:
            print(f"✅ Newsletter {newsletter_id} deleted successfully")
            return True
        else:
            print(f"❌ Newsletter {newsletter_id} not found or already deleted")
            return False
    except Exception as e:
        print(f"❌ Error deleting newsletter: {e}")
        return False

def get_newsletter_by_id(newsletter_id: str, user_id: str) -> Optional[Dict]:
    """Get a specific newsletter by ID"""
    supabase = get_supabase_client()
    
    if not supabase:
        return None
    
    try:
        response = supabase.table("newsletters").select("*").eq("id", newsletter_id).eq("user_id", user_id).single().execute()
        return response.data
    except Exception as e:
        print(f"Error fetching newsletter: {e}")
        return None

# User Sources Management
def save_user_sources(source_data: Dict) -> bool:
    """Save a new content source for a user with enhanced error handling"""
    supabase = get_supabase_client()
    
    if not supabase:
        print("❌ Supabase client not initialized")
        return False
    
    try:
        print(f"🔍 Attempting to save source: {source_data}")
        
        response = supabase.table("user_sources").insert(source_data).execute()
        
        if response.data:
            print(f"✅ Source saved successfully: {response.data}")
            return True
        else:
            print(f"❌ No data returned from insert")
            return False
            
    except Exception as e:
        error_msg = str(e)
        print(f"❌ Error saving user source: {error_msg}")
        
        # Provide specific error messages
        if "duplicate key" in error_msg.lower() or "unique constraint" in error_msg.lower():
            print("   → This source URL already exists for this user")
        elif "violates check constraint" in error_msg.lower():
            print("   → Invalid source type. Allowed types might be limited in database")
        elif "violates foreign key" in error_msg.lower():
            print("   → User ID not found in users table")
        elif "null value" in error_msg.lower():
            print("   → Missing required field")
        
        return False

def get_user_sources(user_id: str) -> List[Dict]:
    """Get all content sources for a user"""
    supabase = get_supabase_client()
    
    if not supabase:
        return []
    
    try:
        response = supabase.table("user_sources").select("*").eq("user_id", user_id).eq("active", True).order("created_at", desc=True).execute()
        return response.data or []
    except Exception as e:
        print(f"Error fetching user sources: {e}")
        return []

def update_user_source(source_id: str, updates: Dict, user_id: str) -> bool:
    """Update a user's content source"""
    supabase = get_supabase_client()
    
    if not supabase:
        return False
    
    try:
        response = supabase.table("user_sources").update(updates).eq("id", source_id).eq("user_id", user_id).execute()
        return bool(response.data)
    except Exception as e:
        print(f"Error updating user source: {e}")
        return False


def delete_user_source(source_id: str, user_id: str) -> bool:
    """
    Delete a user's content source
    
    Args:
        source_id: ID of the source to delete
        user_id: User ID (for security verification)
    
    Returns:
        True if deleted successfully, False otherwise
    """
    try:
        from supabase_client import get_supabase_client
        supabase = get_supabase_client()
        
        # Delete the source (with user_id verification for security)
        response = supabase.table("user_sources").delete().eq("id", source_id).eq("user_id", user_id).execute()
        
        if response.data:
            print(f"✅ Source deleted: {source_id}")
            return True
        else:
            print(f"❌ Failed to delete source: {source_id}")
            return False
            
    except Exception as e:
        print(f"❌ Error deleting source: {e}")
        import traceback
        traceback.print_exc()
        return False

# User Preferences Management
def save_user_preferences(user_id: str, preferences: Dict) -> bool:
    """Save user preferences"""
    supabase = get_supabase_client()
    
    if not supabase:
        return False
    
    try:
        pref_data = {
            "user_id": user_id,
            **preferences,
            "updated_at": "now()"
        }
        
        # Upsert preferences (insert or update if exists)
        response = supabase.table("user_preferences").upsert(pref_data).execute()
        return bool(response.data)
    except Exception as e:
        print(f"Error saving user preferences: {e}")
        return False

def get_user_preferences(user_id: str) -> Optional[Dict]:
    """Get user preferences"""
    supabase = get_supabase_client()
    
    if not supabase:
        return None
    
    try:
        response = supabase.table("user_preferences").select("*").eq("user_id", user_id).single().execute()
        return response.data
    except Exception as e:
        print(f"Error fetching user preferences: {e}")
        return None

# Analytics and Stats
def get_user_stats(user_id: str) -> Dict:
    """Get user statistics"""
    supabase = get_supabase_client()
    
    if not supabase:
        return {}
    
    try:
        newsletters = fetch_newsletters(user_id)
        sources = get_user_sources(user_id)
        
        stats = {
            "total_newsletters": len(newsletters),
            "draft_newsletters": len([n for n in newsletters if n.get('status') == 'draft']),
            "published_newsletters": len([n for n in newsletters if n.get('status') == 'published']),
            "total_sources": len(sources),
            "active_sources": len([s for s in sources if s.get('active', True)]),
            "last_newsletter_date": newsletters[0].get('created_at') if newsletters else None
        }
        
        return stats
    except Exception as e:
        print(f"Error calculating user stats: {e}")
        return {}