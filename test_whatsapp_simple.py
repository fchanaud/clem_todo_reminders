import os
from dotenv import load_dotenv
import sys

# Load environment variables
load_dotenv()

# Get Twilio credentials
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_PHONE_NUMBER = os.getenv("TWILIO_PHONE_NUMBER", "+33668695116")
RECIPIENT_PHONE_NUMBER = os.getenv("RECIPIENT_PHONE_NUMBER", "33668695116")

print("1. Checking Twilio configuration...")
if not all([TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_PHONE_NUMBER]):
    print("ERROR: Missing required Twilio configuration.")
    print(f"  TWILIO_ACCOUNT_SID: {'Set' if TWILIO_ACCOUNT_SID else 'Missing'}")
    print(f"  TWILIO_AUTH_TOKEN: {'Set' if TWILIO_AUTH_TOKEN else 'Missing'}")
    print(f"  TWILIO_PHONE_NUMBER: {'Set' if TWILIO_PHONE_NUMBER else 'Missing'}")
    sys.exit(1)

print("2. Formatting phone numbers for WhatsApp...")
# WhatsApp numbers must be in the format "whatsapp:+1234567890"
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

print(f"  From: {from_number}")
print(f"  To: {to_number}")

print("3. Sending test WhatsApp message...")
try:
    from twilio.rest import Client
    
    # Create message content
    message_body = "🔔 This is a test WhatsApp message from your Todo app"
    
    # Create Twilio client
    client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
    
    # Send the message
    message = client.messages.create(
        body=message_body,
        from_=from_number,
        to=to_number
    )
    
    print(f"✅ Success! Message sent with ID: {message.sid}")
    print(f"  Status: {message.status}")
    
except ImportError:
    print("❌ Error: Twilio library not installed. Run: pip install twilio")
    sys.exit(1)
except Exception as e:
    print(f"❌ Error: {str(e)}")
    print("\nPossible solutions:")
    print("1. Make sure your Twilio account is set up for WhatsApp")
    print("2. Verify that you've joined the Twilio WhatsApp Sandbox")
    print("3. Ensure the recipient has opted in to your WhatsApp sandbox")
    print("4. Check that your account has sufficient credits")
    print("5. Verify your Twilio account status is active")
    sys.exit(1)

print("\n4. Need to update your server.py:")
print("""
# Add this to your send_whatsapp_reminder function:

def send_whatsapp_reminder(task_title, task_priority, due_time, recipient=RECIPIENT_PHONE_NUMBER):
    if not TWILIO_ACCOUNT_SID or not TWILIO_AUTH_TOKEN or not TWILIO_PHONE_NUMBER:
        logger.warning("Twilio WhatsApp API not configured, skipping WhatsApp notification")
        return None
    
    try:
        # Ensure the recipient number has the correct format (add "whatsapp:" prefix if not present)
        if not recipient.startswith("whatsapp:"):
            # Ensure the number starts with a + if not already
            if not recipient.startswith("+"):
                recipient = "+" + recipient
            recipient = f"whatsapp:{recipient}"
            
        # Ensure the sending number has the correct format
        twilio_number = TWILIO_PHONE_NUMBER
        if not twilio_number.startswith("whatsapp:"):
            if not twilio_number.startswith("+"):
                twilio_number = "+" + twilio_number
            twilio_number = f"whatsapp:{twilio_number}"
        
        logger.info(f"Using formatted numbers - From: {twilio_number}, To: {recipient}")
        
        # Format the due time for display
        due_time_str = due_time.strftime("%A, %B %d at %I:%M %p")
        
        # Create a message with task details
        message_body = f"🔔 Reminder: \"{task_title}\" is due on {due_time_str}\\nPriority: {task_priority}"
        
        # Import twilio here to avoid issues if it's not installed
        from twilio.rest import Client
        
        # Create Twilio client
        client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        
        # Send the WhatsApp message
        message = client.messages.create(
            body=message_body,
            from_=twilio_number,
            to=recipient
        )
        
        return message.sid
    except Exception as e:
        logger.error(f"Error sending WhatsApp reminder: {str(e)}", exc_info=True)
        return None
""") 