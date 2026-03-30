"""
Telegram Notifications — sends production alerts via Telegram Bot API.
Gracefully degrades to console logging if credentials are not configured.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID


def _is_configured() -> bool:
    return bool(TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID)


def send_notification(message: str, image_path: str = None) -> bool:
    """
    Send a notification message (and optional image) via Telegram.
    Falls back to console print if not configured.

    Returns True if sent successfully.
    """
    print(f"[telegram] {message}")

    if not _is_configured():
        print("[telegram] Not configured — message logged to console only")
        return False

    try:
        import requests

        base_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"

        if image_path and Path(image_path).exists():
            # Send photo with caption
            with open(image_path, "rb") as photo:
                resp = requests.post(
                    f"{base_url}/sendPhoto",
                    data={"chat_id": TELEGRAM_CHAT_ID, "caption": message[:1024]},
                    files={"photo": photo},
                    timeout=30,
                )
        else:
            # Send text message
            resp = requests.post(
                f"{base_url}/sendMessage",
                data={"chat_id": TELEGRAM_CHAT_ID, "text": message[:4096],
                      "parse_mode": "HTML"},
                timeout=30,
            )

        if resp.status_code == 200:
            print("[telegram] Sent successfully")
            return True
        else:
            print(f"[telegram] Send failed: {resp.status_code} {resp.text[:200]}")
            return False

    except Exception as e:
        print(f"[telegram] Error: {e}")
        return False


def send_error(error_message: str) -> bool:
    """Send an error alert via Telegram."""
    return send_notification(f"🚨 VIDEO FACTORY ERROR\n\n{error_message}")


def send_production_complete(series: str, title: str, video_url: str = None,
                             local_path: str = None, thumbnail_path: str = None) -> bool:
    """Send a production completion notification."""
    msg = f"✅ <b>Video Produced</b>\n\n"
    msg += f"<b>Series:</b> {series}\n"
    msg += f"<b>Title:</b> {title}\n"

    if video_url:
        msg += f"<b>URL:</b> {video_url}\n"
    elif local_path:
        msg += f"<b>Saved:</b> {local_path}\n"

    return send_notification(msg, image_path=thumbnail_path)


if __name__ == "__main__":
    print("[telegram] Module loaded OK.")
    print(f"  Configured: {_is_configured()}")
    send_notification("Test message from Video Factory")
