# Pushover Notification Setup

This project uses [Pushover](https://pushover.net/) for sending notifications for task reminders. Pushover offers a simple API for sending notifications to iOS, Android, and Desktop devices.

## Why Pushover?

Pushover has several advantages over other notification services:
- One-time purchase instead of monthly fees
- Simple API that's easy to use
- Support for delivery to multiple devices with one API call
- Priority levels for different types of notifications
- Much more cost-effective for regular use

## Setup Instructions

1. **Create a Pushover account**:
   - Go to [https://pushover.net/](https://pushover.net/) and sign up for an account
   - Download the Pushover app on your device(s) and log in

2. **Get your User Key**:
   - After logging in, your user key is shown on the main page
   - This is the `PUSHOVER_USER_KEY` needed for your application

3. **Register an Application**:
   - Go to [https://pushover.net/apps/build](https://pushover.net/apps/build)
   - Create a new application with a name like "Todo Reminders"
   - After creating, you'll receive an API Token
   - This is the `PUSHOVER_API_TOKEN` needed for your application

4. **Add to Environment Variables**:
   - In your project's `.env` file, add:
     ```
     PUSHOVER_API_TOKEN=your_api_token_here
     PUSHOVER_USER_KEY=your_user_key_here
     RECIPIENT_USER_KEY=recipient_user_key_here  # Optional - defaults to PUSHOVER_USER_KEY
     ```

5. **Test the Configuration**:
   - Run `python test_pushover_config.py` to check your configuration
   - Run `python test_pushover.py` to send a test message

## Usage

Once configured, the application will automatically send Pushover notifications for task reminders. You can also test sending notifications directly through the API endpoint:

```
POST /api/test-pushover
```

## Priority Levels

The application uses different priority levels based on task importance:
- High priority tasks: Priority 1 (high priority, bypasses quiet hours)
- Normal/Low priority tasks: Priority 0 (normal priority)

## Troubleshooting

If you're not receiving notifications:

1. Check that your API token and user key are correct in your `.env` file
2. Verify that the Pushover app is installed and that you're logged in
3. Check the server logs for any API errors
4. Run the `test_pushover_config.py` script to verify your setup

For more information, refer to the [Pushover API Documentation](https://pushover.net/api). 