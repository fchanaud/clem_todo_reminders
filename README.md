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

## Deployment Instructions

### Backend (FastAPI)

Deploy to Render:

1. Create a new Web Service
2. Connect your GitHub repository
3. Configure the following:
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `cd api && uvicorn server:app --host 0.0.0.0 --port $PORT`
4. Add environment variables:
   - `NEXT_PUBLIC_SUPABASE_URL`
   - `NEXT_PUBLIC_SUPABASE_ANON_KEY`
   - `OPENAI_API_KEY`

### Frontend (Next.js)

Deploy to Render:

1. Create a new Web Service
2. Connect your GitHub repository
3. Configure the following:
   - Build Command: `npm install && npm run build`
   - Start Command: `npm start`
4. Add environment variables:
   - `NEXT_PUBLIC_API_URL` = `https://clem-todo-backend.onrender.com`

## Development Setup

1. Clone the repository
2. Install dependencies:
   ```
   npm install
   pip install -r requirements.txt
   ```
3. Create a `.env.local` file in the root with:
   ```
   NEXT_PUBLIC_API_URL=http://localhost:8000
   ```
4. Create a `.env` file in the `/api` directory with:
   ```
   NEXT_PUBLIC_SUPABASE_URL=your_supabase_url
   NEXT_PUBLIC_SUPABASE_ANON_KEY=your_supabase_key
   OPENAI_API_KEY=your_openai_key
   ```
5. Start the development servers:
   ```
   npm run dev
   cd api && uvicorn server:app --reload
   ```

## Troubleshooting

If you encounter any issues with the Supabase client in production, make sure you're using the latest version of the Supabase Python library (2.15.0 or higher).

The application is deployed at:
- Frontend: https://clem-todo-frontend.onrender.com
- Backend: https://clem-todo-backend.onrender.com
