-- Add phone_number column to tasks table
ALTER TABLE IF EXISTS public.tasks 
ADD COLUMN IF NOT EXISTS phone_number TEXT;

-- Create index for better query performance
CREATE INDEX IF NOT EXISTS idx_tasks_phone_number ON public.tasks (phone_number);

-- Comment on column for documentation
COMMENT ON COLUMN public.tasks.phone_number IS 'Phone number for WhatsApp notifications in international format (e.g., +33668695116)'; 