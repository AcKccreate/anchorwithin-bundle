"""
Affirmations Video Producer — Narrated Long-Form
Produces 10-20 minute affirmation videos with warm TTS + 432Hz background pad.
"""

import json
import os
import sys
import time
import traceback
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from config import OUTPUT_DIR, TEMPLATES_DIR, PRODUCTION_LOG, BRAND_UNDERTONE_HZ
from lib.tts import generate_speech
from lib.audio_gen import generate_background_pad, mix_audio_layers
from lib.visual_gen import generate_gradient_background
from lib.thumbnail import generate_thumbnail
from lib.assembler import assemble_still_video, get_audio_duration
from lib.uploader import upload_to_youtube
from lib.telegram import send_production_complete, send_error


def _load_templates():
    with open(TEMPLATES_DIR / "affirmations_scripts.json") as f:
        return json.load(f)


def _get_next_script(templates):
    produced = set()
    if PRODUCTION_LOG.exists():
        with open(PRODUCTION_LOG) as f:
            for entry in json.load(f):
                if entry.get("series") == "affirmations":
                    produced.add(entry.get("template_id"))

    for t in templates:
        if t["id"] not in produced:
            return t
    return templates[0]


def _log_production(entry: dict):
    log = []
    if PRODUCTION_LOG.exists():
        with open(PRODUCTION_LOG) as f:
            log = json.load(f)
    log.append(entry)
    with open(PRODUCTION_LOG, "w") as f:
        json.dump(log, f, indent=2)


def produce_affirmation_video(config=None) -> dict:
    """Produce a narrated long-form affirmation video with 432Hz undertone."""
    templates = _load_templates()
    config = config or _get_next_script(templates)

    title = config["title"]
    description = config["description"]
    tags = config["tags"]
    narration = config["narration"]

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    video_id = f"aff_{config['id']}_{timestamp}"

    work_dir = OUTPUT_DIR / video_id
    work_dir.mkdir(parents=True, exist_ok=True)

    result = {
        "series": "affirmations",
        "template_id": config["id"],
        "video_id": video_id,
        "title": title,
        "timestamp": timestamp,
        "success": False,
    }

    try:
        print(f"\n{'='*60}")
        print(f"PRODUCING AFFIRMATION: {title}")
        print(f"{'='*60}")

        # Step 1: Generate TTS narration
        print(f"\n[1/5] Generating TTS narration (narrator_warm)...")
        t0 = time.time()
        tts_path = str(work_dir / "tts_raw.mp3")
        generate_speech(narration, character="narrator_warm", output_path=tts_path)
        tts_dur = get_audio_duration(tts_path)
        print(f"  TTS: {os.path.getsize(tts_path) / 1024:.0f} KB, {tts_dur:.0f}s ({time.time()-t0:.1f}s)")

        # Generate 432Hz background pad to match TTS duration
        print("  Generating 432Hz background pad...")
        pad_path = str(work_dir / "pad_432hz.mp3")
        generate_background_pad(BRAND_UNDERTONE_HZ, tts_dur, pad_path)

        # Mix TTS + pad
        audio_path = str(work_dir / "narration_mixed.mp3")
        mix_audio_layers([
            {"path": tts_path, "volume_db": 0},
            {"path": pad_path, "volume_db": -18},
        ], audio_path)
        print(f"  Mixed audio: {os.path.getsize(audio_path) / 1024:.0f} KB ({time.time()-t0:.1f}s)")

        # Step 2: Generate gradient background
        print(f"\n[2/5] Generating gradient background...")
        bg_path = str(work_dir / "background.png")
        generate_gradient_background((8, 5, 20), (40, 20, 60), title, bg_path)
        print(f"  Background: {bg_path}")

        # Step 3: Generate thumbnail
        print(f"\n[3/5] Generating thumbnail...")
        thumb_path = str(work_dir / "thumbnail.jpg")
        thumb_title = title.split("|")[0].strip() if "|" in title else title
        generate_thumbnail(thumb_title, "AnchorWithin Affirmations",
                           thumb_path, style="growth")
        print(f"  Thumbnail: {thumb_path}")

        # Step 4: Assemble video (still image + mixed audio)
        print(f"\n[4/5] Assembling video...")
        t0 = time.time()
        video_path = str(work_dir / f"{video_id}.mp4")
        assembled = assemble_still_video(bg_path, audio_path, video_path)
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

        send_production_complete(
            series="Affirmations",
            title=title,
            video_url=result.get("video_url"),
            local_path=result.get("local_path"),
            thumbnail_path=thumb_path,
        )

        print(f"\n✅ DONE: {title}")

    except Exception as e:
        result["error"] = str(e)
        result["traceback"] = traceback.format_exc()
        print(f"\n❌ FAILED: {e}")
        send_error(f"Affirmation video failed: {title}\n\n{e}")

    _log_production(result)
    return result


if __name__ == "__main__":
    produce_affirmation_video()
