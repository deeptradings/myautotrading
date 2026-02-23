#!/bin/bash
# Keep Telegram webhook tunnel running
# This script should be run as a systemd service or in background

SCRIPT_DIR="/root/.openclaw/workspace/trading-logs"
PID_FILE="$SCRIPT_DIR/.tunnel_pid"
WEBHOOK_PORT=8080

# Load environment
if [ -f "$SCRIPT_DIR/.env" ]; then
    export $(grep -v '^#' "$SCRIPT_DIR/.env" | xargs)
fi

echo "🦞 Telegram Webhook Tunnel Manager"
echo "=================================="

# Check if webhook server is running
if ! systemctl is-active --quiet telegram-webhook; then
    echo "Starting webhook server..."
    systemctl start telegram-webhook
fi

# Kill existing tunnel if running
if [ -f "$PID_FILE" ]; then
    OLD_PID=$(cat "$PID_FILE")
    if kill -0 "$OLD_PID" 2>/dev/null; then
        echo "Stopping existing tunnel (PID: $OLD_PID)..."
        kill "$OLD_PID" 2>/dev/null
        sleep 2
    fi
    rm -f "$PID_FILE"
fi

# Start new tunnel
echo "Starting HTTPS tunnel..."
while true; do
    TUNNEL_OUTPUT=$(mktemp)
    lt --port $WEBHOOK_PORT > "$TUNNEL_OUTPUT" 2>&1 &
    TUNNEL_PID=$!
    echo "$TUNNEL_PID" > "$PID_FILE"
    
    sleep 5
    
    # Get tunnel URL
    TUNNEL_URL=$(grep -oP 'your url is: \Khttps://[^\s]+' "$TUNNEL_OUTPUT" | head -1)
    
    if [ -z "$TUNNEL_URL" ]; then
        echo "Failed to create tunnel, retrying in 10s..."
        rm -f "$TUNNEL_OUTPUT"
        sleep 10
        continue
    fi
    
    echo "✅ Tunnel URL: $TUNNEL_URL"
    
    # Set Telegram webhook
    echo "Configuring Telegram webhook..."
    WEBHOOK_RESPONSE=$(curl -s -X POST "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/setWebhook" \
      -d "url=${TUNNEL_URL}" \
      -d "allowed_updates=[\"message\"]")
    
    WEBHOOK_OK=$(echo "$WEBHOOK_RESPONSE" | jq -r '.ok')
    
    if [ "$WEBHOOK_OK" = "true" ]; then
        echo "✅ Webhook configured: $TUNNEL_URL"
    else
        echo "❌ Webhook config failed, retrying..."
        echo "$WEBHOOK_RESPONSE"
    fi
    
    rm -f "$TUNNEL_OUTPUT"
    
    # Wait for tunnel to exit
    wait $TUNNEL_PID
    
    echo "Tunnel disconnected, reconnecting in 5s..."
    sleep 5
done
