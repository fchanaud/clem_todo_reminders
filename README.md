# Task Manager Web Application

A simple, responsive task manager web application built with Next.js, Python, and Supabase. Includes reminders via Pushover notifications and PWA support for iPhone.

## Features

- Create tasks with title, due time, and priority
- View all tasks in a responsive table
- Delete tasks
- Mobile-friendly interface
- Real-time updates with Supabase
- Push notifications for task reminders via Pushover
- Progressive Web App (PWA) support for iPhone and other devices

## Tech Stack

- Frontend: Next.js with TypeScript
- Backend: Python (FastAPI)
- Database: Supabase
- Styling: Tailwind CSS
- Notifications: Pushover API

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

4. Create a `.env` file in the root directory with your Supabase credentials:
   ```
   NEXT_PUBLIC_SUPABASE_URL=your_supabase_url
   NEXT_PUBLIC_SUPABASE_ANON_KEY=your_supabase_anon_key
   ```

5. For notifications, set up Pushover (see [PUSHOVER_SETUP.md](PUSHOVER_SETUP.md) for details):
   ```
   PUSHOVER_API_TOKEN=your_pushover_token
   PUSHOVER_USER_KEY=your_pushover_key
   ```

6. Generate PWA icons (see [PWA_ICONS_GUIDE.md](PWA_ICONS_GUIDE.md) for details):
   ```bash
   npm install canvas   # Required for icon generation
   npm run generate-icons
   ```

7. Start the development server:
   ```bash
   npm run dev
   ```

8. Start the Python backend:
   ```bash
   python api/server.py
   ```

## Using as a Progressive Web App (PWA)

This application can be installed as a PWA on iOS and Android devices:

### On iPhone:
1. Open the app in Safari
2. Tap the Share button at the bottom
3. Scroll down and tap "Add to Home Screen"
4. Name your app and tap "Add"

### On Android:
1. Open the app in Chrome
2. Tap the three-dot menu
3. Tap "Add to Home Screen"
4. Follow the prompts

The app will install on your home screen and can be launched like any native app, with full screen display and offline capabilities.

## Project Structure

```
├── app/                 # Next.js app directory
│   ├── components/      # React components
│   ├── lib/            # Utility functions
│   └── page.tsx        # Main page
├── api/                # Python backend
│   ├── server.py       # FastAPI server
│   └── migrations/     # Database migrations
├── public/             # Static files
│   ├── icons/          # PWA icons
│   ├── manifest.webmanifest # PWA manifest
│   ├── sw.js           # Service Worker
│   └── offline.html    # Offline fallback page
└── styles/            # CSS styles
```

## Database Schema

The Supabase database contains the following tables:

```sql
create table tasks (
  id uuid default uuid_generate_v4() primary key,
  title text not null,
  due_time timestamp with time zone not null,
  priority text not null,
  created_at timestamp with time zone default now(),
  completed boolean default false,
  phone_number text
);

create table reminders (
  id uuid default uuid_generate_v4() primary key,
  task_id uuid references tasks(id) on delete cascade,
  reminder_time timestamp with time zone not null,
  created_at timestamp with time zone default now()
);

create table app_status (
  id uuid default uuid_generate_v4() primary key,
  name text unique not null,
  value text not null,
  created_at timestamp with time zone default now(),
  updated_at timestamp with time zone default now()
);

create table processed_reminders (
  id uuid default uuid_generate_v4() primary key,
  reminder_id uuid references reminders(id) on delete cascade,
  processed_at timestamp with time zone not null,
  message_id text,
  created_at timestamp with time zone default current_timestamp
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
   - `PUSHOVER_API_TOKEN`
   - `PUSHOVER_USER_KEY`

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
4. Create a `.env` file in the root directory with:
   ```
   NEXT_PUBLIC_SUPABASE_URL=your_supabase_url
   NEXT_PUBLIC_SUPABASE_ANON_KEY=your_supabase_key
   OPENAI_API_KEY=your_openai_key
   PUSHOVER_API_TOKEN=your_pushover_token
   PUSHOVER_USER_KEY=your_pushover_key
   ```
5. Start the development servers:
   ```
   npm run dev
   cd api && uvicorn server:app --reload
   ```

## Troubleshooting

If you encounter connection issues with Supabase, check your environment variables and ensure they are properly set in your Render deployment settings.

The application is deployed at:
- Frontend: https://clem-todo-frontend.onrender.com
- Backend: https://clem-todo-backend.onrender.com
