#!/bin/bash
# Setup GitHub Remote - Run this once to configure the remote repository

REPO_DIR="/root/.openclaw/workspace/trading-logs"

echo "🦞 Trading Logs - GitHub Remote Setup"
echo "======================================"
echo ""

# Store token in environment file
read -p "Enter your GitHub Token: " -s GITHUB_TOKEN
echo ""

echo "$GITHUB_TOKEN" > "$REPO_DIR/.env"
chmod 600 "$REPO_DIR/.env"

echo "✅ Token saved to .env file"
echo ""

cd "$REPO_DIR"

# Configure remote
REMOTE_URL="https://${GITHUB_TOKEN}@github.com/deeptradings/autotrading.git"
git remote remove origin 2>/dev/null || true
git remote add origin "$REMOTE_URL"

echo "✅ Remote configured"
echo ""
echo "Running initial push..."
echo ""

# Initial commit if needed
if ! git rev-parse --verify main >/dev/null 2>&1; then
    git add -A
    git commit -m "Initial commit - trading logs setup"
fi

# Push to GitHub
git push -u origin main

echo ""
echo "✅ Setup complete! Your trading logs will auto-sync every minute."
echo "   Logs directory: $REPO_DIR/logs/"
echo "   Push log: $REPO_DIR/push.log"
