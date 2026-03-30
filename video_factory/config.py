"""
Video Factory - Central Configuration
Reads settings from environment variables / .env file.
All paths default to Windows (C:/Users/acase/AnchorWithin/video_factory/).
"""

import os
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Try to load .env from the same directory as this file
# ---------------------------------------------------------------------------
_env_path = Path(__file__).resolve().parent / ".env"
if _env_path.exists():
    with open(_env_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, value = line.partition("=")
                os.environ.setdefault(key.strip(), value.strip())

# ---------------------------------------------------------------------------
# Base paths
# ---------------------------------------------------------------------------
if sys.platform == "win32":
    _default_base = r"C:\Users\acase\AnchorWithin\video_factory"
else:
    _default_base = str(Path(__file__).resolve().parent)

BASE_DIR = Path(os.getenv("VIDEO_FACTORY_BASE", _default_base))
OUTPUT_DIR = BASE_DIR / "output"
SCRIPTS_DIR = BASE_DIR / "scripts"
LOGS_DIR = BASE_DIR / "logs"
TEMPLATES_DIR = BASE_DIR / "templates"
READY_TO_UPLOAD_DIR = Path(os.getenv(
    "READY_TO_UPLOAD_DIR",
    r"C:\Users\acase\AnchorWithin\videos\ready_to_upload" if sys.platform == "win32" else str(BASE_DIR / "ready_to_upload"),
))

# Create directories on import
for d in [OUTPUT_DIR, SCRIPTS_DIR, LOGS_DIR, TEMPLATES_DIR, READY_TO_UPLOAD_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# Telegram
# ---------------------------------------------------------------------------
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

# ---------------------------------------------------------------------------
# YouTube OAuth
# ---------------------------------------------------------------------------
YOUTUBE_CLIENT_SECRETS = os.getenv("YOUTUBE_CLIENT_SECRETS", "")
YOUTUBE_TOKEN_PATH = os.getenv("YOUTUBE_TOKEN_PATH", str(BASE_DIR / "youtube_token.json"))

# ---------------------------------------------------------------------------
# FFmpeg
# ---------------------------------------------------------------------------
FFMPEG_BIN = os.getenv("FFMPEG_BIN", "ffmpeg")
FFPROBE_BIN = os.getenv("FFPROBE_BIN", "ffprobe")

# ---------------------------------------------------------------------------
# Production log
# ---------------------------------------------------------------------------
PRODUCTION_LOG = LOGS_DIR / "production_log.json"

# ---------------------------------------------------------------------------
# Edge-TTS voice presets
# ---------------------------------------------------------------------------
VOICES = {
    "narrator": "en-US-GuyNeural",
    "narrator_female": "en-US-JennyNeural",
    "narrator_calm": "en-GB-SoniaNeural",     # Sleep stories, journaling
    "narrator_warm": "en-US-AriaNeural",       # Affirmations
    # Global Council characters
    "mia": "en-US-JennyNeural",
    "sora": "en-US-AriaNeural",
    "hoshi": "en-GB-SoniaNeural",
    "julian": "en-US-GuyNeural",
    "mateo": "en-GB-RyanNeural",
}

# ---------------------------------------------------------------------------
# Series schedule config
# ---------------------------------------------------------------------------
SCHEDULE = {
    # Original 3
    "frequency":       {"days_interval": 2, "time": "02:00"},
    "explainer":       {"weekdays": ["tuesday", "friday"], "time": "03:00"},
    "shorts":          {"days_interval": 1, "time": "04:00"},
    # Tier 1: High-CPM Ambient
    "binaural":        {"days_interval": 3, "time": "01:00"},
    "sleep_sounds":    {"days_interval": 3, "time": "00:00"},
    "chakra":          {"weekdays": ["saturday"], "time": "01:00"},
    "sleep_stories":   {"days_interval": 4, "time": "22:00"},
    # Tier 2: Explainer
    "career":          {"weekdays": ["wednesday"], "time": "03:00"},
    "tax":             {"weekdays": ["monday"], "time": "03:00"},
    "productivity":    {"weekdays": ["thursday"], "time": "03:00"},
    "side_hustle":     {"weekdays": ["saturday"], "time": "03:00"},
    "personal_growth": {"weekdays": ["sunday"], "time": "05:00"},
    # Tier 3: Shorts + Specialty
    "tool_tips":       {"days_interval": 1, "time": "05:00"},
    "council_career":  {"days_interval": 2, "time": "04:30"},
    "council_money":   {"days_interval": 2, "time": "04:30"},
    "affirmations":    {"days_interval": 3, "time": "06:00"},
    "anchor_journal":  {"weekdays": ["wednesday", "sunday"], "time": "06:00"},
    "weekly_recap":    {"weekdays": ["sunday"], "time": "10:00"},
}

# ---------------------------------------------------------------------------
# Brand constants
# ---------------------------------------------------------------------------
BRAND_UNDERTONE_HZ = 432  # 432Hz undertone in ALL audio
UPLOAD_PRIVACY = "unlisted"  # FENRIR protocol — always unlisted
