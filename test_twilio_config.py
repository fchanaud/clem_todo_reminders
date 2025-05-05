import os
from dotenv import load_dotenv
import sys

# Load environment variables
load_dotenv()

# Get Twilio credentials
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_PHONE_NUMBER = os.getenv("TWILIO_PHONE_NUMBER")
RECIPIENT_PHONE_NUMBER = os.getenv("RECIPIENT_PHONE_NUMBER")

print("===== TWILIO CONFIGURATION CHECK =====")
print(f"TWILIO_ACCOUNT_SID: {'✅ Set' if TWILIO_ACCOUNT_SID else '❌ Not set'}")
if TWILIO_ACCOUNT_SID:
    print(f"  Value: {TWILIO_ACCOUNT_SID[:5]}...{TWILIO_ACCOUNT_SID[-5:]}")

print(f"TWILIO_AUTH_TOKEN: {'✅ Set' if TWILIO_AUTH_TOKEN else '❌ Not set'}")
if TWILIO_AUTH_TOKEN:
    print(f"  Value: {TWILIO_AUTH_TOKEN[:3]}...{TWILIO_AUTH_TOKEN[-3:]}")

print(f"TWILIO_PHONE_NUMBER: {'✅ Set' if TWILIO_PHONE_NUMBER else '❌ Not set'}")
if TWILIO_PHONE_NUMBER:
    print(f"  Value: {TWILIO_PHONE_NUMBER}")
    print(f"  Has whatsapp: prefix: {'✅ Yes' if TWILIO_PHONE_NUMBER.startswith('whatsapp:') else '❌ No'}")
    if not TWILIO_PHONE_NUMBER.startswith('whatsapp:'):
        print(f"  RECOMMENDATION: Add 'whatsapp:' prefix to your TWILIO_PHONE_NUMBER")

print(f"RECIPIENT_PHONE_NUMBER: {'✅ Set' if RECIPIENT_PHONE_NUMBER else '❌ Not set'}")
if RECIPIENT_PHONE_NUMBER:
    print(f"  Value: {RECIPIENT_PHONE_NUMBER}")

# Try to import the twilio library to make sure it's installed
try:
    from twilio.rest import Client
    print("\nTwilio Library: ✅ Installed")
    
    # Test creating a client
    try:
        if TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN:
            client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
            print("Twilio Client Creation: ✅ Success")
            
            # Check account details
            try:
                account = client.api.accounts(TWILIO_ACCOUNT_SID).fetch()
                print(f"Account Status: {account.status}")
                print(f"Account Type: {account.type}")
            except Exception as e:
                print(f"Account Check Error: {str(e)}")
    except Exception as e:
        print(f"Twilio Client Creation Error: {str(e)}")
except ImportError:
    print("\nTwilio Library: ❌ Not installed")
    print("RECOMMENDATION: Run 'pip install twilio'")

print("\n===== RECOMMENDATIONS =====")
missing = []
if not TWILIO_ACCOUNT_SID:
    missing.append("TWILIO_ACCOUNT_SID")
if not TWILIO_AUTH_TOKEN:
    missing.append("TWILIO_AUTH_TOKEN")
if not TWILIO_PHONE_NUMBER:
    missing.append("TWILIO_PHONE_NUMBER")
elif not TWILIO_PHONE_NUMBER.startswith('whatsapp:'):
    print("1. Add 'whatsapp:' prefix to your TWILIO_PHONE_NUMBER in .env file")
    print("   Example: TWILIO_PHONE_NUMBER=whatsapp:+1234567890")

if missing:
    print(f"1. Set the following environment variables in your .env file: {', '.join(missing)}")

print("\n2. Make sure your Twilio account is properly set up for WhatsApp:")
print("   - You must join the Twilio WhatsApp Sandbox")
print("   - The recipient must have opted in to your sandbox")
print("   - Follow the instructions at: https://www.twilio.com/docs/whatsapp/sandbox") 