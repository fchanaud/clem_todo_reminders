import os
from dotenv import load_dotenv
import sys
import requests

# Load environment variables
load_dotenv()

# Get Pushover credentials
PUSHOVER_USER_KEY = os.getenv("PUSHOVER_USER_KEY")
PUSHOVER_API_TOKEN = os.getenv("PUSHOVER_API_TOKEN")
RECIPIENT_USER_KEY = os.getenv("RECIPIENT_USER_KEY", PUSHOVER_USER_KEY)

print("===== PUSHOVER CONFIGURATION CHECK =====")
print(f"PUSHOVER_API_TOKEN: {'✅ Set' if PUSHOVER_API_TOKEN else '❌ Not set'}")
if PUSHOVER_API_TOKEN:
    print(f"  Value: {PUSHOVER_API_TOKEN[:5]}...{PUSHOVER_API_TOKEN[-5:]}")

print(f"PUSHOVER_USER_KEY: {'✅ Set' if PUSHOVER_USER_KEY else '❌ Not set'}")
if PUSHOVER_USER_KEY:
    print(f"  Value: {PUSHOVER_USER_KEY[:5]}...{PUSHOVER_USER_KEY[-5:]}")

print(f"RECIPIENT_USER_KEY: {'✅ Set' if RECIPIENT_USER_KEY else '❌ Not set'}")
if RECIPIENT_USER_KEY:
    print(f"  Value: {RECIPIENT_USER_KEY[:5]}...{RECIPIENT_USER_KEY[-5:]}")

# Try to send a test message
try:
    print("\nTesting Pushover API connection...")
    
    if not PUSHOVER_API_TOKEN or not PUSHOVER_USER_KEY:
        print("❌ Cannot test API connection - missing credentials")
    else:
        # Try to validate the user key
        validation_url = "https://api.pushover.net/1/users/validate.json"
        validation_data = {
            "token": PUSHOVER_API_TOKEN,
            "user": PUSHOVER_USER_KEY
        }
        
        validation_response = requests.post(validation_url, data=validation_data)
        validation_result = validation_response.json()
        
        if validation_response.status_code == 200 and validation_result.get("status") == 1:
            print("✅ User key validation successful")
            print(f"  Devices: {', '.join(validation_result.get('devices', []))}")
        else:
            print(f"❌ User key validation failed: {validation_result.get('errors', ['Unknown error'])}")
        
        # Try to send a test message
        message_url = "https://api.pushover.net/1/messages.json"
        message_data = {
            "token": PUSHOVER_API_TOKEN,
            "user": RECIPIENT_USER_KEY,
            "message": "This is a test message from the Todo Reminder app.",
            "title": "Pushover Configuration Test"
        }
        
        confirm = input("\nSend a test message? (y/n): ")
        if confirm.lower() != 'y':
            print("Test message canceled.")
        else:
            message_response = requests.post(message_url, data=message_data)
            message_result = message_response.json()
            
            if message_response.status_code == 200 and message_result.get("status") == 1:
                print("✅ Test message sent successfully!")
                print(f"  Message ID: {message_result.get('request')}")
            else:
                print(f"❌ Test message failed: {message_result.get('errors', ['Unknown error'])}")
                
except Exception as e:
    print(f"\n❌ Error testing Pushover API: {str(e)}")

print("\n===== RECOMMENDATIONS =====")
missing = []
if not PUSHOVER_API_TOKEN:
    missing.append("PUSHOVER_API_TOKEN")
if not PUSHOVER_USER_KEY:
    missing.append("PUSHOVER_USER_KEY")

if missing:
    print(f"1. Set the following environment variables in your .env file: {', '.join(missing)}")

print("\n2. Make sure your Pushover account is properly set up:")
print("   - Create an application at https://pushover.net/apps/build")
print("   - Get your user key from https://pushover.net/") 