"""
Weekly Recap Video Producer — Explainer Archetype
Produces 5-10 minute recap slideshows with TTS narration + recap frames.
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
from lib.visual_gen import generate_recap_frame
from lib.thumbnail import generate_thumbnail
from lib.assembler import assemble_slideshow, get_audio_duration
from lib.uploader import upload_to_youtube
from lib.telegram import send_production_complete, send_error


def _load_templates():
    with open(TEMPLATES_DIR / "weekly_recap_scripts.json") as f:
        return json.load(f)


def _get_next_script(templates):
    produced = set()
    if PRODUCTION_LOG.exists():
        with open(PRODUCTION_LOG) as f:
            for entry in json.load(f):
                if entry.get("series") == "weekly_recap":
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


def _build_narration_text(slides: list) -> str:
    """Convert recap slides into a natural narration script."""
    parts = []
    for i, slide in enumerate(slides):
        section = slide["section_title"]
        items = slide["items"]

        if i == 0:
            parts.append(f"Welcome to this week's recap. Let's start with: {section}.")
        else:
            parts.append(f"Moving on to: {section}.")

        for item in items:
            parts.append(item + ".")

        parts.append("")  # Pause between sections

    parts.append("That's all for this week. Stay anchored.")
    return " ".join(parts)


def produce_recap_video(config=None) -> dict:
    """Produce a weekly recap slideshow video."""
    templates = _load_templates()
    config = config or _get_next_script(templates)

    title = config["title"]
    description = config["description"]
    tags = config["tags"]
    slides = config["slides"]

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    video_id = f"recap_{config['id']}_{timestamp}"

    work_dir = OUTPUT_DIR / video_id
    work_dir.mkdir(parents=True, exist_ok=True)

    result = {
        "series": "weekly_recap",
        "template_id": config["id"],
        "video_id": video_id,
        "title": title,
        "timestamp": timestamp,
        "success": False,
    }

    try:
        print(f"\n{'='*60}")
        print(f"PRODUCING RECAP: {title}")
        print(f"{'='*60}")

        # Step 1: Generate narration audio
        print(f"\n[1/5] Generating TTS narration...")
        t0 = time.time()
        narration_text = _build_narration_text(slides)
        audio_path = str(work_dir / "narration.mp3")
        generate_speech(narration_text, character="narrator", output_path=audio_path)
        print(f"  Audio: {os.path.getsize(audio_path) / 1024:.0f} KB ({time.time()-t0:.1f}s)")

        # Step 2: Generate recap slide frames
        print(f"\n[2/5] Generating {len(slides)} recap frames...")
        week_label = config.get("week_label", "WEEKLY RECAP")
        frame_paths = []
        for i, slide in enumerate(slides):
            frame_path = str(work_dir / f"frame_{i:03d}.png")
            generate_recap_frame(week_label, slide["section_title"],
                                 slide["items"], frame_path)
            frame_paths.append(frame_path)
        print(f"  Generated {len(frame_paths)} frames")

        # Step 3: Generate thumbnail
        print(f"\n[3/5] Generating thumbnail...")
        thumb_path = str(work_dir / "thumbnail.jpg")
        thumb_title = title.split("|")[0].strip() if "|" in title else title
        generate_thumbnail(thumb_title, "AnchorWithin Weekly Recap",
                           thumb_path, style="explainer",
                           accent_color=(200, 168, 75))
        print(f"  Thumbnail: {thumb_path}")

        # Step 4: Assemble slideshow video
        print(f"\n[4/5] Assembling slideshow video...")
        t0 = time.time()
        video_path = str(work_dir / f"{video_id}.mp4")

        audio_dur = get_audio_duration(audio_path)
        frame_dur = max(5.0, audio_dur / len(slides)) if audio_dur > 0 else 8.0

        assembled = assemble_slideshow(frame_paths, audio_path, video_path,
                                       frame_duration=frame_dur)
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
            series="Weekly Recap",
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
        send_error(f"Weekly Recap failed: {title}\n\n{e}")

    _log_production(result)
    return result


if __name__ == "__main__":
    produce_recap_video()
