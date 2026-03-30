"""
Personal Growth Narrated Long-Form Video Producer
Produces narrated long-form videos with warm TTS + ambient background pad + still image.
Ties to The Anchor Remembers tool.
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
    with open(TEMPLATES_DIR / "personal_growth_scripts.json") as f:
        return json.load(f)


def _get_next_script(templates):
    """Pick the next script not recently produced."""
    produced = set()
    if PRODUCTION_LOG.exists():
        with open(PRODUCTION_LOG) as f:
            for entry in json.load(f):
                if entry.get("series") == "personal_growth":
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


def produce_personal_growth_video(config=None) -> dict:
    """Produce a complete personal growth narrated long-form video."""
    templates = _load_templates()
    config = config or _get_next_script(templates)

    title = config["title"]
    description = config["description"]
    tags = config["tags"]
    narration = config["narration"]

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    video_id = f"growth_{config['id']}_{timestamp}"

    work_dir = OUTPUT_DIR / video_id
    work_dir.mkdir(parents=True, exist_ok=True)

    result = {
        "series": "personal_growth",
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

        # Step 1: Generate TTS narration + ambient background pad + mix
        print(f"\n[1/5] Generating TTS narration with warm narrator...")
        t0 = time.time()
        voice_path = str(work_dir / "voice.mp3")
        generate_speech(narration, character="narrator_warm", output_path=voice_path)
        voice_dur = get_audio_duration(voice_path)
        print(f"  Voice: {os.path.getsize(voice_path) / 1024:.0f} KB ({time.time()-t0:.1f}s)")

        # Generate ambient background pad to match narration duration (+ 10s buffer)
        pad_duration = max(voice_dur + 10, 60)
        pad_path = str(work_dir / "pad.mp3")
        generate_background_pad(BRAND_UNDERTONE_HZ, pad_duration, pad_path)

        # Mix voice over pad
        audio_path = str(work_dir / "narration_mixed.mp3")
        mix_audio_layers([
            {"path": voice_path, "volume_db": 0},
            {"path": pad_path, "volume_db": -6},
        ], audio_path)
        print(f"  Mixed audio: {os.path.getsize(audio_path) / 1024:.0f} KB")

        # Step 2: Generate single still background image
        print(f"\n[2/5] Generating gradient background...")
        bg_path = str(work_dir / "background.png")
        generate_gradient_background(
            (8, 16, 30), (200, 168, 75), title, bg_path
        )
        print(f"  Background: {bg_path}")

        # Step 3: Generate thumbnail
        print(f"\n[3/5] Generating thumbnail...")
        thumb_path = str(work_dir / "thumbnail.jpg")
        thumb_title = title.split("(")[0].strip() if "(" in title else title
        generate_thumbnail(thumb_title, "Personal Growth", thumb_path, style="growth")
        print(f"  Thumbnail: {thumb_path}")

        # Step 4: Assemble still video (single image + audio)
        print(f"\n[4/5] Assembling still video...")
        t0 = time.time()
        video_path = str(work_dir / f"{video_id}.mp4")
        assembled = assemble_still_video(bg_path, audio_path, video_path)
        if not assembled:
            raise RuntimeError("FFmpeg assembly failed")
        size_mb = os.path.getsize(video_path) / (1024 * 1024)
        print(f"  Video: {size_mb:.1f} MB ({time.time()-t0:.0f}s)")

        # Step 5: Upload
        print(f"\n[5/5] Uploading...")
        upload_result = upload_to_youtube(video_path, title, description, tags, thumb_path)

        result["video_path"] = video_path
        result["thumbnail_path"] = thumb_path
        result["uploaded"] = upload_result.get("uploaded", False)
        result["video_url"] = upload_result.get("url")
        result["local_path"] = upload_result.get("local_path")
        result["success"] = True

        send_production_complete(
            series="Personal Growth / Narrated",
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
        send_error(f"Personal growth video failed: {title}\n\n{e}")

    _log_production(result)
    return result


if __name__ == "__main__":
    produce_personal_growth_video()
