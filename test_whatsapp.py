import os
from dotenv import load_dotenv
from datetime import datetime, timedelta

# Load environment variables
load_dotenv()

# Get Twilio credentials
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_PHONE_NUMBER = os.getenv("TWILIO_PHONE_NUMBER", "+33668695116")
RECIPIENT_PHONE_NUMBER = os.getenv("RECIPIENT_PHONE_NUMBER", "33668695116")

print("Current environment values:")
print(f"TWILIO_ACCOUNT_SID: {TWILIO_ACCOUNT_SID}")
print(f"TWILIO_AUTH_TOKEN: {'*' * len(TWILIO_AUTH_TOKEN) if TWILIO_AUTH_TOKEN else 'Not set'}")
print(f"TWILIO_PHONE_NUMBER: {TWILIO_PHONE_NUMBER}")
print(f"RECIPIENT_PHONE_NUMBER: {RECIPIENT_PHONE_NUMBER}")

# Prepare properly formatted numbers for WhatsApp
from_number = TWILIO_PHONE_NUMBER
if not from_number.startswith("whatsapp:"):
    if not from_number.startswith("+"):
        from_number = "+" + from_number
    from_number = f"whatsapp:{from_number}"

to_number = RECIPIENT_PHONE_NUMBER
if not to_number.startswith("whatsapp:"):
    if not to_number.startswith("+"):
        to_number = "+" + to_number
    to_number = f"whatsapp:{to_number}"

print(f"\nFormatted numbers for WhatsApp:")
print(f"From: {from_number}")
print(f"To: {to_number}")

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

# Import Twilio and send message
try:
    print("\nSending message...")
    from twilio.rest import Client
    
    # Create Twilio client
    client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
    
    # Send the WhatsApp message
    message = client.messages.create(
        body=message_body,
        from_=from_number,
        to=to_number
    )
    
    print(f"\n✅ Success! Message sent with ID: {message.sid}")
    print(f"Status: {message.status}")
    
except Exception as e:
    print(f"\n❌ Error sending message: {str(e)}")
    print("\nPossible solutions:")
    print("1. Make sure your Twilio account is set up for WhatsApp")
    print("2. Ensure the recipient has opted in to your WhatsApp sandbox")
    print("3. Check that your account has sufficient credits")
    print("4. Verify your account status at https://www.twilio.com/console") 