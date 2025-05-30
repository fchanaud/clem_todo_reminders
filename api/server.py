from fastapi import FastAPI, HTTPException, BackgroundTasks, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from datetime import datetime, timedelta
from typing import Optional, List
import os
from dotenv import load_dotenv
from datetime import timezone
import json
import sys
import requests
import time
import logging  # Add logging import

# Monkey patch for gotrue to avoid proxy issues
import httpx
original_init = httpx.Client.__init__
def patched_init(self, *args, **kwargs):
    if 'proxy' in kwargs:
        print("Removing 'proxy' from httpx Client kwargs to prevent errors")
        del kwargs['proxy']
    
    # Disable HTTP/2 if h2 package is not available
    try:
        import h2
        # h2 is available, we can use HTTP/2
    except ImportError:
        print("HTTP/2 support disabled - h2 package not available")
        kwargs['http2'] = False
    
    return original_init(self, *args, **kwargs)
httpx.Client.__init__ = patched_init

# Now import supabase after the monkey patch
from supabase import create_client, Client
# Remove OpenAI import from here - we'll import it when needed

# Configure logging
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

logger = logging.getLogger("todo-reminders")

# Add these lines for even more visible debugging
print("="*80)
print("SERVER STARTING - DEBUGGING ENABLED")
print("="*80)

# Load environment variables (simplify to just loading .env)
load_dotenv()
print("Loaded configuration from .env")

# Determine environment and set table prefix
env = os.getenv("ENV", "development").lower()
TABLE_PREFIX = "dev_" if env == "development" else ""

if env == "development":
    print("Running in DEVELOPMENT environment")
    print(f"Using table prefix: '{TABLE_PREFIX}'")
    # Load development environment file if it exists
    if os.path.exists(".env.development"):
        load_dotenv(".env.development", override=True)
        print("Loaded configuration from .env.development")
else:
    print("Running in PRODUCTION environment")
    print("Using no table prefix")

# Get Supabase credentials
supabase_url = os.getenv("NEXT_PUBLIC_SUPABASE_URL")
supabase_key = os.getenv("NEXT_PUBLIC_SUPABASE_ANON_KEY")

# Define the task key used in database joins
TASK_KEY = "tasks"
logger.info(f"Using table prefix: '{TABLE_PREFIX}'")
logger.info(f"Using task key in joins: '{TASK_KEY}'")

# Pushover API configuration
PUSHOVER_API_TOKEN = os.getenv("PUSHOVER_API_TOKEN")
PUSHOVER_USER_KEY = os.getenv("PUSHOVER_USER_KEY")
RECIPIENT_USER_KEY = os.getenv("RECIPIENT_USER_KEY", PUSHOVER_USER_KEY)  # Default recipient user key

# Global variable to hold the OpenAI client
_openai_client = None

def get_openai_client():
    """Lazy initialization of OpenAI client"""
    global _openai_client
    if _openai_client is None:
        try:
            from openai import OpenAI
            _openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
            logger.info("OpenAI client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize OpenAI client: {str(e)}")
            _openai_client = None
    return _openai_client

# Check if credentials are available
if not supabase_url or not supabase_key:
    raise Exception(
        "Missing Supabase credentials. Please ensure NEXT_PUBLIC_SUPABASE_URL and "
        "NEXT_PUBLIC_SUPABASE_ANON_KEY are set in your .env file. "
        f"Current values - URL: {supabase_url}, Key: {'*' * len(supabase_key) if supabase_key else 'None'}"
    )

app = FastAPI()

# CORS middleware configuration
frontend_url = os.getenv("FRONTEND_URL", "http://localhost:3000")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[frontend_url, "http://localhost:3000", "http://localhost:3001", "https://clem-todo-frontend.onrender.com"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Supabase client - simplified approach
try:
    # Print out environment variables for debugging
    print("Environment Variables:")
    for key, value in os.environ.items():
        if key.startswith(('NEXT_PUBLIC_', 'SUPABASE_', 'OPENAI_', 'PUSHOVER_')):
            print(f"{key}: {'*' * len(value) if value else 'None'}")
    
    # Print package versions for debugging
    import supabase
    import gotrue
    print(f"Supabase version: {getattr(supabase, '__version__', 'unknown')}")
    print(f"GoTrue version: {getattr(gotrue, '__version__', 'unknown')}")
    
    # Create Supabase client with simple configuration
    try:
        # First try with default settings
        supabase: Client = create_client(supabase_url, supabase_key)
    except ImportError as e:
        if "h2 package is not installed" in str(e):
            print("ImportError: HTTP/2 package not available. Trying alternative client configuration...")
            # Create a client options object with HTTP/2 disabled
            from supabase.lib.client_options import ClientOptions
            options = ClientOptions()
            # Set HTTP/2 to False in client options
            if hasattr(options, 'http_options'):
                options.http_options.http2 = False
            supabase: Client = create_client(supabase_url, supabase_key, options)
    
    print(f"Connected to database at {supabase_url[:30]}...")
    logger.info(f"Connected to database")
except Exception as e:
    import traceback
    traceback.print_exc(file=sys.stderr)
    raise

class Reminder(BaseModel):
    reminder_time: datetime
    task_id: str

class Task(BaseModel):
    title: str
    due_time: datetime
    priority: str
    single_reminder: bool = False
    hours_before: Optional[int] = None
    phone_number: Optional[str] = None

def send_pushover_notification(task_title, task_priority, due_time, reminder_time=None, recipient=RECIPIENT_USER_KEY):
    """Send a Pushover notification for a task reminder"""
    if not PUSHOVER_API_TOKEN or not PUSHOVER_USER_KEY:
        logger.warning("Pushover API not configured, skipping notification")
        return None
    
    try:
        import requests
        logger.info("Preparing to send Pushover notification")
        
        # Convert due_time to UK time for display
        # Determine if we're in British Summer Time
        is_british_summer_time = is_bst(due_time)
        
        # Apply UK offset to convert to UK time
        uk_offset = 1 if is_british_summer_time else 0
        uk_due_time = due_time + timedelta(hours=uk_offset)
        
        # Format the UK due time for display
        due_time_str = uk_due_time.strftime("%A, %B %d at %I:%M %p")
        time_zone_suffix = "BST" if is_british_summer_time else "GMT"
        due_time_str = f"{due_time_str} ({time_zone_suffix})"
        
        # Check if this is an urgent reminder (reminder time is same as due time)
        is_urgent = False
        if reminder_time:
            # Round to nearest minute to avoid second differences
            rounded_reminder = reminder_time.replace(second=0, microsecond=0)
            rounded_due = due_time.replace(second=0, microsecond=0)
            is_urgent = rounded_reminder == rounded_due
            
        # Create a message with task details
        message_prefix = "🚨 URGENT: " if is_urgent else "🔔 Reminder: "
        message_body = f"{message_prefix}\"{task_title}\" is due on {due_time_str}\nPriority: {task_priority}"
        
        if is_urgent:
            message_body += "\n⚠️ This task is due now!"
        
        logger.info(f"Preparing Pushover message: {message_body}")
        
        # Set the recipient to the default if not specified
        user_key = recipient or PUSHOVER_USER_KEY
        
        # Determine push priority based on urgency and task priority
        push_priority = 2 if is_urgent else (1 if task_priority == "High" else 0)  # Emergency for urgent, high for high priority
        
        # Send the Pushover notification
        notification_data = {
            "token": PUSHOVER_API_TOKEN,
            "user": user_key,
            "message": message_body,
            "title": "Todo Reminder",
            "priority": push_priority,
        }
        
        # Add emergency parameters if it's an emergency priority (2)
        if push_priority == 2:
            notification_data["retry"] = 30  # Retry every 30 seconds
            notification_data["expire"] = 3600  # Expire after 1 hour
        
        response = requests.post(
            "https://api.pushover.net/1/messages.json",
            data=notification_data
        )
        
        # Check response
        if response.status_code == 200:
            result = response.json()
            if result.get("status") == 1:
                message_id = result.get("request")
                logger.info(f"Pushover notification sent successfully: {message_id}")
                return message_id
        
        # If we get here, there was an error
        error_message = f"Error sending Pushover notification: {response.text}"
        logger.error(error_message)
        return None
    except Exception as e:
        logger.error(f"Error sending Pushover notification: {str(e)}", exc_info=True)
        return None

def check_upcoming_reminders():
    """Check for reminders that match the current hour in UK time, 
    with additional logic to handle Render's free tier spin-down behavior"""
    try:
        logger.info("Starting reminder check")
        print("\n" + "-"*80)
        print("- CHECKING REMINDERS")
        print("-"*80)
        
        # Get current time in UTC
        now_utc = datetime.now(timezone.utc)
        
        # Determine if we're in British Summer Time
        is_british_summer_time = is_bst(now_utc)
        
        # Convert to UK time
        uk_offset = 1 if is_british_summer_time else 0
        now_uk = now_utc + timedelta(hours=uk_offset)
        
        print(f"\nTIME INFO:")
        print(f"  UTC time: {now_utc.isoformat()}")
        print(f"  UK time:  {now_uk.isoformat()}")
        print(f"  BST active: {is_british_summer_time}")
        logger.info(f"Current time - UTC: {now_utc.isoformat()}, UK: {now_uk.isoformat()}, BST active: {is_british_summer_time}")
        
        # For Render free plan: check for missed reminders due to spin-down
        # Look back up to 6 hours to catch any reminders we might have missed
        # This will help recover after app spin-down periods
        catchup_hours = 6  # Look back this many hours for missed reminders
        
        # Get current UK hour and calculate the range for our query
        current_uk_hour = now_uk.replace(minute=0, second=0, microsecond=0)
        catchup_start_uk = current_uk_hour - timedelta(hours=catchup_hours)
        
        # Convert back to UTC for database query
        utc_hour_start = catchup_start_uk - timedelta(hours=uk_offset)
        utc_hour_end = current_uk_hour + timedelta(hours=1) - timedelta(hours=uk_offset)
        
        print(f"\nQUERY PARAMETERS (WITH CATCHUP):")
        print(f"  Current UK hour: {current_uk_hour.hour}:00")
        print(f"  Catchup range: {catchup_start_uk.isoformat()} to {current_uk_hour.isoformat()}")
        print(f"  UTC query range: {utc_hour_start.isoformat()} to {utc_hour_end.isoformat()}")
        logger.info(f"Checking reminders with catchup - looking back {catchup_hours} hours")
        logger.info(f"UTC query range: {utc_hour_start.isoformat()} to {utc_hour_end.isoformat()}")
        
        # Query for reminders within our range
        print(f"\nQUERYING DATABASE...")
        query = f"""
            SELECT * FROM reminders
            JOIN tasks ON reminders.task_id = tasks.id
            WHERE reminder_time >= '{utc_hour_start.isoformat()}'
            AND reminder_time < '{utc_hour_end.isoformat()}'
            AND tasks.completed = false
        """
        print(f"  Query (simplified): {query}")
        
        try:
            reminders_result = (
                supabase.table(f"{TABLE_PREFIX}reminders")
                .select("*, tasks(*)")
                .gte("reminder_time", utc_hour_start.isoformat())
                .lt("reminder_time", utc_hour_end.isoformat())
                .execute()
            )
            
            reminders = reminders_result.data
            print(f"\nRESULTS:")
            print(f"  Found {len(reminders)} reminders in the catchup window")
            logger.info(f"Found {len(reminders)} reminders in the catchup window")
        except Exception as query_error:
            # Handle the case when the reminders table doesn't exist
            error_str = str(query_error)
            if "relation \"public.reminders\" does not exist" in error_str:
                print("  Error: Reminders table doesn't exist yet.")
                logger.error("Reminders table doesn't exist yet.")
                # No reminders to process this time
                reminders = []
            else:
                # Re-raise other errors
                print(f"  ❌ Error querying reminders: {error_str}")
                logger.error(f"Error querying reminders: {error_str}")
                raise query_error
        
        # Check if the processed_reminders table exists (but don't try to create it)
        processed_table_exists = True
        try:
            # Try checking the table
            test_result = supabase.table(f"{TABLE_PREFIX}processed_reminders").select("count").limit(1).execute()
            print(f"  Processed reminders table is accessible")
        except Exception as table_error:
            error_message = str(table_error)
            processed_table_exists = False
            print(f"  The processed_reminders table doesn't exist. Please create it manually with SQL:")
            print(f"""  
CREATE TABLE IF NOT EXISTS processed_reminders (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    reminder_id UUID REFERENCES reminders(id) ON DELETE CASCADE,
    processed_at TIMESTAMP WITH TIME ZONE NOT NULL,
    message_id TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_processed_reminders_reminder_id ON processed_reminders(reminder_id);
            """)
            logger.warning(f"The processed_reminders table doesn't exist: {error_message}")
            logger.warning(f"Please create the processed_reminders table manually in Supabase SQL editor.")
        
        # Add a processed status tracker to avoid duplicate notifications
        # Check last processed reminder time in database
        try:
            processed_status = (
                supabase.table(f"{TABLE_PREFIX}app_status")
                .select("*")
                .eq("name", "last_processed_time")
                .execute()
            ).data
            
            if processed_status and len(processed_status) > 0:
                last_processed_time = datetime.fromisoformat(processed_status[0]["value"].replace('Z', '+00:00'))
                print(f"  Last processed time: {last_processed_time.isoformat()}")
            else:
                # If no record exists, create one with a default time
                default_time = now_utc - timedelta(hours=catchup_hours)
                last_processed_time = default_time
                print(f"  No last processed time found, defaulting to {catchup_hours} hours ago")
                
                supabase.table(f"{TABLE_PREFIX}app_status").insert({
                    "name": "last_processed_time",
                    "value": default_time.isoformat()
                }).execute()
        except Exception as e:
            # If table doesn't exist yet, create it
            print(f"  Error getting last processed time: {str(e)}")
            print(f"  Creating app_status table if needed...")
            
            try:
                # Try to create the table if it doesn't exist
                supabase.table(f"{TABLE_PREFIX}app_status").insert({
                    "name": "last_processed_time",
                    "value": (now_utc - timedelta(hours=catchup_hours)).isoformat()
                }).execute()
                
                last_processed_time = now_utc - timedelta(hours=catchup_hours)
                print(f"  Created new last_processed_time record")
            except Exception as table_e:
                print(f"  Could not create app_status: {str(table_e)}")
                # Default to processing all reminders in our window
                last_processed_time = now_utc - timedelta(hours=catchup_hours)
        
        if len(reminders) > 0:
            print(f"\nREMINDER DETAILS:")
            for i, reminder in enumerate(reminders):
                # Access task data using the task key
                task = reminder.get("tasks", {})
                reminder_time = datetime.fromisoformat(reminder.get("reminder_time").replace('Z', '+00:00'))
                time_ago = now_utc - reminder_time
                hours_ago = time_ago.total_seconds() / 3600
                
                print(f"  {i+1}. Task: {task.get('title', 'Unknown')}")
                print(f"     Reminder time: {reminder.get('reminder_time', 'Unknown')} ({hours_ago:.1f} hours ago)")
                print(f"     Task completed: {task.get('completed', False)}")
                print(f"     Priority: {task.get('priority', 'Unknown')}")
                
                # Also check and log if reminder is already processed
                if processed_table_exists:
                    reminder_id = reminder.get("id")
                    already_processed = check_reminder_processed(reminder_id)
                    if already_processed:
                        print(f"     ⚠️ Already processed: Yes")
                
            logger.info(f"Reminder data: {json.dumps(reminders, default=str)}")
        else:
            print("  No reminders found in the catchup window")
        
        # Process each reminder
        sent_count = 0
        skipped_already_processed = 0
        if len(reminders) > 0:
            print(f"\nPROCESSING REMINDERS:")
            
        for i, reminder in enumerate(reminders):
            # Access task data using the task key
            task = reminder.get("tasks", {})
            if task and not task.get("completed", False):
                reminder_time = datetime.fromisoformat(reminder.get("reminder_time").replace('Z', '+00:00'))
                reminder_id = reminder.get("id")
                
                # Check if this reminder has already been processed
                if processed_table_exists:
                    already_processed = check_reminder_processed(reminder_id)
                    if already_processed:
                        print(f"  Skipping reminder {i+1}: {task.get('title')} - Already processed (found in processed_reminders)")
                        logger.info(f"Skipping reminder {reminder_id} for task '{task.get('title')}' - Already processed")
                        skipped_already_processed += 1
                        continue
                    
                # Process this reminder if it's due (in the past or current hour)
                if reminder_time <= now_utc or (
                    reminder_time.replace(minute=0, second=0, microsecond=0) == 
                    now_utc.replace(minute=0, second=0, microsecond=0)
                ):
                    print(f"  Processing reminder {i+1}: {task.get('title')} at {reminder_time.isoformat()}")
                    logger.info(f"Processing reminder for task: {task.get('title')} at {reminder_time.isoformat()}")
                    logger.info(f"Task details: {json.dumps(task, default=str)}")
                    
                    # Get the task's phone number or use the default
                    recipient = task.get("phone_number", RECIPIENT_USER_KEY)
                    print(f"  Sending to: {recipient}")
                    logger.info(f"Sending reminder message to recipient: {recipient}")
                    
                    # Get the task's due time
                    due_time = datetime.fromisoformat(task.get("due_time").replace('Z', '+00:00'))
                    
                    # Check if the reminder is exactly at the task's due time
                    is_due_time_reminder = reminder_time.replace(second=0, microsecond=0) == due_time.replace(second=0, microsecond=0)
                    if is_due_time_reminder:
                        print(f"  ⚠️ This is an URGENT reminder - task is due now!")
                        logger.info(f"URGENT reminder - task is due now at {reminder_time.isoformat()}")
                    
                    # Check if Pushover is configured
                    send_pushover = True if PUSHOVER_API_TOKEN and PUSHOVER_USER_KEY else False
                    
                    message_results = {}
                    
                    # Send Pushover notification if configured
                    if send_pushover:
                        pushover_message_id = send_pushover_notification(
                            task_title=task.get("title"),
                            task_priority=task.get("priority"),
                            due_time=due_time,
                            reminder_time=reminder_time,
                            recipient=recipient
                        )
                        
                        if pushover_message_id:
                            message_results["pushover"] = pushover_message_id
                            print(f"  ✅ Pushover notification sent successfully, ID: {pushover_message_id}")
                            sent_count += 1
                            
                            # Mark reminder as processed if the table exists
                            if processed_table_exists:
                                if mark_reminder_processed(reminder_id, pushover_message_id, now_utc):
                                    print(f"  ✅ Marked reminder {reminder_id} as processed")
                                else:
                                    print(f"  ⚠️ Failed to mark reminder {reminder_id} as processed")
                            else:
                                print(f"  ⚠️ Cannot mark as processed - processed_reminders table doesn't exist")
                                logger.warning(f"Cannot mark reminder {reminder_id} as processed - table doesn't exist")
                        else:
                            print(f"  ❌ Failed to send Pushover notification")
                    
                    logger.info(f"Reminder messages sent: {json.dumps(message_results)}")
                else:
                    print(f"  Skipping reminder {i+1}: {task.get('title')} - Not due yet ({reminder_time.isoformat()})")
            else:
                reason = "Task already completed" if task and task.get("completed", False) else "Task not found"
                print(f"  Skipping reminder {i+1}: {reason}")
                logger.info(f"Skipping reminder {reminder.get('id')} - Task completed or missing: {bool(task)}, Completed: {task.get('completed', False) if task else 'N/A'}")
        
        # Update the last processed time
        try:
            supabase.table(f"{TABLE_PREFIX}app_status").update({"value": now_utc.isoformat()}).eq("name", "last_processed_time").execute()
            print(f"  Updated last processed time to: {now_utc.isoformat()}")
        except Exception as e:
            print(f"  Error updating last processed time: {str(e)}")
        
        print("\n" + "-"*80)
        print(f"- REMINDER CHECK COMPLETED: {sent_count} sent, {skipped_already_processed} already processed")
        print("-"*80)
        logger.info(f"Reminder check completed successfully: {sent_count} sent, {skipped_already_processed} already processed")
        
        # Store the counts as attributes of the function object for the endpoint to access
        check_upcoming_reminders.last_found_count = len(reminders)
        check_upcoming_reminders.last_sent_count = sent_count
        check_upcoming_reminders.last_skipped_count = skipped_already_processed
        
        return True
    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}")
        import traceback
        print(traceback.format_exc())
        logger.error(f"Error checking upcoming reminders: {str(e)}", exc_info=True)
        
        # Set counts to 0 in case of failure
        check_upcoming_reminders.last_found_count = 0
        check_upcoming_reminders.last_sent_count = 0
        check_upcoming_reminders.last_skipped_count = 0
        
        return False

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

def get_reminder_suggestions(task_title: str, priority: str, due_date: str, created_at: str) -> List[datetime]:
    try:
        client = get_openai_client()
        if not client:
            logger.warning("OpenAI client not available, using fallback reminder suggestion")
            # Return a single reminder at 75% of the time between creation and due date if OpenAI fails
            due_date_dt = datetime.fromisoformat(due_date.replace('Z', '+00:00'))
            created_at_dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
            time_diff = due_date_dt - created_at_dt
            reminder_time = created_at_dt + (time_diff * 0.75)
            return [reminder_time]

        prompt = f"""Given:
Task: {task_title}
Priority: {priority}
Due: {due_date}Z
Now: {created_at}Z

Rules:
- Complex tasks (update CV) → 3-4 reminders
- Medium tasks (clean garage) → 2-3 reminders
- Quick tasks (buy wine) → 1-2 reminders
- Only 08:00-22:00 UK time
- Space evenly
- IMPORTANT: Each reminder time must be unique

Output: JSON array only."""
        
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "Complex tasks (CV/report): 3-4 reminders. Medium (garage/files): 2-3. Quick (calls/errands): 1-2. 08:00-22:00 UK only for reminder times. Space evenly. Return JSON array of ISO dates."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=150
        )
        
        reminder_times = json.loads(response.choices[0].message.content)
        # Convert to datetime objects
        reminder_datetimes = [datetime.fromisoformat(time.replace('Z', '+00:00')) for time in reminder_times]
        
        # Remove duplicates by converting to ISO strings and using a set
        unique_times_iso = set()
        unique_datetimes = []
        
        for dt in reminder_datetimes:
            iso_str = dt.isoformat()
            if iso_str not in unique_times_iso:
                unique_times_iso.add(iso_str)
                unique_datetimes.append(dt)
        
        return unique_datetimes
    except Exception as e:
        print(f"Error getting reminder suggestions: {str(e)}")
        # Return a single reminder at 75% of the time between creation and due date if LLM fails
        due_date_dt = datetime.fromisoformat(due_date.replace('Z', '+00:00'))
        created_at_dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
        time_diff = due_date_dt - created_at_dt
        reminder_time = created_at_dt + (time_diff * 0.75)
        return [reminder_time]

@app.post("/api/tasks")
async def create_task(task: Task):
    try:
        # Check if the due_time is in the past
        now = datetime.now(timezone.utc)
        if task.due_time <= now:
            raise HTTPException(
                status_code=400, 
                detail="Task due time cannot be in the past"
            )
            
        # Create the task
        task_data = {
            "title": task.title,
            "due_time": task.due_time.isoformat(),
            "priority": task.priority
        }
        
        # Add phone number if provided (optional now)
        if task.phone_number:
            task_data["phone_number"] = task.phone_number
            
        task_result = supabase.table(f"{TABLE_PREFIX}tasks").insert(task_data).execute()
        task_id = task_result.data[0]['id']
        
        # Note: Reminders table should already exist, if not handle gracefully
        if task.single_reminder:
            # Calculate single reminder time
            reminder_time = task.due_time - timedelta(hours=task.hours_before)
            reminder_data = {
                "task_id": task_id,
                "reminder_time": reminder_time.isoformat()
            }
            supabase.table(f"{TABLE_PREFIX}reminders").insert(reminder_data).execute()
        else:
            # Get reminder suggestions from LLM
            reminder_times = get_reminder_suggestions(
                task.title,
                task.priority,
                task.due_time.isoformat(),
                datetime.now(timezone.utc).isoformat()
            )
            
            # Set to track already added reminder times
            added_reminder_times = set()
            
            # Create reminders
            for reminder_time in reminder_times:
                # Check for duplicates
                iso_time = reminder_time.isoformat()
                if iso_time in added_reminder_times:
                    logger.info(f"Skipping duplicate reminder time: {iso_time}")
                    continue
                    
                # Add to tracking set
                added_reminder_times.add(iso_time)
                
                # Create reminder
                reminder_data = {
                    "task_id": task_id,
                    "reminder_time": iso_time
                }
                supabase.table(f"{TABLE_PREFIX}reminders").insert(reminder_data).execute()
        
        return task_result.data[0]
    except HTTPException as e:
        # Re-raise HTTP exceptions
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.patch("/api/tasks/{task_id}/complete")
async def complete_task(task_id: str):
    try:
        # Update the task as completed
        result = (
            supabase.table(f"{TABLE_PREFIX}tasks")
            .update({
                "completed": True,
                "completed_at": datetime.now(timezone.utc).isoformat()
            })
            .eq("id", task_id)
            .execute()
        )
        return {"message": "Task marked as completed"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/tasks")
async def get_tasks():
    try:
        # Get incomplete tasks first, ordered by due_time and priority
        incomplete_tasks_result = (
            supabase.table(f"{TABLE_PREFIX}tasks")
            .select("*")
            .eq("completed", False)
            .order('due_time', desc=False)
            .execute()
        )
        incomplete_tasks = incomplete_tasks_result.data

        # Get completed tasks, ordered by completion time
        completed_tasks_result = (
            supabase.table(f"{TABLE_PREFIX}tasks")
            .select("*")
            .eq("completed", True)
            .order('completed_at', desc=True)
            .limit(10)  # Limit to last 10 completed tasks
            .execute()
        )
        completed_tasks = completed_tasks_result.data

        # Sort incomplete tasks by priority
        priority_order = {"High": 0, "Medium": 1, "Low": 2}
        incomplete_tasks.sort(key=lambda x: (x["due_time"], priority_order.get(x["priority"], 3)))

        # Get all task IDs
        all_task_ids = [task["id"] for task in incomplete_tasks + completed_tasks]
        
        # Fetch reminders for all tasks in a single query if there are any tasks
        all_reminders = {}
        if all_task_ids:
            try:
                reminders_result = supabase.table(f"{TABLE_PREFIX}reminders").select("*").in_("task_id", all_task_ids).execute()
                
                # Group reminders by task_id for easier assignment
                for reminder in reminders_result.data:
                    task_id = reminder["task_id"]
                    if task_id not in all_reminders:
                        all_reminders[task_id] = []
                    all_reminders[task_id].append(reminder)
            except Exception as reminder_error:
                # Handle the case when reminders table doesn't exist
                logger.error(f"Error fetching reminders: {str(reminder_error)}")
                # Continue without reminders if there's an error
        
        # Assign reminders to each task
        for task in incomplete_tasks + completed_tasks:
            task["reminders"] = all_reminders.get(task["id"], [])

        return {
            "incomplete_tasks": incomplete_tasks,
            "completed_tasks": completed_tasks
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/tasks/{task_id}")
async def delete_task(task_id: str):
    try:
        # Delete associated reminders first
        supabase.table(f"{TABLE_PREFIX}reminders").delete().eq("task_id", task_id).execute()
        # Then delete the task
        result = supabase.table(f"{TABLE_PREFIX}tasks").delete().eq("id", task_id).execute()
        return {"message": "Task and associated reminders deleted successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class UpdateTaskRequest(BaseModel):
    due_time: Optional[str] = None
    title: Optional[str] = None
    priority: Optional[str] = None

@app.patch("/api/tasks/{task_id}")
async def update_task(task_id: str, request: UpdateTaskRequest):
    try:
        # Build update data from provided fields
        update_data = {}
        if request.due_time is not None:
            update_data["due_time"] = request.due_time
        if request.title is not None:
            update_data["title"] = request.title
        if request.priority is not None:
            update_data["priority"] = request.priority
        
        if not update_data:
            raise HTTPException(status_code=400, detail="No fields to update")
        
        # Update the task
        result = (
            supabase.table(f"{TABLE_PREFIX}tasks")
            .update(update_data)
            .eq("id", task_id)
            .execute()
        )
        
        if not result.data:
            raise HTTPException(status_code=404, detail="Task not found")
        
        return {"message": "Task updated successfully", "task": result.data[0]}
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class UpdateDueDateRequest(BaseModel):
    current_due_date: str
    task_title: str

@app.patch("/api/tasks/{task_id}/update-due-date")
async def update_task_due_date(task_id: str, request: UpdateDueDateRequest):
    try:
        # Get OpenAI suggestion for new due date
        now = datetime.now(timezone.utc)
        current_date = datetime.fromisoformat(request.current_due_date.replace('Z', '+00:00'))
        
        # Try to get OpenAI suggestion, fallback to simple logic if not available
        client = get_openai_client()
        suggested_date_utc = None
        
        if client:
            try:
                prompt = f"""Task: "{request.task_title}"
Current due date: {current_date.strftime('%Y-%m-%d %H:%M')}
Current time: {now.strftime('%Y-%m-%d %H:%M')}

Suggest a better due date for this task. Consider:
- If overdue, suggest within next 1-3 days
- If due soon, extend by appropriate amount based on task complexity
- Keep reasonable working hours (9 AM - 6 PM)
- Return only the new date in format: YYYY-MM-DD HH:MM"""
                
                response = client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[
                        {"role": "system", "content": "You are a helpful assistant that suggests realistic due dates for tasks. Always respond with only the date in YYYY-MM-DD HH:MM format."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.3,
                    max_tokens=50
                )
                
                suggested_date_str = response.choices[0].message.content.strip()
                
                # Parse the suggested date
                try:
                    # Try to parse the date
                    suggested_date = datetime.strptime(suggested_date_str, '%Y-%m-%d %H:%M')
                    # Convert to UTC timezone
                    suggested_date_utc = suggested_date.replace(tzinfo=timezone.utc)
                except ValueError:
                    logger.warning(f"Failed to parse OpenAI suggested date: {suggested_date_str}")
                    suggested_date_utc = None
            except Exception as e:
                logger.error(f"OpenAI request failed: {str(e)}")
                suggested_date_utc = None
        
        # Fallback logic if OpenAI is not available or failed
        if suggested_date_utc is None:
            logger.info("Using fallback date calculation")
            # Simple fallback: add 2 days to current date if parsing fails or OpenAI unavailable
            suggested_date_utc = now + timedelta(days=2)
            suggested_date_utc = suggested_date_utc.replace(hour=14, minute=0, second=0, microsecond=0)
        
        # Ensure the new date is not in the past
        if suggested_date_utc <= now:
            suggested_date_utc = now + timedelta(days=1)
            suggested_date_utc = suggested_date_utc.replace(hour=14, minute=0, second=0, microsecond=0)
        
        # Update the task's due date and mark as edited
        update_data = {
            "due_time": suggested_date_utc.isoformat()
            # Remove edited fields until they are added to the database
            # "edited": True,
            # "edited_at": now.isoformat()
        }
        
        result = (
            supabase.table(f"{TABLE_PREFIX}tasks")
            .update(update_data)
            .eq("id", task_id)
            .execute()
        )
        
        if not result.data:
            raise HTTPException(status_code=404, detail="Task not found")
        
        return {
            "message": "Due date updated successfully",
            "new_due_date": suggested_date_utc.isoformat(),
            "suggested_by_ai": bool(client)
        }
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# New endpoint to test Pushover notification
@app.post("/api/test-pushover")
async def test_pushover_message():
    try:
        # Always use the default user key
        recipient = RECIPIENT_USER_KEY
        if not recipient:
            logger.error("Default recipient user key not configured")
            raise HTTPException(status_code=400, detail="Default recipient user key not configured")
            
        # Log Pushover configuration for debugging
        logger.info(f"Pushover test configuration:")
        logger.info(f"PUSHOVER_API_TOKEN: {'Configured' if PUSHOVER_API_TOKEN else 'Missing'}")
        logger.info(f"PUSHOVER_USER_KEY: {'Configured' if PUSHOVER_USER_KEY else 'Missing'}")
        logger.info(f"RECIPIENT_USER_KEY: {'*****' + recipient[-5:] if recipient else 'Missing'}")
        
        logger.info(f"Sending test Pushover notification to user key ending in {recipient[-5:] if recipient else 'Unknown'}")
        
        # Get current time in UTC and calculate due time 1 hour from now
        now_utc = datetime.now(timezone.utc)
        test_due_time = now_utc + timedelta(hours=1)
        
        # Send a non-urgent notification
        normal_message_id = send_pushover_notification(
            task_title="Test Regular Reminder",
            task_priority="Medium",
            due_time=test_due_time,
            reminder_time=now_utc,  # Current time as reminder time (not equal to due time)
            recipient=recipient
        )
        
        # Also send an urgent notification (reminder time = due time)
        urgent_message_id = send_pushover_notification(
            task_title="Test URGENT Reminder",
            task_priority="High",
            due_time=now_utc,  # Due time is now
            reminder_time=now_utc,  # Reminder time is also now (indicating urgency)
            recipient=recipient
        )
        
        message_ids = []
        if normal_message_id:
            message_ids.append(normal_message_id)
            logger.info(f"Regular test Pushover notification sent successfully with ID: {normal_message_id}")
        
        if urgent_message_id:
            message_ids.append(urgent_message_id)
            logger.info(f"Urgent test Pushover notification sent successfully with ID: {urgent_message_id}")
        
        if message_ids:
            # Get the UK time representation for the response
            is_bst_active = is_bst(test_due_time)
            uk_time = test_due_time + timedelta(hours=1 if is_bst_active else 0)
            time_zone = "BST" if is_bst_active else "GMT"
            
            return {
                "message": f"Test Pushover notifications sent successfully ({len(message_ids)} messages)", 
                "message_ids": message_ids, 
                "to": recipient[-5:] if recipient else "Unknown",
                "time_info": {
                    "utc_time": test_due_time.isoformat(),
                    "uk_time": uk_time.isoformat(),
                    "time_zone": time_zone
                }
            }
        else:
            logger.error("Failed to send Pushover notifications - no message IDs returned")
            raise HTTPException(status_code=500, detail="Failed to send Pushover notifications - check server logs")
    except Exception as e:
        import traceback
        error_detail = str(e)
        stack_trace = traceback.format_exc()
        logger.error(f"Error in test_pushover_message: {error_detail}")
        logger.error(f"Stack trace: {stack_trace}")
        raise HTTPException(status_code=500, detail=f"Error: {error_detail}")

# Add a new endpoint for checking reminders with security
@app.post("/api/check-reminders")
async def check_reminders_endpoint(request: Request):
    # Added highly visible debug messages
    print("\n" + "*"*80)
    print("* CHECK-REMINDERS ENDPOINT CALLED")
    print("*"*80)
    
    # Get verification token from environment
    verify_token = os.getenv("VERIFY_TOKEN")
    
    # Get authorization header
    auth_header = request.headers.get("Authorization")
    
    # Print all headers for debugging
    print("\nRequest headers:")
    for header, value in request.headers.items():
        print(f"  {header}: {value[:20]}{'...' if len(value) > 20 else ''}")
    
    logger.info(f"Received check-reminders request with auth: {auth_header[:15] + '...' if auth_header else 'None'}")
    
    # Verify the token for security (ensure only the cron job can trigger this)
    if verify_token and (not auth_header or auth_header != f"Bearer {verify_token}"):
        print(f"\n❌ UNAUTHORIZED - Expected 'Bearer {verify_token}', got '{auth_header}'")
        logger.warning(f"Unauthorized access attempt to check-reminders endpoint")
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    print(f"\n✅ AUTHORIZATION SUCCESSFUL")
    
    try:
        print("\nStarting reminder check...")
        success = check_upcoming_reminders()
        
        # Get counts from global variables that will be set in check_upcoming_reminders
        reminders_found = getattr(check_upcoming_reminders, 'last_found_count', 0)
        sent_count = getattr(check_upcoming_reminders, 'last_sent_count', 0)
        skipped_count = getattr(check_upcoming_reminders, 'last_skipped_count', 0)
        
        result = {
            "message": "Reminders checked successfully", 
            "timestamp": datetime.now(timezone.utc).isoformat(), 
            "success": success,
            "details": {
                "reminders_found": reminders_found,
                "notifications_sent": sent_count,
                "already_processed": skipped_count
            }
        }
        print(f"\n✅ REMINDER CHECK COMPLETED: {json.dumps(result)}")
        logger.info(f"check-reminders endpoint completed: {json.dumps(result)}")
        return result
    except Exception as e:
        error_msg = str(e)
        print(f"\n❌ ERROR IN REMINDER CHECK: {error_msg}")
        logger.error(f"Error in check-reminders endpoint: {error_msg}", exc_info=True)
        raise HTTPException(status_code=500, detail=error_msg)

@app.on_event("startup")
async def startup_event():
    """Simple startup without migrations"""
    try:
        logger.info("Server starting up...")
        logger.info("Startup completed successfully")
    except Exception as e:
        logger.error(f"Error during startup: {str(e)}")
        # Don't fail startup

@app.get("/")
async def health_check():
    return {
        "status": "ok", 
        "message": "Task Reminder API is running",
        "supabase_configured": bool(supabase_url and supabase_key),
        "openai_configured": bool(get_openai_client()),
        "pushover_configured": bool(PUSHOVER_API_TOKEN and PUSHOVER_USER_KEY)
    }

@app.get("/api/ping")
async def ping():
    """Simple endpoint that returns a 200 OK status to keep the server alive"""
    logger.info("Received ping request to keep server alive")
    return {"status": "alive", "timestamp": datetime.now(timezone.utc).isoformat()}

@app.get("/api/cron-ping")
async def cron_ping():
    """Endpoint for external cron services to ping to keep the server alive"""
    logger.info("Received cron ping to keep server alive")
    # Perform a small dummy database operation to keep connections warm
    try:
        tasks_count = supabase.table(f"{TABLE_PREFIX}tasks").select("id", count="exact").execute()
        logger.info(f"Current tasks count: {tasks_count.count if hasattr(tasks_count, 'count') else 'unknown'}")
    except Exception as e:
        logger.warning(f"Error during cron ping database operation: {str(e)}")
    
    return {
        "status": "alive", 
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "message": "Cron ping received and processed"
    }

@app.post("/api/cron-ping")
async def cron_ping_post():
    """POST endpoint for external cron services to ping to keep the server alive"""
    logger.info("Received POST cron ping to keep server alive")
    # Perform a small dummy database operation to keep connections warm
    try:
        tasks_count = supabase.table(f"{TABLE_PREFIX}tasks").select("id", count="exact").execute()
        logger.info(f"Current tasks count: {tasks_count.count if hasattr(tasks_count, 'count') else 'unknown'}")
    except Exception as e:
        logger.warning(f"Error during cron ping database operation: {str(e)}")
    
    return {
        "status": "alive", 
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "message": "Cron ping received and processed"
    }

@app.head("/api/cron-ping")
async def cron_ping_head():
    """HEAD endpoint for UptimeRobot free plan to ping to keep the server alive"""
    logger.info("Received HEAD cron ping to keep server alive (likely from UptimeRobot)")
    # For HEAD method, we don't need to return a body, just a successful status code
    return None

def check_reminder_processed(reminder_id):
    """
    Check if a reminder has already been processed by querying the processed_reminders table
    Returns True if already processed, False otherwise
    """
    try:
        # First print the reminder_id for debugging
        print(f"  Checking if reminder {reminder_id} has been processed")
        logger.info(f"Checking processed status for reminder: {reminder_id}")
        
        # Check if this specific reminder has been processed (assuming table exists)
        processed_result = (
            supabase.table(f"{TABLE_PREFIX}processed_reminders")
            .select("*")
            .eq("reminder_id", reminder_id)
            .execute()
        )
        
        is_processed = len(processed_result.data) > 0
        print(f"  Reminder {reminder_id} processed status: {is_processed}")
        logger.info(f"Reminder {reminder_id} processed status: {is_processed}")
        
        if is_processed and len(processed_result.data) > 0:
            processed_time = processed_result.data[0].get("processed_at", "unknown")
            print(f"  Reminder {reminder_id} was previously processed at {processed_time}")
            logger.info(f"Reminder {reminder_id} was previously processed at {processed_time}")
        
        # Return the processed status
        return is_processed
    except Exception as e:
        error_message = str(e)
        print(f"  Error checking if reminder {reminder_id} is processed: {error_message}")
        logger.warning(f"Error checking if reminder {reminder_id} is processed: {error_message}")
        
        # If the table doesn't exist, we assume not processed, but don't try to create it here
        # The table should be created manually in Supabase SQL editor
        if "relation" in error_message and "does not exist" in error_message:
            print(f"  The processed_reminders table doesn't exist yet. Please create it using the SQL provided.")
            logger.warning(f"The processed_reminders table doesn't exist yet. Please create it manually.")
        
        # If we can't check, assume not processed to be safe
        return False

def mark_reminder_processed(reminder_id, message_id=None, now_utc=None):
    """
    Mark a reminder as processed in the processed_reminders table
    Returns True if successful, False otherwise
    """
    if now_utc is None:
        now_utc = datetime.now(timezone.utc)
    
    print(f"  Attempting to mark reminder {reminder_id} as processed")
    logger.info(f"Attempting to mark reminder {reminder_id} as processed")
    
    # First check if already processed to avoid duplicate entries
    try:
        already_processed = check_reminder_processed(reminder_id)
        if already_processed:
            print(f"  Reminder {reminder_id} already marked as processed, skipping")
            logger.info(f"Reminder {reminder_id} already marked as processed, skipping")
            return True
    except Exception as check_error:
        error_message = str(check_error)
        print(f"  Error checking if reminder {reminder_id} is already processed: {error_message}")
        logger.warning(f"Error checking if reminder {reminder_id} is already processed: {error_message}")
        # Continue anyway to try to mark it
        
    try:
        # Prepare data for insertion
        data = {
            "reminder_id": reminder_id,
            "processed_at": now_utc.isoformat(),
        }
        if message_id:
            data["message_id"] = message_id
        
        print(f"  Marking reminder {reminder_id} as processed at {now_utc.isoformat()}")
        logger.info(f"Marking reminder {reminder_id} as processed with data: {json.dumps(data, default=str)}")
        
        # Try to insert the record
        insert_result = supabase.table(f"{TABLE_PREFIX}processed_reminders").insert(data).execute()
        
        print(f"  ✅ Successfully marked reminder {reminder_id} as processed")
        logger.info(f"Successfully marked reminder {reminder_id} as processed")
        
        # Double check insertion worked by querying the table
        verify_result = (
            supabase.table(f"{TABLE_PREFIX}processed_reminders")
            .select("*")
            .eq("reminder_id", reminder_id)
            .execute()
        )
        if len(verify_result.data) > 0:
            print(f"  ✅ Verified reminder {reminder_id} is marked as processed")
            logger.info(f"Verified reminder {reminder_id} is marked as processed")
        else:
            print(f"  ⚠️ Could not verify reminder {reminder_id} was marked as processed")
            logger.warning(f"Could not verify reminder {reminder_id} was marked as processed")
        
        return True
    except Exception as e:
        error_message = str(e)
        print(f"  ❌ Error marking reminder {reminder_id} as processed: {error_message}")
        logger.error(f"Error marking reminder {reminder_id} as processed: {error_message}")
        
        # If table doesn't exist, inform user to create it
        if "relation" in error_message and "does not exist" in error_message:
            print(f"  ❌ The processed_reminders table doesn't exist. Please create it manually using SQL")
            logger.error(f"The processed_reminders table doesn't exist. Please create it manually using SQL.")
            print(f"""  
CREATE TABLE IF NOT EXISTS processed_reminders (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    reminder_id UUID REFERENCES reminders(id) ON DELETE CASCADE,
    processed_at TIMESTAMP WITH TIME ZONE NOT NULL,
    message_id TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_processed_reminders_reminder_id ON processed_reminders(reminder_id);
            """)
        
        return False

# Add an admin endpoint to reset the processed reminders
@app.post("/api/admin/reset-processed-reminders")
async def reset_processed_reminders(request: Request):
    """Admin endpoint to reset processed reminders so they can be sent again"""
    print("\n" + "*"*80)
    print("* RESET PROCESSED REMINDERS ENDPOINT CALLED")
    print("*"*80)
    
    # Get verification token from environment
    verify_token = os.getenv("VERIFY_TOKEN", "clemencefranklin")  # Default for local testing
    
    # Get authorization header
    auth_header = request.headers.get("Authorization")
    
    # Print all headers for debugging
    print("\nRequest headers:")
    for header, value in request.headers.items():
        print(f"  {header}: {value[:20]}{'...' if len(value) > 20 else ''}")
    
    logger.info(f"Received reset-processed-reminders request with auth: {auth_header[:15] + '...' if auth_header else 'None'}")
    
    # Verify the token for security
    if verify_token and (not auth_header or auth_header != f"Bearer {verify_token}"):
        print(f"\n❌ UNAUTHORIZED - Expected 'Bearer {verify_token}', got '{auth_header}'")
        logger.warning(f"Unauthorized access attempt to reset-processed-reminders endpoint")
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    print(f"\n✅ AUTHORIZATION SUCCESSFUL")
    logger.info(f"Authorization successful for reset-processed-reminders endpoint")
    
    try:
        # Try to clear the processed_reminders table
        try:
            # Try to delete all records
            print(f"  Deleting all records from processed_reminders table")
            deleted_result = supabase.table(f"{TABLE_PREFIX}processed_reminders").delete().neq("id", "dummy").execute()
            processed_cleared = True
            cleared_count = len(deleted_result.data)
            print(f"  Deleted {cleared_count} processed reminder records")
        except Exception as e:
            error_message = str(e)
            processed_cleared = False
            cleared_count = 0
            print(f"  Could not clear processed_reminders table: {error_message}")
            logger.warning(f"Could not clear processed_reminders table: {error_message}")
            
            # If table doesn't exist, inform the user
            if "relation" in error_message and "does not exist" in error_message:
                print(f"  The processed_reminders table doesn't exist yet. Please create it using SQL:")
                print(f"""  
CREATE TABLE IF NOT EXISTS processed_reminders (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    reminder_id UUID REFERENCES reminders(id) ON DELETE CASCADE,
    processed_at TIMESTAMP WITH TIME ZONE NOT NULL,
    message_id TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_processed_reminders_reminder_id ON processed_reminders(reminder_id);
                """)
        
        # Also reset the last_processed_time in app_status as a fallback
        reset_time = datetime.now(timezone.utc) - timedelta(hours=24)
        try:
            print(f"  Resetting last_processed_time to {reset_time.isoformat()}")
            
            # First check if the record exists
            app_status_result = (
                supabase.table(f"{TABLE_PREFIX}app_status")
                .select("*")
                .eq("name", "last_processed_time")
                .execute()
            )
            
            if app_status_result.data and len(app_status_result.data) > 0:
                # Update existing record
                update_result = (
                    supabase.table(f"{TABLE_PREFIX}app_status")
                    .update({"value": reset_time.isoformat()})
                    .eq("name", "last_processed_time")
                    .execute()
                )
                print(f"  Updated existing last_processed_time record")
            else:
                # Insert new record
                insert_result = (
                    supabase.table(f"{TABLE_PREFIX}app_status")
                    .insert({"name": "last_processed_time", "value": reset_time.isoformat()})
                    .execute()
                )
                print(f"  Created new last_processed_time record")
            
            time_reset = True
            print(f"  ✅ Successfully reset last_processed_time to {reset_time.isoformat()}")
        except Exception as e:
            error_message = str(e)
            time_reset = False
            print(f"  Could not reset last_processed_time: {error_message}")
            logger.warning(f"Could not reset last_processed_time: {error_message}")
        
        result = {
            "message": "Reminder processing history reset",
            "processed_reminders_cleared": processed_cleared,
            "cleared_count": cleared_count,
            "last_processed_time_reset": time_reset,
            "reset_to": reset_time.isoformat() if time_reset else None,
            "note": "If processed_reminders table doesn't exist, please create it manually in Supabase" if not processed_cleared else None
        }
        
        print("\n" + "-"*80)
        print(f"- REMINDER PROCESSING HISTORY RESET COMPLETED")
        print(f"- Cleared: {cleared_count} records, Time reset: {time_reset}")
        print("-"*80)
        
        logger.info(f"Reset reminder processing history: {json.dumps(result)}")
        
        return result
    except Exception as e:
        error_msg = str(e)
        print(f"\n❌ ERROR RESETTING REMINDER PROCESSING HISTORY: {error_msg}")
        logger.error(f"Error resetting reminder processing history: {error_msg}", exc_info=True)
        raise HTTPException(status_code=500, detail=error_msg)

@app.post("/api/admin/add-edited-fields")
async def add_edited_fields(request: Request):
    """Admin endpoint to add the edited and edited_at fields to the tasks table"""
    print("\n" + "*"*80)
    print("* ADD EDITED FIELDS ENDPOINT CALLED")
    print("*"*80)
    
    # Get verification token from environment
    verify_token = os.getenv("VERIFY_TOKEN", "clemencefranklin")  # Default for local testing
    
    # Get authorization header
    auth_header = request.headers.get("Authorization")
    
    logger.info(f"Received add-edited-fields request with auth: {auth_header[:15] + '...' if auth_header else 'None'}")
    
    # Verify the token for security
    if verify_token and (not auth_header or auth_header != f"Bearer {verify_token}"):
        print(f"\n❌ UNAUTHORIZED - Expected 'Bearer {verify_token}', got '{auth_header}'")
        logger.warning(f"Unauthorized access attempt to add-edited-fields endpoint")
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    print(f"\n✅ AUTHORIZATION SUCCESSFUL")
    logger.info(f"Authorization successful for add-edited-fields endpoint")
    
    try:
        # SQL to add the edited fields
        sql = f"""
        ALTER TABLE public.{TABLE_PREFIX}tasks 
        ADD COLUMN IF NOT EXISTS edited BOOLEAN DEFAULT FALSE,
        ADD COLUMN IF NOT EXISTS edited_at TIMESTAMP WITH TIME ZONE;
        """
        
        print(f"Adding edited fields to {TABLE_PREFIX}tasks table...")
        print(f"SQL: {sql}")
        
        try:
            # Try to execute the SQL
            result = supabase.rpc("exec_sql", {"query": sql}).execute()
            print(f"✅ Successfully added edited fields to tasks table")
            
            # Verify the fields were added by trying to query them
            test_query = supabase.table(f"{TABLE_PREFIX}tasks").select("id, edited, edited_at").limit(1).execute()
            print(f"✅ Verified that edited fields are accessible")
            
            return {
                "message": "Edited fields added successfully",
                "table": f"{TABLE_PREFIX}tasks",
                "fields_added": ["edited", "edited_at"],
                "success": True
            }
        except Exception as e:
            error_message = str(e)
            print(f"❌ Error adding edited fields: {error_message}")
            logger.error(f"Error adding edited fields: {error_message}")
            
            # Try alternative approach - simple table update
            try:
                print("Trying alternative approach...")
                # First try to query the table to see current structure
                table_info = supabase.table(f"{TABLE_PREFIX}tasks").select("*").limit(1).execute()
                if table_info.data:
                    existing_fields = list(table_info.data[0].keys()) if table_info.data else []
                    print(f"Current table fields: {existing_fields}")
                    
                    if 'edited' not in existing_fields or 'edited_at' not in existing_fields:
                        return {
                            "message": "Fields need to be added manually",
                            "error": error_message,
                            "sql_to_run": sql,
                            "instructions": "Please run this SQL in Supabase SQL editor",
                            "success": False
                        }
                    else:
                        return {
                            "message": "Fields already exist",
                            "table": f"{TABLE_PREFIX}tasks",
                            "existing_fields": existing_fields,
                            "success": True
                        }
                else:
                    raise Exception("Could not query table structure")
            except Exception as e2:
                print(f"❌ Alternative approach also failed: {str(e2)}")
                return {
                    "message": "Failed to add edited fields",
                    "error": f"Primary: {error_message}, Alternative: {str(e2)}",
                    "sql_to_run": sql,
                    "instructions": "Please run this SQL manually in Supabase SQL editor",
                    "success": False
                }
    except Exception as e:
        error_msg = str(e)
        print(f"\n❌ ERROR ADDING EDITED FIELDS: {error_msg}")
        logger.error(f"Error adding edited fields: {error_msg}", exc_info=True)
        raise HTTPException(status_code=500, detail=error_msg)

if __name__ == "__main__":
    import uvicorn
    print(f"Supabase URL configured: {'Yes' if supabase_url else 'No'}")
    print(f"Supabase Key configured: {'Yes' if supabase_key else 'No'}")
    print(f"OpenAI API Key configured: {'Yes' if get_openai_client() else 'No'}")
    print(f"Pushover API configured: {'Yes' if PUSHOVER_API_TOKEN and PUSHOVER_USER_KEY else 'No'}")
    print("\nDatabase Configuration:")
    print(f"- Environment: {'PRODUCTION' if supabase_url else 'DEVELOPMENT'}")
    print("\nServer Usage:")
    print("- Run locally: python server.py")
    print("\nSetup Instructions:")
    print("- Ensure your .env file has the required environment variables")
    uvicorn.run(app, host="0.0.0.0", port=8000) 