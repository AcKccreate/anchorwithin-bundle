"""
AnchorWithin Tool Tips — SHORT Producer
Produces 30-60 second vertical tip cards for AnchorWithin tools.
"""

import json
import os
import sys
import time
import traceback
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from config import OUTPUT_DIR, TEMPLATES_DIR, PRODUCTION_LOG
from lib.tts import generate_speech
from lib.visual_gen import generate_tool_tip_card
from lib.thumbnail import generate_thumbnail
from lib.assembler import assemble_still_video
from lib.uploader import upload_to_youtube
from lib.telegram import send_production_complete, send_error


def _load_templates():
    with open(TEMPLATES_DIR / "tool_tips_scripts.json") as f:
        return json.load(f)


def _get_next_script(templates):
    produced = set()
    if PRODUCTION_LOG.exists():
        with open(PRODUCTION_LOG) as f:
            for entry in json.load(f):
                if entry.get("series") == "tool_tips":
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


def produce_tool_tip(config=None) -> dict:
    """Produce a single-narrator tool tip SHORT video."""
    templates = _load_templates()
    config = config or _get_next_script(templates)

    title = config["title"]
    description = config["description"]
    tags = config["tags"]
    tool_name = config["tool_name"]
    tip_text = config["tip_text"]
    narration = config["narration"]

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    video_id = f"tip_{config['id']}_{timestamp}"

    work_dir = OUTPUT_DIR / video_id
    work_dir.mkdir(parents=True, exist_ok=True)

    result = {
        "series": "tool_tips",
        "template_id": config["id"],
        "video_id": video_id,
        "title": title,
        "timestamp": timestamp,
        "success": False,
    }

    try:
        print(f"\n{'='*60}")
        print(f"PRODUCING TOOL TIP: {title}")
        print(f"{'='*60}")

        # Step 1: Generate TTS narration
        print(f"\n[1/5] Generating TTS narration...")
        t0 = time.time()
        audio_path = str(work_dir / "narration.mp3")
        generate_speech(narration, character="narrator", output_path=audio_path)
        print(f"  Audio: {os.path.getsize(audio_path) / 1024:.0f} KB ({time.time()-t0:.1f}s)")

        # Step 2: Generate tool tip card (vertical 1080x1920)
        print(f"\n[2/5] Generating tool tip card...")
        card_path = str(work_dir / "card.png")
        generate_tool_tip_card(tool_name, tip_text, card_path)
        print(f"  Card: {card_path}")

        # Step 3: Generate thumbnail
        print(f"\n[3/5] Generating thumbnail...")
        thumb_path = str(work_dir / "thumbnail.jpg")
        generate_thumbnail(tool_name, tip_text, thumb_path,
                           style="shorts", accent_color=(200, 168, 75))
        print(f"  Thumbnail: {thumb_path}")

        # Step 4: Assemble vertical video (single card + audio)
        print(f"\n[4/5] Assembling vertical video...")
        t0 = time.time()
        video_path = str(work_dir / f"{video_id}.mp4")
        assembled = assemble_still_video(card_path, audio_path, video_path)
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
            series="Tool Tips",
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
        send_error(f"Tool Tip failed: {title}\n\n{e}")

    _log_production(result)
    return result


if __name__ == "__main__":
    produce_tool_tip()
