-- Migration script to add reminder_times column to tasks table
-- This is a safe migration that can be run multiple times

-- Step 1: Check if reminder_times column exists, and add it if it doesn't
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_name = 'tasks'
        AND column_name = 'reminder_times'
    ) THEN
        ALTER TABLE tasks ADD COLUMN reminder_times JSONB DEFAULT '[]'::jsonb;
        RAISE NOTICE 'Added reminder_times column to tasks table';
    ELSE
        RAISE NOTICE 'reminder_times column already exists in tasks table';
    END IF;
END $$; 