"""
Video Factory — Main Orchestrator
Runs all 18 series on schedule, handles errors gracefully.
Can be run as a service (NSSM on Windows, systemd on Linux).

Usage:
    python factory.py                      # Run scheduler (infinite loop)
    python factory.py --run-once frequency  # Produce one frequency video
    python factory.py --run-once binaural   # Produce one binaural beat video
    python factory.py --run-once all        # Produce one of each
    python factory.py --list                # List all registered series
"""

import argparse
import importlib
import logging
import sys
import time
import traceback
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from config import LOGS_DIR, SCHEDULE

# Set up logging
log_file = LOGS_DIR / f"factory_{datetime.now().strftime('%Y%m%d')}.log"
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger("VideoFactory")

# ---------------------------------------------------------------------------
# Series Registry: maps series name → (module_path, function_name)
# ---------------------------------------------------------------------------
SERIES_REGISTRY = {
    # Original 3
    "frequency":       ("series.frequency",       "produce_frequency_video"),
    "explainer":       ("series.explainer",        "produce_explainer_video"),
    "shorts":          ("series.shorts",           "produce_short"),
    # Tier 1: High-CPM Ambient
    "binaural":        ("series.binaural",         "produce_binaural_video"),
    "sleep_sounds":    ("series.sleep_sounds",     "produce_sleep_sounds_video"),
    "chakra":          ("series.chakra",           "produce_chakra_video"),
    "sleep_stories":   ("series.sleep_stories",    "produce_sleep_story"),
    # Tier 2: Explainer
    "career":          ("series.career",           "produce_career_video"),
    "tax":             ("series.tax",              "produce_tax_video"),
    "productivity":    ("series.productivity",     "produce_productivity_video"),
    "side_hustle":     ("series.side_hustle",      "produce_side_hustle_video"),
    "personal_growth": ("series.personal_growth",  "produce_personal_growth_video"),
    # Tier 3: Shorts + Specialty
    "tool_tips":       ("series.tool_tips",        "produce_tool_tip"),
    "council_career":  ("series.council_career",   "produce_council_career_short"),
    "council_money":   ("series.council_money",    "produce_council_money_short"),
    "affirmations":    ("series.affirmations",     "produce_affirmation_video"),
    "anchor_journal":  ("series.anchor_journal",   "produce_journal_video"),
    "weekly_recap":    ("series.weekly_recap",     "produce_recap_video"),
}


def run_series(name: str) -> dict:
    """Run a single production for any registered series."""
    if name not in SERIES_REGISTRY:
        logger.error(f"Unknown series: {name}")
        return {"success": False, "error": f"Unknown series: {name}"}

    module_path, func_name = SERIES_REGISTRY[name]
    logger.info(f"Starting {name} production...")

    try:
        mod = importlib.import_module(module_path)
        produce_fn = getattr(mod, func_name)
        result = produce_fn()
        if result.get("success"):
            logger.info(f"{name} completed: {result.get('title')}")
        else:
            logger.error(f"{name} failed: {result.get('error')}")
        return result
    except Exception as e:
        logger.error(f"{name} crashed: {e}\n{traceback.format_exc()}")
        try:
            from lib.telegram import send_error
            send_error(f"{name} production crashed:\n{e}")
        except Exception:
            pass
        return {"success": False, "error": str(e)}


def run_once(series: str) -> dict:
    """Run a single production for the specified series (or all)."""
    if series == "all":
        results = {}
        for s in SERIES_REGISTRY:
            results[s] = run_series(s)
        return results
    return run_series(series)


def run_scheduler():
    """Run the production scheduler (infinite loop)."""
    import schedule as sched

    logger.info("=" * 60)
    logger.info("VIDEO FACTORY STARTING — 18 SERIES")
    logger.info("=" * 60)

    try:
        from lib.telegram import send_notification
        series_count = len(SERIES_REGISTRY)
        send_notification(f"🏭 Video Factory started — {series_count} series on schedule.")
    except Exception:
        pass

    # Register all series from SCHEDULE config
    for name, conf in SCHEDULE.items():
        if name not in SERIES_REGISTRY:
            logger.warning(f"Schedule entry '{name}' has no registered producer — skipping")
            continue

        # Create a closure to capture the series name
        def make_runner(series_name):
            return lambda: run_series(series_name)

        if "days_interval" in conf:
            sched.every(conf["days_interval"]).days.at(conf["time"]).do(make_runner(name))
        elif "weekdays" in conf:
            for day in conf["weekdays"]:
                getattr(sched.every(), day).at(conf["time"]).do(make_runner(name))

    logger.info(f"Registered {len(sched.get_jobs())} scheduled jobs:")
    for job in sched.get_jobs():
        logger.info(f"  {job}")

    # Main loop
    while True:
        try:
            sched.run_pending()
        except Exception as e:
            logger.error(f"Scheduler error: {e}")
            try:
                from lib.telegram import send_error
                send_error(f"Scheduler error:\n{e}")
            except Exception:
                pass
        time.sleep(60)


def main():
    all_series = list(SERIES_REGISTRY.keys()) + ["all"]

    parser = argparse.ArgumentParser(description="Video Factory — Autonomous Video Production (18 Series)")
    parser.add_argument("--run-once", choices=all_series, metavar="SERIES",
                        help=f"Produce one video immediately. Options: {', '.join(all_series)}")
    parser.add_argument("--list", action="store_true",
                        help="List all registered series and exit")
    args = parser.parse_args()

    if args.list:
        print(f"\n{'='*60}")
        print(f"VIDEO FACTORY — {len(SERIES_REGISTRY)} REGISTERED SERIES")
        print(f"{'='*60}")
        for name, (mod, func) in SERIES_REGISTRY.items():
            sched_info = SCHEDULE.get(name, {})
            if "days_interval" in sched_info:
                freq = f"every {sched_info['days_interval']} days at {sched_info['time']}"
            elif "weekdays" in sched_info:
                freq = f"{', '.join(sched_info['weekdays'])} at {sched_info['time']}"
            else:
                freq = "unscheduled"
            print(f"  {name:20s} → {mod}.{func}  [{freq}]")
        print()
        sys.exit(0)

    if args.run_once:
        result = run_once(args.run_once)
        if isinstance(result, dict) and "success" in result:
            sys.exit(0 if result.get("success") else 1)
        sys.exit(0)
    else:
        run_scheduler()


if __name__ == "__main__":
    main()
