# Deployment Fixes for Render

This guide addresses common deployment issues with the Clem Todo Reminders application on Render.

## 1. Fixing the "proxy" Parameter Error

If you encounter this error:
```
CRITICAL ERROR initializing Supabase client: Client.__init__() got an unexpected keyword argument 'proxy'
```

### Solution:

1. **Update the Supabase package version**
   - In your `api/requirements.txt` file, set `supabase==1.2.0`
   - This older version doesn't have the proxy parameter issue

2. **Redeploy your backend service**
   - On Render dashboard, click on your backend service
   - Click "Manual Deploy" > "Deploy latest commit"

## 2. Adding the phone_number Column to the tasks Table

If you encounter this error:
```
"detail": "{'code': 'PGRST204', 'details': None, 'hint': None, 'message': \"Could not find the 'phone_number' column of 'tasks' in the schema cache\"}"
```

### Solution:

1. **Log in to Supabase dashboard**
   - Go to your project dashboard
   - Click on "SQL Editor" in the left sidebar

2. **Run the following SQL**
   ```sql
   -- Add phone_number column to tasks table
   ALTER TABLE IF EXISTS public.tasks 
   ADD COLUMN IF NOT EXISTS phone_number TEXT;

   -- Create index for better query performance
   CREATE INDEX IF NOT EXISTS idx_tasks_phone_number ON public.tasks (phone_number);

   -- Comment on column for documentation
   COMMENT ON COLUMN public.tasks.phone_number IS 'Phone number for WhatsApp notifications in international format (e.g., +33668695116)';
   ```

3. **Click "Run" or press Ctrl+Enter**

4. **Restart your backend service**
   - On Render dashboard, click on your backend service
   - Click "Manual Deploy" > "Clear Build Cache & Deploy"

## 3. Verifying Environment Variables

Ensure these environment variables are correctly set in your Render service:

1. **Supabase Configuration**
   - `SUPABASE_URL` or `NEXT_PUBLIC_SUPABASE_URL`
   - `SUPABASE_KEY` or `NEXT_PUBLIC_SUPABASE_ANON_KEY`

2. **Meta WhatsApp Business API Configuration**
   - `META_PHONE_NUMBER_ID`
   - `META_ACCESS_TOKEN`
   - `META_API_VERSION` (should be "v18.0" or newer)
   - `RECIPIENT_PHONE_NUMBER` (should be "33668695116")

3. **OpenAI Configuration**
   - `OPENAI_API_KEY`

4. **Security Token**
   - `VERIFY_TOKEN` (for authenticating cron job requests)

## 4. Testing the Backend After Fixes

1. **Test the health endpoint**
   ```
   https://clem-todo-backend.onrender.com/
   ```

2. **Test a WhatsApp message**
   ```
   https://clem-todo-backend.onrender.com/api/test-whatsapp
   ```

## 5. Common Issues and Solutions

- **"Service not responding" on Render**: Add a `/` health check endpoint to your API
- **"Cold starts" affecting reminders**: Use the cron job to regularly ping your service
- **Database connection issues**: Ensure your IP is allowed in Supabase dashboard
- **WhatsApp message failures**: Verify your Meta Business API setup is complete 