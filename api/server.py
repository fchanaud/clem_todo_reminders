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
from openai import OpenAI

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

# Get Supabase credentials - simple approach with a single set
supabase_url = os.getenv("NEXT_PUBLIC_SUPABASE_URL")
supabase_key = os.getenv("NEXT_PUBLIC_SUPABASE_ANON_KEY")

# No more table prefixes - simplify to use the same tables in all environments
TABLE_PREFIX = ""
print(f"Using simplified database configuration with no table prefixes")
logger.info(f"Using simplified database configuration with no table prefixes")

# Define the task key used in database joins
TASK_KEY = "tasks"
logger.info(f"Using task key in joins: '{TASK_KEY}'")

# Pushover API configuration
PUSHOVER_API_TOKEN = os.getenv("PUSHOVER_API_TOKEN")
PUSHOVER_USER_KEY = os.getenv("PUSHOVER_USER_KEY")
RECIPIENT_USER_KEY = os.getenv("RECIPIENT_USER_KEY", PUSHOVER_USER_KEY)  # Default recipient user key

# Initialize OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

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

def send_pushover_notification(task_title, task_priority, due_time, recipient=RECIPIENT_USER_KEY):
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
        
        # Create a message with task details
        message_body = f"🔔 Reminder: \"{task_title}\" is due on {due_time_str}\nPriority: {task_priority}"
        
        logger.info(f"Preparing Pushover message: {message_body}")
        
        # Set the recipient to the default if not specified
        user_key = recipient or PUSHOVER_USER_KEY
        
        # Send the Pushover notification
        response = requests.post(
            "https://api.pushover.net/1/messages.json",
            data={
                "token": PUSHOVER_API_TOKEN,
                "user": user_key,
                "message": message_body,
                "title": "Todo Reminder",
                "priority": 1 if task_priority == "High" else 0,  # Higher priority for high-priority tasks
            }
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
                supabase.table("reminders")
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
                print("  Error: Reminders table doesn't exist yet. Creating it...")
                logger.error("Reminders table doesn't exist yet.")
                
                # Create the reminders table
                try:
                    execute_migration()
                except Exception as migration_error:
                    print(f"  ❌ Failed to create reminders table: {str(migration_error)}")
                    logger.error(f"Failed to create reminders table: {str(migration_error)}")
                
                # No reminders to process this time
                reminders = []
            else:
                # Re-raise other errors
                print(f"  ❌ Error querying reminders: {error_str}")
                logger.error(f"Error querying reminders: {error_str}")
                raise query_error
        
        # Make sure the processed_reminders table exists
        try:
            # Try checking the table
            test_result = supabase.table("processed_reminders").select("count").limit(1).execute()
            print(f"  Processed reminders table is accessible")
        except Exception as table_error:
            print(f"  Creating processed_reminders table: {str(table_error)}")
            try:
                # Create the processed_reminders table
                create_processed_table_query = """
                CREATE TABLE IF NOT EXISTS processed_reminders (
                    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                    reminder_id UUID REFERENCES reminders(id) ON DELETE CASCADE,
                    processed_at TIMESTAMP WITH TIME ZONE NOT NULL,
                    message_id TEXT,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                );
                CREATE INDEX IF NOT EXISTS idx_processed_reminders_reminder_id ON processed_reminders(reminder_id);
                """
                # Create table via RPC
                supabase.rpc("exec_sql", {"query": create_processed_table_query}).execute()
                print(f"  ✅ Successfully created processed_reminders table")
            except Exception as create_error:
                print(f"  ❌ Failed to create processed_reminders table: {str(create_error)}")
        
        # Add a processed status tracker to avoid duplicate notifications
        # Check last processed reminder time in database
        try:
            processed_status = (
                supabase.table("app_status")
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
                
                supabase.table("app_status").insert({
                    "name": "last_processed_time",
                    "value": default_time.isoformat()
                }).execute()
        except Exception as e:
            # If table doesn't exist yet, create it
            print(f"  Error getting last processed time: {str(e)}")
            print(f"  Creating app_status table if needed...")
            
            try:
                # Try to create the table if it doesn't exist
                supabase.table("app_status").insert({
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
                    
                    # Check if Pushover is configured
                    send_pushover = True if PUSHOVER_API_TOKEN and PUSHOVER_USER_KEY else False
                    
                    message_results = {}
                    
                    # Send Pushover notification if configured
                    if send_pushover:
                        pushover_message_id = send_pushover_notification(
                            task_title=task.get("title"),
                            task_priority=task.get("priority"),
                            due_time=datetime.fromisoformat(task.get("due_time").replace('Z', '+00:00')),
                            recipient=recipient
                        )
                        
                        if pushover_message_id:
                            message_results["pushover"] = pushover_message_id
                            print(f"  ✅ Pushover notification sent successfully, ID: {pushover_message_id}")
                            sent_count += 1
                            
                            # Mark reminder as processed
                            if mark_reminder_processed(reminder_id, pushover_message_id, now_utc):
                                print(f"  ✅ Marked reminder {reminder_id} as processed")
                            else:
                                print(f"  ⚠️ Failed to mark reminder {reminder_id} as processed")
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
            supabase.table("app_status").update({"value": now_utc.isoformat()}).eq("name", "last_processed_time").execute()
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
        return [datetime.fromisoformat(time.replace('Z', '+00:00')) for time in reminder_times]
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
            
        task_result = supabase.table("tasks").insert(task_data).execute()
        task_id = task_result.data[0]['id']
        
        # Make sure the reminders table exists
        try:
            execute_migration()
        except Exception as migration_error:
            logger.error(f"Error running migration: {str(migration_error)}")
            # Continue with task creation even if migration fails
        
        if task.single_reminder:
            # Calculate single reminder time
            reminder_time = task.due_time - timedelta(hours=task.hours_before)
            reminder_data = {
                "task_id": task_id,
                "reminder_time": reminder_time.isoformat()
            }
            supabase.table("reminders").insert(reminder_data).execute()
        else:
            # Get reminder suggestions from LLM
            reminder_times = get_reminder_suggestions(
                task.title,
                task.priority,
                task.due_time.isoformat(),
                datetime.now(timezone.utc).isoformat()
            )
            
            # Create reminders
            for reminder_time in reminder_times:
                reminder_data = {
                    "task_id": task_id,
                    "reminder_time": reminder_time.isoformat()
                }
                supabase.table("reminders").insert(reminder_data).execute()
        
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
            supabase.table("tasks")
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
            supabase.table("tasks")
            .select("*")
            .eq("completed", False)
            .order('due_time', desc=False)
            .execute()
        )
        incomplete_tasks = incomplete_tasks_result.data

        # Get completed tasks, ordered by completion time
        completed_tasks_result = (
            supabase.table("tasks")
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
                reminders_result = supabase.table("reminders").select("*").in_("task_id", all_task_ids).execute()
                
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
        supabase.table("reminders").delete().eq("task_id", task_id).execute()
        # Then delete the task
        result = supabase.table("tasks").delete().eq("id", task_id).execute()
        return {"message": "Task and associated reminders deleted successfully"}
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
        
        # Send the notification with UK time display
        message_id = send_pushover_notification(
            task_title="Test Reminder",
            task_priority="Medium",
            due_time=test_due_time,
            recipient=recipient
        )
        
        if message_id:
            # Get the UK time representation for the response
            is_bst_active = is_bst(test_due_time)
            uk_time = test_due_time + timedelta(hours=1 if is_bst_active else 0)
            time_zone = "BST" if is_bst_active else "GMT"
            
            logger.info(f"Test Pushover notification sent successfully with ID: {message_id}")
            return {
                "message": "Test Pushover notification sent successfully", 
                "message_id": message_id, 
                "to": recipient[-5:] if recipient else "Unknown",
                "time_info": {
                    "utc_time": test_due_time.isoformat(),
                    "uk_time": uk_time.isoformat(),
                    "time_zone": time_zone
                }
            }
        else:
            logger.error("Failed to send Pushover notification - no message ID returned")
            raise HTTPException(status_code=500, detail="Failed to send Pushover notification - check server logs")
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
    """Run database migrations on startup"""
    try:
        logger.info("Running database migrations...")
        
        # Create the reminders table if it doesn't exist
        execute_migration()
            
        logger.info("Database migrations completed")
    except Exception as e:
        logger.error(f"Error running migrations: {str(e)}")
        # Don't fail startup if migrations fail

@app.get("/")
async def health_check():
    return {
        "status": "ok", 
        "message": "Task Reminder API is running",
        "supabase_configured": bool(supabase_url and supabase_key),
        "openai_configured": bool(client.api_key),
        "pushover_configured": bool(PUSHOVER_API_TOKEN and PUSHOVER_USER_KEY)
    }

def execute_migration():
    """Helper function to execute the reminders table migration"""
    # Determine the migration file path based on environment
    migration_paths = [
        "api/migrations/create_reminders_table.sql",  # From project root
        "migrations/create_reminders_table.sql",      # From api directory
        "./migrations/create_reminders_table.sql",    # Explicitly relative
        "/app/api/migrations/create_reminders_table.sql"  # Absolute path for containerized environments
    ]
    
    # Try each path until one works
    for path in migration_paths:
        try:
            if os.path.exists(path):
                with open(path) as f:
                    migration_sql = f.read()
                    # No more table prefixes
                    migration_sql = migration_sql.replace("public.reminders", "public.reminders")
                    migration_sql = migration_sql.replace("tasks(id)", "tasks(id)")
                    migration_sql = migration_sql.replace("idx_reminders_task_id", "idx_reminders_task_id")
                    # Use rpc instead of query for Supabase 2.3.4
                    supabase.rpc("exec_sql", {"query": migration_sql}).execute()
                logger.info(f"Applied create_reminders_table migration from path: {path}")
                
                # Try to create the processed_reminders table too
                try:
                    create_processed_table_query = """
                    CREATE TABLE IF NOT EXISTS processed_reminders (
                        id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                        reminder_id UUID REFERENCES reminders(id) ON DELETE CASCADE,
                        processed_at TIMESTAMP WITH TIME ZONE NOT NULL,
                        message_id TEXT,
                        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                    );
                    CREATE INDEX IF NOT EXISTS idx_processed_reminders_reminder_id ON processed_reminders(reminder_id);
                    """
                    supabase.rpc("exec_sql", {"query": create_processed_table_query}).execute()
                    logger.info("Created processed_reminders table")
                except Exception as e:
                    logger.warning(f"Could not create processed_reminders table: {str(e)}")
                
                return True
        except Exception as path_error:
            logger.warning(f"Could not apply migration from path {path}: {str(path_error)}")
    
    # As a last resort, use direct table creation
    try:
        logger.warning("Using direct table creation as SQL file could not be read")
        
        # Create reminders table
        try:
            # First check if table exists
            result = supabase.table("reminders").select("id").limit(1).execute()
            logger.info("Reminders table already exists")
        except Exception:
            # Create the reminders table
            logger.info("Creating reminders table")
            # We can't use raw SQL easily in this version, so we'll create tables using Supabase REST API
            # This will be caught by Supabase if table already exists
            result = supabase.table("tasks").select("id").limit(1).execute()
        
        # Create app_status table
        try:
            # First check if table exists
            result = supabase.table("app_status").select("id").limit(1).execute()
            logger.info("App status table already exists")
        except Exception:
            # Create the app_status table and insert initial record
            logger.info("Creating app_status table")
            try:
                # Initialize with a last_processed_time record
                supabase.table("app_status").insert({
                    "name": "last_processed_time",
                    "value": datetime.now(timezone.utc).isoformat()
                }).execute()
                logger.info("Created app_status table with initial record")
            except Exception as e:
                logger.error(f"Error creating app_status table: {str(e)}")
        
        # Create processed_reminders table
        try:
            # Check if table exists
            result = supabase.table("processed_reminders").select("id").limit(1).execute()
            logger.info("Processed reminders table already exists")
        except Exception:
            logger.info("Processed reminders table doesn't exist yet")
            # Can't create it easily without SQL - will be created when needed
        
        logger.info("Database tables checked/created")
        return True
    except Exception as e:
        logger.error(f"Failed to apply migration: {str(e)}")
        return False

def check_reminder_processed(reminder_id):
    """
    Check if a reminder has already been processed by querying the processed_reminders table
    Returns True if already processed, False otherwise
    """
    try:
        # First ensure the table exists
        try:
            # Try to access the table to see if it exists
            test_result = supabase.table("processed_reminders").select("count").limit(1).execute()
            logger.info(f"Processed reminders table exists and is accessible")
        except Exception as table_error:
            # Table doesn't exist or isn't accessible, create it
            logger.warning(f"Processed reminders table issue: {str(table_error)}")
            logger.info("Creating processed_reminders table")
            create_processed_table_query = """
            CREATE TABLE IF NOT EXISTS processed_reminders (
                id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                reminder_id UUID REFERENCES reminders(id) ON DELETE CASCADE,
                processed_at TIMESTAMP WITH TIME ZONE NOT NULL,
                message_id TEXT,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            );
            CREATE INDEX IF NOT EXISTS idx_processed_reminders_reminder_id ON processed_reminders(reminder_id);
            """
            # Try to create the table via RPC
            try:
                supabase.rpc("exec_sql", {"query": create_processed_table_query}).execute()
                logger.info("Successfully created processed_reminders table")
            except Exception as rpc_error:
                logger.error(f"Failed to create processed_reminders table via RPC: {str(rpc_error)}")
        
        # Now check if this specific reminder has been processed
        result = (
            supabase.table("processed_reminders")
            .select("*")
            .eq("reminder_id", reminder_id)
            .execute()
        )
        
        is_processed = len(result.data) > 0
        logger.info(f"Reminder {reminder_id} processed status check: {is_processed}")
        if is_processed:
            logger.info(f"Reminder {reminder_id} was previously processed at {result.data[0].get('processed_at')}")
        
        # If any records found, the reminder has been processed
        return is_processed
    except Exception as e:
        logger.warning(f"Error checking if reminder {reminder_id} is processed: {str(e)}")
        # If we can't check, assume not processed to be safe
        return False

def mark_reminder_processed(reminder_id, message_id=None, now_utc=None):
    """
    Mark a reminder as processed in the processed_reminders table
    Returns True if successful, False otherwise
    """
    if now_utc is None:
        now_utc = datetime.now(timezone.utc)
    
    # First check if already processed to avoid duplicate entries
    try:
        already_processed = check_reminder_processed(reminder_id)
        if already_processed:
            logger.info(f"Reminder {reminder_id} already marked as processed, skipping")
            return True
    except Exception as check_error:
        logger.warning(f"Error checking if reminder {reminder_id} is already processed: {str(check_error)}")
        # Continue anyway to try to mark it
        
    try:
        data = {
            "reminder_id": reminder_id,
            "processed_at": now_utc.isoformat(),
        }
        if message_id:
            data["message_id"] = message_id
        
        logger.info(f"Marking reminder {reminder_id} as processed with data: {json.dumps(data, default=str)}")
        insert_result = supabase.table("processed_reminders").insert(data).execute()
        logger.info(f"Successfully marked reminder {reminder_id} as processed")
        return True
    except Exception as e:
        error_str = str(e)
        # If the table doesn't exist, try to create it
        if "relation" in error_str and "does not exist" in error_str:
            try:
                # Create the processed_reminders table
                logger.info("Creating processed_reminders table")
                create_processed_table_query = """
                CREATE TABLE IF NOT EXISTS processed_reminders (
                    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                    reminder_id UUID REFERENCES reminders(id) ON DELETE CASCADE,
                    processed_at TIMESTAMP WITH TIME ZONE NOT NULL,
                    message_id TEXT,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                );
                CREATE INDEX IF NOT EXISTS idx_processed_reminders_reminder_id ON processed_reminders(reminder_id);
                """
                # Try to create the table via RPC
                try:
                    supabase.rpc("exec_sql", {"query": create_processed_table_query}).execute()
                    
                    # Try insertion again
                    data = {
                        "reminder_id": reminder_id,
                        "processed_at": now_utc.isoformat(),
                    }
                    if message_id:
                        data["message_id"] = message_id
                    
                    supabase.table("processed_reminders").insert(data).execute()
                    logger.info(f"Successfully created table and marked reminder {reminder_id} as processed")
                    return True
                except Exception as rpc_error:
                    logger.error(f"Failed to create processed_reminders table via RPC: {str(rpc_error)}")
                    return False
            except Exception as create_error:
                logger.error(f"Failed to create processed_reminders table: {str(create_error)}")
                return False
        else:
            logger.error(f"Error marking reminder {reminder_id} as processed: {error_str}")
            return False

# Add an admin endpoint to reset the processed reminders
@app.post("/api/admin/reset-processed-reminders")
async def reset_processed_reminders(request: Request):
    """Admin endpoint to reset processed reminders so they can be sent again"""
    # Get verification token from environment
    verify_token = os.getenv("VERIFY_TOKEN")
    
    # Get authorization header
    auth_header = request.headers.get("Authorization")
    
    # Verify the token for security
    if verify_token and (not auth_header or auth_header != f"Bearer {verify_token}"):
        logger.warning(f"Unauthorized access attempt to reset-processed-reminders endpoint")
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    try:
        # Try to clear the processed_reminders table
        try:
            deleted_result = supabase.table("processed_reminders").delete().neq("id", "dummy").execute()
            processed_cleared = True
            cleared_count = len(deleted_result.data)
        except Exception as e:
            processed_cleared = False
            cleared_count = 0
            logger.warning(f"Could not clear processed_reminders table: {str(e)}")
        
        # Also reset the last_processed_time in app_status as a fallback
        reset_time = datetime.now(timezone.utc) - timedelta(hours=24)
        try:
            update_result = (
                supabase.table("app_status")
                .update({"value": reset_time.isoformat()})
                .eq("name", "last_processed_time")
                .execute()
            )
            time_reset = True
        except Exception as e:
            time_reset = False
            logger.warning(f"Could not reset last_processed_time: {str(e)}")
        
        return {
            "message": "Reminder processing history reset",
            "processed_reminders_cleared": processed_cleared,
            "cleared_count": cleared_count,
            "last_processed_time_reset": time_reset,
            "reset_to": reset_time.isoformat() if time_reset else None
        }
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Error resetting reminder processing history: {error_msg}", exc_info=True)
        raise HTTPException(status_code=500, detail=error_msg)

if __name__ == "__main__":
    import uvicorn
    print(f"Supabase URL configured: {'Yes' if supabase_url else 'No'}")
    print(f"Supabase Key configured: {'Yes' if supabase_key else 'No'}")
    print(f"OpenAI API Key configured: {'Yes' if client.api_key else 'No'}")
    print(f"Pushover API configured: {'Yes' if PUSHOVER_API_TOKEN and PUSHOVER_USER_KEY else 'No'}")
    print("\nDatabase Configuration:")
    print(f"- Environment: {'PRODUCTION' if supabase_url else 'DEVELOPMENT'}")
    print("\nServer Usage:")
    print("- Run locally: python server.py")
    print("\nSetup Instructions:")
    print("- Ensure your .env file has the required environment variables")
    uvicorn.run(app, host="0.0.0.0", port=8000) 