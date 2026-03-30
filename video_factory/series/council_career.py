"""
Global Council: Career Shorts Producer
Produces 30-60 second vertical debate videos — career-focused topics.
Same pipeline as shorts.py (multi-character debate format).
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
from lib.tts import generate_speech_segments
from lib.visual_gen import generate_character_card
from lib.thumbnail import generate_thumbnail
from lib.assembler import assemble_segments_video
from lib.uploader import upload_to_youtube
from lib.telegram import send_production_complete, send_error


def _load_templates():
    with open(TEMPLATES_DIR / "council_career_scripts.json") as f:
        return json.load(f)


def _get_next_script(templates):
    produced = set()
    if PRODUCTION_LOG.exists():
        with open(PRODUCTION_LOG) as f:
            for entry in json.load(f):
                if entry.get("series") == "council_career":
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


# Character accent colors for thumbnails
CHAR_COLORS = {
    "mia": (255, 120, 180),
    "sora": (120, 200, 255),
    "hoshi": (255, 200, 100),
    "julian": (100, 255, 150),
    "mateo": (200, 130, 255),
}


def produce_council_career_short(config=None) -> dict:
    """Produce a complete Global Council career debate short video."""
    templates = _load_templates()
    config = config or _get_next_script(templates)

    title = config["title"]
    description = config["description"]
    tags = config["tags"]
    segments = config["segments"]

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    video_id = f"gcc_{config['id']}_{timestamp}"

    work_dir = OUTPUT_DIR / video_id
    work_dir.mkdir(parents=True, exist_ok=True)

    result = {
        "series": "council_career",
        "template_id": config["id"],
        "video_id": video_id,
        "title": title,
        "timestamp": timestamp,
        "success": False,
    }

    try:
        print(f"\n{'='*60}")
        print(f"PRODUCING CAREER SHORT: {title}")
        print(f"{'='*60}")

        # Step 1: Generate TTS for each character
        print(f"\n[1/5] Generating TTS for {len(segments)} characters...")
        t0 = time.time()
        audio_dir = str(work_dir / "audio")
        tts_results = generate_speech_segments(segments, audio_dir)
        print(f"  Generated {len(tts_results)} audio segments ({time.time()-t0:.1f}s)")

        # Step 2: Generate character cards (vertical 1080x1920)
        print(f"\n[2/5] Generating character cards...")
        card_paths = {}
        for seg in tts_results:
            char = seg["character"].lower()
            if char not in card_paths:
                card_path = str(work_dir / f"card_{char}.png")
                generate_character_card(seg["character"], card_path)
                card_paths[char] = card_path
        print(f"  Generated {len(card_paths)} unique character cards")

        # Step 3: Generate thumbnail
        print(f"\n[3/5] Generating thumbnail...")
        thumb_path = str(work_dir / "thumbnail.jpg")
        first_char = segments[0]["character"]
        accent = CHAR_COLORS.get(first_char.lower(), (200, 200, 200))
        topic = config.get("topic", title)
        generate_thumbnail(topic, "The Global Council — Career",
                           thumb_path, style="shorts", accent_color=accent)

        # Step 4: Assemble vertical video
        print(f"\n[4/5] Assembling vertical video...")
        t0 = time.time()
        video_path = str(work_dir / f"{video_id}.mp4")

        assembly_segments = []
        for seg in tts_results:
            char = seg["character"].lower()
            assembly_segments.append({
                "image_path": card_paths[char],
                "audio_path": seg["audio_path"],
            })

        assembled = assemble_segments_video(assembly_segments, video_path)
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
            series="Global Council — Career",
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
        send_error(f"Council Career short failed: {title}\n\n{e}")

    _log_production(result)
    return result


if __name__ == "__main__":
    produce_council_career_short()
