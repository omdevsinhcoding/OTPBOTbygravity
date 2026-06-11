#!/bin/bash

echo "🚀 Setting up TPBOT as a background service..."

# Get current user and path
CURRENT_USER=$(whoami)
DIR=$(pwd)

# Create the service file
cat <<EOF | sudo tee /etc/systemd/system/tpbot.service > /dev/null
[Unit]
Description=TPBOT Telegram Bot & Verification Server
After=network.target

[Service]
User=$CURRENT_USER
WorkingDirectory=$DIR
ExecStart=$DIR/venv/bin/python run.py
Restart=always
RestartSec=5
StandardOutput=syslog
StandardError=syslog
SyslogIdentifier=tpbot

[Install]
WantedBy=multi-user.target
EOF

# Reload and enable
sudo systemctl daemon-reload
sudo systemctl enable tpbot
sudo systemctl start tpbot

echo "✅ TPBOT is now running in the background!"
echo ""
echo "🎉 You can now safely close PowerShell! The bot will run forever."
echo "If your VPS restarts, the bot will automatically turn itself back on."
echo ""
echo "📌 Useful Commands:"
echo "To check status : sudo systemctl status tpbot"
echo "To view logs    : sudo journalctl -u tpbot -f"
echo "To stop bot     : sudo systemctl stop tpbot"
echo "To restart bot  : sudo systemctl restart tpbot"
