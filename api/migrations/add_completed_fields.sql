-- Add completed and completed_at columns to existing tasks table
ALTER TABLE public.tasks 
ADD COLUMN IF NOT EXISTS completed BOOLEAN DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS completed_at TIMESTAMP WITH TIME ZONE;

-- Update any existing rows to have completed = FALSE
UPDATE public.tasks 
SET completed = FALSE 
WHERE completed IS NULL;

-- Drop existing trigger if it exists
DROP TRIGGER IF EXISTS update_tasks_updated_at ON tasks;

-- Recreate the trigger with updated_at handling
CREATE TRIGGER update_tasks_updated_at
    BEFORE UPDATE ON tasks
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column(); 