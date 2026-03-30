"""
AI Sleep Stories Video Producer
Produces narrated long-form sleep stories with calming TTS and ambient background pad.
"""

import json
import os
import sys
import time
import traceback
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from config import OUTPUT_DIR, TEMPLATES_DIR, LOGS_DIR, PRODUCTION_LOG, BRAND_UNDERTONE_HZ
from lib.tts import generate_speech
from lib.audio_gen import generate_background_pad, mix_audio_layers
from lib.visual_gen import generate_gradient_background
from lib.thumbnail import generate_thumbnail
from lib.assembler import assemble_still_video
from lib.uploader import upload_to_youtube
from lib.telegram import send_production_complete, send_error


def _load_templates():
    with open(TEMPLATES_DIR / "sleep_stories_scripts.json") as f:
        return json.load(f)


def _get_next_script(templates):
    """Pick the next sleep story that hasn't been produced recently."""
    produced = set()
    if PRODUCTION_LOG.exists():
        with open(PRODUCTION_LOG) as f:
            for entry in json.load(f):
                if entry.get("series") == "sleep_stories":
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


def produce_sleep_story(config: dict = None) -> dict:
    """
    Produce a complete AI sleep story video.

    Pipeline:
      1. Generate TTS narration (narrator_calm voice)
      2. Generate ambient background pad (432Hz)
      3. Mix narration + pad into final audio
      4. Generate dark gradient background with title
      5. Generate thumbnail, assemble, upload

    Args:
        config: Optional specific story config dict.
                If None, picks the next unproduced story.

    Returns:
        Production result dict.
    """
    templates = _load_templates()
    config = config or _get_next_script(templates)

    title = config["title"]
    description = config["description"]
    tags = config["tags"]
    narration = config["narration"]

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    video_id = f"story_{config['id']}_{timestamp}"

    # Working directory for this production
    work_dir = OUTPUT_DIR / video_id
    work_dir.mkdir(parents=True, exist_ok=True)

    result = {
        "series": "sleep_stories",
        "template_id": config["id"],
        "video_id": video_id,
        "title": title,
        "timestamp": timestamp,
        "success": False,
    }

    try:
        print(f"\n{'='*60}")
        print(f"PRODUCING: {title}")
        print(f"{'='*60}")

        # Step 1: Generate TTS narration
        print(f"\n[1/5] Generating TTS narration ({len(narration)} chars)...")
        t0 = time.time()
        narration_path = str(work_dir / "narration.mp3")
        generate_speech(narration, character="narrator_calm", output_path=narration_path)
        narration_size = os.path.getsize(narration_path) / (1024 * 1024)
        print(f"  Narration: {narration_size:.1f} MB ({time.time()-t0:.0f}s)")

        # Determine duration from the narration audio
        from pydub import AudioSegment
        narration_audio = AudioSegment.from_file(narration_path)
        narration_duration_secs = len(narration_audio) / 1000.0
        # Add 30 seconds of trailing silence for gentle fade-out
        total_duration = narration_duration_secs + 30
        print(f"  Narration duration: {narration_duration_secs:.0f}s, total with fade: {total_duration:.0f}s")

        # Step 1b: Generate ambient background pad
        print(f"\n  Generating background pad ({total_duration:.0f}s)...")
        pad_path = str(work_dir / "pad.mp3")
        generate_background_pad(BRAND_UNDERTONE_HZ, total_duration, pad_path)

        # Step 1c: Mix narration + pad
        print(f"  Mixing narration with background pad...")
        audio_path = str(work_dir / "audio.mp3")
        mix_audio_layers([
            {"path": narration_path, "volume_db": 0},
            {"path": pad_path, "volume_db": -6},
        ], audio_path)
        print(f"  Mixed audio: {os.path.getsize(audio_path) / (1024*1024):.1f} MB ({time.time()-t0:.0f}s)")

        duration = int(total_duration)

        # Step 2: Generate background image
        print(f"\n[2/5] Generating gradient background...")
        bg_path = str(work_dir / "background.png")
        # Extract story title (before the em dash or pipe)
        display_title = title.split(" — ")[0].split(" | ")[0].strip()
        generate_gradient_background((5, 5, 15), (12, 10, 25), display_title, bg_path)
        print(f"  Background: {bg_path}")

        # Step 3: Generate thumbnail
        print(f"\n[3/5] Generating thumbnail...")
        thumb_path = str(work_dir / "thumbnail.jpg")
        generate_thumbnail(display_title, "A Sleep Story | AnchorWithin",
                           thumb_path, style="sleep")
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
            series="Sleep Stories",
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
        send_error(f"Sleep story failed: {title}\n\n{e}")

    # Log production
    _log_production(result)
    return result


if __name__ == "__main__":
    produce_sleep_story()
