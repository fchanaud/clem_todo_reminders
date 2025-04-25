import os
from dotenv import load_dotenv
from supabase import create_client, Client

def apply_migrations():
    # Load environment variables
    load_dotenv()
    
    # Initialize Supabase client using the public variables
    supabase_url = os.getenv("NEXT_PUBLIC_SUPABASE_URL")
    supabase_key = os.getenv("NEXT_PUBLIC_SUPABASE_ANON_KEY")
    
    if not supabase_url or not supabase_key:
        raise ValueError("Missing Supabase credentials in .env file")
    
    supabase: Client = create_client(supabase_url, supabase_key)
    
    print("Applying database migrations...")
    
    try:
        # Read migration file
        with open('api/migrations/init.sql', 'r') as file:
            migration_sql = file.read()
            
        # Split the migration file into individual statements
        statements = migration_sql.split(';')
        
        # Execute each statement
        for statement in statements:
            statement = statement.strip()
            if statement:  # Skip empty statements
                try:
                    print(f"Executing statement: {statement}")
                    # Use the REST API to execute SQL
                    response = supabase.rpc('exec_sql', {'query': statement}).execute()
                    print(f"Statement executed successfully")
                except Exception as e:
                    print(f"Error executing statement: {str(e)}")
                    print(f"Statement was: {statement}")
                    raise e
                    
        print("Migrations applied successfully!")
        
    except Exception as e:
        print(f"Error applying migrations: {str(e)}")
        raise e

if __name__ == "__main__":
    apply_migrations() 