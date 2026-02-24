#!/bin/bash

# ==============================================================================
# [DEPRECATED] Master Management Script for Sensex Scalping Algo
# PLEASE USE algo_master.py IN THE ROOT DIRECTORY INSTEAD.
# Example: python3 ../algo_master.py [start|stop|status]
# ==============================================================================

COMMAND=$1
MODE=${2:-paper} # Default to paper if not specified

# Define app names based on mode
if [ "$MODE" == "live" ]; then
    APP_NAME="sensex-scalper"
    SCRIPT="live_trade.py"
else
    APP_NAME="sensex-paper"
    SCRIPT="paper_trade.py"
fi

BASE_DIR="/home/ubuntu/sensex_scalping_algo"
VENV_PYTHON="$BASE_DIR/venv/bin/python"

echo "[$(date '+%Y-%m-%d %H:%M:%S')] Executing: $COMMAND $MODE"

cd "$BASE_DIR" || exit 1

# Ensure directories exist
mkdir -p reports logs

case "$COMMAND" in
    start)
        echo "🚀 Starting $APP_NAME..."
        # 1. Pull latest code from master
        git pull origin master
        
        # 2. Start/Restart via PM2
        if pm2 describe "$APP_NAME" > /dev/null 2>&1; then
            echo "🔄 Restarting existing process..."
            pm2 restart "$APP_NAME"
        else
            echo "🆕 Starting fresh process..."
            pm2 start "$VENV_PYTHON $SCRIPT" --name "$APP_NAME"
            pm2 save
        fi
        echo "✅ $APP_NAME is now running."
        ;;
        
    stop)
        echo "⏹️ Stopping $APP_NAME..."
        if pm2 describe "$APP_NAME" > /dev/null 2>&1; then
            pm2 stop "$APP_NAME"
            echo "✅ $APP_NAME has been stopped."
            
            # For paper mode, generate a final report for the day
            if [ "$MODE" == "paper" ]; then
                echo "📊 Generating end-of-day paper report..."
                "$VENV_PYTHON" tools/export_report.py "reports/paper_summary_$(date +%F).csv" today
            fi
        else
            echo "⚠️ Process $APP_NAME not found. Nothing to stop."
        fi
        ;;
        
    *)
        echo "❌ Usage: $0 [start|stop] [mode: paper|live]"
        exit 1
        ;;
esac
