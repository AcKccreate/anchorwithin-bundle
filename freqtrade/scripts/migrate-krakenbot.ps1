# Migration script: Stop KrakenBot, start FreqtradeBot (Windows/NSSM)
$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectDir = Split-Path -Parent $ScriptDir

Write-Host "=== KrakenBot -> FreqtradeBot Migration ===" -ForegroundColor Cyan

# Check for NSSM
if (-not (Get-Command nssm -ErrorAction SilentlyContinue)) {
    Write-Host "ERROR: NSSM is required. Download from https://nssm.cc/" -ForegroundColor Red
    Write-Host "Install NSSM and add it to your PATH, then re-run this script."
    exit 1
}

# Stop and remove old KrakenBot service
Write-Host "Checking for existing KrakenBot service..."
$krakenService = Get-Service -Name "KrakenBot" -ErrorAction SilentlyContinue
if ($krakenService) {
    Write-Host "Stopping KrakenBot service..."
    nssm stop KrakenBot
    Start-Sleep -Seconds 3
    Write-Host "Removing KrakenBot service..."
    nssm remove KrakenBot confirm
    Write-Host "KrakenBot service stopped and removed." -ForegroundColor Green
} else {
    Write-Host "KrakenBot service not found (already removed or not installed)."
}

# Register FreqtradeBot as NSSM service
$PythonPath = Join-Path $ProjectDir ".venv\Scripts\python.exe"
$FreqtradePath = Join-Path $ProjectDir ".venv\Scripts\freqtrade.exe"
$ConfigPath = Join-Path $ProjectDir "user_data\config.json"
$LogDir = Join-Path $ProjectDir "user_data\logs"

# Create logs directory
if (-not (Test-Path $LogDir)) {
    New-Item -ItemType Directory -Path $LogDir | Out-Null
}

Write-Host "Registering FreqtradeBot service with NSSM..."
nssm install FreqtradeBot $FreqtradePath trade --strategy AnchorRSI --config $ConfigPath
nssm set FreqtradeBot AppDirectory $ProjectDir
nssm set FreqtradeBot DisplayName "FreqtradeBot - AnchorWithin Trading Bot"
nssm set FreqtradeBot Description "Freqtrade trading bot with AnchorRSI strategy on Kraken exchange"
nssm set FreqtradeBot Start SERVICE_AUTO_START
nssm set FreqtradeBot AppStdout (Join-Path $LogDir "freqtradebot-stdout.log")
nssm set FreqtradeBot AppStderr (Join-Path $LogDir "freqtradebot-stderr.log")
nssm set FreqtradeBot AppRotateFiles 1
nssm set FreqtradeBot AppRotateBytes 10485760

# Start the service
Write-Host "Starting FreqtradeBot service..."
nssm start FreqtradeBot

Write-Host ""
Write-Host "=== Migration Complete ===" -ForegroundColor Green
Write-Host "FreqtradeBot service is now running."
Write-Host ""
Write-Host "Useful commands:"
Write-Host "  Status:   nssm status FreqtradeBot"
Write-Host "  Stop:     nssm stop FreqtradeBot"
Write-Host "  Restart:  nssm restart FreqtradeBot"
Write-Host "  Edit:     nssm edit FreqtradeBot"
Write-Host "  Logs:     Get-Content $LogDir\freqtradebot-stdout.log -Tail 50"
Write-Host ""
