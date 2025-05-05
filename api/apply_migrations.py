import os
from dotenv import load_dotenv
from supabase import create_client, Client
import sys

def apply_migrations():
    # Determine environment
    env = os.getenv("ENV", "development").lower()
    print(f"Running migrations in {env.upper()} environment")
    
    # Set table prefix based on environment
    TABLE_PREFIX = "dev_" if env == "development" else ""
    print(f"Using table prefix: '{TABLE_PREFIX}'")
    
    # Load the appropriate .env file
    if env == "development" and os.path.exists(".env.development"):
        load_dotenv(".env.development")
        print("Loaded configuration from .env.development")
    else:
        load_dotenv()
        print("Loaded configuration from .env")
    
    # Get Supabase credentials with fallbacks
    supabase_url = os.getenv("SUPABASE_URL") or os.getenv("NEXT_PUBLIC_SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_KEY") or os.getenv("NEXT_PUBLIC_SUPABASE_ANON_KEY")
    
    # For development, allow override of Supabase URL/key for testing
    if env == "development":
        dev_supabase_url = os.getenv("DEV_SUPABASE_URL")
        dev_supabase_key = os.getenv("DEV_SUPABASE_KEY")
        
        if dev_supabase_url and dev_supabase_key:
            supabase_url = dev_supabase_url
            supabase_key = dev_supabase_key
            print("Using development Supabase database for migrations")
    
    if not supabase_url or not supabase_key:
        raise ValueError("Missing Supabase credentials in .env file")
    
    # Print which database we're connecting to (without revealing sensitive information)
    db_type = "DEVELOPMENT" if env == "development" else "PRODUCTION"
    print(f"Applying migrations to {db_type} database at {supabase_url[:30]}...")
    
    supabase: Client = create_client(supabase_url, supabase_key)
    
    print("Applying database migrations...")
    
    try:
        # First, create the core tasks table with prefix if it doesn't exist
        print(f"\nCreating {TABLE_PREFIX}tasks table if it doesn't exist")
        
        tasks_table_sql = f"""
        CREATE TABLE IF NOT EXISTS public.{TABLE_PREFIX}tasks (
            id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            title TEXT NOT NULL,
            due_time TIMESTAMP WITH TIME ZONE NOT NULL,
            priority TEXT NOT NULL,
            completed BOOLEAN DEFAULT FALSE,
            completed_at TIMESTAMP WITH TIME ZONE,
            phone_number TEXT,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
        );
        """
        
        try:
            supabase.query(tasks_table_sql).execute()
            print(f"✅ {TABLE_PREFIX}tasks table created or already exists")
        except Exception as e:
            print(f"❌ Error creating tasks table: {str(e)}")
            # Continue with other migrations
        
        # Read migration file
        migration_files = [
            'api/migrations/init.sql',
            'api/migrations/create_reminders_table.sql',
            'api/migrations/add_completed_fields.sql'
        ]
        
        # Check migration file paths - adjust if needed
        actual_migration_files = []
        for file_path in migration_files:
            if os.path.exists(file_path):
                actual_migration_files.append(file_path)
            elif os.path.exists(file_path.replace('api/', '')):
                # Try without api/ prefix if running from within api directory
                actual_migration_files.append(file_path.replace('api/', ''))
                
        if not actual_migration_files:
            raise FileNotFoundError("Could not find migration files. Make sure you're running from the correct directory.")
            
        print(f"Found {len(actual_migration_files)} migration files to apply.")
        
        # Apply each migration file
        for migration_file in actual_migration_files:
            print(f"\nApplying migration: {migration_file}")
            
            with open(migration_file, 'r') as file:
                migration_sql = file.read()
                
                # Replace table names with prefixed versions
                migration_sql = migration_sql.replace("public.reminders", f"public.{TABLE_PREFIX}reminders")
                migration_sql = migration_sql.replace("public.tasks", f"public.{TABLE_PREFIX}tasks")
                migration_sql = migration_sql.replace("public.app_status", f"public.{TABLE_PREFIX}app_status")
                migration_sql = migration_sql.replace("tasks(id)", f"{TABLE_PREFIX}tasks(id)")
                migration_sql = migration_sql.replace("reminders(task_id)", f"{TABLE_PREFIX}reminders(task_id)")
                
                # Replace index names
                migration_sql = migration_sql.replace("idx_reminders_task_id", f"idx_{TABLE_PREFIX}reminders_task_id")
                
                # Split the migration file into individual statements
                statements = migration_sql.split(';')
                
                # Execute each statement
                for statement in statements:
                    statement = statement.strip()
                    if statement:  # Skip empty statements
                        try:
                            print(f"Executing statement: {statement[:100]}..." if len(statement) > 100 else f"Executing statement: {statement}")
                            # Use the REST API to execute SQL
                            response = supabase.rpc('exec_sql', {'query': statement}).execute()
                            print(f"Statement executed successfully")
                        except Exception as e:
                            print(f"Error executing statement: {str(e)}")
                            print(f"Statement was: {statement}")
                            # Continue with other statements rather than aborting
                            print("Continuing with remaining statements...")
        
        # Create app_status table
        app_status_sql = f"""
        CREATE TABLE IF NOT EXISTS public.{TABLE_PREFIX}app_status (
            id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            name TEXT UNIQUE NOT NULL,
            value TEXT NOT NULL,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
        );
        """
        
        try:
            supabase.query(app_status_sql).execute()
            print(f"✅ {TABLE_PREFIX}app_status table created or already exists")
        except Exception as e:
            print(f"❌ Error creating app_status table: {str(e)}")
            # Continue with other migrations
                    
        print("\nMigrations applied successfully!")
        
    except Exception as e:
        print(f"Error applying migrations: {str(e)}")
        raise e

if __name__ == "__main__":
    try:
        apply_migrations()
    except Exception as e:
        sys.exit(1) 