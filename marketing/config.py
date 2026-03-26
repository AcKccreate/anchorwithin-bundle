"""Shared configuration for AnchorWithin marketing automation."""

import os
from pathlib import Path

# ── Paths ──
BASE_DIR = Path(__file__).resolve().parent.parent
LOG_DIR = BASE_DIR / "logs"
LOG_DIR.mkdir(exist_ok=True)

# ── Product catalog ──
PRODUCTS = [
    {
        "name": "AI Resume Optimizer",
        "slug": "resume-optimizer",
        "url": "https://ackcreate.github.io/resume-optimizer/",
        "category": "Career",
        "price": "$4.99",
        "description": "Score your resume against any job description. AI-rewrite bullet points. Beat ATS filters.",
        "hashtags": ["#resume", "#jobsearch", "#career", "#AI"],
    },
    {
        "name": "AI Tax Companion",
        "slug": "tax-companion",
        "url": "https://ackcreate.github.io/tax-deduction-calculator/",
        "category": "Finance",
        "price": "$4.99",
        "description": "Year-round tax tracking for freelancers. 19 deduction categories. Finds what you're missing.",
        "hashtags": ["#taxes", "#freelancer", "#finance", "#AI"],
    },
    {
        "name": "432 Hz Resonance Generator",
        "slug": "resonance-generator",
        "url": "https://ackcreate.github.io/resonance-generator/",
        "category": "Wellness",
        "price": "$2.99",
        "description": "Real-time 432Hz audio synthesis with particle visuals, affirmations, and guided sessions.",
        "hashtags": ["#432Hz", "#meditation", "#wellness", "#healing"],
    },
    {
        "name": "AI Side Hustle Planner",
        "slug": "side-hustle-planner",
        "url": "https://ackcreate.github.io/side-hustle-planner/",
        "category": "Income",
        "price": "$2.99",
        "description": "Answer 5 questions. Get a personalized 30-day action plan for your side hustle.",
        "hashtags": ["#sidehustle", "#entrepreneur", "#income", "#AI"],
    },
    {
        "name": "AI Companion",
        "slug": "ai-companion",
        "url": "https://ackcreate.github.io/ai-companion/",
        "category": "Productivity",
        "price": "$2.99",
        "description": "Chat companion with 3 personalities, conversation memory, follow-up questions, and 4 built-in games.",
        "hashtags": ["#AI", "#chatbot", "#productivity", "#companion"],
    },
    {
        "name": "The Anchor Remembers",
        "slug": "anchor-remembers",
        "url": "https://ackcreate.github.io/anchor-remembers/",
        "category": "Personal",
        "price": "$4.99",
        "description": "25 guided questions for preserving what matters. Memory chat, PDF export, 432Hz comfort audio.",
        "hashtags": ["#legacy", "#memory", "#family", "#AI"],
    },
]

BUNDLE_URL = "https://buy.stripe.com/00wbJ2d5A7mv5obc6S67S0d"
BUNDLE_SITE = "https://ackcreate.github.io/anchorwithin-bundle/"
BUNDLE_PRICE = "$19.99"
INDIVIDUAL_TOTAL = "$22.96"

# ── API keys (from environment) ──
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")

TWITTER_API_KEY = os.environ.get("TWITTER_API_KEY", "")
TWITTER_API_SECRET = os.environ.get("TWITTER_API_SECRET", "")
TWITTER_ACCESS_TOKEN = os.environ.get("TWITTER_ACCESS_TOKEN", "")
TWITTER_ACCESS_SECRET = os.environ.get("TWITTER_ACCESS_SECRET", "")

REDDIT_CLIENT_ID = os.environ.get("REDDIT_CLIENT_ID", "")
REDDIT_CLIENT_SECRET = os.environ.get("REDDIT_CLIENT_SECRET", "")
REDDIT_USERNAME = os.environ.get("REDDIT_USERNAME", "")
REDDIT_PASSWORD = os.environ.get("REDDIT_PASSWORD", "")

STRIPE_SECRET_KEY = os.environ.get("STRIPE_SECRET_KEY", "")

# ── Telegram helper ──
def send_telegram(message: str) -> bool:
    """Send a message via the AnchorWithin Telegram bot."""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("[telegram] TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID not set — skipping.")
        return False
    import urllib.request
    import urllib.parse
    import json

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    data = urllib.parse.urlencode({
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "Markdown",
    }).encode()
    try:
        req = urllib.request.Request(url, data=data)
        with urllib.request.urlopen(req, timeout=15) as resp:
            result = json.loads(resp.read())
            if result.get("ok"):
                print("[telegram] Message sent.")
                return True
            print(f"[telegram] API error: {result}")
            return False
    except Exception as exc:
        print(f"[telegram] Failed: {exc}")
        return False
