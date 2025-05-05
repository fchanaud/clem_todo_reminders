-- Migration script to create app_status table
-- This is a safe migration that can be run multiple times

-- Check if app_status table exists, and create it if it doesn't
CREATE TABLE IF NOT EXISTS app_status (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name TEXT UNIQUE NOT NULL,
    value TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Insert default record for last_processed_time if it doesn't exist
INSERT INTO app_status (name, value)
VALUES ('last_processed_time', CURRENT_TIMESTAMP::TEXT)
ON CONFLICT (name) DO NOTHING; 