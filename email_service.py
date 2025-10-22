"""
Simple Email Service for CreatorPulse
Sends newsletters via Gmail SMTP
"""
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
from dotenv import load_dotenv

# Force reload environment variables
load_dotenv(override=True)

# Debug: Print configuration status on module load
_sender = os.getenv("SENDER_EMAIL")
_password = os.getenv("SENDER_EMAIL_PASSWORD")
print("=" * 60)
print("📧 EMAIL SERVICE INITIALIZATION")
print(f"SENDER_EMAIL: {_sender if _sender else '❌ NOT SET'}")
print(f"SENDER_EMAIL_PASSWORD: {'✅ SET' if _password else '❌ NOT SET'}")
if _password:
    print(f"Password length: {len(_password)} chars")
    print(f"Password first 4 chars: {_password[:4]}...")
    print(f"Has spaces: {' ' in _password}")
print(f"Current working directory: {os.getcwd()}")
print(f".env file exists: {os.path.exists('.env')}")
if os.path.exists('.env'):
    with open('.env', 'r') as f:
        lines = f.readlines()
        print(f".env file has {len(lines)} lines")
        for i, line in enumerate(lines, 1):
            if 'SENDER' in line and not line.strip().startswith('#'):
                # Show line but mask password
                if 'PASSWORD' in line:
                    print(f"Line {i}: SENDER_EMAIL_PASSWORD=***masked***")
                else:
                    print(f"Line {i}: {line.strip()}")
print("=" * 60)


def send_newsletter_email(recipient_email: str, subject: str, html_content: str) -> bool:
    """
    Send newsletter via Gmail SMTP
    
    Args:
        recipient_email: Email address to send to
        subject: Email subject line
        html_content: HTML content of the newsletter
    
    Returns:
        bool: True if sent successfully, False otherwise
    """
    try:
        # Force reload to ensure we have latest values
        load_dotenv(override=True)
        
        # Get credentials from environment
        sender_email = os.getenv("SENDER_EMAIL")
        sender_password = os.getenv("SENDER_EMAIL_PASSWORD")
        
        print(f"\n🔍 send_newsletter_email() check:")
        print(f"sender_email: {sender_email if sender_email else '❌ NOT SET'}")
        print(f"sender_password: {'✅ SET' if sender_password else '❌ NOT SET'}")
        
        if not sender_email or not sender_password:
            print("❌ Email credentials not configured in .env file")
            print("Add SENDER_EMAIL and SENDER_EMAIL_PASSWORD to your .env file")
            return False
        
        # Remove any whitespace from password
        sender_password = sender_password.strip().replace(' ', '')
        
        # Create message
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = f"CreatorPulse <{sender_email}>"
        msg['To'] = recipient_email
        
        # Attach HTML content
        html_part = MIMEText(html_content, 'html')
        msg.attach(html_part)
        
        # Send via Gmail SMTP
        print(f"📧 Attempting to send email to {recipient_email}...")
        with smtplib.SMTP('smtp.gmail.com', 587) as server:
            server.starttls()
            print(f"🔐 Logging in with {sender_email}...")
            server.login(sender_email, sender_password)
            server.send_message(msg)
        
        print(f"✅ Email sent successfully to {recipient_email}")
        return True
        
    except smtplib.SMTPAuthenticationError as e:
        print(f"❌ Authentication failed: {e}")
        print("Make sure you're using an App Password, not your regular Gmail password.")
        print("App Password should be 16 characters with NO SPACES")
        return False
    except Exception as e:
        print(f"❌ Error sending email: {e}")
        import traceback
        traceback.print_exc()
        return False


def send_test_email(recipient_email: str) -> bool:
    """
    Send a test email to verify configuration
    
    Args:
        recipient_email: Email address to send test to
    
    Returns:
        bool: True if sent successfully
    """
    test_html = """
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
    </head>
    <body style="margin: 0; padding: 0; font-family: Arial, sans-serif;">
        <div style="max-width: 600px; margin: 0 auto; padding: 40px 20px;">
            <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 30px; border-radius: 12px; text-align: center;">
                <h1 style="color: white; margin: 0; font-size: 28px;">✅ Email Test Successful!</h1>
            </div>
            
            <div style="background: #f8fafc; padding: 30px; margin-top: 20px; border-radius: 12px;">
                <p style="font-size: 16px; color: #334155; margin: 0 0 15px 0;">
                    Great news! Your CreatorPulse email configuration is working perfectly.
                </p>
                <p style="font-size: 14px; color: #64748b; margin: 0;">
                    You can now send newsletters directly from the app.
                </p>
            </div>
            
            <div style="text-align: center; margin-top: 30px;">
                <p style="color: #94a3b8; font-size: 12px;">
                    CreatorPulse Email Delivery System
                </p>
            </div>
        </div>
    </body>
    </html>
    """
    
    return send_newsletter_email(
        recipient_email=recipient_email,
        subject="✅ CreatorPulse Email Test",
        html_content=test_html
    )


def is_email_configured() -> bool:
    """
    Check if email credentials are configured
    
    Returns:
        bool: True if both SENDER_EMAIL and SENDER_EMAIL_PASSWORD are set
    """
    # Force reload to ensure we have latest values
    load_dotenv(override=True)
    
    sender_email = os.getenv("SENDER_EMAIL")
    sender_password = os.getenv("SENDER_EMAIL_PASSWORD")
    
    # Detailed debug output
    print(f"\n🔍 is_email_configured() check:")
    print(f"SENDER_EMAIL: {sender_email if sender_email else '❌ NOT SET'}")
    print(f"SENDER_EMAIL_PASSWORD: {'✅ SET (' + str(len(sender_password)) + ' chars)' if sender_password else '❌ NOT SET'}")
    
    if sender_password:
        print(f"Password has spaces: {' ' in sender_password}")
        print(f"Password first 4 chars: {sender_password[:4]}...")
    
    result = bool(sender_email and sender_password)
    print(f"Result: {result}")
    
    return result


# ============================================================================
# TELEGRAM DELIVERY (NEW - FREE Alternative to Email/WhatsApp)
# ============================================================================

def send_telegram_message(chat_id: str, message: str) -> bool:
    """
    Send message via Telegram Bot
    
    Args:
        chat_id: Telegram chat ID (get from user)
        message: Message text (markdown supported)
    
    Returns:
        bool: True if sent successfully
    """
    try:
        import requests
        
        bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
        
        if not bot_token:
            print("❌ TELEGRAM_BOT_TOKEN not configured in .env file")
            print("Get token from @BotFather on Telegram")
            return False
        
        # Telegram Bot API endpoint
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        
        payload = {
            "chat_id": chat_id,
            "text": message,
            "parse_mode": "Markdown"  # Supports *bold*, _italic_, etc.
        }
        
        print(f"📱 Sending Telegram message to {chat_id}...")
        
        response = requests.post(url, json=payload, timeout=10)
        
        if response.status_code == 200:
            print(f"✅ Telegram message sent!")
            return True
        else:
            print(f"❌ Telegram API error: {response.text}")
            return False
        
    except Exception as e:
        print(f"❌ Error sending Telegram message: {e}")
        import traceback
        traceback.print_exc()
        return False


def send_newsletter_via_telegram(chat_id: str, newsletter_title: str, newsletter_content: str) -> bool:
    """
    Send newsletter summary via Telegram
    
    Args:
        chat_id: Telegram chat ID
        newsletter_title: Newsletter title
        newsletter_content: Full HTML content
    
    Returns:
        bool: True if sent successfully
    """
    try:
        # Create summary for Telegram
        summary = create_telegram_summary(newsletter_title, newsletter_content)
        
        # Send via Telegram
        return send_telegram_message(chat_id, summary)
        
    except Exception as e:
        print(f"❌ Error sending newsletter via Telegram: {e}")
        return False


def create_telegram_summary(title: str, html_content: str, max_length: int = 4000) -> str:
    """
    Create Telegram-friendly summary from newsletter HTML
    Telegram supports Markdown and has 4096 char limit
    
    Args:
        title: Newsletter title
        html_content: Full HTML content
        max_length: Max characters (Telegram limit is 4096)
    
    Returns:
        str: Formatted Telegram message with Markdown
    """
    import re
    
    # Remove HTML tags
    clean_text = re.sub(r'<[^>]+>', '', html_content)
    clean_text = re.sub(r'\s+', ' ', clean_text).strip()
    
    # Extract first few sections
    sections = clean_text.split('.')[:15]  # More text allowed in Telegram
    summary_text = '. '.join(sections) + '.'
    
    # Truncate if too long
    if len(summary_text) > max_length - 300:
        summary_text = summary_text[:max_length - 300] + '...'
    
    # Format with Markdown
    message = f"""📰 *{title}*

{summary_text}

---
_Powered by CreatorPulse_
"""
    
    return message[:4096]  # Telegram's hard limit


def is_telegram_configured() -> bool:
    """
    Check if Telegram Bot token is configured
    
    Returns:
        bool: True if token is set
    """
    load_dotenv(override=True)
    
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    
    print(f"\n🔍 is_telegram_configured() check:")
    print(f"TELEGRAM_BOT_TOKEN: {'✅ SET' if bot_token else '❌ NOT SET'}")
    
    return bool(bot_token)


def send_test_telegram(chat_id: str) -> bool:
    """
    Send test Telegram message
    
    Args:
        chat_id: Telegram chat ID
    
    Returns:
        bool: True if sent successfully
    """
    test_message = """✅ *Telegram Test Successful!*

Great news! Your CreatorPulse Telegram Bot is working perfectly.

You can now receive newsletters directly on Telegram.

_CreatorPulse Delivery System_"""
    
    return send_telegram_message(chat_id, test_message)


def get_telegram_chat_id() -> str:
    """
    Get user's Telegram chat ID with better error handling
    User must send /start to the bot first
    
    Returns:
        str: Chat ID or helpful instructions
    """
    try:
        import requests
        
        bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
        
        if not bot_token:
            return "❌ Bot token not configured in .env"
        
        print(f"\n🔍 Fetching Telegram updates...")
        
        # Get updates from bot
        url = f"https://api.telegram.org/bot{bot_token}/getUpdates"
        response = requests.get(url, timeout=10)
        
        print(f"Response status: {response.status_code}")
        
        if response.status_code != 200:
            error_data = response.json()
            error_msg = error_data.get('description', 'Unknown error')
            return f"❌ API Error: {error_msg}"
        
        data = response.json()
        
        if not data.get("ok"):
            return f"❌ API returned error: {data.get('description', 'Unknown')}"
        
        results = data.get("result", [])
        
        print(f"Found {len(results)} updates")
        
        if not results:
            return """⚠️ No messages found yet!

📝 Steps to get your Chat ID:
1. Open Telegram
2. Search for your bot (the name you gave it)
3. Click START or send /start
4. Come back here and click 'Get My Chat ID' again

💡 Your bot username should end with 'bot'"""
        
        # Get the most recent message's chat_id
        # Try to find the latest message from any update type
        chat_id = None
        latest_update = results[-1]
        
        # Check different message types
        if "message" in latest_update:
            chat_id = latest_update["message"].get("chat", {}).get("id")
        elif "edited_message" in latest_update:
            chat_id = latest_update["edited_message"].get("chat", {}).get("id")
        elif "channel_post" in latest_update:
            chat_id = latest_update["channel_post"].get("chat", {}).get("id")
        
        if chat_id:
            # Get username for confirmation
            username = latest_update.get("message", {}).get("from", {}).get("username", "Unknown")
            first_name = latest_update.get("message", {}).get("from", {}).get("first_name", "")
            
            print(f"✅ Found chat_id: {chat_id} for user: {username} ({first_name})")
            
            return f"{chat_id}"
        else:
            return """⚠️ Could not extract Chat ID from updates.

Try these steps:
1. Delete your bot and create a new one with @BotFather
2. Send /start to the new bot
3. Try again"""
        
    except requests.Timeout:
        return "⏱️ Request timed out. Check your internet connection."
    except requests.RequestException as e:
        return f"🌐 Network error: {str(e)}"
    except Exception as e:
        print(f"❌ Error in get_telegram_chat_id: {e}")
        import traceback
        traceback.print_exc()
        return f"❌ Error: {str(e)}"