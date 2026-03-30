#!/usr/bin/env bash
# Freqtrade setup script for AnchorWithin trading bot
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_DIR"

echo "=== AnchorWithin Freqtrade Setup ==="

# Check Python version
if ! command -v python3 &>/dev/null; then
    echo "ERROR: Python 3 is required. Install Python 3.10+ first."
    exit 1
fi

PYTHON_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
echo "Python version: $PYTHON_VERSION"

# Check for TA-Lib C library
if ! ldconfig -p 2>/dev/null | grep -q libta_lib; then
    echo ""
    echo "WARNING: TA-Lib C library not found."
    echo "Install it with:"
    echo "  Ubuntu/Debian: sudo apt-get install libta-lib-dev"
    echo "  Fedora/RHEL:   sudo dnf install ta-lib-devel"
    echo "  Or build from source: https://ta-lib.org/"
    echo ""
    read -p "Continue anyway? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Create virtual environment
if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv .venv
fi

echo "Activating virtual environment..."
source .venv/bin/activate

# Install dependencies
echo "Installing Freqtrade and dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Initialize Freqtrade user directory (creates missing subdirs)
echo "Initializing Freqtrade user directory..."
freqtrade create-userdir --userdir user_data 2>/dev/null || true

# Copy config template if real config doesn't exist
if [ ! -f "user_data/config.json" ]; then
    echo "Creating config.json from template..."
    cp user_data/config.json.example user_data/config.json

    # Substitute environment variables from .env
    if [ -f ".env" ]; then
        echo "Loading API keys from .env..."
        set -a
        source .env
        set +a

        if [ -n "${KRAKEN_API_KEY:-}" ]; then
            sed -i "s/YOUR_KRAKEN_API_KEY/$KRAKEN_API_KEY/g" user_data/config.json
        fi
        if [ -n "${KRAKEN_PRIVATE_KEY:-}" ]; then
            sed -i "s/YOUR_KRAKEN_PRIVATE_KEY/$KRAKEN_PRIVATE_KEY/g" user_data/config.json
        fi
        if [ -n "${TELEGRAM_BOT_TOKEN:-}" ]; then
            sed -i "s/YOUR_TELEGRAM_BOT_TOKEN/$TELEGRAM_BOT_TOKEN/g" user_data/config.json
        fi
        if [ -n "${TELEGRAM_CHAT_ID:-}" ]; then
            sed -i "s/YOUR_TELEGRAM_CHAT_ID/$TELEGRAM_CHAT_ID/g" user_data/config.json
        fi

        echo "API keys injected into config.json"
    else
        echo "WARNING: No .env file found. Copy .env.example to .env and fill in your keys."
        echo "Then re-run this script or manually edit user_data/config.json"
    fi
else
    echo "config.json already exists, skipping..."
fi

# Download historical data for backtesting
echo ""
echo "Downloading historical data for backtesting..."
freqtrade download-data \
    --config user_data/config.json \
    --pairs BTC/USD ETH/USD \
    --timerange 20260101-20260329 \
    --timeframe 5m \
    || echo "WARNING: Data download failed. You may need to configure API keys first."

echo ""
echo "=== Setup Complete ==="
echo ""
echo "Next steps:"
echo "  1. Copy .env.example to .env and fill in your API keys (if not done)"
echo "  2. Backtest:  freqtrade backtesting --strategy AnchorRSI --config user_data/config.json --timerange 20260101-20260329"
echo "  3. Dry-run:   freqtrade trade --strategy AnchorRSI --config user_data/config.json --dry-run"
echo "  4. Live:      freqtrade trade --strategy AnchorRSI --config user_data/config.json"
echo ""
