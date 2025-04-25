# Task Manager Web Application

A simple, responsive task manager web application built with Next.js, Python, and Supabase.

## Features

- Create tasks with title, due time, and priority
- View all tasks in a responsive table
- Delete tasks
- Mobile-friendly interface
- Real-time updates with Supabase

## Tech Stack

- Frontend: Next.js with TypeScript
- Backend: Python (FastAPI)
- Database: Supabase
- Styling: Tailwind CSS

## Prerequisites

1. Node.js (v16 or higher)
2. Python 3.8+
3. Supabase account

## Setup

1. Clone the repository
2. Install frontend dependencies:
   ```bash
   npm install
   ```

3. Install backend dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Create a `.env.local` file in the root directory with your Supabase credentials:
   ```
   NEXT_PUBLIC_SUPABASE_URL=your_supabase_url
   NEXT_PUBLIC_SUPABASE_ANON_KEY=your_supabase_anon_key
   ```

5. Start the development server:
   ```bash
   npm run dev
   ```

6. Start the Python backend:
   ```bash
   python api/server.py
   ```

## Project Structure

```
├── app/                 # Next.js app directory
│   ├── components/      # React components
│   ├── lib/            # Utility functions
│   └── page.tsx        # Main page
├── api/                # Python backend
│   ├── server.py       # FastAPI server
│   └── database.py     # Database operations
├── public/             # Static files
└── styles/            # CSS styles
```

## Database Schema

The Supabase database contains a single `tasks` table with the following schema:

```sql
create table tasks (
  id uuid default uuid_generate_v4() primary key,
  title text not null,
  due_time timestamp with time zone not null,
  priority text not null,
  created_at timestamp with time zone default now()
);
```

## Contributing

Feel free to submit issues and enhancement requests!
