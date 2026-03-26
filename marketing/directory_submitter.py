"""
AnchorWithin Directory Submitter
=================================
Scheduled daily at 11:00 AM via Windows Task Scheduler.
Submits/pings product listings to AI tool directories and aggregators.

Usage:
    python -m marketing.directory_submitter
    python -m marketing.directory_submitter --dry-run
    python -m marketing.directory_submitter --list
"""

import argparse
import datetime
import json
import logging
import sys
import urllib.parse
import urllib.request
from pathlib import Path

from . import config

LOG_FILE = config.LOG_DIR / "directory_submitter.log"
STATE_FILE = config.LOG_DIR / "directory_state.json"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler(),
    ],
)
log = logging.getLogger(__name__)

# ── Directory targets ──
# Each entry represents a directory/aggregator where AnchorWithin tools can be listed.
# "method" is how we interact: "ping" = hit a URL, "api" = use their API, "manual" = log reminder.
DIRECTORIES = [
    {
        "name": "Google Ping",
        "method": "ping",
        "url": "https://www.google.com/ping?sitemap=https://ackcreate.github.io/anchorwithin-bundle/sitemap.xml",
        "frequency_days": 7,
    },
    {
        "name": "Bing IndexNow",
        "method": "indexnow",
        "url": "https://www.bing.com/indexnow",
        "frequency_days": 7,
    },
    {
        "name": "Product Hunt",
        "method": "manual",
        "url": "https://www.producthunt.com/posts/new",
        "frequency_days": 90,
        "notes": "Submit each tool individually. Best on Tuesday-Thursday.",
    },
    {
        "name": "AlternativeTo",
        "method": "manual",
        "url": "https://alternativeto.net/manage-apps/",
        "frequency_days": 30,
        "notes": "List as alternatives to Grammarly (resume), TurboTax (tax), Calm (432Hz).",
    },
    {
        "name": "There's An AI For That",
        "method": "manual",
        "url": "https://theresanaiforthat.com/submit/",
        "frequency_days": 30,
        "notes": "Submit each tool with category tags.",
    },
    {
        "name": "AI Tool Directory",
        "method": "manual",
        "url": "https://aitoolsdirectory.com/submit",
        "frequency_days": 30,
        "notes": "Submit bundle page with all 6 tools described.",
    },
    {
        "name": "Futurepedia",
        "method": "manual",
        "url": "https://www.futurepedia.io/submit-tool",
        "frequency_days": 30,
        "notes": "AI tool directory — submit each tool separately.",
    },
    {
        "name": "ToolPilot.ai",
        "method": "manual",
        "url": "https://www.toolpilot.ai/submit",
        "frequency_days": 30,
        "notes": "Submit with screenshots and pricing info.",
    },
    {
        "name": "Indie Hackers",
        "method": "manual",
        "url": "https://www.indiehackers.com/products",
        "frequency_days": 14,
        "notes": "Post a product update or milestone. Share revenue if comfortable.",
    },
    {
        "name": "Hacker News (Show HN)",
        "method": "manual",
        "url": "https://news.ycombinator.com/submitlink",
        "frequency_days": 30,
        "notes": "Show HN post for the most technical tool. Keep title factual.",
    },
    {
        "name": "BetaList",
        "method": "manual",
        "url": "https://betalist.com/submit",
        "frequency_days": 60,
        "notes": "Good for new tool launches. Requires tagline + description.",
    },
    {
        "name": "SaaSHub",
        "method": "manual",
        "url": "https://www.saashub.com/submit",
        "frequency_days": 30,
        "notes": "List as SaaS alternative with pricing comparison.",
    },
]


def load_state() -> dict:
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text())
    return {"submissions": {}}


def save_state(state: dict):
    STATE_FILE.write_text(json.dumps(state, indent=2))


def days_since_last(state: dict, directory_name: str) -> int | None:
    """Return days since last submission, or None if never submitted."""
    last = state["submissions"].get(directory_name)
    if not last:
        return None
    last_date = datetime.date.fromisoformat(last)
    return (datetime.date.today() - last_date).days


def ping_url(url: str, dry_run: bool = False) -> bool:
    """Send a GET request to a URL (sitemap ping, etc.)."""
    if dry_run:
        log.info("[dry-run] Would ping: %s", url)
        return True
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "AnchorWithin-DirectoryBot/1.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            log.info("[ping] %s → %s", url, resp.status)
            return resp.status < 400
    except Exception as exc:
        log.error("[ping] %s → Failed: %s", url, exc)
        return False


def submit_indexnow(dry_run: bool = False) -> bool:
    """Submit URLs to IndexNow (Bing/Yandex)."""
    indexnow_key = config.os.environ.get("INDEXNOW_KEY", "")
    if not indexnow_key:
        log.warning("[indexnow] INDEXNOW_KEY not set — skipping.")
        return False

    urls = [config.BUNDLE_SITE] + [p["url"] for p in config.PRODUCTS]

    if dry_run:
        log.info("[dry-run] Would submit %d URLs to IndexNow", len(urls))
        return True

    payload = json.dumps({
        "host": "ackcreate.github.io",
        "key": indexnow_key,
        "urlList": urls,
    }).encode()

    try:
        req = urllib.request.Request(
            "https://api.indexnow.org/indexnow",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            log.info("[indexnow] Submitted %d URLs → %s", len(urls), resp.status)
            return resp.status < 400
    except Exception as exc:
        log.error("[indexnow] Failed: %s", exc)
        return False


def run(dry_run: bool = False, list_only: bool = False):
    """Main directory submission routine."""
    log.info("=" * 50)
    log.info("AnchorWithin Directory Submitter — %s", datetime.datetime.now().strftime("%Y-%m-%d %H:%M"))

    state = load_state()
    today = datetime.date.today().isoformat()
    actions_taken = []
    reminders = []

    for directory in DIRECTORIES:
        name = directory["name"]
        freq = directory["frequency_days"]
        days = days_since_last(state, name)
        due = days is None or days >= freq

        status = "NEVER" if days is None else f"{days}d ago"

        if list_only:
            marker = "→ DUE" if due else "  ok"
            log.info("  %s %-30s (last: %s, every %dd)", marker, name, status, freq)
            continue

        if not due:
            log.info("[skip] %s — last submitted %s (every %dd)", name, status, freq)
            continue

        log.info("[due] %s — %s", name, status)

        if directory["method"] == "ping":
            success = ping_url(directory["url"], dry_run=dry_run)
            if success:
                state["submissions"][name] = today
                actions_taken.append(f"✓ {name}")
            else:
                actions_taken.append(f"✗ {name}")

        elif directory["method"] == "indexnow":
            success = submit_indexnow(dry_run=dry_run)
            if success:
                state["submissions"][name] = today
                actions_taken.append(f"✓ {name}")
            else:
                actions_taken.append(f"✗ {name}")

        elif directory["method"] == "manual":
            notes = directory.get("notes", "")
            reminders.append(f"• *{name}*: {notes}\n  {directory['url']}")
            # Don't mark as done — user must do it manually
            actions_taken.append(f"📋 {name} (reminder sent)")

    if list_only:
        return

    save_state(state)

    # ── Send Telegram summary ──
    parts = [f"📁 *Directory Submitter* ({today})"]
    if actions_taken:
        parts.append("\n".join(actions_taken))
    if reminders:
        parts.append("\n*Manual submissions due:*\n" + "\n".join(reminders))
    if not actions_taken and not reminders:
        parts.append("Nothing due today.")

    summary = "\n\n".join(parts)
    log.info("Summary:\n%s", summary)
    config.send_telegram(summary)
    log.info("Done.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AnchorWithin Directory Submitter")
    parser.add_argument("--dry-run", action="store_true", help="Preview actions without executing")
    parser.add_argument("--list", action="store_true", help="List all directories and their status")
    args = parser.parse_args()

    run(dry_run=args.dry_run, list_only=args.list)
