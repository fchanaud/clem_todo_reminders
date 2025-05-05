import os
from dotenv import load_dotenv
from datetime import datetime, timedelta, timezone
from supabase import create_client
import uuid

# Load environment variables
load_dotenv()

# Get Supabase credentials
supabase_url = os.getenv("SUPABASE_URL") or os.getenv("NEXT_PUBLIC_SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_KEY") or os.getenv("NEXT_PUBLIC_SUPABASE_ANON_KEY")

# Initialize Supabase client
supabase = create_client(supabase_url, supabase_key)

# For development, use dev_ table prefix
ENV = os.getenv("ENV", "development").lower()
TABLE_PREFIX = "dev_" if ENV == "development" else ""

# Generate a unique task ID
task_id = str(uuid.uuid4())

# Create the task - due in 10 minutes
now = datetime.now(timezone.utc)
due_time = now + timedelta(minutes=10)

# Create a test task
task_data = {
    "id": task_id,
    "title": "Test Pushover Notification",
    "due_time": due_time.isoformat(),
    "priority": "High",  # High priority to test priority=1
    "completed": False,
    "created_at": now.isoformat()
}

# Insert the task
task_result = supabase.table(f"{TABLE_PREFIX}tasks").insert(task_data).execute()
print(f"Task created: {task_result.data[0]['id']}")

# Create a reminder for 1 minute from now
reminder_time = now + timedelta(minutes=1)
reminder_data = {
    "task_id": task_id,
    "reminder_time": reminder_time.isoformat()
}

# Insert the reminder
reminder_result = supabase.table(f"{TABLE_PREFIX}reminders").insert(reminder_data).execute()
print(f"Reminder created: {reminder_result.data[0]['id']}")

print(f"\nTest task '{task_data['title']}' created with a reminder due at {reminder_time.strftime('%H:%M:%S')}")
print(f"The check-reminders endpoint should detect this reminder in about 1 minute")
print(f"Current time: {now.strftime('%H:%M:%S')}") 