"""
AnchorWithin Auto-Poster
========================
Scheduled daily at 10:00 AM via Windows Task Scheduler.
Posts rotating promotional content to Twitter/X and Reddit.

Usage:
    python -m marketing.auto_poster
    python -m marketing.auto_poster --dry-run
    python -m marketing.auto_poster --platform twitter
    python -m marketing.auto_poster --platform reddit
"""

import argparse
import datetime
import hashlib
import json
import logging
import random
import sys
from pathlib import Path

from . import config

LOG_FILE = config.LOG_DIR / "auto_poster.log"
STATE_FILE = config.LOG_DIR / "poster_state.json"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler(),
    ],
)
log = logging.getLogger(__name__)

# ── Post templates ──
TEMPLATES = [
    # Single-product spotlight
    "🚀 {product_name} — {description}\n\nTry free: {product_url}\nGet all 6 tools for {bundle_price}: {bundle_url}\n\n{hashtags}",
    # Bundle value pitch
    "💡 6 AI tools. One payment. No subscription.\n\nResume Optimizer · Tax Companion · 432Hz Generator · Side Hustle Planner · AI Companion · The Anchor Remembers\n\n{bundle_price} instead of {individual_total}\n{bundle_url}\n\n#AI #tools #productivity",
    # Problem/solution
    "Still juggling resumes, taxes, and side hustle ideas manually?\n\nAnchorWithin bundles 6 AI tools that handle it for you — {bundle_price}, one-time.\n\n{bundle_url}\n\n#AI #automation #sidehustle",
    # Social proof / curiosity
    "What if one toolkit could optimize your resume, track your taxes, plan your side hustle, AND help you relax?\n\nThat's AnchorWithin. 6 tools, {bundle_price}.\n\n{bundle_url}",
    # Single-product deep dive
    "🎵 432 Hz is called the \"frequency of the universe.\"\n\nOur Resonance Generator creates real-time 432Hz audio with particle visuals and guided affirmations.\n\nTry free: https://ackcreate.github.io/resonance-generator/\n\n#432Hz #meditation #wellness",
    # Career focus
    "📝 Your resume gets 6 seconds of attention.\n\nAI Resume Optimizer scores it against job descriptions, finds missing keywords, and rewrites bullets to beat ATS filters.\n\nFree version: https://ackcreate.github.io/resume-optimizer/\n\n#resume #jobsearch #career",
    # Tax season
    "🧾 Freelancers leave $5,000+ in deductions on the table every year.\n\nAI Tax Companion tracks 19 categories — home office, equipment, health insurance, retirement.\n\nFree version: https://ackcreate.github.io/tax-deduction-calculator/\n\n#taxes #freelancer #deductions",
    # Legacy / emotional
    "⚓ Some stories only you can tell.\n\nThe Anchor Remembers uses 25 guided questions to help preserve your memories — with chat, PDF export, and 432Hz comfort audio.\n\nFree version: https://ackcreate.github.io/anchor-remembers/\n\n#legacy #family #memory",
]

REDDIT_SUBREDDITS = [
    {"name": "SideHustle", "product_idx": 3},
    {"name": "freelance", "product_idx": 1},
    {"name": "resumes", "product_idx": 0},
    {"name": "personalfinance", "product_idx": 1},
    {"name": "Meditation", "product_idx": 2},
    {"name": "productivity", "product_idx": 4},
]


def load_state() -> dict:
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text())
    return {"last_template_idx": -1, "last_reddit_idx": -1, "posts": []}


def save_state(state: dict):
    STATE_FILE.write_text(json.dumps(state, indent=2))


def pick_template(state: dict) -> tuple[int, str]:
    """Rotate through templates sequentially, cycling back to start."""
    idx = (state.get("last_template_idx", -1) + 1) % len(TEMPLATES)
    return idx, TEMPLATES[idx]


def fill_template(template: str, product: dict | None = None) -> str:
    """Fill placeholders in a template string."""
    if product is None:
        product = random.choice(config.PRODUCTS)
    return template.format(
        product_name=product["name"],
        description=product["description"],
        product_url=product["url"],
        bundle_price=config.BUNDLE_PRICE,
        bundle_url=config.BUNDLE_URL,
        individual_total=config.INDIVIDUAL_TOTAL,
        hashtags=" ".join(product["hashtags"]),
    )


def post_to_twitter(text: str, dry_run: bool = False) -> bool:
    """Post a tweet using Twitter API v2."""
    if dry_run:
        log.info("[twitter/dry-run] Would post:\n%s", text)
        return True

    if not config.TWITTER_API_KEY:
        log.warning("[twitter] API keys not configured — skipping.")
        return False

    try:
        import tweepy
    except ImportError:
        log.error("[twitter] tweepy not installed. Run: pip install tweepy")
        return False

    try:
        client = tweepy.Client(
            consumer_key=config.TWITTER_API_KEY,
            consumer_secret=config.TWITTER_API_SECRET,
            access_token=config.TWITTER_ACCESS_TOKEN,
            access_token_secret=config.TWITTER_ACCESS_SECRET,
        )
        resp = client.create_tweet(text=text)
        log.info("[twitter] Posted tweet ID: %s", resp.data["id"])
        return True
    except Exception as exc:
        log.error("[twitter] Failed: %s", exc)
        return False


def post_to_reddit(title: str, body: str, subreddit: str, dry_run: bool = False) -> bool:
    """Post to a subreddit using PRAW."""
    if dry_run:
        log.info("[reddit/dry-run] Would post to r/%s:\n  Title: %s\n  Body: %s", subreddit, title, body)
        return True

    if not config.REDDIT_CLIENT_ID:
        log.warning("[reddit] API credentials not configured — skipping.")
        return False

    try:
        import praw
    except ImportError:
        log.error("[reddit] praw not installed. Run: pip install praw")
        return False

    try:
        reddit = praw.Reddit(
            client_id=config.REDDIT_CLIENT_ID,
            client_secret=config.REDDIT_CLIENT_SECRET,
            username=config.REDDIT_USERNAME,
            password=config.REDDIT_PASSWORD,
            user_agent="AnchorWithin Auto-Poster v1.0",
        )
        sub = reddit.subreddit(subreddit)
        submission = sub.submit(title=title, selftext=body)
        log.info("[reddit] Posted to r/%s: %s", subreddit, submission.url)
        return True
    except Exception as exc:
        log.error("[reddit] Failed to post to r/%s: %s", subreddit, exc)
        return False


def run(platforms: list[str] | None = None, dry_run: bool = False):
    """Main auto-poster routine."""
    log.info("=" * 50)
    log.info("AnchorWithin Auto-Poster starting — %s", datetime.datetime.now().strftime("%Y-%m-%d %H:%M"))

    state = load_state()
    today = datetime.date.today().isoformat()
    results = []

    if platforms is None:
        platforms = ["twitter", "reddit"]

    # ── Twitter ──
    if "twitter" in platforms:
        idx, template = pick_template(state)
        product = config.PRODUCTS[idx % len(config.PRODUCTS)]
        text = fill_template(template, product)
        success = post_to_twitter(text, dry_run=dry_run)
        state["last_template_idx"] = idx
        results.append(f"Twitter: {'✓' if success else '✗'}")

    # ── Reddit ──
    if "reddit" in platforms:
        ridx = (state.get("last_reddit_idx", -1) + 1) % len(REDDIT_SUBREDDITS)
        target = REDDIT_SUBREDDITS[ridx]
        product = config.PRODUCTS[target["product_idx"]]
        title = f"{product['name']} — Free AI tool for {product['category'].lower()}"
        body = (
            f"{product['description']}\n\n"
            f"Try the free version: {product['url']}\n\n"
            f"Part of the AnchorWithin toolkit ({config.BUNDLE_PRICE} for all 6): {config.BUNDLE_URL}"
        )
        success = post_to_reddit(title, body, target["name"], dry_run=dry_run)
        state["last_reddit_idx"] = ridx
        results.append(f"Reddit r/{target['name']}: {'✓' if success else '✗'}")

    # ── Save state & notify ──
    state["posts"].append({"date": today, "results": results})
    # Keep only the last 90 days of history
    state["posts"] = state["posts"][-90:]
    save_state(state)

    summary = " | ".join(results)
    log.info("Results: %s", summary)

    config.send_telegram(f"📢 *Auto-Poster* ({today})\n{summary}")
    log.info("Done.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AnchorWithin Auto-Poster")
    parser.add_argument("--dry-run", action="store_true", help="Preview posts without publishing")
    parser.add_argument("--platform", choices=["twitter", "reddit"], help="Post to a specific platform only")
    args = parser.parse_args()

    platforms = [args.platform] if args.platform else None
    run(platforms=platforms, dry_run=args.dry_run)
