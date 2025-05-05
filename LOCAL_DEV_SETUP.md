# Local Development Setup

This document explains how to set up a local development environment for testing without affecting your production data.

## Using Table Prefixes for Development

The application is configured to use table prefixes in development mode, which lets you:
- Use the same Supabase project for both development and production
- Keep development data separate from production data 
- Test features without affecting real users
- Easily switch between development and production environments

When in development mode (the default), all tables are prefixed with `dev_` (e.g., `dev_tasks`, `dev_reminders`). In production mode, tables have no prefix.

## Setting Up Your Development Environment

### 1. Create Your Environment File

1. Copy the template environment file:
   ```bash
   cp env.development.example .env.development
   ```

2. Edit `.env.development` with your actual Supabase credentials:
   ```
   ENV=development
   
   # Supabase Database (same for development and production)
   NEXT_PUBLIC_SUPABASE_URL=https://your-supabase-url.supabase.co
   NEXT_PUBLIC_SUPABASE_ANON_KEY=your-supabase-anon-key
   
   # Other config values...
   ```

### 2. Initialize the Database Tables

Run the migration script to create the development tables (with the `dev_` prefix):

```bash
cd api
python apply_migrations.py
```

This will create the following tables in your Supabase project:
- `dev_tasks` - For storing task information
- `dev_reminders` - For storing reminders linked to tasks
- `dev_app_status` - For storing application state

## Running the Application in Development Mode

Start the backend server:

```bash
python api/server.py
```

You should see output confirming development mode:

```
Running in DEVELOPMENT environment
Using table prefix: 'dev_'
Loaded configuration from .env.development
Connected to DEVELOPMENT database at https://your-supabase-url.supabase...
```

## Switching Between Environments

### Using Development Tables (default)

```bash
# No special flags needed - this is the default
python api/server.py
```

### Using Production Tables

Option 1: Set ENV in the terminal:
```bash
ENV=production python api/server.py
```

Option 2: Modify your `.env.development` file:
```
ENV=production
```

## How It Works

The application automatically:
1. Detects if it's running in development or production mode
2. Uses the table prefix `dev_` for all database operations in development mode
3. Uses no prefix for production mode

This means all API endpoints and background processes work the same way in both environments, but they operate on different sets of tables.

## Troubleshooting

- If tables are missing in development mode, check server logs to confirm the correct prefix is being used
- To reset your development environment, you can drop the prefixed tables:
  ```sql
  DROP TABLE dev_reminders;
  DROP TABLE dev_tasks;
  DROP TABLE dev_app_status;
  ```
  Then run the migrations again
- If you see errors about foreign keys, make sure you created the `dev_tasks` table before the `dev_reminders` table 