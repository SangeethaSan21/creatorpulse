"""
Centralized Supabase client to share authenticated session across modules
"""
import os
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# Single shared Supabase client instance
supabase: Client = None

def get_supabase_client() -> Client:
    """Get or create the Supabase client instance"""
    global supabase
    
    if supabase is None:
        if SUPABASE_URL and SUPABASE_KEY:
            try:
                supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
                print("✅ Supabase client initialized")
            except Exception as e:
                print(f"❌ Failed to initialize Supabase client: {e}")
                raise
        else:
            raise ValueError("Missing SUPABASE_URL or SUPABASE_KEY")
    
    return supabase

def reset_supabase_client():
    """Reset the client (useful for testing or logout)"""
    global supabase
    supabase = None