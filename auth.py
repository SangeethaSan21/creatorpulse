from datetime import datetime, UTC
from supabase_client import get_supabase_client

# Shared Supabase client for this module
supabase = get_supabase_client()

def sign_up(email, password, username=None):
    """Create a new user account"""
    if not supabase:
        print("Supabase client not initialized")
        return None
    
    try:
        res = supabase.auth.sign_up({"email": email, "password": password})
        
        if res.user:
            # Generate username from email if not provided
            if not username:
                username = email.split("@")[0]
            
            user_data = {
                "id": res.user.id,
                "email": res.user.email,
                "username": username
            }
            
            # Create user profile in users table
            try:
                supabase.table("users").upsert({
                    "id": user_data['id'],
                    "email": email,
                    "username": username,
                    "display_name": username,
                    "name": username,
                    "created_at": datetime.now(UTC).isoformat()
                }).execute()
            except Exception as e:
                print(f"Warning: Could not create user profile: {e}")
            
            return user_data
        return None
    except Exception as e:
        print(f"Sign-up error: {e}")
        return None

def sign_in(email, password):
    """Sign in existing user and maintain session"""
    if not supabase:
        print("Supabase client not initialized")
        return None
    
    try:
        # Sign in using Supabase auth - this sets the session
        res = supabase.auth.sign_in_with_password({
            "email": email, 
            "password": password
        })
        
        if res.user:
            # Fetch username from users table
            try:
                user_profile = supabase.table("users").select("username, display_name").eq("id", res.user.id).single().execute()
                username = user_profile.data.get("username") if user_profile.data else email.split("@")[0]
                display_name = user_profile.data.get("display_name") if user_profile.data else username
            except:
                username = email.split("@")[0]
                display_name = username
            
            user_data = {
                "id": res.user.id,
                "email": res.user.email,
                "username": username,
                "display_name": display_name,
                "session": res.session
            }
            
            print(f"✅ Login successful - User ID: {user_data['id']}")
            print(f"✅ Username: {username}")
            print(f"✅ Session established: {res.session is not None}")
            
            return user_data
        else:
            print("❌ Login failed: Invalid credentials")
            return None
    except Exception as e:
        print(f"❌ Login error: {e}")
        return None

def sign_out():
    """Sign out current user"""
    if not supabase:
        return False
    
    try:
        supabase.auth.sign_out()
        print("✅ User signed out successfully")
        return True
    except Exception as e:
        print(f"Sign-out error: {e}")
        return False

def get_current_user():
    """Get current authenticated user"""
    if not supabase:
        return None
    
    try:
        user = supabase.auth.get_user()
        if user:
            print(f"✅ Current user: {user.user.id if user.user else 'None'}")
        return user.user if user else None
    except Exception as e:
        print(f"Error getting current user: {e}")
        return None

def reset_password(email):
    """Send password reset email"""
    if not supabase:
        return False
    
    try:
        res = supabase.auth.reset_password_email(email)
        return True
    except Exception as e:
        print(f"Password reset error: {e}")
        return False