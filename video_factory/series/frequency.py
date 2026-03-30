"""
Frequency / Sound Healing Video Producer
Produces 1-hour ambient videos with healing frequency tones.
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
from lib.audio_gen import generate_frequency_tone
from lib.visual_gen import generate_frequency_background
from lib.thumbnail import generate_thumbnail
from lib.assembler import assemble_still_video
from lib.uploader import upload_to_youtube
from lib.telegram import send_production_complete, send_error


def _load_templates():
    with open(TEMPLATES_DIR / "frequency_scripts.json") as f:
        return json.load(f)


def _get_next_frequency(templates):
    """Pick the next frequency that hasn't been produced recently."""
    log_path = PRODUCTION_LOG
    produced = set()
    if log_path.exists():
        with open(log_path) as f:
            for entry in json.load(f):
                if entry.get("series") == "frequency":
                    produced.add(entry.get("template_id"))

    for t in templates:
        if t["id"] not in produced:
            return t

    # All produced — cycle back to first
    return templates[0]


def _log_production(entry: dict):
    """Append a production entry to the log."""
    log_path = PRODUCTION_LOG
    log = []
    if log_path.exists():
        with open(log_path) as f:
            log = json.load(f)
    log.append(entry)
    with open(log_path, "w") as f:
        json.dump(log, f, indent=2)


def produce_frequency_video(freq_config: dict = None) -> dict:
    """
    Produce a complete frequency healing video.

    Args:
        freq_config: Optional specific frequency config dict.
                     If None, picks the next unproduced frequency.

    Returns:
        Production result dict.
    """
    templates = _load_templates()
    config = freq_config or _get_next_frequency(templates)

    freq_hz = config["frequency_hz"]
    duration = config["duration_secs"]
    title = config["title"]
    description = config["description"]
    tags = config["tags"]

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    video_id = f"freq_{freq_hz}hz_{timestamp}"

    # Working directory for this production
    work_dir = OUTPUT_DIR / video_id
    work_dir.mkdir(parents=True, exist_ok=True)

    result = {
        "series": "frequency",
        "template_id": config["id"],
        "video_id": video_id,
        "title": title,
        "frequency_hz": freq_hz,
        "timestamp": timestamp,
        "success": False,
    }

    try:
        print(f"\n{'='*60}")
        print(f"PRODUCING: {title}")
        print(f"{'='*60}")

        # Step 1: Generate audio
        print(f"\n[1/5] Generating {freq_hz}Hz tone ({duration}s)...")
        t0 = time.time()
        audio_path = str(work_dir / "audio.mp3")
        generate_frequency_tone(freq_hz, duration, audio_path)
        print(f"  Audio: {os.path.getsize(audio_path) / (1024*1024):.1f} MB ({time.time()-t0:.0f}s)")

        # Step 2: Generate background image
        print(f"\n[2/5] Generating background image...")
        bg_path = str(work_dir / "background.png")
        generate_frequency_background(freq_hz, bg_path)
        print(f"  Background: {bg_path}")

        # Step 3: Generate thumbnail
        print(f"\n[3/5] Generating thumbnail...")
        thumb_path = str(work_dir / "thumbnail.jpg")
        generate_thumbnail(f"{int(freq_hz)}Hz", "Deep Healing Frequency | Sleep Music",
                           thumb_path, style="frequency")
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

        # Step 5: Upload or save locally
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
            series="Sound Healing / Frequency",
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
        send_error(f"Frequency video failed: {title}\n\n{e}")

    # Log production
    _log_production(result)
    return result


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Produce a frequency healing video")
    parser.add_argument("--freq", type=int, help="Specific frequency in Hz")
    parser.add_argument("--duration", type=int, default=60, help="Duration in seconds (default: 60 for testing)")
    args = parser.parse_args()

    if args.freq:
        config = {
            "id": f"test_{args.freq}",
            "frequency_hz": args.freq,
            "duration_secs": args.duration,
            "title": f"{args.freq}Hz — Test Frequency Video",
            "description": f"Test video for {args.freq}Hz frequency.",
            "tags": [f"{args.freq}Hz", "test"],
        }
        produce_frequency_video(config)
    else:
        produce_frequency_video()
