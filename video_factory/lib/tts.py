"""
TTS Wrapper — generates speech audio using edge-tts.
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from config import VOICES


async def _generate_speech_async(text: str, voice: str, output_path: str) -> str:
    """Async implementation of TTS generation."""
    import edge_tts

    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(output_path)
    return output_path


def generate_speech(text: str, voice: str = None, output_path: str = "output.mp3",
                    character: str = None) -> str:
    """
    Generate speech audio from text using edge-tts.

    Args:
        text: The text to speak
        voice: Full edge-tts voice name (e.g. "en-US-GuyNeural")
        output_path: Where to save the .mp3 file
        character: Character name from VOICES preset (overrides voice if set)

    Returns:
        Path to the saved .mp3 file.
    """
    if character and character.lower() in VOICES:
        voice = VOICES[character.lower()]
    elif not voice:
        voice = VOICES["narrator"]

    output_path = str(output_path)
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    # Run the async edge-tts call
    loop = asyncio.new_event_loop()
    try:
        loop.run_until_complete(_generate_speech_async(text, voice, output_path))
    finally:
        loop.close()

    return output_path


def generate_speech_segments(segments: list, output_dir: str) -> list:
    """
    Generate multiple speech files for a multi-character script.

    Args:
        segments: List of dicts with keys: "character", "text"
        output_dir: Directory to save audio files

    Returns:
        List of dicts: {"character": str, "audio_path": str, "text": str}
    """
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    results = []
    for i, seg in enumerate(segments):
        out_path = str(Path(output_dir) / f"segment_{i:03d}.mp3")
        generate_speech(seg["text"], character=seg["character"], output_path=out_path)
        results.append({
            "character": seg["character"],
            "audio_path": out_path,
            "text": seg["text"],
        })
    return results


if __name__ == "__main__":
    out = generate_speech("Hello, this is a test of the video factory text to speech system.",
                          output_path="/tmp/test_tts.mp3")
    import os
    size_kb = os.path.getsize(out) / 1024
    print(f"Generated: {out} ({size_kb:.0f} KB)")
