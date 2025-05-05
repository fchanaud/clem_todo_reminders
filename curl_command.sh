#!/bin/bash
# Script to test the WhatsApp API endpoint

echo "Testing WhatsApp API endpoint..."
curl -X POST http://localhost:8000/api/test-whatsapp -v

echo ""
echo "If you still see errors, check the server logs for details" 