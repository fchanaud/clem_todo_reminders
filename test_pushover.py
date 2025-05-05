import os
from dotenv import load_dotenv
from datetime import datetime, timedelta
import requests

# Load environment variables
load_dotenv()

# Get Pushover credentials
PUSHOVER_API_TOKEN = os.getenv("PUSHOVER_API_TOKEN")
PUSHOVER_USER_KEY = os.getenv("PUSHOVER_USER_KEY")
RECIPIENT_USER_KEY = os.getenv("RECIPIENT_USER_KEY", PUSHOVER_USER_KEY)

print("Current environment values:")
print(f"PUSHOVER_API_TOKEN: {'*' * min(len(PUSHOVER_API_TOKEN or ''), 5)}...{'*' * min(len(PUSHOVER_API_TOKEN or ''), 5) if PUSHOVER_API_TOKEN else 'Not set'}")
print(f"PUSHOVER_USER_KEY: {'*' * min(len(PUSHOVER_USER_KEY or ''), 5)}...{'*' * min(len(PUSHOVER_USER_KEY or ''), 5) if PUSHOVER_USER_KEY else 'Not set'}")
print(f"RECIPIENT_USER_KEY: {'*' * min(len(RECIPIENT_USER_KEY or ''), 5)}...{'*' * min(len(RECIPIENT_USER_KEY or ''), 5) if RECIPIENT_USER_KEY else 'Not set'}")

# Prepare message content
due_time = datetime.now() + timedelta(hours=1)
message_body = f"🔔 Test Reminder: This is a test message sent on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"

print(f"\nMessage body:")
print(message_body)

# Ask for confirmation before sending
confirm = input("\nSend the test message? (y/n): ")
if confirm.lower() != 'y':
    print("Test cancelled.")
    exit()

# Send Pushover notification
try:
    print("\nSending message...")
    
    # Send the Pushover message
    response = requests.post(
        "https://api.pushover.net/1/messages.json",
        data={
            "token": PUSHOVER_API_TOKEN,
            "user": RECIPIENT_USER_KEY,
            "message": message_body,
            "title": "Todo Reminder Test",
            "priority": 0,  # Normal priority
        }
    )
    
    result = response.json()
    
    if response.status_code == 200 and result.get("status") == 1:
        print(f"\n✅ Success! Message sent with ID: {result.get('request')}")
    else:
        print(f"\n❌ Error sending message: {result.get('errors', ['Unknown error'])}")
    
except Exception as e:
    print(f"\n❌ Error sending message: {str(e)}")
    print("\nPossible solutions:")
    print("1. Make sure your Pushover credentials are correct")
    print("2. Ensure you have internet connectivity")
    print("3. Check that you have sufficient credits on your Pushover account") 