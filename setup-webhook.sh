#!/bin/bash
# Setup Telegram Webhook with HTTPS tunnel

SCRIPT_DIR="/root/.openclaw/workspace/trading-logs"
ENV_FILE="$SCRIPT_DIR/.env"
WEBHOOK_PORT=8080

# Load environment variables
if [ -f "$ENV_FILE" ]; then
    export $(grep -v '^#' "$ENV_FILE" | xargs)
fi

echo "🦞 Telegram Webhook Setup"
echo "========================="
echo ""

# Check if webhook server is running
if ! systemctl is-active --quiet telegram-webhook; then
    echo "❌ Webhook server is not running"
    echo "Starting webhook server..."
    systemctl start telegram-webhook
fi

echo "✅ Webhook server is running on port $WEBHOOK_PORT"
echo ""

# Start localtunnel in background
echo "🚀 Starting HTTPS tunnel..."
TUNNEL_OUTPUT=$(mktemp)
lt --port $WEBHOOK_PORT > "$TUNNEL_OUTPUT" 2>&1 &
TUNNEL_PID=$!
sleep 5

# Get tunnel URL
TUNNEL_URL=$(grep -oP 'your url is: \Khttps://[^\s]+' "$TUNNEL_OUTPUT" | head -1)

if [ -z "$TUNNEL_URL" ]; then
    echo "❌ Failed to create tunnel"
    cat "$TUNNEL_OUTPUT"
    exit 1
fi

echo "✅ Tunnel URL: $TUNNEL_URL"
echo ""

# Save tunnel PID for later
echo "$TUNNEL_PID" > "$SCRIPT_DIR/.tunnel_pid"

# Set Telegram webhook
echo "📡 Configuring Telegram webhook..."
WEBHOOK_RESPONSE=$(curl -s -X POST "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/setWebhook" \
  -d "url=${TUNNEL_URL}" \
  -d "allowed_updates=[\"message\"]")

WEBHOOK_OK=$(echo "$WEBHOOK_RESPONSE" | jq -r '.ok')

if [ "$WEBHOOK_OK" = "true" ]; then
    echo "✅ Webhook configured successfully!"
    echo ""
    echo "Webhook URL: $TUNNEL_URL"
    echo "Chat ID: $TELEGRAM_CHAT_ID"
    echo ""
    echo "📝 Test by sending a message to the Telegram group"
    echo "   Logs will be written to: $SCRIPT_DIR/logs/"
    echo "   Webhook logs: $SCRIPT_DIR/webhook.log"
else
    echo "❌ Failed to configure webhook"
    echo "$WEBHOOK_RESPONSE" | jq .
    exit 1
fi

# Cleanup
rm -f "$TUNNEL_OUTPUT"
