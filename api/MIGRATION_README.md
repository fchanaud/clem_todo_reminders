# Database Schema Migration

This migration combines the tasks and reminders tables, embedding reminders directly into tasks as a JSON array.

## Benefits
- Reduces database complexity
- Eliminates joins when querying tasks and their reminders
- Simplifies code maintenance

## Prerequisites
- Python 3.7+
- Supabase credentials (SUPABASE_URL and SUPABASE_KEY set in your .env file)

## Migration Steps

### Option 1: Using the Python Script (Recommended)

1. Make sure your environment variables are set correctly:
   ```
   SUPABASE_URL=your_supabase_url
   SUPABASE_KEY=your_supabase_key
   ```

2. Run the migration script:
   ```
   cd api
   python migrate.py
   ```

3. Monitor the output to ensure all tasks are migrated correctly

4. After confirming everything works correctly, you can manually drop the reminders table in the Supabase dashboard

### Option 2: Using SQL Directly

If you prefer to run the SQL migration directly:

1. Connect to your Supabase database via the SQL editor in the Supabase dashboard

2. Run the migration SQL script:
   ```sql
   -- Step 1: Add reminder_times column to tasks table
   ALTER TABLE tasks 
   ADD COLUMN reminder_times jsonb DEFAULT '[]'::jsonb;

   -- Step 2: Copy existing reminders to the tasks table
   UPDATE tasks
   SET reminder_times = (
     SELECT jsonb_agg(r.reminder_time)
     FROM reminders r
     WHERE r.task_id = tasks.id
   );

   -- Step 3: Only after confirming the migration worked
   -- DROP TABLE reminders;
   ```

## Rollback Plan

If you need to revert the changes:

1. If you've dropped the reminders table, recreate it:
   ```sql
   CREATE TABLE reminders (
     id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
     task_id UUID REFERENCES tasks(id) ON DELETE CASCADE,
     reminder_time TIMESTAMPTZ NOT NULL,
     created_at TIMESTAMPTZ DEFAULT now()
   );
   ```

2. Repopulate the reminders table from the tasks.reminder_times array:
   ```sql
   INSERT INTO reminders (task_id, reminder_time)
   SELECT id, jsonb_array_elements_text(reminder_times)::timestamptz
   FROM tasks
   WHERE jsonb_array_length(reminder_times) > 0;
   ```

3. Remove the reminder_times column from tasks:
   ```sql
   ALTER TABLE tasks DROP COLUMN reminder_times;
   ``` 