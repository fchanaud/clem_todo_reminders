#!/usr/bin/env python3
"""
Run database migration to fix the schema for the todo app.
"""

import os
import sys
from dotenv import load_dotenv
from supabase import create_client, Client

# Load environment variables
load_dotenv()

# Get Supabase credentials
supabase_url = os.getenv("SUPABASE_URL") or os.getenv("NEXT_PUBLIC_SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_KEY") or os.getenv("NEXT_PUBLIC_SUPABASE_ANON_KEY")

if not supabase_url or not supabase_key:
    raise Exception(
        "Missing Supabase credentials. Please ensure SUPABASE_URL and "
        "SUPABASE_KEY are set in your .env file."
    )

print("="*80)
print("DATABASE MIGRATION SCRIPT")
print("="*80)

# Initialize Supabase client
try:
    supabase: Client = create_client(supabase_url, supabase_key)
    print("Connected to Supabase successfully")
except Exception as e:
    print(f"Error connecting to Supabase: {str(e)}")
    sys.exit(1)

def run_migration(filename):
    try:
        # Read migration SQL
        with open(filename, 'r') as file:
            migration_sql = file.read()
        
        print(f"\nRunning migration: {filename}")
        
        # Execute the SQL using the Supabase REST API
        # First check if we can use the rpc endpoint
        try:
            result = supabase.rpc(
                "exec_sql", 
                {"sql_query": migration_sql}
            ).execute()
            print(f"Migration {filename} executed successfully via RPC")
            return True
        except Exception as rpc_error:
            print(f"RPC execution failed: {str(rpc_error)}")
            print("Attempting alternative approach...")
            
            # Fallback - We'll need to run the SQL in Supabase dashboard
            print("\n" + "="*80)
            print(f"IMPORTANT: Cannot execute {filename} directly via API")
            print("Please run the following SQL in the Supabase dashboard SQL editor:")
            print("="*80)
            print("\n" + migration_sql + "\n")
            print("="*80)
            return False
    except Exception as e:
        print(f"Error running migration {filename}: {str(e)}")
        return False

try:
    # Run migrations in order
    migrations = [
        'migration_create_app_status.sql',
        'migration_add_reminder_times.sql'
    ]
    
    all_success = True
    for migration in migrations:
        success = run_migration(migration)
        if not success:
            all_success = False
    
    if all_success:
        print("\nAll migrations executed successfully!")
    else:
        print("\nSome migrations need to be run manually in the Supabase dashboard.")
        print("After running the SQL, restart your application")
    
    print("\nMigration script completed!")
    
except Exception as e:
    print(f"Error during migration process: {str(e)}")
    sys.exit(1) 