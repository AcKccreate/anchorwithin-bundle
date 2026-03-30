"""
Video Factory — Main Orchestrator
Runs all series on schedule, handles errors gracefully.
Can be run as a service (NSSM on Windows, systemd on Linux).

Usage:
    python factory.py                      # Run scheduler (infinite loop)
    python factory.py --run-once frequency  # Produce one frequency video
    python factory.py --run-once explainer  # Produce one explainer video
    python factory.py --run-once shorts     # Produce one Global Council short
    python factory.py --run-once all        # Produce one of each
"""

import argparse
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


def run_frequency():
    """Produce a frequency healing video."""
    logger.info("Starting frequency video production...")
    try:
        from series.frequency import produce_frequency_video
        result = produce_frequency_video()
        if result.get("success"):
            logger.info(f"Frequency video completed: {result.get('title')}")
        else:
            logger.error(f"Frequency video failed: {result.get('error')}")
        return result
    except Exception as e:
        logger.error(f"Frequency production crashed: {e}\n{traceback.format_exc()}")
        try:
            from lib.telegram import send_error
            send_error(f"Frequency production crashed:\n{e}")
        except Exception:
            pass
        return {"success": False, "error": str(e)}


def run_explainer():
    """Produce an explainer video."""
    logger.info("Starting explainer video production...")
    try:
        from series.explainer import produce_explainer_video
        result = produce_explainer_video()
        if result.get("success"):
            logger.info(f"Explainer video completed: {result.get('title')}")
        else:
            logger.error(f"Explainer video failed: {result.get('error')}")
        return result
    except Exception as e:
        logger.error(f"Explainer production crashed: {e}\n{traceback.format_exc()}")
        try:
            from lib.telegram import send_error
            send_error(f"Explainer production crashed:\n{e}")
        except Exception:
            pass
        return {"success": False, "error": str(e)}


def run_shorts():
    """Produce a Global Council short."""
    logger.info("Starting Global Council short production...")
    try:
        from series.shorts import produce_short
        result = produce_short()
        if result.get("success"):
            logger.info(f"Short completed: {result.get('title')}")
        else:
            logger.error(f"Short failed: {result.get('error')}")
        return result
    except Exception as e:
        logger.error(f"Shorts production crashed: {e}\n{traceback.format_exc()}")
        try:
            from lib.telegram import send_error
            send_error(f"Shorts production crashed:\n{e}")
        except Exception:
            pass
        return {"success": False, "error": str(e)}


def run_once(series: str):
    """Run a single production for the specified series."""
    if series == "frequency":
        return run_frequency()
    elif series == "explainer":
        return run_explainer()
    elif series == "shorts":
        return run_shorts()
    elif series == "all":
        results = {}
        for s in ["frequency", "explainer", "shorts"]:
            results[s] = run_once(s)
        return results
    else:
        logger.error(f"Unknown series: {series}")
        return {"success": False, "error": f"Unknown series: {series}"}


def run_scheduler():
    """Run the production scheduler (infinite loop)."""
    import schedule as sched

    logger.info("=" * 60)
    logger.info("VIDEO FACTORY STARTING")
    logger.info(f"Schedule: {SCHEDULE}")
    logger.info("=" * 60)

    try:
        from lib.telegram import send_notification
        send_notification("🏭 Video Factory started and running on schedule.")
    except Exception:
        pass

    # Set up schedules
    freq_conf = SCHEDULE["frequency"]
    exp_conf = SCHEDULE["explainer"]
    shorts_conf = SCHEDULE["shorts"]

    # Frequency: every N days at specified time
    sched.every(freq_conf["days_interval"]).days.at(freq_conf["time"]).do(run_frequency)

    # Explainer: specific weekdays
    for day in exp_conf["weekdays"]:
        getattr(sched.every(), day).at(exp_conf["time"]).do(run_explainer)

    # Shorts: daily
    sched.every(shorts_conf["days_interval"]).days.at(shorts_conf["time"]).do(run_shorts)

    logger.info("Scheduled jobs:")
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
        time.sleep(60)  # Check every minute


def main():
    parser = argparse.ArgumentParser(description="Video Factory — Autonomous Video Production")
    parser.add_argument("--run-once", choices=["frequency", "explainer", "shorts", "all"],
                        help="Produce one video immediately (for testing)")
    args = parser.parse_args()

    if args.run_once:
        result = run_once(args.run_once)
        if isinstance(result, dict) and not isinstance(result.get("success"), dict):
            sys.exit(0 if result.get("success") else 1)
        sys.exit(0)
    else:
        run_scheduler()


if __name__ == "__main__":
    main()
