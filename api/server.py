from fastapi import FastAPI, HTTPException
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

# Load environment variables
load_dotenv()

# Get Supabase credentials
supabase_url = os.getenv("NEXT_PUBLIC_SUPABASE_URL")
supabase_key = os.getenv("NEXT_PUBLIC_SUPABASE_ANON_KEY")

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
    supabase: Client = create_client(supabase_url, supabase_key)
except Exception as e:
    print(f"Error initializing Supabase client: {e}")
    print(f"Supabase URL: {supabase_url}")
    print(f"Supabase Key Length: {len(supabase_key) if supabase_key else 'None'}")
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

@app.get("/")
async def health_check():
    return {
        "status": "ok", 
        "message": "Task Reminder API is running",
        "supabase_configured": bool(supabase_url and supabase_key),
        "openai_configured": bool(client.api_key)
    }

if __name__ == "__main__":
    import uvicorn
    print(f"Supabase URL configured: {'Yes' if supabase_url else 'No'}")
    print(f"Supabase Key configured: {'Yes' if supabase_key else 'No'}")
    print(f"OpenAI API Key configured: {'Yes' if client.api_key else 'No'}")
    uvicorn.run(app, host="0.0.0.0", port=8000) 