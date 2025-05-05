# New endpoint to test WhatsApp notification
@app.post("/api/test-whatsapp")
async def test_whatsapp_message():
    try:
        # Always use the default number
        recipient = RECIPIENT_PHONE_NUMBER
        if not recipient:
            logger.error("Default phone number not configured")
            raise HTTPException(status_code=400, detail="Default phone number not configured")
            
        # Log Twilio configuration
        logger.info(f"Testing WhatsApp with configured Twilio account")
        logger.info(f"TWILIO_ACCOUNT_SID configured: {bool(TWILIO_ACCOUNT_SID)}")
        logger.info(f"TWILIO_AUTH_TOKEN configured: {bool(TWILIO_AUTH_TOKEN)}")
        logger.info(f"TWILIO_PHONE_NUMBER configured: {TWILIO_PHONE_NUMBER}")
        logger.info(f"Recipient number: {recipient}")
        
        message_id = send_whatsapp_reminder(
            task_title="Test Reminder",
            task_priority="Medium",
            due_time=datetime.now(timezone.utc) + timedelta(hours=1),
            recipient=recipient
        )
        
        if message_id:
            logger.info(f"Test WhatsApp message sent successfully with ID: {message_id}")
            return {"message": "Test WhatsApp message sent successfully", "message_id": message_id, "to": recipient}
        else:
            logger.error("Failed to send WhatsApp message - no message ID returned")
            raise HTTPException(status_code=500, detail="Failed to send WhatsApp message - check server logs")
    except Exception as e:
        import traceback
        error_detail = str(e)
        stack_trace = traceback.format_exc()
        logger.error(f"Error in test_whatsapp_message: {error_detail}")
        logger.error(f"Stack trace: {stack_trace}")
        raise HTTPException(status_code=500, detail=f"Error: {error_detail}") 