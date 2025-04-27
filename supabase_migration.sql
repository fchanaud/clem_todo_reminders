-- Add phone_number column to tasks table
ALTER TABLE IF EXISTS public.tasks 
ADD COLUMN IF NOT EXISTS phone_number TEXT;

-- Create index for better query performance
CREATE INDEX IF NOT EXISTS idx_tasks_phone_number ON public.tasks (phone_number);

-- Comment on column for documentation
COMMENT ON COLUMN public.tasks.phone_number IS 'Phone number for WhatsApp notifications in international format (e.g., +33668695116)';

-- Create app_status table for tracking application state
CREATE TABLE IF NOT EXISTS public.app_status (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name TEXT NOT NULL UNIQUE,
    value TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create a trigger to automatically update the updated_at column
DROP TRIGGER IF EXISTS update_app_status_updated_at ON app_status;
CREATE TRIGGER update_app_status_updated_at
    BEFORE UPDATE ON app_status
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Comment on app_status table
COMMENT ON TABLE public.app_status IS 'Stores application state and metadata like last processed reminder time'; 