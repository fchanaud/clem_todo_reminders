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
        print("Meta WhatsApp API not configured, skipping WhatsApp notification")
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
        
        # Send the request
        response = requests.post(url, json=payload, headers=headers)
        response_data = response.json()
        
        if response.status_code == 200:
            print(f"WhatsApp reminder sent successfully: {response_data}")
            # Return the message ID from the response
            return response_data.get("messages", [{}])[0].get("id")
        else:
            print(f"Error sending WhatsApp reminder: {response_data}")
            return None
    except Exception as e:
        print(f"Error sending WhatsApp reminder: {str(e)}")
        return None

def check_upcoming_reminders():
    """Check for reminders that are due in the next minute and send notifications"""
    try:
        # Get current time
        now = datetime.now(timezone.utc)
        one_minute_later = now + timedelta(minutes=1)
        
        # Format times for Supabase query
        now_str = now.isoformat()
        one_minute_later_str = one_minute_later.isoformat()
        
        # Query for reminders between now and 1 minute in the future
        reminders_result = (
            supabase.table("reminders")
            .select("*, tasks(*)")
            .gte("reminder_time", now_str)
            .lt("reminder_time", one_minute_later_str)
            .execute()
        )
        
        reminders = reminders_result.data
        
        # Process each reminder
        for reminder in reminders:
            task = reminder.get("tasks", {})
            if task and not task.get("completed", False):
                print(f"Processing reminder for task: {task.get('title')}")
                
                # Get the task's phone number or use the default
                recipient = task.get("phone_number", RECIPIENT_PHONE_NUMBER)
                
                # Send the WhatsApp reminder
                send_whatsapp_reminder(
                    task_title=task.get("title"),
                    task_priority=task.get("priority"),
                    due_time=datetime.fromisoformat(task.get("due_time")),
                    recipient=recipient
                )
    except Exception as e:
        print(f"Error checking upcoming reminders: {str(e)}")

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
    # Get verification token from environment
    verify_token = os.getenv("VERIFY_TOKEN")
    
    # Get authorization header
    auth_header = request.headers.get("Authorization")
    
    # Verify the token for security (ensure only the cron job can trigger this)
    if verify_token and (not auth_header or auth_header != f"Bearer {verify_token}"):
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    try:
        check_upcoming_reminders()
        return {"message": "Reminders checked successfully", "timestamp": datetime.now(timezone.utc).isoformat()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

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