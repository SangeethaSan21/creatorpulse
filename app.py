import os
import json
import streamlit as st
from datetime import datetime, UTC
from dotenv import load_dotenv
import threading  
import schedule   
import time
import re       

# Load environment variables FIRST before any other imports
load_dotenv()

from supabase_client import get_supabase_client

from auth import sign_in, sign_up, sign_out
from content_aggregator import parse_rss_feed, extract_trends, parse_multiple_feeds, detect_trending_topics,aggregate_all_sources 
from draft_generator import generate_newsletter_with_ai
from models import fetch_newsletters, save_newsletter, save_user_sources, get_user_sources, update_newsletter
from utils import validate_email, validate_rss_url
from style_trainer import analyze_writing_style, save_style_profile, get_style_profile, generate_style_prompt
from feedback_system import record_feedback, get_feedback_stats, get_engagement_analytics, start_review_timer, stop_review_timer, get_average_review_time, save_edit_history, get_edit_patterns, calculate_edit_metrics   
from email_service import send_newsletter_email, send_test_email, is_email_configured, send_telegram_message, send_newsletter_via_telegram, is_telegram_configured, send_test_telegram, get_telegram_chat_id
from social_media_generator import generate_social_posts, save_social_post, get_user_social_posts

# Load environment variables
load_dotenv()
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")


# Initialize Supabase client using shared instance
try:
    supabase = get_supabase_client()
    print("✅ Supabase client initialized successfully")
except Exception as e:
    st.error("⚠️ Failed to connect to Supabase")
    st.error(f"Error: {str(e)}")
    st.markdown("""
    ### Setup Required
    
    To use CreatorPulse, you need to add three API keys as environment variables:
    
    1. **SUPABASE_URL** - Your Supabase project URL
    2. **SUPABASE_KEY** - Your Supabase anon/public key  
    3. **GROQ_API_KEY** - Your Groq API key
    
    📖 **See [SETUP_GUIDE.md](SETUP_GUIDE.md) for detailed instructions.**
    
    ### Quick Links:
    - [Get Supabase Keys](https://supabase.com) - Free database & auth
    - [Get Groq API Key](https://console.groq.com) - Free AI generation
    """)
    st.stop()

# Page configuration
st.set_page_config(
    page_title="CreatorPulse - AI Newsletter Curator", 
    page_icon="📰",
    layout="wide",
    initial_sidebar_state="expanded"
)

def html_to_pdf(html_content: str) -> bytes:
    """Convert HTML newsletter to PDF using reportlab"""
    from reportlab.lib.pagesizes import letter
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from io import BytesIO
    import re
    
    try:
        # Extract text from HTML
        text = re.sub(r'<[^>]+>', '', html_content)
        text = re.sub(r'\s+', ' ', text).strip()
        
        # Create PDF
        pdf_buffer = BytesIO()
        doc = SimpleDocTemplate(pdf_buffer, pagesize=letter)
        story = []
        styles = getSampleStyleSheet()
        
        # Split into paragraphs
        for para in text.split('\n'):
            if para.strip():
                story.append(Paragraph(para, styles['Normal']))
                story.append(Spacer(1, 0.1*inch))
        
        doc.build(story)
        
        pdf_buffer.seek(0)
        return pdf_buffer.getvalue()
        
    except Exception as e:
        print(f"Error converting HTML to PDF: {e}")
        return None

def generate_diff_html(original: str, edited: str) -> str:
    """Generate HTML diff visualization"""
    import difflib
    
    # Split into lines
    original_lines = original.splitlines()
    edited_lines = edited.splitlines()
    
    # Generate diff
    diff = difflib.unified_diff(
        original_lines,
        edited_lines,
        lineterm='',
        n=3  # Context lines
    )
    
    # Convert to HTML
    html_parts = ['<div style="font-family: monospace; font-size: 12px; background: #f8f9fa; padding: 15px; border-radius: 8px; max-height: 400px; overflow-y: auto;">']
    
    for line in diff:
        if line.startswith('+++') or line.startswith('---'):
            continue  # Skip file markers
        elif line.startswith('@@'):
            html_parts.append(f'<div style="color: #6c757d; margin: 10px 0;">{line}</div>')
        elif line.startswith('+'):
            html_parts.append(f'<div style="background: #d4edda; color: #155724; padding: 2px 5px;">+ {line[1:]}</div>')
        elif line.startswith('-'):
            html_parts.append(f'<div style="background: #f8d7da; color: #721c24; padding: 2px 5px;">- {line[1:]}</div>')
        else:
            html_parts.append(f'<div style="color: #495057; padding: 2px 5px;">{line}</div>')
    
    html_parts.append('</div>')
    
    return ''.join(html_parts)


# Initialize session state
def initialize_session_state():
    defaults = {
        "user": None,
        "user_id": None,
        "generated_newsletter": None,
        "newsletters": [],
        "user_sources": [],
        "current_trends": [],
        "current_articles": [],
        "current_newsletter_id": None,
        "current_newsletter_title": None
    }
    for key, default_value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = default_value

initialize_session_state()


def background_scheduler():
    """
    Background thread that checks and sends scheduled newsletters
    Runs every minute automatically
    """
    print("🚀 Background scheduler thread started!")
    
    def check_and_send_scheduled():
        """Check for scheduled deliveries and send them"""
        try:
            supabase = get_supabase_client()
            current_time = datetime.now().strftime('%H:%M')
            
            # Get all active schedules
            response = supabase.table("scheduled_deliveries").select("*").eq("is_active", True).execute()
            
            if not response.data:
                return
            
            # Check each schedule
            for schedule_data in response.data:
                schedule_time = schedule_data.get('schedule_time', '')[:5]  # HH:MM
                
                # If time matches, send newsletter
                if schedule_time == current_time:
                    user_id = schedule_data['user_id']
                    print(f"⏰ Time to send newsletter for user {user_id}")
                    
                    try:
                        # Get user email
                        user_response = supabase.table("users").select("email").eq("id", user_id).single().execute()
                        if not user_response.data:
                            continue
                        
                        user_email = user_response.data['email']
                        print(f"📧 Generating newsletter for {user_email}")
                        
                        # Get user's RSS sources
                        user_sources = get_user_sources(user_id)
                        rss_feeds = [s['url'] for s in user_sources if s.get('type') in ['rss_feed', 'rss']]
                        
                        # Use default feeds if no sources configured
                        if not rss_feeds:
                            rss_feeds = [
                                "https://techcrunch.com/feed/",
                                "https://www.theverge.com/rss/index.xml"
                            ]
                        
                        # Fetch articles
                        articles = parse_multiple_feeds(rss_feeds, max_articles_per_feed=5)
                        
                        if not articles:
                            print(f"❌ No articles found for {user_email}")
                            continue
                        
                        # Extract trends
                        trends = extract_trends(articles)
                        
                        # Generate newsletter with AI
                        title = f"Daily Digest - {datetime.now().strftime('%B %d, %Y')}"
                        content = generate_newsletter_with_ai(
                            articles=articles,
                            trends=trends,
                            title=title,
                            topic="Technology & Innovation",
                            tone="Professional",
                            api_key=GROQ_API_KEY,
                            user_id=user_id
                        )
                        
                        # Save to database
                        newsletter_data = {
                            "user_id": user_id,
                            "title": title,
                            "content": content,
                            "status": "draft",
                            "trends": json.dumps(trends),
                            "topic": "Technology & Innovation",
                            "tone": "Professional",
                            "created_at": datetime.now(UTC).isoformat()
                        }
                        
                        saved_id = save_newsletter(newsletter_data)
                        
                        if not saved_id:
                            print(f"❌ Failed to save newsletter")
                            continue
                        
                        print(f"💾 Newsletter saved with ID: {saved_id}")
                        
                        # Send email
                        delivery_method = schedule_data.get('delivery_method', 'email')
                        subject = f"📰 {title}"
                        success = False
                        
                        # Send via Email
                        if delivery_method in ['email', 'both']:
                            email_success = send_newsletter_email(
                                recipient_email=user_email,
                                subject=subject,
                                html_content=content
                            )
                            if email_success:
                                print(f"✅ Email sent to {user_email}")
                                success = True
                        
                        # ✅ NEW: Send via Telegram
                        if delivery_method in ['telegram', 'both']:
                            telegram_chat_id = schedule_data.get('telegram_chat_id')
                            if telegram_chat_id:
                                telegram_success = send_newsletter_via_telegram(
                                    chat_id=telegram_chat_id,
                                    newsletter_title=title,
                                    newsletter_content=content
                                )
                                if telegram_success:
                                    print(f"✅ Telegram sent to chat {telegram_chat_id}")
                                    success = True
                            else:
                                print("⚠️ Telegram selected but no chat_id found")
                        
                        if success:
                            print(f"✅ Newsletter sent to {user_email}")
                            
                            # Update last delivery time
                            supabase.table("scheduled_deliveries").update({
                                "last_delivered_at": datetime.now(UTC).isoformat()
                            }).eq("user_id", user_id).execute()
                            
                            # Update newsletter status
                            update_newsletter(saved_id, {
                                "status": "sent",
                                "sent_at": datetime.now(UTC).isoformat()
                            }, user_id)
                            
                            print(f"🎉 Scheduled delivery completed!")
                        else:
                            print(f"❌ Failed to send email to {user_email}")
                    
                    except Exception as e:
                        print(f"❌ Error processing schedule for user {user_id}: {e}")
                        import traceback
                        traceback.print_exc()
        
        except Exception as e:
            print(f"❌ Scheduler error: {e}")
    
    # Schedule the job to run every minute
    schedule.every(1).minutes.do(check_and_send_scheduled)
    
    # Keep running forever
    while True:
        schedule.run_pending()
        time.sleep(30)  # Sleep for 30 seconds between checks


def start_scheduler():
    """Start the background scheduler thread"""
    if 'scheduler_thread_started' not in st.session_state:
        st.session_state.scheduler_thread_started = True
        
        # Create and start background thread
        scheduler_thread = threading.Thread(target=background_scheduler, daemon=True)
        scheduler_thread.start()


# Custom CSS for better styling
st.markdown("""
<style>
.main-header {
    text-align: center;
    color: #1e293b;
    margin-bottom: 2rem;
}
.success-box {
    padding: 1rem;
    background-color: #dcfce7;
    border-left: 4px solid #22c55e;
    border-radius: 0.5rem;
    margin: 1rem 0;
}
.error-box {
    padding: 1rem;
    background-color: #fef2f2;
    border-left: 4px solid #ef4444;
    border-radius: 0.5rem;
    margin: 1rem 0;
}
.info-box {
    padding: 1rem;
    background-color: #f0f9ff;
    border-left: 4px solid #3b82f6;
    border-radius: 0.5rem;
    margin: 1rem 0;
}
</style>
""", unsafe_allow_html=True)

# Authentication Section
def render_auth_section():
    """Enhanced authentication section with modern styling"""
    
    # Custom CSS for beautiful auth page
    st.markdown("""
    
    <style>
    /* Hide Streamlit branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    /* Main container styling */
    .block-container {
    padding-top: 0 !important;
    padding-bottom: 0 !important;
    max-width: 100% !important;
}

.auth-header {
    width: 100vw; /* full viewport width */
    margin-left: calc(-50vw + 50%);
    border-radius: 0;
    padding: 4rem 2rem;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    text-align: center;
    color: white;
    box-shadow: 0 10px 40px rgba(102, 126, 234, 0.3);
}
    
    /* Auth header styling */
    .auth-header {
        text-align: center;
        margin-bottom: 3rem;
        padding: 2rem;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        border-radius: 20px;
        color: white;
        box-shadow: 0 10px 40px rgba(102, 126, 234, 0.3);
    }
    
    .auth-logo {
        font-size: 4rem;
        margin-bottom: 1rem;
        animation: float 3s ease-in-out infinite;
    }
    
    @keyframes float {
        0%, 100% { transform: translateY(0px); }
        50% { transform: translateY(-10px); }
    }
    
    .auth-title {
        font-size: 3rem;
        font-weight: 800;
        margin: 0;
        letter-spacing: -1px;
    }
    
    .auth-subtitle {
        font-size: 1.2rem;
        opacity: 0.95;
        margin-top: 0.5rem;
    }
    
    /* Features section */
    .features-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
        gap: 1.5rem;
        margin: 2rem 0 3rem 0;
    }
    
    .feature-card {
        background: linear-gradient(135deg, #f6f8fb 0%, #ffffff 100%);
        padding: 1.5rem;
        border-radius: 12px;
        border: 2px solid #e2e8f0;
        transition: all 0.3s ease;
    }
    
    .feature-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 10px 30px rgba(0, 0, 0, 0.1);
        border-color: #667eea;
    }
    
    .feature-icon {
        font-size: 2.5rem;
        margin-bottom: 0.5rem;
    }
    
    .feature-title {
        font-size: 1.1rem;
        font-weight: 700;
        color: #1e293b;
        margin-bottom: 0.5rem;
    }
    
    .feature-desc {
        font-size: 0.9rem;
        color: #64748b;
        line-height: 1.5;
    }
    
    /* Tab styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 10px;
        background: white;
        padding: 8px;
        border-radius: 12px;
        box-shadow: 0 2px 10px rgba(0, 0, 0, 0.05);
    }
    
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        padding: 0 30px;
        background: transparent;
        border-radius: 8px;
        font-weight: 600;
        font-size: 1rem;
        color: #64748b;
        border: none;
    }
    
    .stTabs [data-baseweb="tab"]:hover {
        background: #f1f5f9;
        color: #1e293b;
    }
    
    .stTabs [aria-selected="true"] {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%) !important;
        color: white !important;
    }
    
    /* Form styling */
    .stTextInput > div > div > input {
        background: #f8fafc;
        border: 2px solid #e2e8f0;
        border-radius: 10px;
        padding: 12px 16px;
        font-size: 15px;
        transition: all 0.3s;
    }
    
    .stTextInput > div > div > input:focus {
        background: white;
        border-color: #667eea;
        box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
    }
    
    /* Button styling */
    .stButton > button {
        width: 100%;
        background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%) !important;
        color: white !important;
        border: none !important;
        border-radius: 8px !important;
        padding: 10px 16px !important;
        font-size: 14px !important;
        font-weight: 600 !important;
        transition: all 0.2s ease !important;
        box-shadow: 0 2px 8px rgba(59, 130, 246, 0.3)
    }
    
    .stButton > button:hover {
        background: linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%) !important;
        box-shadow: 0 4px 12px rgba(59, 130, 246, 0.4) !important;
        transform: translateY(-1px) !important;
    }
    
    .stButton > button:active {
        transform: translateY(0);
    }

    .stDownloadButton > button {
    background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%) !important;
    color: white !important;
    border: none !important;
    }

    .stDownloadButton > button:hover {
        background: linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%) !important;
    }
    
    /* Form labels */
    .stTextInput > label {
        font-weight: 600;
        color: #2d3748;
        font-size: 14px;
        margin-bottom: 8px;
    }
    
    /* Success/Error messages */
    .stSuccess {
        background: #dcfce7;
        border-left: 4px solid #22c55e;
        border-radius: 8px;
        padding: 1rem;
    }
    
    .stError {
        background: #fef2f2;
        border-left: 4px solid #ef4444;
        border-radius: 8px;
        padding: 1rem;
    }
    
    /* Help text */
    .help-text {
        background: #f0f9ff;
        border-left: 4px solid #3b82f6;
        border-radius: 8px;
        padding: 1rem;
        margin: 1rem 0;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Header section
    st.markdown("""
    <div class='auth-header'>
        <div class='auth-logo'>📰</div>
        <h1 class='auth-title'>CreatorPulse</h1>
        <p class='auth-subtitle'>AI-Powered Newsletter Curation Platform</p>
    </div>
    """, unsafe_allow_html=True)
    
  
      
    # Authentication tabs
    tab1, tab2 = st.tabs(["🔐 Sign In", "✨ Create Account"])
    
    with tab1:
        st.markdown("<br>", unsafe_allow_html=True)
        
        with st.form("login_form", clear_on_submit=False):
            st.markdown("### Welcome back!")
            st.markdown("Sign in to continue to your dashboard")
            st.markdown("<br>", unsafe_allow_html=True)
            
            email = st.text_input(
                "Email Address",
                placeholder="your@email.com",
                key="login_email"
            )
            
            password = st.text_input(
                "Password",
                type="password",
                placeholder="Enter your password",
                key="login_password"
            )
            
            col1, col2 = st.columns([1, 1])
            with col1:
                remember = st.checkbox("Remember me")
            with col2:
                st.markdown("<div style='text-align: right; padding-top: 4px;'><a href='#' style='color: #667eea; text-decoration: none; font-weight: 600;'>Forgot password?</a></div>", unsafe_allow_html=True)
            
            st.markdown("<br>", unsafe_allow_html=True)
            submitted = st.form_submit_button("Sign In", use_container_width=True)
        
        if submitted:
            if not validate_email(email):
                st.error("❌ Please enter a valid email address")
            elif len(password) < 6:
                st.error("❌ Password must be at least 6 characters long")
            else:
                with st.spinner("🔄 Signing in..."):
                    user = sign_in(email, password)
                    if user:
                        st.session_state.user = user
                        st.session_state.user_id = user["id"]
                        st.success("✅ Successfully logged in!")
                        st.balloons()
                        st.rerun()
                    else:
                        st.error("❌ Invalid email or password. Please try again.")
    
    with tab2:
        st.markdown("<br>", unsafe_allow_html=True)
        
        with st.form("signup_form", clear_on_submit=False):
            st.markdown("### Create your account")
            st.markdown("Join CreatorPulse and start curating smarter")
            st.markdown("<br>", unsafe_allow_html=True)
            
            col1, col2 = st.columns(2)
            
            with col1:
                email = st.text_input(
                    "Email Address",
                    placeholder="your@email.com",
                    key="signup_email"
                )
            
            with col2:
                username = st.text_input(
                    "Username",
                    placeholder="johndoe",
                    key="signup_username",
                    help="Letters, numbers, underscores, and hyphens only (min 3 chars)"
                )
            
            password = st.text_input(
                "Password",
                type="password",
                placeholder="Create a strong password",
                key="signup_password",
                help="Must be at least 6 characters"
            )
            
            confirm_password = st.text_input(
                "Confirm Password",
                type="password",
                placeholder="Re-enter your password",
                key="confirm_password"
            )
            
            st.markdown("<br>", unsafe_allow_html=True)
            
            agree = st.checkbox("I agree to the Terms of Service and Privacy Policy")
            
            st.markdown("<br>", unsafe_allow_html=True)
            submitted = st.form_submit_button("Create Account", use_container_width=True)
            
            if submitted:
                if not agree:
                    st.error("❌ Please agree to the Terms of Service and Privacy Policy")
                elif not validate_email(email):
                    st.error("❌ Please enter a valid email address")
                elif not username or len(username) < 3:
                    st.error("❌ Username must be at least 3 characters long")
                elif not re.match(r'^[a-zA-Z0-9_-]+$', username):
                    st.error("❌ Username can only contain letters, numbers, underscores, and hyphens")
                elif len(password) < 6:
                    st.error("❌ Password must be at least 6 characters long")
                elif password != confirm_password:
                    st.error("❌ Passwords do not match")
                else:
                    with st.spinner("🔄 Creating your account..."):
                        user = sign_up(email, password, username)
                        if user:
                            st.session_state.user = user
                            st.session_state.user_id = user["id"]
                            st.success(f"🎉 Account created successfully! Welcome, @{username}!")
                            st.balloons()
                            st.rerun()
                        else:
                            st.error("❌ Failed to create account. Username or email may already exist.")
    
    # Footer
    st.markdown("<br><br>", unsafe_allow_html=True)
    st.markdown("""
    <div style='text-align: center; color: #94a3b8; font-size: 0.9rem; padding: 2rem 0;'>
        <p>🔒 Secure authentication powered by Supabase</p>
        <p style='margin-top: 0.5rem;'>Need help? <a href='#' style='color: #667eea; text-decoration: none;'>Contact Support</a></p>
    </div>
    """, unsafe_allow_html=True)

# Main Dashboard
def render_dashboard():
    username = st.session_state.user.get('username') or st.session_state.user.get('display_name') or st.session_state.user.get('email', 'User')
    st.markdown(f"<h2>Welcome back, {username}! 👋</h2>", unsafe_allow_html=True)

    if 'current_page' not in st.session_state:
        st.session_state.current_page = "Dashboard"
    
    # Sidebar Navigation
    with st.sidebar:
        st.markdown("### Navigation")
        
        # Navigation buttons
        col1 = st.columns(1)[0]
        
        nav_items = [
            ("📊", "Dashboard"),
            ("✏️", "Create Newsletter"),
            ("📡", "RSS Sources"),
            ("🎨", "Style Trainer"),
            ("⏰", "Scheduler"),
            ("📊", "Analytics"),
            ("⚙️", "Settings"),
            ("📱", "Social Media")
        ]
        
        for emoji, label in nav_items:
            # Highlight current page
            if st.session_state.current_page == label:
                button_style = "primary"
            else:
                button_style = "secondary"
            
            if st.button(f"{emoji} {label}", use_container_width=True, type=button_style):
                st.session_state.current_page = label
                st.rerun()
        
        st.markdown("---")
        
        if st.button("🚪 Logout", use_container_width=True):
            sign_out()
            st.session_state.clear()
            st.rerun()
        
        st.markdown("---")
        st.markdown("### Quick Stats")
        newsletters = fetch_newsletters(st.session_state.user_id)
        st.metric("Total Newsletters", len(newsletters))
        draft_count = len([n for n in newsletters if n.get('status') == 'draft'])
        st.metric("Drafts", draft_count)
    
    # Main content - render based on sidebar selection
    if st.session_state.current_page == "Dashboard":
        render_dashboard_tab()
    elif st.session_state.current_page == "Create Newsletter":
        render_create_newsletter_tab()
    elif st.session_state.current_page == "RSS Sources":
        render_sources_tab()
    elif st.session_state.current_page == "Style Trainer":
        render_style_trainer_tab()
    elif st.session_state.current_page == "Scheduler":
        render_scheduler_tab()
    elif st.session_state.current_page == "Analytics":
        render_analytics_tab()
    elif st.session_state.current_page == "Settings":
        render_settings_tab()
    elif st.session_state.current_page == "Social Media":
        render_social_media_tab()

def render_dashboard_tab():
    """Render dashboard with custom HTML/CSS for professional card layout"""
    
    newsletters = fetch_newsletters(st.session_state.user_id)
    
    # Custom CSS for the entire dashboard
    st.markdown("""
    <style>
    /* Background */
    [data-testid="stAppViewContainer"] {
        background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
    }
    
    /* Dashboard Header */
    .dashboard-header {
        margin-bottom: 30px;
    }
    
    .dashboard-title {
        font-size: 32px;
        font-weight: 700;
        color: #1a202c;
        margin: 0;
    }
    
    .dashboard-subtitle {
        font-size: 14px;
        color: #718096;
        margin: 5px 0 0 0;
    }
    
    /* Stat Cards */
    .stat-card {
        background: white;
        border-radius: 12px;
        padding: 24px;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
        border: 1px solid #e2e8f0;
        transition: all 0.3s ease;
    }
    
    .stat-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 16px rgba(0, 0, 0, 0.12);
    }
    
    .stat-label {
        font-size: 13px;
        color: #718096;
        font-weight: 500;
        margin-bottom: 8px;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    
    .stat-value {
        font-size: 36px;
        font-weight: 700;
        color: #2d3748;
        margin-bottom: 4px;
    }
    
    .stat-card:nth-child(2) .stat-value {
        color: #d69e2e;
    }
    
    .stat-card:nth-child(3) .stat-value {
        color: #38a169;
    }
    
    .stat-hint {
        font-size: 12px;
        color: #a0aec0;
    }
    
    /* Streamlit Expander Styling */
    .stExpander {
        background: white !important;
        border: 1px solid #e2e8f0 !important;
        border-radius: 12px !important;
        margin-bottom: 16px !important;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08) !important;
        transition: all 0.3s ease !important;
    }
    
    .stExpander:hover {
        border-color: #cbd5e0 !important;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08) !important;
    }
    
    .stExpander > div {
        border: none !important;
    }
    
    /* Expander Header */
    .stExpander > summary {
        padding: 16px 20px !important;
        background: #f7fafc !important;
        border-bottom: 1px solid #e2e8f0 !important;
        font-weight: 600 !important;
        color: #2d3748 !important;
        cursor: pointer !important;
    }
    
    .stExpander > summary:hover {
        background: #edf2f7 !important;
    }
    
    /* Expander Content */
    .stExpander > div > div {
        padding: 24px 20px !important;
    }
    
    .status-badge {
        display: inline-block;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 12px;
        font-weight: 600;
        margin-left: 12px;
    }
    
    .status-draft {
        background: #fef5e7;
        color: #7d6608;
        border: 1px solid #f9e79f;
    }
    
    .status-published {
        background: #d5f4e6;
        color: #0b5345;
        border: 1px solid #a9dfbf;
    }
    
    .status-sent {
        background: #d6eaf8;
        color: #0c3483;
        border: 1px solid #85c1e2;
    }
    
    @media (max-width: 768px) {
        .stat-card {
            grid-template-columns: 1fr;
        }
    }
    </style>
    """, unsafe_allow_html=True)
    
    if not newsletters:
        st.markdown("""
        <div class='info-box'>
            <h4>🚀 Welcome to CreatorPulse!</h4>
            <p>You haven't created any newsletters yet. Get started by:</p>
            <ul>
                <li>Adding RSS feed sources in the <strong>Sources</strong> tab</li>
                <li>Creating your first newsletter in the <strong>Create Newsletter</strong> tab</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
        return
    
    # Header
    st.markdown("""
    <div class='dashboard-header'>
        <h1 class='dashboard-title'>📊 Your Newsletter Dashboard</h1>
        <p class='dashboard-subtitle'>Manage and track all your newsletters</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Stats Cards
    col1, col2, col3 = st.columns(3)
    
    total = len(newsletters)
    drafts = len([n for n in newsletters if n.get('status') == 'draft'])
    published = len([n for n in newsletters if n.get('status') == 'published'])
    
    with col1:
        st.markdown(f"""
        <div class='stat-card'>
            <div class='stat-label'>Total Newsletters</div>
            <div class='stat-value'>{total}</div>
            <div class='stat-hint'>All time</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
        <div class='stat-card'>
            <div class='stat-label'>Drafts</div>
            <div class='stat-value'>{drafts}</div>
            <div class='stat-hint'>Waiting for review</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown(f"""
        <div class='stat-card'>
            <div class='stat-label'>Published</div>
            <div class='stat-value'>{published}</div>
            <div class='stat-hint'>Live campaigns</div>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Recent Newsletters Section
    st.markdown("""
    <h2 style='font-size: 24px; font-weight: 700; color: #1a202c; margin-bottom: 20px;'>
        Recent Newsletters
    </h2>
    """, unsafe_allow_html=True)
    
    # Newsletter Cards using Streamlit Expanders
    for i, newsletter in enumerate(newsletters[:10]):
        status = newsletter.get('status', 'draft')
        title = newsletter.get('title', 'Untitled')
        topic = newsletter.get('topic', 'N/A')
        tone = newsletter.get('tone', 'N/A')
        created = newsletter.get('created_at', 'N/A')
        newsletter_id = newsletter.get('id')
        
        # Format date
        if created != 'N/A':
            try:
                dt = datetime.fromisoformat(created.replace('Z', '+00:00'))
                formatted_date = dt.strftime('%B %d, %Y at %I:%M %p')
            except:
                formatted_date = created[:10]
        else:
            formatted_date = 'N/A'
        
        # Status badge styling
        status_class = f"status-{status}"
        status_text = status.upper()
        
        # Expander header with title and status (plain text, no HTML)
        expander_label = f"📰 {title} — {status_text}"
        
        with st.expander(expander_label, expanded=False):
            # Status badge display
            st.markdown(f"<div class='status-badge {status_class}'>{status_text}</div>", unsafe_allow_html=True)
            
            st.divider()
            
            # Details section
            col1, col2 = st.columns([2, 1])
            
            with col1:
                st.markdown(f"**Topic:** {topic}")
                st.markdown(f"**Tone:** {tone}")
            
            with col2:
                st.markdown(f"**Created:** {formatted_date}")
            
            st.divider()
            
            # Action buttons
            col1, col2, col3, col4, col5, col6 = st.columns(6)
            
            with col1:
                if st.button("👁 View", key=f"view_{i}", use_container_width=True):
                    st.session_state[f'show_newsletter_{i}'] = not st.session_state.get(f'show_newsletter_{i}', False)
                    st.rerun()
            
            with col2:
                st.download_button(
                    label="📥 Download",
                    data=newsletter.get('content', ''),
                    file_name=f"{title.replace(' ', '_')}.html",
                    mime="text/html",
                    key=f"dl_{i}",
                    use_container_width=True
                )
            
            with col3:
                if st.button("👍 Good", key=f"up_{i}", use_container_width=True):
                    if record_feedback(newsletter_id, st.session_state.user_id, "thumbs_up"):
                        st.success("Feedback saved!")
                
            with col4:
                if st.button("👎 Bad", key=f"down_{i}", use_container_width=True):
                    if record_feedback(newsletter_id, st.session_state.user_id, "thumbs_down"):
                        st.info("Noted!")
                
            with col5:
                if st.button("🗑️ Delete", key=f"delete_{i}", use_container_width=True):
                    if f'confirm_delete_{i}' not in st.session_state:
                        st.session_state[f'confirm_delete_{i}'] = True
                        st.warning("⚠️ Click again to confirm")
                    elif st.session_state.get(f'confirm_delete_{i}', False):
                        from models import delete_newsletter
                        if delete_newsletter(newsletter_id, st.session_state.user_id):
                            st.success("✅ Deleted!")
                            if f'confirm_delete_{i}' in st.session_state:
                                del st.session_state[f'confirm_delete_{i}']
                            st.rerun()
                        else:
                            st.error("❌ Failed to delete")

            with col6:
                if st.button("📧 Send", key=f"send_{i}", use_container_width=True):
                    if not is_email_configured():
                        st.error("Email not configured")
                    else:
                        user_email = st.session_state.user.get('email')
                        with st.spinner("Sending..."):
                            if send_newsletter_email(
                                recipient_email=user_email,
                                subject=f"📰 {title}",
                                html_content=newsletter.get('content', '')
                            ):
                                st.success("Email sent!")
            
            # Preview if toggled
            if st.session_state.get(f'show_newsletter_{i}', False):
                st.markdown("---")
                st.markdown("### 📄 Newsletter Preview")
                content = newsletter.get('content', '<p>No content</p>')
                st.components.v1.html(content, height=600, scrolling=True)
            
          

def render_create_newsletter_tab():
    st.subheader("✏️ Create New Newsletter")
    
    with st.form("newsletter_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            title_input = st.text_input("Newsletter Title", placeholder="Weekly Tech Digest")
            topic = st.text_input("Topic/Theme", placeholder="Technology, AI, Startups")
            tone = st.selectbox("Writing Tone", ["Professional", "Casual", "Creative", "Technical"])
        
        with col2:
            max_articles = st.slider("Maximum Articles", min_value=3, max_value=20, value=8)
            include_trends = st.checkbox("Include Trends Section", value=True)
            
            # Get user's saved sources for dropdown
            user_sources = get_user_sources(st.session_state.user_id)
            
            # Popular RSS feeds
            popular_feeds = {
                "-- Select or enter custom URL --": "",
                "TechCrunch": "https://techcrunch.com/feed/",
                "The Verge": "https://www.theverge.com/rss/index.xml",
                "Ars Technica": "https://feeds.arstechnica.com/arstechnica/index",
                "Wired": "https://www.wired.com/feed/rss",
                "MIT Technology Review": "https://www.technologyreview.com/feed/",
                "VentureBeat": "https://venturebeat.com/feed/",
                "Hacker News": "https://news.ycombinator.com/rss",
                "OpenAI Blog": "https://openai.com/blog/rss.xml",
                "AI News": "https://www.artificialintelligence-news.com/feed/"
            }
            
            # Add user's saved sources to dropdown
            for source in user_sources:
                source_name = f"My Source: {source.get('name')}"
                popular_feeds[source_name] = source.get('url')
            
            # Dropdown for RSS feed
            selected_feed = st.selectbox(
                "Custom RSS Feed (optional)",
                options=list(popular_feeds.keys())
            )
            
            # Get the URL from selection
            custom_rss = popular_feeds.get(selected_feed, "")
            
            # Show text input if user wants to enter custom URL
            if selected_feed == "-- Select or enter custom URL --":
                custom_rss = st.text_input(
                    "Or enter custom URL:",
                    placeholder="https://example.com/feed.xml",
                    key="custom_rss_input"
                )
            else:
                # Show selected URL
                if custom_rss:
                    st.caption(f"📡 Selected: {custom_rss}")
        
        submitted = st.form_submit_button("🚀 Generate Newsletter", use_container_width=True)
        
    if submitted:
        if not title_input or not topic:
            st.error("Please fill in the newsletter title and topic.")
        else:
            with st.spinner("Generating your newsletter... This may take a few moments."):
                try:
                    # ⭐ Get user sources - ALL TYPES
                    user_sources = get_user_sources(st.session_state.user_id)

                    # Separate by type
                    rss_feeds = [s['url'] for s in user_sources if s['type'] in ['rss_feed', 'rss', 'newsletter', 'blog']]
                    twitter_handles = [s['url'] for s in user_sources if s['type'] == 'twitter_handle']
                    twitter_hashtags = [s['url'] for s in user_sources if s['type'] == 'twitter_hashtag']
                    youtube_channels = [s['url'] for s in user_sources if s['type'] == 'youtube_channel']

                    # Debug output to console
                    print(f"\n📡 Sources Configuration:")
                    print(f"  RSS Feeds: {rss_feeds}")
                    print(f"  Twitter Handles: {twitter_handles}")
                    print(f"  Twitter Hashtags: {twitter_hashtags}")
                    print(f"  YouTube Channels: {youtube_channels}")

                    # Add custom RSS if provided
                    if custom_rss and validate_rss_url(custom_rss):
                        rss_feeds.append(custom_rss)

                    # Use default feeds if no sources configured
                    if not rss_feeds and not twitter_handles and not twitter_hashtags and not youtube_channels:
                        rss_feeds = [
                            "https://techcrunch.com/feed/",
                            "https://feeds.feedburner.com/oreilly/radar"
                        ]
                        st.info("Using default RSS feeds. Add your own sources in the Sources tab for personalized content.")

                    # ⭐ Fetch from ALL sources using the unified aggregator

                    all_articles = aggregate_all_sources(
                        rss_feeds=rss_feeds if rss_feeds else None,
                        twitter_handles=twitter_handles if twitter_handles else None,
                        twitter_hashtags=twitter_hashtags if twitter_hashtags else None,
                        youtube_channels=youtube_channels if youtube_channels else None,
                        max_per_source=5
                    )
                    
                    print(f"\n✅ Total articles fetched: {len(all_articles)}")

                    if not all_articles:
                        st.error("Could not fetch articles from any sources. Please check your sources and try again.")
                        st.info("Debug: Check the console/terminal for detailed error messages.")
                    else:
                        # Show source breakdown
                        rss_count = len([a for a in all_articles if a.get('source') not in ['Twitter', 'YouTube']])
                        twitter_count = len([a for a in all_articles if a.get('source') == 'Twitter'])
                        youtube_count = len([a for a in all_articles if a.get('source') == 'YouTube'])
                        
                        st.success(f"✅ Fetched {len(all_articles)} articles: {rss_count} from RSS, {twitter_count} from Twitter, {youtube_count} from YouTube")
                    
                        # Extract trends if enabled
                        if include_trends:
                            trends = detect_trending_topics(all_articles, use_google_trends=True)
                        else:
                            trends = []
                        
                        # Generate newsletter with AI
                        if GROQ_API_KEY:
                            content = generate_newsletter_with_ai(
                                articles=all_articles,
                                trends=trends,
                                title=title_input,
                                topic=topic,
                                tone=tone,
                                api_key=GROQ_API_KEY,
                                user_id=st.session_state.user_id,
                                max_articles=max_articles
                            )
                            
                            # Save newsletter
                            newsletter_data = {
                                "user_id": st.session_state.user_id,
                                "title": title_input,
                                "content": content,
                                "status": "draft",
                                "trends": json.dumps(trends),
                                "topic": topic,
                                "tone": tone,
                                "created_at": datetime.now(UTC).isoformat()
                            }
                            
                            saved_id = save_newsletter(newsletter_data)
                            if saved_id:
                                st.session_state.generated_newsletter = content
                                st.session_state.current_newsletter_id = saved_id
                                st.session_state.current_newsletter_title = title_input
                                st.session_state.current_articles = all_articles
                                st.session_state.current_trends = trends
                                st.success("✅ Newsletter generated successfully!")
                                st.rerun()
                            else:
                                st.error("Failed to save newsletter. Please try again.")
                        else:
                            st.error("Groq API key is missing. Please set the GROQ_API_KEY environment variable.")
                        
                except Exception as e:
                    st.error(f"An error occurred while generating the newsletter: {str(e)}")
                    import traceback
                    st.error(f"Details: {traceback.format_exc()}")

  

    # Display generated newsletter
    if st.session_state.generated_newsletter:
        st.markdown("---")
        st.subheader("📄 Generated Newsletter Preview")
        
        # Start review timer
        newsletter_id = st.session_state.get('current_newsletter_id', None)
        if newsletter_id and 'review_timer_started' not in st.session_state:
            start_review_timer(newsletter_id, st.session_state.user_id)
            st.session_state.review_timer_started = True
        
        # Action buttons
        col1, col2, col3, col4, col5, col6, col7 = st.columns([1, 1, 1, 1, 1, 1, 1])
        
        with col1:
            if st.button("👍 Good Draft", use_container_width=True, key="thumbs_up_preview"):
                if newsletter_id:
                    if record_feedback(newsletter_id, st.session_state.user_id, "thumbs_up"):
                        st.success("Thanks!")
                    else:
                        st.error("Failed to save feedback")

        
        with col2:
            if st.button("👎 Needs Work", use_container_width=True, key="thumbs_down_preview"):
                if newsletter_id:
                    if record_feedback(newsletter_id, st.session_state.user_id, "thumbs_down"):
                        st.info("We'll improve!")
                    else:
                        st.error("Failed to save feedback")
        
        with col3:
            st.download_button(
                label="📄 HTML",
                data=st.session_state.generated_newsletter,
                file_name=f"newsletter_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html",
                mime="text/html",
                use_container_width=True,
                key="download_html"
            )
        
        with col4:
            pdf_data = html_to_pdf(st.session_state.generated_newsletter)
            if pdf_data:
                st.download_button(
                    label="📕 PDF",
                    data=pdf_data,
                    file_name=f"newsletter_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
                    mime="application/pdf",
                    use_container_width=True,
                    key="download_pdf"
                )
            else:
                st.error("PDF conversion failed")
        
        with col5:
            if st.button("📧 Send Email", use_container_width=True, key="send_email_btn"):
                if not is_email_configured():
                    st.error("⚠️ Email not configured! Go to Settings tab to configure.")
                else:
                    user_email = st.session_state.user.get('email')
                    newsletter_title = st.session_state.get('current_newsletter_title', 'Your Newsletter')
                    subject = f"📰 {newsletter_title} - {datetime.now().strftime('%B %d, %Y')}"
                    
                    with st.spinner("Sending email..."):
                        success = send_newsletter_email(
                            recipient_email=user_email,
                            subject=subject,
                            html_content=st.session_state.generated_newsletter
                        )
                        
                        if success:
                            st.success(f"✅ Newsletter sent to {user_email}!")
                            
                            review_time = stop_review_timer(newsletter_id, st.session_state.user_id, "sent")
                            if review_time and review_time <= 20:
                                st.info(f"⚡ Completed in {review_time} min - Under target!")
                            
                            if 'review_timer_started' in st.session_state:
                                del st.session_state.review_timer_started
                            
                            update_newsletter(
                                newsletter_id,
                                {"status": "sent", "sent_at": datetime.now(UTC).isoformat()},
                                st.session_state.user_id
                            )
                        else:
                            st.error("❌ Failed to send email. Check console for errors.")
        
        with col6:
            if st.button("🗑️ Clear", use_container_width=True, key="clear_btn"):
                st.session_state.generated_newsletter = None
                st.session_state.current_newsletter_id = None
                st.session_state.current_newsletter_title = None
                if 'review_timer_started' in st.session_state:
                    del st.session_state.review_timer_started
                st.rerun()
        
        with col7:
            if st.button("✏️ Edit", use_container_width=True):
                st.session_state.editing_mode = True
                st.rerun()

      
               
        # Edit interface
        if st.session_state.get('editing_mode', False):
            st.markdown("---")
            st.subheader("✏️ Edit Newsletter")
            
            # Create two columns for side-by-side comparison
            col_original, col_edited = st.columns(2)
            
            with col_original:
                st.markdown("**📄 Original Draft**")
                st.text_area(
                    "Original",
                    value=st.session_state.generated_newsletter,
                    height=400,
                    disabled=True,
                    key="original_preview",
                    label_visibility="collapsed"
                )
            
            with col_edited:
                st.markdown("**✏️ Your Edits**")
                edited = st.text_area(
                    "Edited",
                    value=st.session_state.generated_newsletter,
                    height=400,
                    key="edited_content",
                    label_visibility="collapsed"
                )
            
            # Show diff statistics in real-time
            if edited != st.session_state.generated_newsletter:
                metrics = calculate_edit_metrics(
                    st.session_state.generated_newsletter,
                    edited
                )
                
                st.markdown("---")
                st.markdown("### 📊 Edit Statistics")
                
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    st.metric("Original Words", metrics.get('original_word_count', 0))
                with col2:
                    st.metric("Edited Words", metrics.get('edited_word_count', 0))
                with col3:
                    change = metrics.get('edited_word_count', 0) - metrics.get('original_word_count', 0)
                    st.metric("Word Change", change, delta=f"{change:+d}")
                with col4:
                    severity = metrics.get('severity', 'unknown').title()
                    severity_color = {
                        'Minimal': '🟢',
                        'Minor': '🟡',
                        'Moderate': '🟠',
                        'Major': '🔴'
                    }
                    st.metric("Severity", f"{severity_color.get(severity, '⚪')} {severity}")
                
                # Show visual diff
                with st.expander("🔍 View Detailed Changes", expanded=False):
                    diff_html = generate_diff_html(
                        st.session_state.generated_newsletter,
                        edited
                    )
                    st.markdown(diff_html, unsafe_allow_html=True)
            
            col_e1, col_e2 = st.columns(2)
            
            with col_e1:
                if st.button("💾 Save Edits", use_container_width=True, type="primary"):
                    metrics = calculate_edit_metrics(
                        st.session_state.generated_newsletter,
                        edited
                    )
                    
                    save_edit_history(
                        newsletter_id,
                        st.session_state.user_id,
                        st.session_state.generated_newsletter,
                        edited
                    )
                    
                    st.session_state.generated_newsletter = edited
                    st.session_state.editing_mode = False
                    st.success(f"✅ Saved! Changed {metrics['edit_ratio']*100:.1f}%")
                    st.rerun()
            
            with col_e2:
                if st.button("❌ Cancel", use_container_width=True):
                    st.session_state.editing_mode = False
                    st.rerun()
        
        # Email configuration warning
        if not is_email_configured():
            st.warning("""
            ⚠️ **Email Sending Not Configured**
            
            To enable email delivery:
            1. Add `SENDER_EMAIL` and `SENDER_EMAIL_PASSWORD` to your `.env` file
            2. See **Settings** tab for detailed instructions
            """)
        
        # ✅ IMPROVED: Render newsletter preview with proper scrolling
        st.markdown("### 📧 Newsletter Preview")
        
        # Count articles in the HTML
        import re
        article_count = len(re.findall(r'<article style="margin-bottom:', st.session_state.generated_newsletter))
        st.info(f"📊 This newsletter contains {article_count} articles")
        
        # ✅ CRITICAL FIX: Increase height to show all articles
        # Each article is ~300-400px, so 7 articles = ~2500-3000px
        st.components.v1.html(
            st.session_state.generated_newsletter,
            height=3000,  # ✅ INCREASED from 1400 to 3000
            scrolling=True
        )


def render_sources_tab():
    st.subheader("📡 Manage Your Content Sources")
    
    # Initialize session state for form reset
    if 'source_form_key' not in st.session_state:
        st.session_state.source_form_key = 0
    
    # Popular RSS Feeds Dictionary
    POPULAR_RSS_FEEDS = {
        "Technology": {
            "TechCrunch": "https://techcrunch.com/feed/",
            "The Verge": "https://www.theverge.com/rss/index.xml",
            "Ars Technica": "https://feeds.arstechnica.com/arstechnica/index",
            "Wired": "https://www.wired.com/feed/rss",
            "MIT Technology Review": "https://www.technologyreview.com/feed/",
            "VentureBeat": "https://venturebeat.com/feed/",
            "Hacker News": "https://news.ycombinator.com/rss",
            "Engadget": "https://www.engadget.com/rss.xml",
            "ZDNet": "https://www.zdnet.com/news/rss.xml"
        },
        "AI & Machine Learning": {
            "OpenAI Blog": "https://openai.com/blog/rss.xml",
            "Google AI Blog": "https://ai.googleblog.com/feeds/posts/default",
            "AI News": "https://www.artificialintelligence-news.com/feed/",
            "VentureBeat AI": "https://venturebeat.com/category/ai/feed/",
            "Machine Learning Mastery": "https://machinelearningmastery.com/feed/"
        },
        "Business & Startups": {
            "Forbes Tech": "https://www.forbes.com/technology/feed/",
            "Business Insider Tech": "https://www.businessinsider.com/sai/rss",
            "Inc. Technology": "https://www.inc.com/technology/rss",
            "Entrepreneur Tech": "https://www.entrepreneur.com/topic/technology.rss",
            "Fast Company Tech": "https://www.fastcompany.com/technology/rss"
        },
        "Science": {
            "Science Daily": "https://www.sciencedaily.com/rss/all.xml",
            "Phys.org": "https://phys.org/rss-feed/",
            "Scientific American": "https://www.scientificamerican.com/feeds/rss/news/",
            "Live Science": "https://www.livescience.com/feeds/all"
        },
        "Design & Creativity": {
            "Smashing Magazine": "https://www.smashingmagazine.com/feed/",
            "A List Apart": "https://alistapart.com/main/feed/",
            "Creative Bloq": "https://www.creativebloq.com/feed"
        }
    }
    
    # Add new source
    st.markdown("#### Add New Source")
    
    # ⭐ Radio button OUTSIDE form - controls which form to show
    url_input_method = st.radio(
        "Choose how to add RSS feed:",
        ["Select from popular sources", "Enter custom URL"],
        horizontal=True,
        key=f"url_method_{st.session_state.source_form_key}"
    )
    
    # ============================================================================
    # FORM 1: Select from Popular Sources
    # ============================================================================
    if url_input_method == "Select from popular sources":
        with st.form(key=f"add_source_form_{st.session_state.source_form_key}"):
            st.markdown("**Popular RSS Feeds:**")
            
            # Create a flat list of all feeds for the selectbox
            feed_options = ["-- Select a feed --"]
            feed_map = {}
            
            for cat, feeds in POPULAR_RSS_FEEDS.items():
                for name, url in feeds.items():
                    display_name = f"{cat} → {name}"
                    feed_options.append(display_name)
                    feed_map[display_name] = {"name": name, "url": url, "category": cat}
            
            selected_feed = st.selectbox(
                "Choose a popular RSS feed:", 
                feed_options,
                key=f"feed_select_{st.session_state.source_form_key}"
            )
            
            # Show the URL that will be used
            source_url = ""
            auto_fill_name = ""
            auto_fill_category = "Technology"
            
            if selected_feed != "-- Select a feed --":
                feed_info = feed_map[selected_feed]
                source_url = feed_info["url"]
                auto_fill_name = feed_info["name"]
                auto_fill_category = feed_info["category"]
                
                st.info(f"📡 URL: `{source_url}`")
            
            col1, col2 = st.columns(2)
            
            with col1:
                source_name = st.text_input(
                    "Source Name", 
                    value=auto_fill_name,
                    placeholder="TechCrunch",
                    key=f"source_name_{st.session_state.source_form_key}"
                )
                source_type = st.selectbox(
                    "Source Type", 
                    ["RSS Feed", "Newsletter", "Blog"],
                    key=f"source_type_{st.session_state.source_form_key}"
                )
            
            with col2:
                category_options = ["Technology", "AI & Machine Learning", "Business & Startups", "Science", "Design & Creativity", "General", "Other"]
                
                default_category_index = category_options.index(auto_fill_category) if auto_fill_category in category_options else 0
                
                category = st.selectbox(
                    "Category", 
                    category_options,
                    index=default_category_index,
                    key=f"category_{st.session_state.source_form_key}"
                )
            
            col_btn1, col_btn2 = st.columns([3, 1])
            with col_btn1:
                submitted = st.form_submit_button("➕ Add Source", use_container_width=True)
            with col_btn2:
                reset = st.form_submit_button("🔄 Reset", use_container_width=True)
            
            if reset:
                st.session_state.source_form_key += 1
                st.rerun()
            
            if submitted:
                if not source_name:
                    st.error("Please provide a source name.")
                elif not source_url:
                    st.error("Please select a feed from the dropdown.")
                else:
                    # Validate RSS URL
                    with st.spinner("Validating RSS feed..."):
                        is_valid = validate_rss_url(source_url)
                    
                    if is_valid:
                        # Normalize type
                        type_mapping = {
                            "RSS Feed": "rss_feed",
                            "Newsletter": "newsletter",
                            "Blog": "blog"
                        }
                        
                        source_data = {
                            "user_id": st.session_state.user_id,
                            "name": source_name,
                            "url": source_url,
                            "type": type_mapping.get(source_type, "rss_feed"),
                            "category": category,
                            "active": True,
                            "created_at": datetime.now(UTC).isoformat()
                        }
                        
                        try:
                            if save_user_sources(source_data):
                                st.success(f"✅ Added {source_name} successfully!")
                                st.session_state.source_form_key += 1
                                st.rerun()
                            else:
                                st.error("❌ Failed to add source. The source may already exist.")
                        except Exception as e:
                            st.error(f"❌ Error adding source: {str(e)}")
                    else:
                        st.error("❌ Invalid RSS feed URL. Please check and try again.")
    
    # ============================================================================
    # FORM 2: Enter Custom URL (supports all source types)
    # ============================================================================
    else:  # "Enter custom URL"
        with st.form(key=f"add_custom_source_form_{st.session_state.source_form_key}"):
            col1, col2 = st.columns(2)
            
            with col1:
                source_name = st.text_input(
                    "Source Name", 
                    placeholder="TechCrunch",
                    key=f"custom_source_name_{st.session_state.source_form_key}"
                )
                
                # ⭐ All source types including Twitter and YouTube
                source_type = st.selectbox(
                    "Source Type", 
                    ["RSS Feed", "Newsletter", "Blog", "Twitter Handle", "Twitter Hashtag", "YouTube Channel"],
                    key=f"custom_source_type_{st.session_state.source_form_key}"
                )
            
            with col2:
                category = st.selectbox(
                    "Category", 
                    ["Technology", "AI & Machine Learning", "Business & Startups", "Science", "Design & Creativity", "General", "Other"],
                    key=f"custom_category_{st.session_state.source_form_key}"
                )
                
                # ⭐ Dynamic placeholder based on source type
                if source_type == "Twitter Handle":
                    placeholder = "elonmusk (without @)"
                    help_text = "Enter Twitter username without @"
                elif source_type == "Twitter Hashtag":
                    placeholder = "AI (without #)"
                    help_text = "Enter hashtag without #"
                elif source_type == "YouTube Channel":
                    placeholder = "@TechCrunch or channel URL"
                    help_text = "Enter channel handle (@username), channel ID, or full URL"
                else:
                    placeholder = "https://example.com/feed/"
                    help_text = "Enter RSS feed URL"
                
                source_url = st.text_input(
                    "URL / Handle / Hashtag", 
                    placeholder=placeholder,
                    help=help_text,
                    key=f"custom_url_{st.session_state.source_form_key}"
                )
            
            col_btn1, col_btn2 = st.columns([3, 1])
            with col_btn1:
                submitted = st.form_submit_button("➕ Add Source", use_container_width=True)
            with col_btn2:
                reset = st.form_submit_button("🔄 Reset", use_container_width=True)
            
            if reset:
                st.session_state.source_form_key += 1
                st.rerun()
            
            if submitted:
                if not source_name:
                    st.error("Please provide a source name.")
                elif not source_url:
                    st.error("Please enter a URL, handle, or hashtag.")
                else:
                    # ⭐ Different validation for different source types
                    is_valid = False
                    
                    if source_type == "Twitter Handle":
                        # Remove @ if present
                        source_url = source_url.lstrip('@')
                        is_valid = len(source_url) > 0 and source_url.replace('_', '').isalnum()
                        if not is_valid:
                            st.error("Invalid Twitter handle. Enter without @ (e.g., 'elonmusk')")
                    
                    elif source_type == "Twitter Hashtag":
                        # Remove # if present
                        source_url = source_url.lstrip('#')
                        is_valid = len(source_url) > 0
                        if not is_valid:
                            st.error("Invalid hashtag. Enter without # (e.g., 'AI')")
                    
                    elif source_type == "YouTube Channel":
                        # Accept channel ID, @handle, or URL - NO validation needed
                        # Just check it's not empty
                        source_url = source_url.strip()
                        is_valid = len(source_url) > 0
                        
                        if not is_valid:
                            st.error("Invalid YouTube channel. Enter @handle, channel ID, or URL")
                        else:
                            # Clean up URL if needed
                            # Keep as-is, the scraper will handle it
                            pass
                    
                    else:
                        # Validate RSS URL
                        with st.spinner("Validating RSS feed..."):
                            is_valid = validate_rss_url(source_url)
                        
                        if not is_valid:
                            st.error("❌ Invalid RSS feed URL. The feed could not be validated.")
                    
                    if is_valid:
                        # Normalize type to match database constraint
                        type_mapping = {
                            "RSS Feed": "rss_feed",
                            "Newsletter": "newsletter",
                            "Blog": "blog",
                            "Twitter Handle": "twitter_handle",
                            "Twitter Hashtag": "twitter_hashtag",
                            "YouTube Channel": "youtube_channel"
                        }
                        
                        source_data = {
                            "user_id": st.session_state.user_id,
                            "name": source_name,
                            "url": source_url,
                            "type": type_mapping.get(source_type, "rss_feed"),
                            "category": category,
                            "active": True,
                            "created_at": datetime.now(UTC).isoformat()
                        }
                        
                        try:
                            result = save_user_sources(source_data)
                            if result:
                                st.success(f"✅ Added {source_name} successfully!")
                                st.session_state.source_form_key += 1
                                st.rerun()
                            else:
                                st.error("❌ Failed to add source. The source may already exist or there's a database error.")
                                st.info(f"Debug: Trying to save - Name: {source_name}, URL: {source_url}, Type: {source_data['type']}")
                        except Exception as e:
                            st.error(f"❌ Error adding source: {str(e)}")
                            st.code(str(e), language="text")
                            import traceback
                            st.code(traceback.format_exc(), language="text")
    
    st.markdown("---")
    st.markdown("💡 **Tip:** Can't find a feed? Try adding `/feed/` or `/rss.xml` to the end of the website URL!")
    
    st.markdown("---")
    
    # Display existing sources
    st.markdown("#### Your Sources")
    user_sources = get_user_sources(st.session_state.user_id)
    
    if not user_sources:
        st.info("No sources configured yet. Add your first source above to get started!")
        return
    
    for i, source in enumerate(user_sources):
        with st.expander(f"📰 {source.get('name', 'Unnamed Source')} ({source.get('category', 'N/A')})"):
            col1, col2, col3 = st.columns([2, 2, 1])
            
            with col1:
                st.markdown(f"**Type:** {source.get('type', 'N/A').replace('_', ' ').title()}")
                
                # Display differently based on type
                source_type = source.get('type', 'rss_feed')
                url = source.get('url', 'N/A')
                
                if source_type == 'twitter_handle':
                    st.markdown(f"**Handle:** [@{url}](https://twitter.com/{url})")
                elif source_type == 'twitter_hashtag':
                    st.markdown(f"**Hashtag:** [#{url}](https://twitter.com/hashtag/{url})")
                elif source_type == 'youtube_channel':
                    st.markdown(f"**Channel:** {url}")
                else:
                    st.markdown(f"**URL:** [{url}]({url})")
            
            with col2:
                st.markdown(f"**Category:** {source.get('category', 'N/A')}")
                st.markdown(f"**Status:** {'✅ Active' if source.get('active') else '❌ Inactive'}")
            
            with col3:
                if st.button("🗑️ Remove", key=f"remove_{i}"):
                    # Confirm deletion
                    if f'confirm_remove_{i}' not in st.session_state:
                        st.session_state[f'confirm_remove_{i}'] = True
                        st.warning("⚠️ Click Remove again to confirm deletion")
                    else:
                        # Actually delete the source
                        from models import delete_user_source
                        
                        source_id = source.get('id')
                        if delete_user_source(source_id, st.session_state.user_id):
                            st.success(f"✅ Removed {source.get('name')}!")
                            del st.session_state[f'confirm_remove_{i}']
                            st.rerun()
                        else:
                            st.error("❌ Failed to remove source")
                            
def render_settings_tab():
    st.subheader("⚙️ Settings")
    
    # User information
    st.markdown("#### Account Information")
    col1, col2 = st.columns(2)
    
    username = st.session_state.user.get('username') or st.session_state.user.get('display_name') or st.session_state.user.get('email', 'User').split('@')[0]
    
    with col1:
        st.markdown(f"**Username:** @{username}")
        st.markdown(f"**Email:** {st.session_state.user.get('email', 'N/A')}")
    
    with col2:
        st.markdown(f"**User ID:** {st.session_state.user.get('id', 'N/A')[:8]}...")
        st.markdown("**Account Type:** Free")
    st.markdown("---")
    
    # Email Configuration Section
    st.markdown("#### 📧 Email Configuration")
        
    if is_email_configured():
        sender_email = os.getenv("SENDER_EMAIL")
        st.success(f"✅ Email configured: {sender_email}")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("📧 Send Test Email", use_container_width=True):
                test_email = st.session_state.user.get('email')
                with st.spinner("Sending test email..."):
                    if send_test_email(test_email):
                        st.success(f"✅ Test email sent to {test_email}!")
                        st.balloons()
                    else:
                        st.error("❌ Test failed. Check your configuration.")
        
        with col2:
            st.info("✅ Email service is ready!")
    else:
        st.error("⚠️ Email not configured")
        
        with st.expander("📖 How to Configure Email (Gmail)", expanded=True):
            st.markdown("""
            ### Step 1: Enable 2-Factor Authentication
            1. Go to [Google Account Security](https://myaccount.google.com/security)
            2. Turn on **2-Step Verification**
            
            ### Step 2: Generate App Password
            1. Go to [App Passwords](https://myaccount.google.com/apppasswords)
            2. Select **Mail** and **Other (Custom name)**
            3. Name it "CreatorPulse"
            4. Click **Generate**
            5. Copy the 16-character password (no spaces)
            
            ### Step 3: Update .env File
            Add these lines to your `.env` file:
            ```
            SENDER_EMAIL=your-email@gmail.com
            SENDER_EMAIL_PASSWORD=abcd efgh ijkl mnop
            ```
            
            ### Step 4: Restart the App
            Stop the app (Ctrl+C) and run `streamlit run app.py` again.
            
            ---
            
            **Alternative Services:**
            - SendGrid (free tier: 100 emails/day)
            - AWS SES (cheap and reliable)
            - Mailgun (developer-friendly)
            """)
    
    st.markdown("---")
    
    # Preferences
    st.markdown("#### Newsletter Preferences")
    with st.form("preferences_form"):
        default_tone = st.selectbox("Default Writing Tone", ["Professional", "Casual", "Creative", "Technical"])
        default_length = st.selectbox("Default Newsletter Length", ["Short (5-8 articles)", "Medium (8-12 articles)", "Long (12-15 articles)"])
        include_trends_default = st.checkbox("Include trends section by default", value=True)
        
        if st.form_submit_button("💾 Save Preferences"):
            st.success("Preferences saved successfully!")
    
    st.markdown("---")
    
    # Data management
    st.markdown("#### Data Management")
    st.warning("⚠️ Danger Zone")
    if st.button("🗑️ Delete All Newsletters", type="secondary"):
        st.error("This action cannot be undone. Contact support to proceed.")

    st.markdown("#### 📱 Telegram Bot (FREE Delivery)")
    
    if is_telegram_configured():
        st.success("✅ Telegram Bot is configured!")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**Get Your Chat ID:**")
            if st.button("🔍 Get My Chat ID", use_container_width=True):
                chat_id = get_telegram_chat_id()
                st.code(chat_id, language=None)
                st.caption("📋 Copy this and use in Scheduler tab")
        
        with col2:
            test_chat_id = st.text_input("Test Chat ID", placeholder="123456789")
            if st.button("📱 Send Test", use_container_width=True):
                if test_chat_id:
                    if send_test_telegram(test_chat_id):
                        st.success("✅ Test sent!")
                    else:
                        st.error("❌ Failed")
    else:
        st.warning("⚠️ Telegram Bot not configured")
        with st.expander("📖 Setup Guide", expanded=True):
            st.markdown("""
            ### Quick Setup (2 minutes):
            
            1. **Open Telegram** → Search `@BotFather`
            2. **Send** `/newbot`
            3. **Name it**: "CreatorPulse Bot"
            4. **Username**: "yourname_creatorpulse_bot"
            5. **Copy the token** (long text)
            6. **Add to `.env`**:
```
               TELEGRAM_BOT_TOKEN=your_token_here
```
            7. **Restart app**
            8. **Find your bot** on Telegram → Send `/start`
            9. **Get Chat ID** from button above
            """)


def render_social_media_tab():
    """Social Media Post Generator Tab"""
    st.subheader("📱 Social Media Post Generator")
    
    st.markdown("""
    Transform your newsletter into engaging social media content for Twitter/X and LinkedIn.
    Perfect for maximizing your content's reach across platforms.
    """)
    
    # Check if there's a generated newsletter to work with
    has_newsletter = st.session_state.get('generated_newsletter') is not None
    
    if not has_newsletter:
        # Show saved newsletters to choose from
        newsletters = fetch_newsletters(st.session_state.user_id)
        
        if not newsletters:
            st.info("👋 Create a newsletter first to generate social media posts!")
            st.markdown("Go to the **Create Newsletter** tab to get started.")
            return
        
        st.markdown("### 📰 Select a Newsletter")
        
        # Newsletter selector
        newsletter_options = {
            f"{n.get('title', 'Untitled')} ({n.get('created_at', 'N/A')[:10]})": n 
            for n in newsletters[:10]
        }
        
        selected_title = st.selectbox(
            "Choose newsletter to convert:",
            options=list(newsletter_options.keys())
        )
        
        selected_newsletter = newsletter_options[selected_title]
        newsletter_content = selected_newsletter.get('content', '')
        newsletter_id = selected_newsletter.get('id')
        
        # Try to get articles and trends from the newsletter
        try:
            trends = json.loads(selected_newsletter.get('trends', '[]'))
        except:
            trends = []
        
        # Get articles from user sources
        user_sources = get_user_sources(st.session_state.user_id)
        rss_feeds = [s['url'] for s in user_sources if s.get('type') in ['rss_feed', 'rss']]
        
        if rss_feeds:
            articles = parse_multiple_feeds(rss_feeds, max_articles_per_feed=3)
        else:
            articles = []
    else:
        # Use current generated newsletter
        newsletter_content = st.session_state.generated_newsletter
        newsletter_id = st.session_state.get('current_newsletter_id')
        
        # Get stored data
        articles = st.session_state.get('current_articles', [])
        trends = st.session_state.get('current_trends', [])
    
    st.markdown("---")
    
    # Platform selection and generation
    col1, col2 = st.columns(2)
    
    with col1:
        platform = st.selectbox(
            "📱 Select Platform",
            ["twitter", "linkedin"],
            format_func=lambda x: "Twitter/X" if x == "twitter" else "LinkedIn"
        )
    
    with col2:
        tone = st.selectbox(
            "🎨 Tone",
            ["Professional", "Casual", "Enthusiastic", "Analytical"]
        )
    
    # Generate button
    if st.button("🚀 Generate Social Posts", use_container_width=True, type="primary"):
        if not GROQ_API_KEY:
            st.error("❌ Groq API key not configured")
            return
        
        with st.spinner(f"Generating {platform} posts..."):
            result = generate_social_posts(
                newsletter_content=newsletter_content,
                articles=articles if articles else [],
                trends=trends if trends else [],
                platform=platform,
                api_key=GROQ_API_KEY,
                tone=tone
            )
            
            if result.get("error"):
                st.error(f"❌ Error: {result['error']}")
            else:
                # Save to session state
                st.session_state.current_social_posts = result
                
                # Save to database
                save_social_post(result, st.session_state.user_id, newsletter_id)
                
                st.success("✅ Social posts generated!")
                st.rerun()
    
    # Display generated posts
    if st.session_state.get('current_social_posts'):
        posts_data = st.session_state.current_social_posts
        platform_name = "Twitter/X" if posts_data['platform'] == 'twitter' else "LinkedIn"
        
        st.markdown("---")
        st.markdown(f"### ✨ Generated {platform_name} Posts")
        
        posts = posts_data.get('posts', [])
        
        if posts_data['platform'] == 'twitter':
            # Display Twitter thread
            st.markdown("**🧵 Twitter Thread:**")
            
            for i, tweet in enumerate(posts, 1):
                char_count = len(tweet)
                color = "🟢" if char_count <= 280 else "🔴"
                
                st.markdown(f"**Tweet {i}/{len(posts)}** {color} ({char_count}/280 chars)")
                st.text_area(
                    f"tweet_{i}",
                    value=tweet,
                    height=100,
                    key=f"tweet_display_{i}",
                    label_visibility="collapsed"
                )
                
                col_a, col_b = st.columns([3, 1])
                with col_a:
                    if st.button(f"📋 Copy Tweet {i}", key=f"copy_tweet_{i}", use_container_width=True):
                        st.code(tweet, language=None)
                        st.caption("👆 Select and copy the text above")
        
        else:
            # Display LinkedIn post
            st.markdown("**💼 LinkedIn Post:**")
            
            post = posts[0]
            char_count = len(post)
            
            st.info(f"📊 {char_count} characters (ideal: 1200-1500)")
            
            st.text_area(
                "linkedin_post",
                value=post,
                height=400,
                key="linkedin_display",
                label_visibility="collapsed"
            )
            
            # Show hashtags
            hashtags = posts_data.get('hashtags', [])
            if hashtags:
                st.markdown(f"**Hashtags:** {' '.join(hashtags)}")
        
        # Action buttons
        st.markdown("---")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("📋 Copy All", use_container_width=True):
                full_text = posts_data.get('full_text', '')
                st.code(full_text, language=None)
                st.caption("👆 Select and copy the text above")
        
        with col2:
            # Download as text file
            full_text = posts_data.get('full_text', '')
            filename = f"{posts_data['platform']}_post_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
            
            st.download_button(
                label="💾 Download",
                data=full_text,
                file_name=filename,
                mime="text/plain",
                use_container_width=True
            )
        
        with col3:
            if st.button("🔄 Clear", use_container_width=True):
                del st.session_state.current_social_posts
                st.rerun()
        
        # Optional: Auto-publish (if API configured)
        st.markdown("---")
        st.markdown("### 🚀 Auto-Publish (Optional)")
        
        with st.expander("⚙️ Configure API Credentials"):
            st.warning("⚠️ Auto-publishing requires API credentials. For now, copy-paste manually.")
            
            if posts_data['platform'] == 'twitter':
                st.markdown("""
                **Twitter API Setup:**
                1. Go to [Twitter Developer Portal](https://developer.twitter.com/)
                2. Create an app and get API keys
                3. Add to `.env`:
                   ```
                   TWITTER_CONSUMER_KEY=your_key
                   TWITTER_CONSUMER_SECRET=your_secret
                   TWITTER_ACCESS_TOKEN=your_token
                   TWITTER_ACCESS_TOKEN_SECRET=your_token_secret
                   ```
                """)
            else:
                st.markdown("""
                **LinkedIn API Setup:**
                1. Go to [LinkedIn Developers](https://www.linkedin.com/developers/)
                2. Create an app and get credentials
                3. Add to `.env`:
                   ```
                   LINKEDIN_ACCESS_TOKEN=your_token
                   LINKEDIN_PERSON_URN=your_urn
                   ```
                """)
    
    # Show saved posts history
    st.markdown("---")
    st.markdown("### 📚 Saved Posts")
    
    saved_posts = get_user_social_posts(st.session_state.user_id)
    
    if saved_posts:
        for i, post in enumerate(saved_posts[:5]):
            platform_emoji = "🐦" if post['platform'] == 'twitter' else "💼"
            platform_name = "Twitter" if post['platform'] == 'twitter' else "LinkedIn"
            
            with st.expander(f"{platform_emoji} {platform_name} - {post['created_at'][:10]}"):
                st.text_area(
                    f"saved_post_{i}",
                    value=post['content'],
                    height=200,
                    key=f"saved_display_{i}",
                    label_visibility="collapsed"
                )
    else:
        st.info("No saved posts yet. Generate your first one above!")


def render_style_trainer_tab():
    """Writing Style Trainer Tab"""
    st.subheader("✏️ Train Your Writing Style")
    
    st.markdown("""
    Upload or paste at least 3 of your past newsletters to train the AI to match your writing voice.
    The more samples you provide (recommended: 5-10), the better the AI will capture your style.
    """)
    
    # Check if user already has a style profile
    existing_profile = get_style_profile(st.session_state.user_id)
    
    if existing_profile:
        st.success("✅ You have an active writing style profile!")
        
        profile = existing_profile['style_profile']
        st.markdown("### Your Style Profile")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Samples Analyzed", profile.get('sample_count', 0))
        with col2:
            tone = profile.get('tone_indicators', {}).get('dominant_tone', 'N/A')
            st.metric("Dominant Tone", tone.title())
        with col3:
            avg_length = profile.get('avg_sentence_length', 0)
            st.metric("Avg Sentence Length", f"{avg_length} words")
        
        # Show custom prompt
        with st.expander("🔍 View AI Writing Instructions"):
            st.code(existing_profile['custom_prompt'], language='text')
        
        st.markdown("---")
    
    # Upload new samples
    st.markdown("### " + ("Update" if existing_profile else "Create") + " Style Profile")
    
    input_method = st.radio(
        "How would you like to provide samples?",
        ["Paste text", "Upload file"],
        horizontal=True,
        help="Choose 'Paste text' for easier input of multiple newsletters"
    )
    
    newsletters = []
    
    if input_method == "Paste text":
        st.markdown("**Paste your past newsletters below (one per box):**")
        st.caption("💡 Tip: Paste 3-10 newsletters for best results")
        
        num_samples = st.number_input("Number of samples", min_value=3, max_value=10, value=3)
        
        for i in range(num_samples):
            newsletter = st.text_area(
                f"Newsletter #{i+1}",
                height=150,
                key=f"newsletter_{i}",
                placeholder="Paste your newsletter content here..."
            )
            if newsletter.strip():
                newsletters.append(newsletter)
    
    else:
        st.markdown("**Upload a single text file containing all your newsletters:**")
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.info("""
            📝 **File Format Required:**
            
            Your file must contain multiple newsletters separated by `---` (three dashes).
            """)
        
        with col2:
            # Download template button
            template_content = """Newsletter 1 Title
This is my first newsletter content...
Add your actual newsletter text here.
---
Newsletter 2 Title
This is my second newsletter content...
Add more content here.
---
Newsletter 3 Title
This is my third newsletter content...
Keep adding more newsletters.
"""
            st.download_button(
                label="📥 Download Template",
                data=template_content,
                file_name="newsletter_template.txt",
                mime="text/plain",
                use_container_width=True,
                help="Download a template file with the correct format"
            )
        
        st.code("""Example:
Newsletter 1 content here...
---
Newsletter 2 content here...
---
Newsletter 3 content here...""", language="text")
        
        uploaded_file = st.file_uploader(
            "Upload ONE file with multiple newsletters (TXT or MD)",
            type=['txt', 'md'],
            help="File must contain 3+ newsletters separated by ---"
        )
        
        if uploaded_file:
            content = uploaded_file.read().decode('utf-8')
            newsletters = [n.strip() for n in content.split('---') if n.strip()]
            
            if len(newsletters) > 0:
                st.success(f"✅ Found {len(newsletters)} newsletter(s) in the file")
                
                if len(newsletters) < 3:
                    st.warning(f"⚠️ You need {3 - len(newsletters)} more newsletter(s). Add them separated by ---")
                else:
                    st.success(f"🎉 Perfect! You have {len(newsletters)} newsletters - ready to analyze!")
            else:
                st.error("❌ No newsletters found. Make sure to separate them with ---")
    
    if st.button("🎯 Analyze & Save Style Profile", disabled=len(newsletters) < 3, use_container_width=True):
        if len(newsletters) < 3:
            st.error("Please provide at least 3 newsletter samples")
        else:
            with st.spinner("Analyzing your writing style..."):
                style_profile = analyze_writing_style(newsletters)
                
                if style_profile.get('status') == 'insufficient_data':
                    st.error(style_profile['message'])
                else:
                    # Save profile
                    if save_style_profile(st.session_state.user_id, style_profile):
                        st.success("✅ Style profile saved successfully!")
                        st.balloons()
                        st.rerun()
                    else:
                        st.error("Failed to save style profile. Please try again.")
    
    # Show current count
    if len(newsletters) > 0:
        st.info(f"📝 Found {len(newsletters)} newsletter(s). {max(0, 3 - len(newsletters))} more needed.")


def render_analytics_tab():
    """Analytics & Performance Tab"""
    st.subheader("📊 Analytics & Performance")
    
    # Time period selector
    period = st.selectbox("Time Period", ["Last 7 days", "Last 30 days", "Last 90 days"])
    days = {"Last 7 days": 7, "Last 30 days": 30, "Last 90 days": 90}[period]
    
    # Get feedback stats
    feedback_stats = get_feedback_stats(st.session_state.user_id, days)
    
    # Get engagement analytics
    engagement_stats = get_engagement_analytics(st.session_state.user_id, days)
    
    # Display KPIs
    st.markdown("### 🎯 Key Performance Indicators")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        acceptance = feedback_stats.get('acceptance_rate', 0)
        target = 70
        delta = f"{acceptance - target:+.1f}%" if acceptance > 0 else None
        st.metric(
            "Draft Acceptance Rate",
            f"{acceptance}%",
            delta=delta,
            delta_color="normal"
        )
        st.caption(f"Target: ≥{target}%")
    
    with col2:
        edit_ratio = feedback_stats.get('avg_edit_ratio', 0)
        st.metric(
            "Avg Edit Ratio",
            f"{edit_ratio*100:.0f}%",
            help="Lower is better - indicates drafts needed less editing"
        )
        st.caption("Target: <30%")
    
    with col3:
        open_rate = engagement_stats.get('avg_open_rate', 0)
        st.metric(
            "Avg Open Rate",
            f"{open_rate}%"
        )
        st.caption("Industry avg: 20-25%")
    
    with col4:
        click_rate = engagement_stats.get('avg_click_rate', 0)
        st.metric(
            "Avg Click Rate",
            f"{click_rate}%"
        )
        st.caption("Industry avg: 2-5%")
    
    st.markdown("---")
    
    # Feedback breakdown
    st.markdown("### 👍 Feedback Summary")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Total Newsletters", feedback_stats.get('total_newsletters', 0))
    with col2:
        st.metric("👍 Thumbs Up", feedback_stats.get('thumbs_up', 0))
    with col3:
        st.metric("👎 Thumbs Down", feedback_stats.get('thumbs_down', 0))
    
    # Engagement trend
    st.markdown("### 📈 Engagement Trend")
    trend = engagement_stats.get('trend', 'no_data')
    
    trend_icons = {
        'improving': '📈',
        'stable': '➡️',
        'declining': '📉',
        'no_data': '❓'
    }
    
    trend_messages = {
        'improving': 'Great! Your engagement is improving!',
        'stable': 'Your engagement is stable.',
        'declining': 'Your engagement is declining. Consider reviewing your content strategy.',
        'no_data': 'Not enough data to determine trend.'
    }
    
    st.info(f"{trend_icons[trend]} {trend_messages[trend]}")
    
    # Recommendations
    st.markdown("### 💡 Recommendations")
    
    recommendations = []
    
    if acceptance < 70:
        recommendations.append("🎯 Your acceptance rate is below target. Consider retraining your writing style profile.")
    
    if edit_ratio > 0.3:
        recommendations.append("✏️ You're making significant edits. Review the AI-generated drafts and provide feedback.")
    
    if open_rate > 0 and open_rate < 20:
        recommendations.append("📧 Your open rates are below average. Consider improving subject lines and send times.")
    
    if not recommendations:
        recommendations.append("🌟 Great job! All metrics are on track!")
    
    for rec in recommendations:
        st.markdown(f"- {rec}")

    st.markdown("---")
    st.markdown("### ⏱️ Review Time (PDF KPI)")
        
    time_stats = get_average_review_time(st.session_state.user_id, days)
        
    col1, col2 = st.columns(2)

    with col1:
        avg = time_stats.get('avg_time_minutes', 0)
        st.metric("Avg Review Time", f"{avg} min", "Target: ≤20 min")
        
    with col2:
        success = time_stats.get('success_rate', 0)
        st.metric("Under Target", f"{success}%")
        
    st.markdown("---")
    st.markdown("### ✏️ Edit Patterns")
    
    edit_stats = get_edit_patterns(st.session_state.user_id, days)
    
    st.metric("Avg Edit Ratio", f"{edit_stats.get('avg_edit_ratio', 0)*100:.1f}%", "Target: <30%")


def render_scheduler_tab():
    """Email Scheduler Tab with Dynamic Form Fields"""
    st.subheader("⏰ Schedule Newsletter Delivery")
    
    # Show scheduler status
    if st.session_state.get('scheduler_thread_started', False):
        st.success("✅ Background scheduler is active - checking every minute")
    else:
        st.warning("⚠️ Scheduler not started yet - refresh if you just logged in")
    
    st.markdown("""
    Set up automatic morning delivery of your AI-generated newsletter drafts.
    Receive them at your preferred time every day.
    """)
    
    # Get existing schedule
    supabase = get_supabase_client()
    
    try:
        response = supabase.table("scheduled_deliveries").select("*").eq("user_id", st.session_state.user_id).execute()
        existing_schedule = response.data[0] if response.data and len(response.data) > 0 else None
    except Exception as e:
        print(f"Error fetching schedule: {e}")
        existing_schedule = None
    
    # ============================================================================
    # DYNAMIC FORM - Shows/hides fields based on selection
    # ============================================================================
    
    # Step 1: Delivery method selection OUTSIDE the form
    st.markdown("### 📮 Delivery Configuration")
    
    delivery_method = st.selectbox(
        "Delivery Method",
        ["Email", "Telegram", "Both"],
        index=["Email", "Telegram", "Both"].index(existing_schedule.get('delivery_method', 'email').title()) if existing_schedule else 0,
        help="💡 Telegram is FREE and instant!",
        key="delivery_method_selector"
    )
    
    st.markdown("---")
    
    # Step 2: Form with conditional fields
    with st.form("scheduler_form"):
        st.markdown("### ⏰ Schedule Settings")
        
        col1, col2 = st.columns(2)
        
        with col1:
            delivery_time = st.time_input(
                "Delivery Time",
                value=datetime.strptime(existing_schedule.get('schedule_time', '08:00:00'), '%H:%M:%S').time() if existing_schedule else datetime.strptime('08:00:00', '%H:%M:%S').time()
            )
        
        with col2:
            timezone = st.selectbox(
                "Timezone",
                ["UTC", "America/New_York", "America/Los_Angeles", "Europe/London", "Asia/Kolkata"],
                index=["UTC", "America/New_York", "America/Los_Angeles", "Europe/London", "Asia/Kolkata"].index(existing_schedule.get('timezone', 'UTC')) if existing_schedule else 4
            )
        
        is_active = st.checkbox(
            "Enable Scheduled Delivery",
            value=existing_schedule.get('is_active', True) if existing_schedule else True
        )
        
        st.markdown("---")
        st.markdown("### 📬 Delivery Details")
        
        # ✅ CONDITIONAL FIELDS - Show based on delivery_method selection
        
        # Show Email field if Email or Both
        if delivery_method in ["Email", "Both"]:
            st.markdown("#### 📧 Email Configuration")
            email = st.text_input(
                "Delivery Email",
                value=st.session_state.user.get('email', ''),
                disabled=True,
                help="Newsletters will be sent to your registered email"
            )
            
            if not is_email_configured():
                st.warning("⚠️ Email not configured. Go to Settings tab to set up email delivery.")
        
        # Show Telegram field if Telegram or Both
        if delivery_method in ["Telegram", "Both"]:
            st.markdown("#### 📱 Telegram Configuration")
            
            telegram_chat_id = st.text_input(
                "Telegram Chat ID",
                value=existing_schedule.get('telegram_chat_id', '') if existing_schedule else '',
                placeholder="5263562291",
                help="Get your Chat ID from Settings → Telegram Configuration → Get My Chat ID"
            )
            
            if not is_telegram_configured():
                st.error("❌ Telegram Bot not configured. Go to Settings tab first.")
                st.markdown("""
                **Quick Setup:**
                1. Go to Settings tab
                2. Follow Telegram Bot setup guide
                3. Get your Chat ID
                4. Come back here
                """)
            else:
                st.success("✅ Telegram Bot is configured!")
                
                # Helper link
                col_help1, col_help2 = st.columns(2)
                with col_help1:
                    st.caption("Don't have your Chat ID?")
                with col_help2:
                    st.markdown("[Go to Settings →](#settings)", unsafe_allow_html=True)
        
        st.markdown("---")
        
        # Submit button
        submitted = st.form_submit_button("💾 Save Schedule", use_container_width=True, type="primary")
        
        if submitted:
            # Validation
            errors = []
            
            # Validate Telegram if selected
            if delivery_method in ["Telegram", "Both"]:
                if not telegram_chat_id:
                    errors.append("❌ Please enter your Telegram Chat ID")
                elif not telegram_chat_id.strip().lstrip('-').isdigit():
                    errors.append("❌ Chat ID should contain only numbers (can start with -)")
                
                if not is_telegram_configured():
                    errors.append("❌ Telegram Bot not configured in Settings")
            
            # Validate Email if selected
            if delivery_method in ["Email", "Both"]:
                if not is_email_configured():
                    errors.append("❌ Email not configured in Settings")
            
            # Show all errors
            if errors:
                for error in errors:
                    st.error(error)
                st.info("💡 Go to Settings tab to complete the configuration")
                return
            
            # Save schedule
            schedule_data = {
                "user_id": st.session_state.user_id,
                "schedule_time": delivery_time.strftime('%H:%M:%S'),
                "timezone": timezone,
                "delivery_method": delivery_method.lower(),
                "is_active": is_active
            }
            
            # Add Telegram chat_id if applicable
            if delivery_method in ["Telegram", "Both"]:
                schedule_data["telegram_chat_id"] = telegram_chat_id.strip()
            
            try:
                supabase.table("scheduled_deliveries").upsert(
                    schedule_data,
                    on_conflict="user_id"
                ).execute()
                
                st.success("✅ Delivery schedule saved successfully!")
                st.balloons()
                
                # Show summary
                st.info(f"""
                **📅 Schedule Summary:**
                - Time: {delivery_time.strftime('%I:%M %p')} ({timezone})
                - Method: {delivery_method}
                - Status: {'🟢 Active' if is_active else '🔴 Inactive'}
                """)
                
            except Exception as e:
                st.error(f"Failed to save schedule: {str(e)}")
                st.code(str(e), language="text")
    
    # Show current schedule below form
    if existing_schedule:
        st.markdown("---")
        st.markdown("### 📅 Current Schedule")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            time_str = existing_schedule.get('schedule_time', 'N/A')
            tz_str = existing_schedule.get('timezone', 'UTC')
            st.info(f"**⏰ Time**\n{time_str}\n{tz_str}")
        
        with col2:
            method = existing_schedule.get('delivery_method', 'email').title()
            method_emoji = {
                'Email': '📧',
                'Telegram': '📱',
                'Both': '📧📱'
            }
            st.info(f"**{method_emoji.get(method, '📮')} Method**\n{method}")
        
        with col3:
            status = "🟢 Active" if existing_schedule.get('is_active') else "🔴 Inactive"
            st.info(f"**Status**\n{status}")
        
        if existing_schedule.get('last_delivered_at'):
            st.caption(f"🕒 Last delivered: {existing_schedule.get('last_delivered_at')}")
        else:
            st.caption("📭 No deliveries yet")

# Main application logic
def main():
    start_scheduler()
    
    if not st.session_state.user:
        render_auth_section()
    else:
        render_dashboard()

if __name__ == "__main__":
    main()