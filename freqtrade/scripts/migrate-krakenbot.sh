#!/usr/bin/env bash
# Migration script: Stop KrakenBot, start FreqtradeBot (Linux/systemd)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

echo "=== KrakenBot → FreqtradeBot Migration ==="

# Stop and disable old KrakenBot service
if systemctl list-units --full --all 2>/dev/null | grep -q "krakenbot"; then
    echo "Stopping KrakenBot service..."
    sudo systemctl stop krakenbot
    sudo systemctl disable krakenbot
    echo "KrakenBot service stopped and disabled."
else
    echo "KrakenBot service not found (already removed or not installed)."
fi

# Create FreqtradeBot systemd service
SERVICE_FILE="/etc/systemd/system/freqtradebot.service"
PYTHON_PATH="$PROJECT_DIR/.venv/bin/python"
FREQTRADE_PATH="$PROJECT_DIR/.venv/bin/freqtrade"

echo "Creating FreqtradeBot systemd service..."
sudo tee "$SERVICE_FILE" > /dev/null << EOF
[Unit]
Description=FreqtradeBot - AnchorWithin Trading Bot
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=$(whoami)
WorkingDirectory=$PROJECT_DIR
ExecStart=$FREQTRADE_PATH trade --strategy AnchorRSI --config user_data/config.json
Restart=on-failure
RestartSec=30
StandardOutput=append:$PROJECT_DIR/user_data/logs/freqtradebot.log
StandardError=append:$PROJECT_DIR/user_data/logs/freqtradebot.log

[Install]
WantedBy=multi-user.target
EOF

# Create logs directory
mkdir -p "$PROJECT_DIR/user_data/logs"

# Reload systemd and start
sudo systemctl daemon-reload
sudo systemctl enable freqtradebot
sudo systemctl start freqtradebot

echo ""
echo "=== Migration Complete ==="
echo "FreqtradeBot service is now running."
echo ""
echo "Useful commands:"
echo "  Status:   sudo systemctl status freqtradebot"
echo "  Logs:     journalctl -u freqtradebot -f"
echo "  Stop:     sudo systemctl stop freqtradebot"
echo "  Restart:  sudo systemctl restart freqtradebot"
echo ""
