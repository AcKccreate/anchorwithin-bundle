# AnchorWithin Freqtrade Trading Bot

Freqtrade-based trading bot using the **AnchorRSI** strategy on the Kraken exchange.

## Strategy: AnchorRSI

| Parameter | Value |
|-----------|-------|
| Indicators | RSI(14) + MACD(12,26,9) |
| Entry | RSI crosses above 30 AND MACD bullish |
| Exit | RSI crosses below 70 AND MACD bearish |
| Stop-loss | 5% trailing |
| Take profit | 10% |
| Pairs | BTC/USD, ETH/USD |
| Timeframe | 5m |

## Prerequisites

- Python 3.10+
- [TA-Lib C library](https://ta-lib.org/) (`sudo apt-get install libta-lib-dev` on Ubuntu)
- [NSSM](https://nssm.cc/) (Windows service management, optional)

## Quick Start

### 1. Configure API Keys

```bash
cp .env.example .env
# Edit .env with your Kraken API keys and Telegram bot token
```

### 2. Run Setup

**Linux:**
```bash
chmod +x scripts/setup.sh
./scripts/setup.sh
```

**Windows (PowerShell):**
```powershell
.\scripts\setup.ps1
```

### 3. Backtest First

Always backtest before risking real money:

```bash
source .venv/bin/activate  # Linux
# .\.venv\Scripts\Activate.ps1  # Windows

freqtrade backtesting --strategy AnchorRSI --config user_data/config.json --timerange 20260101-20260329
```

- If backtest shows profit → proceed to dry-run
- If backtest shows loss → adjust strategy parameters before going live

### 4. Dry-Run

Paper trade for at least 1 week to validate:

```bash
freqtrade trade --strategy AnchorRSI --config user_data/config.json --dry-run
```

### 5. Go Live

Once dry-run is profitable:

```bash
freqtrade trade --strategy AnchorRSI --config user_data/config.json
```

## Telegram Notifications

1. Create a bot via [@BotFather](https://t.me/BotFather) on Telegram
2. Get your chat ID via [@userinfobot](https://t.me/userinfobot)
3. Add `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` to your `.env` file
4. Run the setup script to inject them into the config

You'll receive notifications for entries, exits, stop-losses, and balance updates.

## Migration from KrakenBot

Stop the old KrakenBot service and register FreqtradeBot:

**Linux:**
```bash
chmod +x scripts/migrate-krakenbot.sh
sudo ./scripts/migrate-krakenbot.sh
```

**Windows (run as Administrator):**
```powershell
.\scripts\migrate-krakenbot.ps1
```

This will:
1. Stop and disable the old KrakenBot service
2. Register FreqtradeBot as an NSSM/systemd service
3. Start the new service automatically

## Service Management

**Linux (systemd):**
```bash
sudo systemctl status freqtradebot
sudo systemctl stop freqtradebot
sudo systemctl restart freqtradebot
journalctl -u freqtradebot -f
```

**Windows (NSSM):**
```powershell
nssm status FreqtradeBot
nssm stop FreqtradeBot
nssm restart FreqtradeBot
```

## Project Structure

```
├── .env.example                 # API key template
├── requirements.txt             # Python dependencies
├── scripts/
│   ├── setup.sh                 # Linux setup
│   ├── setup.ps1                # Windows setup
│   ├── migrate-krakenbot.sh     # Linux migration
│   └── migrate-krakenbot.ps1    # Windows migration
└── user_data/
    ├── config.json.example      # Freqtrade config template
    └── strategies/
        └── AnchorRSI.py         # Trading strategy
```
