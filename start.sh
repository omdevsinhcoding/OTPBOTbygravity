#!/bin/bash

echo "====================================="
echo "   🚀 TPBOT Easy Start / Restart     "
echo "====================================="

# 1. Kill old processes to free up port 8080
echo "🧹 Cleaning up old bot processes..."
fuser -k 8080/tcp 2>/dev/null
pkill -f "python run.py" 2>/dev/null
sleep 2

# 2. Activate virtual environment
echo "🐍 Activating Python Environment..."
if [ -d "venv" ]; then
    source venv/bin/activate
else
    echo "❌ ERROR: venv folder not found! Please create it and install requirements."
    exit 1
fi

# 3. Run Database Migrations automatically
echo "🗄️  Updating Database Schema..."
python -m alembic upgrade head
if [ $? -ne 0 ]; then
    echo "❌ ERROR: Database migration failed. Check your DATABASE_URL in .env."
    exit 1
fi

# 4. Start the bot
echo "🤖 Starting the Bot in background..."
nohup python run.py > bot.log 2>&1 &

echo "====================================="
echo "✅ BOT IS RUNNING SUCCESSFULLY!"
echo "📄 To view live logs, run: tail -f bot.log"
echo "====================================="
