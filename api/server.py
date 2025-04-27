from fastapi import FastAPI, HTTPException, BackgroundTasks, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from datetime import datetime, timedelta
from typing import Optional, List
import os
from dotenv import load_dotenv
from supabase import create_client, Client
from openai import OpenAI
from datetime import timezone
import json
import sys
import requests
import time
import logging  # Add logging import

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

# Load environment variables
load_dotenv()

# Get Supabase credentials with fallbacks
supabase_url = os.getenv("SUPABASE_URL") or os.getenv("NEXT_PUBLIC_SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_KEY") or os.getenv("NEXT_PUBLIC_SUPABASE_ANON_KEY")

# Meta WhatsApp Business API configuration
META_API_VERSION = os.getenv("META_API_VERSION", "v18.0")
META_PHONE_NUMBER_ID = os.getenv("META_PHONE_NUMBER_ID")
META_ACCESS_TOKEN = os.getenv("META_ACCESS_TOKEN")
RECIPIENT_PHONE_NUMBER = os.getenv("RECIPIENT_PHONE_NUMBER", "33668695116")  # Default to the fixed WhatsApp number

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

# Initialize Supabase client
try:
    # Print out environment variables for debugging
    print("Environment Variables:")
    for key, value in os.environ.items():
        if key.startswith(('NEXT_PUBLIC_', 'SUPABASE_', 'OPENAI_', 'META_')):
            print(f"{key}: {'*' * len(value) if value else 'None'}")
    
    # Print package versions for debugging
    import supabase
    import gotrue
    print(f"Supabase version: {getattr(supabase, '__version__', 'unknown')}")
    print(f"GoTrue version: {getattr(gotrue, '__version__', 'unknown')}")
    
    # Create Supabase client without any extra options that might cause compatibility issues
    # Use a simple client creation without additional options
    supabase: Client = create_client(supabase_url, supabase_key)
except Exception as e:
    print(f"CRITICAL ERROR initializing Supabase client: {e}")
    print(f"Supabase URL: {supabase_url}")
    print(f"Supabase Key Length: {len(supabase_key) if supabase_key else 'None'}")
    print(f"Full error traceback:", file=sys.stderr)
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

def send_whatsapp_reminder(task_title, task_priority, due_time, recipient=RECIPIENT_PHONE_NUMBER):
    """Send a WhatsApp message for a task reminder using Meta Cloud API"""
    if not META_ACCESS_TOKEN or not META_PHONE_NUMBER_ID:
        logger.warning("Meta WhatsApp API not configured, skipping WhatsApp notification")
        return None
    
    try:
        # Ensure the recipient number has the correct format (remove any "whatsapp:" prefix)
        if recipient.startswith("whatsapp:"):
            recipient = recipient[9:]  # Remove "whatsapp:" prefix
        
        # Ensure the number starts with a + if not already
        if not recipient.startswith("+"):
            recipient = "+" + recipient
            
        # Format the due time for display
        due_time_str = due_time.strftime("%A, %B %d at %I:%M %p")
        
        # Create a message with task details
        message_body = f"🔔 Reminder: \"{task_title}\" is due on {due_time_str}\nPriority: {task_priority}"
        
        logger.info(f"Preparing WhatsApp message: {message_body}")
        
        # Meta WhatsApp API endpoint
        url = f"https://graph.facebook.com/{META_API_VERSION}/{META_PHONE_NUMBER_ID}/messages"
        
        # Prepare the payload
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": recipient,
            "type": "text",
            "text": {
                "preview_url": False,
                "body": message_body
            }
        }
        
        # Headers with the access token
        headers = {
            "Authorization": f"Bearer {META_ACCESS_TOKEN}",
            "Content-Type": "application/json"
        }
        
        # Log request details (but hide the token)
        logger.info(f"WhatsApp API request to URL: {url}")
        logger.info(f"WhatsApp API payload: {json.dumps(payload)}")
        logger.info(f"WhatsApp API request headers: Authorization: Bearer ******, Content-Type: application/json")
        
        # Send the request
        response = requests.post(url, json=payload, headers=headers)
        response_data = response.json()
        
        if response.status_code == 200:
            logger.info(f"WhatsApp reminder sent successfully: {json.dumps(response_data)}")
            # Return the message ID from the response
            return response_data.get("messages", [{}])[0].get("id")
        else:
            logger.error(f"Error sending WhatsApp reminder: Status {response.status_code}, Response: {json.dumps(response_data)}")
            return None
    except Exception as e:
        logger.error(f"Error sending WhatsApp reminder: {str(e)}", exc_info=True)
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
                task = reminder.get("tasks", {})
                reminder_time = datetime.fromisoformat(reminder.get("reminder_time").replace('Z', '+00:00'))
                time_ago = now_utc - reminder_time
                hours_ago = time_ago.total_seconds() / 3600
                
                print(f"  {i+1}. Task: {task.get('title', 'Unknown')}")
                print(f"     Reminder time: {reminder.get('reminder_time', 'Unknown')} ({hours_ago:.1f} hours ago)")
                print(f"     Task completed: {task.get('completed', False)}")
                print(f"     Priority: {task.get('priority', 'Unknown')}")
                
            logger.info(f"Reminder data: {json.dumps(reminders, default=str)}")
        else:
            print("  No reminders found in the catchup window")
        
        # Process each reminder
        sent_count = 0
        skipped_already_processed = 0
        if len(reminders) > 0:
            print(f"\nPROCESSING REMINDERS:")
            
        for i, reminder in enumerate(reminders):
            task = reminder.get("tasks", {})
            if task and not task.get("completed", False):
                reminder_time = datetime.fromisoformat(reminder.get("reminder_time").replace('Z', '+00:00'))
                
                # Skip if we already processed this reminder
                if reminder_time <= last_processed_time:
                    print(f"  Skipping reminder {i+1}: {task.get('title')} - Already processed before")
                    skipped_already_processed += 1
                    continue
                
                print(f"  Processing reminder {i+1}: {task.get('title')} at {reminder_time.isoformat()}")
                logger.info(f"Processing reminder for task: {task.get('title')} at {reminder_time.isoformat()}")
                logger.info(f"Task details: {json.dumps(task, default=str)}")
                
                # Get the task's phone number or use the default
                recipient = task.get("phone_number", RECIPIENT_PHONE_NUMBER)
                print(f"  Sending to: {recipient}")
                logger.info(f"Sending WhatsApp message to recipient: {recipient}")
                
                # Send the WhatsApp reminder
                message_id = send_whatsapp_reminder(
                    task_title=task.get("title"),
                    task_priority=task.get("priority"),
                    due_time=datetime.fromisoformat(task.get("due_time").replace('Z', '+00:00')),
                    recipient=recipient
                )
                
                if message_id:
                    print(f"  ✅ Message sent successfully, ID: {message_id}")
                    sent_count += 1
                else:
                    print(f"  ❌ Failed to send message")
                logger.info(f"WhatsApp message sent with ID: {message_id}")
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
        return True
    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}")
        import traceback
        print(traceback.format_exc())
        logger.error(f"Error checking upcoming reminders: {str(e)}", exc_info=True)
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
        # Create the task
        task_data = {
            "title": task.title,
            "due_time": task.due_time.isoformat(),
            "priority": task.priority
        }
        
        # Add phone number if provided
        if task.phone_number:
            task_data["phone_number"] = task.phone_number
            
        task_result = supabase.table("tasks").insert(task_data).execute()
        task_id = task_result.data[0]['id']
        
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

        # Fetch reminders for all tasks
        for task in incomplete_tasks + completed_tasks:
            reminders_result = supabase.table("reminders").select("*").eq("task_id", task["id"]).execute()
            task["reminders"] = reminders_result.data

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

# New endpoint to test WhatsApp notification
@app.post("/api/test-whatsapp")
async def test_whatsapp_message():
    try:
        # Always use the default number
        recipient = RECIPIENT_PHONE_NUMBER
        if not recipient:
            raise HTTPException(status_code=400, detail="Default phone number not configured")
            
        message_id = send_whatsapp_reminder(
            task_title="Test Reminder",
            task_priority="Medium",
            due_time=datetime.now(timezone.utc) + timedelta(hours=1),
            recipient=recipient
        )
        
        if message_id:
            return {"message": "Test WhatsApp message sent successfully", "message_id": message_id, "to": recipient}
        else:
            raise HTTPException(status_code=500, detail="Failed to send WhatsApp message")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

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
        result = {"message": "Reminders checked successfully", "timestamp": datetime.now(timezone.utc).isoformat(), "success": success}
        print(f"\n✅ REMINDER CHECK COMPLETED: {json.dumps(result)}")
        logger.info(f"check-reminders endpoint completed: {json.dumps(result)}")
        return result
    except Exception as e:
        error_msg = str(e)
        print(f"\n❌ ERROR IN REMINDER CHECK: {error_msg}")
        logger.error(f"Error in check-reminders endpoint: {error_msg}", exc_info=True)
        raise HTTPException(status_code=500, detail=error_msg)

@app.get("/")
async def health_check():
    return {
        "status": "ok", 
        "message": "Task Reminder API is running",
        "supabase_configured": bool(supabase_url and supabase_key),
        "openai_configured": bool(client.api_key),
        "meta_whatsapp_configured": bool(META_ACCESS_TOKEN and META_PHONE_NUMBER_ID)
    }

if __name__ == "__main__":
    import uvicorn
    print(f"Supabase URL configured: {'Yes' if supabase_url else 'No'}")
    print(f"Supabase Key configured: {'Yes' if supabase_key else 'No'}")
    print(f"OpenAI API Key configured: {'Yes' if client.api_key else 'No'}")
    print(f"Meta WhatsApp API configured: {'Yes' if META_ACCESS_TOKEN and META_PHONE_NUMBER_ID else 'No'}")
    uvicorn.run(app, host="0.0.0.0", port=8000) 