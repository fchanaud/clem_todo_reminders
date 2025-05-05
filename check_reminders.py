import os
from dotenv import load_dotenv
from datetime import datetime, timedelta, timezone
from supabase import create_client

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

# Current time
now = datetime.now(timezone.utc)
print(f"Current time (UTC): {now.isoformat()}")

# Check for recent tasks
print("\n=== RECENT TASKS ===")
tasks_result = (
    supabase.table(f"{TABLE_PREFIX}tasks")
    .select("*")
    .order("created_at", desc=True)
    .limit(5)
    .execute()
)

tasks = tasks_result.data
for i, task in enumerate(tasks):
    print(f"{i+1}. ID: {task['id']}")
    print(f"   Title: {task['title']}")
    print(f"   Priority: {task['priority']}")
    print(f"   Due: {task['due_time']}")
    print(f"   Created: {task['created_at']}")
    print(f"   Completed: {task['completed']}")
    print()

# Check for recent reminders
print("\n=== RECENT REMINDERS ===")
reminders_result = (
    supabase.table(f"{TABLE_PREFIX}reminders")
    .select("*")
    .order("created_at", desc=True)
    .limit(5)
    .execute()
)

reminders = reminders_result.data
for i, reminder in enumerate(reminders):
    print(f"{i+1}. ID: {reminder['id']}")
    print(f"   Task ID: {reminder['task_id']}")
    print(f"   Reminder Time: {reminder['reminder_time']}")
    print(f"   Created: {reminder['created_at']}")
    print()

# Check the last processed time
print("\n=== LAST PROCESSED TIME ===")
processed_status = (
    supabase.table(f"{TABLE_PREFIX}app_status")
    .select("*")
    .eq("name", "last_processed_time")
    .execute()
).data

if processed_status and len(processed_status) > 0:
    last_processed_time = datetime.fromisoformat(processed_status[0]["value"].replace('Z', '+00:00'))
    print(f"Last processed time: {last_processed_time.isoformat()}")
    print(f"Minutes ago: {(now - last_processed_time).total_seconds() / 60:.2f}")
else:
    print("No last processed time found") 