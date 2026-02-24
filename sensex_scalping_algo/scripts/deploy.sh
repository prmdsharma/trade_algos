#!/bin/bash

# [DEPRECATED] Legacy Deployment Script
# PLEASE USE algo_master.py IN THE ROOT DIRECTORY INSTEAD.
# Example: python3 ../algo_master.py deploy sensex_scalping

# Configuration
REMOTE_USER="ubuntu"
REMOTE_HOST="80.225.201.34"
SSH_KEY="~/ocip/ssh-key-2026-02-17.key"
REMOTE_DIR="~/sensex_scalping_algo"

# Mode selection
MODE=${1:-live}

if [ "$MODE" == "live" ]; then
    PM2_APP_NAME="sensex-scalper"
    START_CMD="venv/bin/python live_trade.py"
elif [ "$MODE" == "paper" ]; then
    PM2_APP_NAME="sensex-paper"
    START_CMD="venv/bin/python paper_trade.py"
else
    echo "❌ Error: Invalid mode '$MODE'. Use 'live' or 'paper'."
    exit 1
fi

# 1. Enforce Master Branch
CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)
if [ "$CURRENT_BRANCH" != "master" ]; then
    echo "❌ Error: Deployment is only allowed from the 'master' branch."
    echo "Current branch: $CURRENT_BRANCH"
    exit 1
fi

echo "🚀 Starting Production Deployment ($MODE mode) from 'master'..."

# 2. Sync Files
echo "⬆️ Syncing Files..."
# Create directory on remote if it doesn't exist
ssh -i $SSH_KEY $REMOTE_USER@$REMOTE_HOST "mkdir -p $REMOTE_DIR"

rsync -avz --exclude '.env' --exclude '__pycache__' \
      --exclude '.git' --exclude '.DS_Store' \
      --exclude 'database/trades.db' --exclude 'logs/*' \
      --exclude 'venv' --exclude '.pytest_cache' \
      -e "ssh -i $SSH_KEY" ./ $REMOTE_USER@$REMOTE_HOST:$REMOTE_DIR/

# 3. Restart Services on Remote
echo "🔄 Restarting Remote Services..."
ssh -i $SSH_KEY $REMOTE_USER@$REMOTE_HOST "
    cd $REMOTE_DIR
    
    # Ensure venv exists and sync dependencies
    if [ ! -d \"venv\" ]; then
        echo '⚠️ venv not found. Creating one...'
        python3 -m venv venv
    fi
    echo '📦 Ensuring dependencies are up to date...'
    venv/bin/pip install -r requirements.txt

    echo '--- PM2 Status Before ---'
    pm2 list
    
    echo '--- Restarting $PM2_APP_NAME ---'
    if pm2 describe $PM2_APP_NAME > /dev/null 2>&1; then
        pm2 restart $PM2_APP_NAME
        echo '✅ PM2 process restarted.'
    else
        echo '⚠️ Process not found in PM2, starting fresh...'
        pm2 start '$START_CMD' --name $PM2_APP_NAME
        pm2 save
        echo '✅ PM2 process started and saved.'
    fi
    
    sleep 2
    echo '--- PM2 Status After ---'
    pm2 list
"

echo "✅ Deployment ($MODE mode) Successful!"
