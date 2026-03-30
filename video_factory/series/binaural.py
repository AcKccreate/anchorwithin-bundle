"""
Binaural Beats Focus/Sleep Video Producer
Produces stereo binaural beat videos for focus, meditation, and sleep.
"""

import json
import os
import sys
import time
import traceback
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from config import OUTPUT_DIR, TEMPLATES_DIR, LOGS_DIR, PRODUCTION_LOG
from lib.audio_gen import generate_binaural_beat
from lib.visual_gen import generate_binaural_background
from lib.thumbnail import generate_thumbnail
from lib.assembler import assemble_still_video
from lib.uploader import upload_to_youtube
from lib.telegram import send_production_complete, send_error


def _load_templates():
    with open(TEMPLATES_DIR / "binaural_scripts.json") as f:
        return json.load(f)


def _get_next_script(templates):
    """Pick the next binaural script that hasn't been produced recently."""
    produced = set()
    if PRODUCTION_LOG.exists():
        with open(PRODUCTION_LOG) as f:
            for entry in json.load(f):
                if entry.get("series") == "binaural":
                    produced.add(entry.get("template_id"))

    for t in templates:
        if t["id"] not in produced:
            return t

    # All produced — cycle back to first
    return templates[0]


def _log_production(entry: dict):
    """Append a production entry to the log."""
    log = []
    if PRODUCTION_LOG.exists():
        with open(PRODUCTION_LOG) as f:
            log = json.load(f)
    log.append(entry)
    with open(PRODUCTION_LOG, "w") as f:
        json.dump(log, f, indent=2)


def produce_binaural_video(config: dict = None) -> dict:
    """
    Produce a complete binaural beats video.

    Args:
        config: Optional specific script config dict.
                If None, picks the next unproduced script.

    Returns:
        Production result dict.
    """
    templates = _load_templates()
    config = config or _get_next_script(templates)

    base_freq = config["base_freq"]
    beat_freq = config["beat_freq"]
    beat_type = config["beat_type"]
    duration = config["duration_secs"]
    title = config["title"]
    description = config["description"]
    tags = config["tags"]

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    video_id = f"binaural_{beat_type}_{beat_freq}hz_{timestamp}"

    # Working directory for this production
    work_dir = OUTPUT_DIR / video_id
    work_dir.mkdir(parents=True, exist_ok=True)

    result = {
        "series": "binaural",
        "template_id": config["id"],
        "video_id": video_id,
        "title": title,
        "beat_type": beat_type,
        "base_freq": base_freq,
        "beat_freq": beat_freq,
        "timestamp": timestamp,
        "success": False,
    }

    try:
        print(f"\n{'='*60}")
        print(f"PRODUCING: {title}")
        print(f"{'='*60}")

        # Step 1: Generate binaural beat audio
        print(f"\n[1/5] Generating binaural beat (base={base_freq}Hz, beat={beat_freq}Hz, {duration}s)...")
        t0 = time.time()
        audio_path = str(work_dir / "audio.mp3")
        generate_binaural_beat(base_freq, beat_freq, duration, audio_path)
        print(f"  Audio: {os.path.getsize(audio_path) / (1024*1024):.1f} MB ({time.time()-t0:.0f}s)")

        # Step 2: Generate background image
        print(f"\n[2/5] Generating binaural background ({beat_type})...")
        bg_path = str(work_dir / "background.png")
        generate_binaural_background(beat_type, bg_path)
        print(f"  Background: {bg_path}")

        # Step 3: Generate thumbnail
        print(f"\n[3/5] Generating thumbnail...")
        thumb_path = str(work_dir / "thumbnail.jpg")
        generate_thumbnail(f"{beat_freq}Hz {beat_type.capitalize()}",
                           "Binaural Beats | Headphones Required",
                           thumb_path, style="binaural")
        print(f"  Thumbnail: {thumb_path}")

        # Step 4: Assemble video
        print(f"\n[4/5] Assembling video (this may take a while)...")
        t0 = time.time()
        video_path = str(work_dir / f"{video_id}.mp4")
        assembled = assemble_still_video(bg_path, audio_path, video_path, duration=duration)
        if not assembled:
            raise RuntimeError("FFmpeg assembly failed")
        size_mb = os.path.getsize(video_path) / (1024 * 1024)
        print(f"  Video: {size_mb:.1f} MB ({time.time()-t0:.0f}s)")

        # Step 5: Upload (UNLISTED — FENRIR protocol)
        print(f"\n[5/5] Uploading...")
        upload_result = upload_to_youtube(video_path, title, description, tags, thumb_path)

        result["video_path"] = video_path
        result["thumbnail_path"] = thumb_path
        result["uploaded"] = upload_result.get("uploaded", False)
        result["video_url"] = upload_result.get("url")
        result["local_path"] = upload_result.get("local_path")
        result["success"] = True

        # Notify
        send_production_complete(
            series="Binaural Beats",
            title=title,
            video_url=result.get("video_url"),
            local_path=result.get("local_path"),
            thumbnail_path=thumb_path,
        )

        print(f"\n✅ DONE: {title}")
        print(f"   Video: {video_path}")
        if result.get("video_url"):
            print(f"   URL: {result['video_url']}")

    except Exception as e:
        result["error"] = str(e)
        result["traceback"] = traceback.format_exc()
        print(f"\n❌ FAILED: {e}")
        send_error(f"Binaural video failed: {title}\n\n{e}")

    # Log production
    _log_production(result)
    return result


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Produce a binaural beats video")
    parser.add_argument("--base", type=float, help="Base frequency in Hz")
    parser.add_argument("--beat", type=float, help="Beat frequency in Hz")
    parser.add_argument("--type", dest="beat_type", default="alpha", help="Beat type (delta/theta/alpha/beta/gamma)")
    parser.add_argument("--duration", type=int, default=60, help="Duration in seconds (default: 60 for testing)")
    args = parser.parse_args()

    if args.base and args.beat:
        cfg = {
            "id": f"test_{args.beat_type}_{int(args.beat)}",
            "base_freq": args.base,
            "beat_freq": args.beat,
            "beat_type": args.beat_type,
            "duration_secs": args.duration,
            "title": f"{args.beat}Hz {args.beat_type.capitalize()} — Test Binaural Beat",
            "description": f"Test binaural beat video: {args.beat}Hz {args.beat_type}.",
            "tags": ["binaural beats", "test"],
        }
        produce_binaural_video(cfg)
    else:
        produce_binaural_video()
