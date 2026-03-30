"""
Audio Generator — produces frequency tones for Sound Healing videos.
Uses numpy for sine wave generation, pydub for mixing and export.
"""

import numpy as np
from pydub import AudioSegment
from pathlib import Path
import io
import sys
import os

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from config import BRAND_UNDERTONE_HZ


def generate_sine_wave(frequency_hz: float, duration_secs: float,
                       sample_rate: int = 44100, amplitude: float = 0.8) -> np.ndarray:
    """Generate a pure sine wave as numpy array of float samples."""
    t = np.linspace(0, duration_secs, int(sample_rate * duration_secs), endpoint=False)
    wave = amplitude * np.sin(2 * np.pi * frequency_hz * t)
    return wave


def numpy_to_audio_segment(samples: np.ndarray, sample_rate: int = 44100) -> AudioSegment:
    """Convert a numpy float array (-1..1) to a pydub AudioSegment."""
    # Convert to 16-bit PCM
    pcm = (samples * 32767).astype(np.int16)
    return AudioSegment(
        data=pcm.tobytes(),
        sample_width=2,
        frame_rate=sample_rate,
        channels=1,
    )


def generate_frequency_tone(freq_hz: float, duration_secs: float, output_path: str,
                            undertone: bool = True, fade_secs: float = 5.0) -> str:
    """
    Generate a frequency healing tone and save as MP3.

    Args:
        freq_hz: Primary frequency in Hz (e.g. 432, 528, 741)
        duration_secs: Duration in seconds
        output_path: Where to save the .mp3 file
        undertone: If True, layer a subtle 432Hz undertone underneath
        fade_secs: Fade-in/out duration in seconds

    Returns:
        Path to the saved file.
    """
    sample_rate = 44100
    output_path = str(output_path)

    # Generate primary tone
    primary = generate_sine_wave(freq_hz, duration_secs, sample_rate, amplitude=0.7)

    # Add subtle binaural-style modulation (slow amplitude wobble)
    t = np.linspace(0, duration_secs, int(sample_rate * duration_secs), endpoint=False)
    modulation = 1.0 + 0.05 * np.sin(2 * np.pi * 0.1 * t)  # 0.1 Hz gentle pulse
    primary = primary * modulation

    # Layer 432Hz undertone if requested and primary isn't already 432
    if undertone and abs(freq_hz - BRAND_UNDERTONE_HZ) > 1.0:
        undertone_wave = generate_sine_wave(BRAND_UNDERTONE_HZ, duration_secs, sample_rate, amplitude=0.15)
        primary = primary + undertone_wave

    # Clip to prevent distortion
    primary = np.clip(primary, -1.0, 1.0)

    # Convert to AudioSegment
    audio = numpy_to_audio_segment(primary, sample_rate)

    # Apply fade-in and fade-out
    fade_ms = int(fade_secs * 1000)
    audio = audio.fade_in(fade_ms).fade_out(fade_ms)

    # Export
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    audio.export(output_path, format="mp3", bitrate="192k")
    return output_path


if __name__ == "__main__":
    # Quick test: generate a 30-second 432Hz tone
    out = generate_frequency_tone(432, 30, "/tmp/test_432hz.mp3")
    size_kb = os.path.getsize(out) / 1024
    print(f"Generated: {out} ({size_kb:.0f} KB)")
