import requests
import smtplib
import os
import json
from datetime import datetime
from email.message import EmailMessage

# Get credentials from environment variables (set in GitHub Secrets)
EMAIL_FROM = os.environ.get('EMAIL_FROM')
EMAIL_TO = os.environ.get('EMAIL_TO')
GMAIL_APP_PASSWORD = os.environ.get('GMAIL_APP_PASSWORD')

STATE_FILE = 'last_state.json'


def send_email_alert(app_name, rank_position):
    """Send email notification when ChatGPT reaches #1"""
    try:
        msg = EmailMessage()
        msg['Subject'] = f'🎉 ChatGPT is #{rank_position} on App Store!'
        msg['From'] = EMAIL_FROM
        msg['To'] = EMAIL_TO
        
        body = f"""
ChatGPT App Store Ranking Alert
================================

Status: ChatGPT has reached rank #{rank_position}!
Current #1 App: {app_name}
Time: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC

This is an automated alert from your GitHub Actions monitor.
Checks run every 1 minute automatically.

---
Powered by GitHub Actions
        """
        
        msg.set_content(body)
        
        # Connect to Gmail's SMTP server
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login(EMAIL_FROM, GMAIL_APP_PASSWORD)
            smtp.send_message(msg)
        
        print(f"✅ Email alert sent successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Failed to send email: {e}")
        return False


def send_status_email(chatgpt_rank, top_app, total_apps):
    """Send periodic status update (optional)"""
    try:
        msg = EmailMessage()
        msg['Subject'] = f'📊 App Store Status: ChatGPT is #{chatgpt_rank}'
        msg['From'] = EMAIL_FROM
        msg['To'] = EMAIL_TO
        
        body = f"""
App Store Ranking Update
========================

ChatGPT Current Rank: #{chatgpt_rank}
Current #1 App: {top_app}
Time: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC

Monitoring top {total_apps} apps every 1 minute.

---
Powered by GitHub Actions
        """
        
        msg.set_content(body)
        
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login(EMAIL_FROM, GMAIL_APP_PASSWORD)
            smtp.send_message(msg)
        
        print(f"✅ Status email sent!")
        return True
        
    except Exception as e:
        print(f"⚠️  Failed to send status email: {e}")
        return False


def get_top_apps():
    """Fetch top free apps from iTunes RSS feed"""
    try:
        url = "https://itunes.apple.com/us/rss/topfreeapplications/limit=25/json"
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        entries = data.get('feed', {}).get('entry', [])
        
        # Handle single entry case
        if isinstance(entries, dict):
            entries = [entries]
        
        # Extract app names with their rankings
        apps = []
        for i, entry in enumerate(entries, 1):
            app_name = entry.get('im:name', {}).get('label', 'Unknown')
            apps.append({'rank': i, 'name': app_name})
        
        return apps
        
    except Exception as e:
        print(f"⚠️  Error fetching data: {e}")
        return []


def find_chatgpt_rank(apps):
    """Find ChatGPT's current rank in the list"""
    for app in apps:
        if 'ChatGPT' in app['name']:
            return app['rank'], app['name']
    return None, None


def load_last_state():
    """Load the last known state from file"""
    try:
        if os.path.exists(STATE_FILE):
            with open(STATE_FILE, 'r') as f:
                return json.load(f)
    except:
        pass
    return {'last_rank': None, 'alert_sent_for_rank_1': False}


def save_state(state):
    """Save current state to file"""
    try:
        with open(STATE_FILE, 'w') as f:
            json.dump(state, f)
    except Exception as e:
        print(f"⚠️  Could not save state: {e}")


def main():
    """Main monitoring function - runs once per GitHub Action"""
    timestamp = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
    print(f"{'='*60}")
    print(f"🚀 App Store Monitor - Run at {timestamp} UTC")
    print(f"{'='*60}\n")
    
    # Validate credentials
    if not all([EMAIL_FROM, EMAIL_TO, GMAIL_APP_PASSWORD]):
        print("❌ ERROR: Missing email credentials!")
        print("Please set EMAIL_FROM, EMAIL_TO, and GMAIL_APP_PASSWORD in GitHub Secrets")
        return
    
    # Load previous state
    state = load_last_state()
    last_rank = state.get('last_rank')
    alert_sent = state.get('alert_sent_for_rank_1', False)
    
    # Fetch current rankings
    apps = get_top_apps()
    
    if not apps:
        print("⚠️  No data received from App Store")
        return
    
    # Get top app info
    top_app = apps[0]['name']
    print(f"📱 Current #1 App: {top_app}")
    
    # Find ChatGPT's position
    chatgpt_rank, chatgpt_name = find_chatgpt_rank(apps)
    
    if chatgpt_rank:
        print(f"🔍 ChatGPT found at rank #{chatgpt_rank}")
        
        # Check if rank changed
        if last_rank != chatgpt_rank:
            print(f"📊 Rank changed: #{last_rank} → #{chatgpt_rank}")
        
        # Send alert if ChatGPT is #1 and we haven't alerted yet
        if chatgpt_rank == 1:
            if not alert_sent:
                print(f"🎉 ChatGPT is #1! Sending alert...")
                send_email_alert(chatgpt_name, chatgpt_rank)
                state['alert_sent_for_rank_1'] = True
            else:
                print(f"✅ ChatGPT is still #1 (already alerted)")
        else:
            # Reset alert flag if dropped from #1
            if alert_sent:
                print(f"📉 ChatGPT dropped from #1 to #{chatgpt_rank}")
            state['alert_sent_for_rank_1'] = False
        
        # Update state
        state['last_rank'] = chatgpt_rank
        save_state(state)
        
    else:
        print(f"❌ ChatGPT not found in top 25")
        state['last_rank'] = None
        state['alert_sent_for_rank_1'] = False
        save_state(state)
    
    print(f"\n{'='*60}")
    print(f"✅ Check complete - Next run in 1 minute")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
