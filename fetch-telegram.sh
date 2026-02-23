#!/bin/bash
# Fetch trading logs from Telegram Bot
# Checks for new messages and writes to local log files

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="$SCRIPT_DIR/.env"
LOGS_DIR="$SCRIPT_DIR/logs"
STATE_FILE="$SCRIPT_DIR/.telegram_state"

# Load environment variables
if [ -f "$ENV_FILE" ]; then
    export $(grep -v '^#' "$ENV_FILE" | xargs)
fi

# Check if token is configured
if [ -z "$TELEGRAM_BOT_TOKEN" ] || [ -z "$TELEGRAM_CHAT_ID" ]; then
    echo "[$(date -Iseconds)] WARNING: Telegram credentials not set, skipping fetch"
    exit 0
fi

# Create logs directory if not exists
mkdir -p "$LOGS_DIR"

# Get last update offset from state file
OFFSET=0
if [ -f "$STATE_FILE" ]; then
    OFFSET=$(cat "$STATE_FILE")
fi

# Fetch updates from Telegram Bot API
# Note: For groups, we need to fetch all updates and filter by chat_id
RESPONSE=$(curl -s "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/getUpdates?offset=${OFFSET}&limit=10")

# Extract updates
UPDATES=$(echo "$RESPONSE" | jq -r '.result[]?')

if [ -z "$UPDATES" ]; then
    echo "[$(date -Iseconds)] No new Telegram messages"
    exit 0
fi

# Process each update
echo "$UPDATES" | while read -r update; do
    UPDATE_ID=$(echo "$update" | jq -r '.update_id')
    CHAT_ID=$(echo "$update" | jq -r '.message.chat.id // empty')
    MESSAGE_TEXT=$(echo "$update" | jq -r '.message.text // empty')
    MESSAGE_DATE=$(echo "$update" | jq -r '.message.date // 0')
    
    # Skip if not from our target chat
    if [ "$CHAT_ID" != "$TELEGRAM_CHAT_ID" ]; then
        continue
    fi
    
    if [ -z "$MESSAGE_TEXT" ]; then
        continue
    fi
    
    # Convert Unix timestamp to ISO format
    MESSAGE_TIME=$(date -d "@$MESSAGE_DATE" -Iseconds 2>/dev/null || date -Iseconds)
    
    # Extract date for log file
    LOG_DATE=$(date -d "@$MESSAGE_DATE" +%Y-%m-%d 2>/dev/null || date +%Y-%m-%d)
    LOG_FILE="$LOGS_DIR/${LOG_DATE}.log"
    
    # Parse trading information from message
    # Expected format may vary, adjust parsing as needed
    echo "[$MESSAGE_TIME] TELEGRAM $MESSAGE_TEXT" >> "$LOG_FILE"
    
    # Update offset
    NEW_OFFSET=$((UPDATE_ID + 1))
    echo "$NEW_OFFSET" > "$STATE_FILE"
    
    echo "[$(date -Iseconds)] Processed message $UPDATE_ID from chat $CHAT_ID"
done

# Update offset for next run
LAST_UPDATE_ID=$(echo "$RESPONSE" | jq -r '.result[-1]?.update_id // 0')
if [ "$LAST_UPDATE_ID" != "0" ] && [ "$LAST_UPDATE_ID" != "null" ]; then
    echo $((LAST_UPDATE_ID + 1)) > "$STATE_FILE"
fi

echo "[$(date -Iseconds)] Telegram fetch complete"
