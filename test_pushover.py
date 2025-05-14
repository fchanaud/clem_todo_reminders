import os
from dotenv import load_dotenv
from datetime import datetime, timedelta, timezone
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

# Helper function to check if a date is in British Summer Time
def is_bst(utc_time):
    """Check if the current time is during British Summer Time"""
    year = utc_time.year
    
    # Function to find the last Sunday in a given month and year
    def last_sunday(year, month):
        # Get the last day of the month
        if month == 12:
            last_day = datetime(year + 1, 1, 1, tzinfo=timezone.utc) - timedelta(days=1)
        else:
            last_day = datetime(year, month + 1, 1, tzinfo=timezone.utc) - timedelta(days=1)
        
        # Find the last Sunday
        offset = last_day.weekday()
        if offset != 6:  # 6 is Sunday
            last_day = last_day - timedelta(days=offset + 1)
        
        return last_day
    
    # Calculate BST start and end for the current year
    bst_start = last_sunday(year, 3).replace(hour=1)  # Last Sunday in March, 1am UTC
    bst_end = last_sunday(year, 10).replace(hour=1)  # Last Sunday in October, 1am UTC
    
    # Determine if current time is during BST
    return bst_start <= utc_time < bst_end

# Prepare message content using UK time
now_utc = datetime.now(timezone.utc)
due_time = now_utc + timedelta(hours=1)

# Convert to UK time
is_british_summer_time = is_bst(now_utc)
uk_offset = 1 if is_british_summer_time else 0
uk_due_time = due_time + timedelta(hours=uk_offset)

# Format the UK time for display
uk_time_str = uk_due_time.strftime("%Y-%m-%d %H:%M:%S")
time_zone_suffix = "BST" if is_british_summer_time else "GMT"

message_body = f"🔔 Test Reminder: This is a test message sent at {uk_time_str} {time_zone_suffix}"

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