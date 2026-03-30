# Freqtrade setup script for AnchorWithin trading bot (Windows)
$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectDir = Split-Path -Parent $ScriptDir
Set-Location $ProjectDir

Write-Host "=== AnchorWithin Freqtrade Setup ===" -ForegroundColor Cyan

# Check Python
try {
    $pythonVersion = python --version 2>&1
    Write-Host "Python version: $pythonVersion"
} catch {
    Write-Host "ERROR: Python is required. Install Python 3.10+ from python.org" -ForegroundColor Red
    exit 1
}

# Create virtual environment
if (-not (Test-Path ".venv")) {
    Write-Host "Creating virtual environment..."
    python -m venv .venv
}

Write-Host "Activating virtual environment..."
& .\.venv\Scripts\Activate.ps1

# Install dependencies
Write-Host "Installing Freqtrade and dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Initialize Freqtrade user directory
Write-Host "Initializing Freqtrade user directory..."
try { freqtrade create-userdir --userdir user_data } catch { }

# Copy config template if real config doesn't exist
if (-not (Test-Path "user_data\config.json")) {
    Write-Host "Creating config.json from template..."
    Copy-Item "user_data\config.json.example" "user_data\config.json"

    # Substitute environment variables from .env
    if (Test-Path ".env") {
        Write-Host "Loading API keys from .env..."
        $envContent = Get-Content ".env" | Where-Object { $_ -match "=" -and $_ -notmatch "^\s*#" }
        $envVars = @{}
        foreach ($line in $envContent) {
            $parts = $line -split "=", 2
            $envVars[$parts[0].Trim()] = $parts[1].Trim()
        }

        $config = Get-Content "user_data\config.json" -Raw
        if ($envVars.ContainsKey("KRAKEN_API_KEY")) {
            $config = $config.Replace("YOUR_KRAKEN_API_KEY", $envVars["KRAKEN_API_KEY"])
        }
        if ($envVars.ContainsKey("KRAKEN_PRIVATE_KEY")) {
            $config = $config.Replace("YOUR_KRAKEN_PRIVATE_KEY", $envVars["KRAKEN_PRIVATE_KEY"])
        }
        if ($envVars.ContainsKey("TELEGRAM_BOT_TOKEN")) {
            $config = $config.Replace("YOUR_TELEGRAM_BOT_TOKEN", $envVars["TELEGRAM_BOT_TOKEN"])
        }
        if ($envVars.ContainsKey("TELEGRAM_CHAT_ID")) {
            $config = $config.Replace("YOUR_TELEGRAM_CHAT_ID", $envVars["TELEGRAM_CHAT_ID"])
        }
        Set-Content "user_data\config.json" $config

        Write-Host "API keys injected into config.json" -ForegroundColor Green
    } else {
        Write-Host "WARNING: No .env file found. Copy .env.example to .env and fill in your keys." -ForegroundColor Yellow
    }
} else {
    Write-Host "config.json already exists, skipping..."
}

# Download historical data
Write-Host ""
Write-Host "Downloading historical data for backtesting..."
try {
    freqtrade download-data `
        --config user_data/config.json `
        --pairs BTC/USD ETH/USD `
        --timerange 20260101-20260329 `
        --timeframe 5m
} catch {
    Write-Host "WARNING: Data download failed. You may need to configure API keys first." -ForegroundColor Yellow
}

Write-Host ""
Write-Host "=== Setup Complete ===" -ForegroundColor Green
Write-Host ""
Write-Host "Next steps:"
Write-Host "  1. Copy .env.example to .env and fill in your API keys (if not done)"
Write-Host "  2. Backtest:  freqtrade backtesting --strategy AnchorRSI --config user_data/config.json --timerange 20260101-20260329"
Write-Host "  3. Dry-run:   freqtrade trade --strategy AnchorRSI --config user_data/config.json --dry-run"
Write-Host "  4. Live:      freqtrade trade --strategy AnchorRSI --config user_data/config.json"
Write-Host ""
