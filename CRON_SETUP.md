# Setting Up WhatsApp Reminders with Render Cron Jobs

This guide explains how to set up WhatsApp notifications for your tasks using Meta WhatsApp Business API and Render's free tier with Cron Jobs.

## Why Use a Cron Job?

Render's free tier services spin down after 15 minutes of inactivity. This means the background processes that check for upcoming reminders would stop working when the service is inactive. By using a Cron Job, we can ensure reminders are checked regularly even when the main service is spun down.

## Setup Instructions

### 1. Create Your Render Services

1. **Deploy Your Frontend and Backend**
   - Use the existing `render.yaml` to deploy your frontend and backend services
   - Wait for both services to be fully deployed

### 2. Set Up Meta WhatsApp Business API

1. **Create a Meta Developer Account**
   - Sign up at [developers.facebook.com](https://developers.facebook.com/)
   - Create a new Meta App in the developers dashboard
   - Set up the WhatsApp API in your Meta App

2. **Complete WhatsApp Business Account Setup**
   - Connect your WhatsApp Business Account to your Meta App
   - Set up a phone number for WhatsApp messaging
   - Complete the verification process

3. **Get Your API Credentials**
   - Get your Phone Number ID from the WhatsApp dashboard
   - Generate a Permanent Access Token for your app

### 3. Configure Environment Variables

1. **In the Render Dashboard**
   - Navigate to your backend service (clem-todo-backend)
   - Go to the "Environment" tab
   - Add the following environment variables:
     - `META_PHONE_NUMBER_ID`: Your WhatsApp Phone Number ID
     - `META_ACCESS_TOKEN`: Your Permanent Access Token
     - `META_API_VERSION`: Set to "v18.0" (or the latest version)
     - `RECIPIENT_PHONE_NUMBER`: Default is set to "33668695116" (configured automatically)
     - `VERIFY_TOKEN`: Generate a random string for security (e.g., use `openssl rand -hex 16`)

### 4. Set Up the Cron Job

1. **Create a New Cron Job Service**
   - In the Render dashboard, go to "New+" and select "Cron Job"
   - Give it a name: "check-reminders"
   - Set the schedule to: `0 7-21 * * *` (runs once every hour between 7am and 9pm)
   - Set the command to: 
     ```
     curl -X POST -H "Authorization: Bearer $VERIFY_TOKEN" https://clem-todo-backend.onrender.com/api/check-reminders
     ```
   - Replace `clem-todo-backend` with your actual backend service name if different

2. **Set Environment Variables for the Cron Job**
   - Add `VERIFY_TOKEN` with the exact same value you used in the backend service

### 5. Testing the Setup

1. **Send a Test WhatsApp Message**
   - Use the test endpoint by navigating to:
     ```
     https://clem-todo-backend.onrender.com/api/test-whatsapp
     ```
   - The message will be sent to the predefined number (+33668695116)
   - You should receive a test message on WhatsApp

## Troubleshooting

- **WhatsApp Messages Not Sending**
  - Ensure your Meta App is properly configured for WhatsApp
  - Verify the recipient number is correctly formatted (with country code)
  - Check that your WhatsApp Business account is active and not in a restricted state
  
- **Cron Job Not Triggering**
  - Check the Render logs for the Cron Job
  - Verify the VERIFY_TOKEN matches between the backend and Cron Job
  - Ensure the backend URL is correct in the Cron Job command

## Pricing Information

- **Meta WhatsApp Business API**: First 1,000 conversations per month are FREE
  - After 1,000 conversations: approximately $0.005-$0.03 per conversation
  - Pricing varies by country and conversation type
  - Much more cost-effective than Twilio for monthly usage

- **Render Free Tier**:
  - Includes the Cron Job service at no additional cost
  - Allows your application to use WhatsApp reminders while maintaining free tier benefits

## Future Enhancements

1. **Add Rich Message Templates**: Create template messages with buttons and interactive elements
2. **Implement User Responses**: Allow users to respond to WhatsApp messages to mark tasks as complete
3. **Add Image/Media Support**: Send charts or images with task details for better visualization 