# Reminder Notifications System

This document explains how the reminder notification system works and recent fixes that were made.

## How Reminders Work

1. When a task is created, one or more reminders are scheduled through the Supabase database.
2. A background service (triggered by API endpoint `/api/check-reminders`) checks for reminders that are due.
3. If a reminder is found, a Pushover notification is sent to the configured recipient.

## Table Prefix Handling

The application supports both development and production environments with different table prefixes:

- Development: Tables have a `dev_` prefix (e.g., `dev_tasks`, `dev_reminders`)
- Production: Tables have no prefix (e.g., `tasks`, `reminders`)

## Fixed Issue: Notification Delivery

**Problem:** Reminders were being detected by the check-reminders service but not processed correctly. This happened because the join operation between tasks and reminders was returning data with the task information under a key that included the table prefix (`dev_tasks` or `tasks`), but the code was looking for it under a generic `tasks` key.

**Solution:** The code now uses a consistent `TASK_KEY` constant that includes the right table prefix based on the environment. This ensures that task data can be properly accessed from the joined query results, regardless of environment.

## Testing Notifications

To test that notifications are working:

1. Create a test reminder using `python create_test_reminder.py` or `python create_past_reminder.py`
2. Trigger a check using `curl -X POST http://localhost:8000/api/check-reminders`
3. Test direct notification using `curl -X POST http://localhost:8000/api/test-pushover`

If you don't receive notifications, check:
- Your Pushover API credentials (PUSHOVER_API_TOKEN, PUSHOVER_USER_KEY)
- The app status to ensure the reminder wasn't already processed
- The server logs for any errors in notification sending

## Pushover Configuration

Refer to PUSHOVER_SETUP.md for details on setting up Pushover for notifications. 