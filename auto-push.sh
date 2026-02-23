#!/bin/bash
# Trading Logs Auto-Push Script
# Checks for uncommitted/unpushed changes and pushes to GitHub

set -e

REPO_DIR="/root/.openclaw/workspace/trading-logs"

cd "$REPO_DIR"

# Step 1: Fetch new Telegram messages first
echo "[$(date -Iseconds)] Fetching Telegram messages..."
bash "$REPO_DIR/fetch-telegram.sh" 2>&1 | tee -a "$REPO_DIR/push.log"

# Load token from .env file
if [ -f "$REPO_DIR/.env" ]; then
    export GITHUB_TOKEN=$(grep GITHUB_TOKEN "$REPO_DIR/.env" | cut -d'=' -f2)
fi

# Check if token is configured
if [ -z "$GITHUB_TOKEN" ]; then
    echo "[$(date -Iseconds)] WARNING: GITHUB_TOKEN not set, skipping push"
    exit 0
fi

# Check if token is configured
if [ -z "$GITHUB_TOKEN" ]; then
    echo "[$(date -Iseconds)] WARNING: GITHUB_TOKEN not set, skipping push"
    exit 0
fi

REMOTE_URL="https://${GITHUB_TOKEN}@github.com/deeptradings/autotrading.git"

# Check if there are any changes
if ! git diff --quiet || ! git diff --cached --quiet; then
    echo "[$(date -Iseconds)] Changes detected, committing..."
    git add -A
    git commit -m "Auto-commit trading logs at $(date -Iseconds)"
fi

# Check if remote exists, if not add it
if ! git remote get-url origin >/dev/null 2>&1; then
    git remote add origin "$REMOTE_URL"
fi

# Update remote URL with current token
git remote set-url origin "$REMOTE_URL"

# Push changes
echo "[$(date -Iseconds)] Pushing to GitHub..."
git push origin main 2>&1 | tee -a "$REPO_DIR/push.log"

echo "[$(date -Iseconds)] Sync complete"
