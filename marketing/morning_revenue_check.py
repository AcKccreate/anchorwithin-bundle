"""
AnchorWithin Morning Revenue Check
====================================
Scheduled daily at 7:00 AM via Windows Task Scheduler.
Pulls revenue data from Stripe and sends a Telegram summary.

Usage:
    python -m marketing.morning_revenue_check
    python -m marketing.morning_revenue_check --days 7
    python -m marketing.morning_revenue_check --dry-run
"""

import argparse
import datetime
import json
import logging
import urllib.parse
import urllib.request
from pathlib import Path

from . import config

LOG_FILE = config.LOG_DIR / "revenue_check.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler(),
    ],
)
log = logging.getLogger(__name__)


def stripe_api(endpoint: str, params: dict | None = None) -> dict | None:
    """Make a GET request to the Stripe API."""
    if not config.STRIPE_SECRET_KEY:
        log.warning("[stripe] STRIPE_SECRET_KEY not set.")
        return None

    import base64
    url = f"https://api.stripe.com/v1/{endpoint}"
    if params:
        url += "?" + urllib.parse.urlencode(params)

    auth = base64.b64encode(f"{config.STRIPE_SECRET_KEY}:".encode()).decode()
    req = urllib.request.Request(url, headers={
        "Authorization": f"Basic {auth}",
    })

    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read())
    except Exception as exc:
        log.error("[stripe] API error: %s", exc)
        return None


def get_charges_since(since: datetime.datetime) -> list[dict]:
    """Fetch successful charges since a given datetime."""
    timestamp = int(since.timestamp())
    data = stripe_api("charges", {
        "created[gte]": timestamp,
        "limit": 100,
        "expand[]": "data.customer",
    })
    if not data or "data" not in data:
        return []
    return [c for c in data["data"] if c.get("paid") and not c.get("refunded")]


def get_balance() -> dict | None:
    """Fetch current Stripe balance."""
    return stripe_api("balance")


def format_currency(amount_cents: int, currency: str = "usd") -> str:
    """Format cents to dollars."""
    if currency == "usd":
        return f"${amount_cents / 100:.2f}"
    return f"{amount_cents / 100:.2f} {currency.upper()}"


def run(days: int = 1, dry_run: bool = False):
    """Main revenue check routine."""
    log.info("=" * 50)
    log.info("AnchorWithin Revenue Check — %s", datetime.datetime.now().strftime("%Y-%m-%d %H:%M"))

    if dry_run:
        log.info("[dry-run] Would check Stripe for last %d day(s) and send Telegram summary.", days)
        config.send_telegram(
            f"☀️ *Morning Revenue Check* (dry run)\n"
            f"Would check last {days} day(s) of Stripe data."
        )
        return

    if not config.STRIPE_SECRET_KEY:
        msg = (
            "☀️ *Morning Revenue Check*\n\n"
            "⚠️ STRIPE\\_SECRET\\_KEY not configured.\n"
            "Set it as an environment variable to enable revenue tracking."
        )
        log.warning("Stripe key not set.")
        config.send_telegram(msg)
        return

    since = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=days)
    charges = get_charges_since(since)
    balance_data = get_balance()

    # ── Compute metrics ──
    total_revenue = sum(c.get("amount", 0) for c in charges)
    charge_count = len(charges)

    # Breakdown by description/product
    product_counts: dict[str, int] = {}
    product_revenue: dict[str, int] = {}
    for charge in charges:
        desc = charge.get("description", "Unknown")
        # Try to match to a known product
        matched = "Other"
        for product in config.PRODUCTS:
            if product["name"].lower() in desc.lower() or product["slug"] in desc.lower():
                matched = product["name"]
                break
        if "bundle" in desc.lower() or "toolkit" in desc.lower():
            matched = "Complete Toolkit Bundle"
        product_counts[matched] = product_counts.get(matched, 0) + 1
        product_revenue[matched] = product_revenue.get(matched, 0) + charge.get("amount", 0)

    # ── Balance ──
    available = 0
    pending = 0
    if balance_data and "available" in balance_data:
        for b in balance_data["available"]:
            if b.get("currency") == "usd":
                available = b.get("amount", 0)
        for b in balance_data.get("pending", []):
            if b.get("currency") == "usd":
                pending = b.get("amount", 0)

    # ── Build message ──
    period = f"last {days} day{'s' if days > 1 else ''}"
    lines = [
        f"☀️ *Morning Revenue Check*",
        f"📅 {period} ({since.strftime('%b %d')} → {datetime.date.today().strftime('%b %d')})",
        "",
        f"💰 *Revenue:* {format_currency(total_revenue)}",
        f"🛒 *Sales:* {charge_count}",
    ]

    if product_counts:
        lines.append("")
        lines.append("*Breakdown:*")
        for product, count in sorted(product_counts.items(), key=lambda x: -x[1]):
            rev = format_currency(product_revenue[product])
            lines.append(f"  • {product}: {count} sale{'s' if count != 1 else ''} ({rev})")

    lines.append("")
    lines.append(f"🏦 *Stripe Balance:*")
    lines.append(f"  Available: {format_currency(available)}")
    lines.append(f"  Pending: {format_currency(pending)}")

    # ── Daily average ──
    if days > 1 and charge_count > 0:
        daily_avg = total_revenue / days
        lines.append("")
        lines.append(f"📊 *Daily avg:* {format_currency(int(daily_avg))}/day")

    message = "\n".join(lines)
    log.info("Report:\n%s", message)
    config.send_telegram(message)
    log.info("Done.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AnchorWithin Morning Revenue Check")
    parser.add_argument("--days", type=int, default=1, help="Number of days to look back (default: 1)")
    parser.add_argument("--dry-run", action="store_true", help="Preview without hitting Stripe API")
    args = parser.parse_args()

    run(days=args.days, dry_run=args.dry_run)
