#!/usr/bin/env python3
"""
Akira Episode 1 — Audio Generation Pipeline
Generates voiceover, ambient drone, lo-fi music pad, and final mix.
"""

import asyncio
import io
import os
import struct
import wave

import numpy as np
import edge_tts
from pydub import AudioSegment

# ── Configuration ──────────────────────────────────────────────────────────
SAMPLE_RATE = 44100
DURATION = 40  # seconds
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "output", "akira")

VOICEOVER_TEXT = (
    "In a city drowning in noise, one frequency cut through. "
    "They called it The Node. "
    "A forgotten room. A dead machine. But the signal was alive. "
    "174 Hertz. The frequency of foundation. "
    "Of grounding. Of remembering what you forgot you knew. "
    "The Explorer found it by accident. Or maybe the signal found them. "
    "This is Sector 4. And nothing here is what it seems. "
    "The anchor holds."
)


def numpy_to_audio_segment(samples, sample_rate=SAMPLE_RATE):
    """Convert a float64 numpy array (-1..1) to a pydub AudioSegment."""
    samples = np.clip(samples, -1.0, 1.0)
    int16_data = (samples * 32767).astype(np.int16)

    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(int16_data.tobytes())
    buf.seek(0)
    return AudioSegment.from_wav(buf)


# ── 1. Voiceover ──────────────────────────────────────────────────────────
async def generate_voiceover(output_path):
    """Generate Oracle voiceover. Tries edge-tts first, falls back to espeak-ng."""
    print("[1/4] Generating voiceover...")

    # Try edge-tts (best quality, requires internet)
    try:
        communicate = edge_tts.Communicate(
            VOICEOVER_TEXT, voice="en-US-AnaNeural", rate="-15%"
        )
        await communicate.save(output_path)
        print(f"  ✓ Voiceover saved (edge-tts): {output_path}")
        return
    except Exception as e:
        print(f"  ⚠ edge-tts failed ({e.__class__.__name__}), falling back to espeak-ng...")

    # Fallback: espeak-ng (offline, lower quality but works)
    import subprocess
    import shutil
    wav_tmp = output_path.replace(".mp3", "_tmp.wav")
    espeak_bin = shutil.which("espeak-ng") or shutil.which("espeak")
    if not espeak_bin:
        raise RuntimeError("No TTS engine available (edge-tts needs internet, espeak-ng not installed)")

    # Use female voice (en+f3), slow speed (130 wpm), with pitch 40 for gravitas
    subprocess.run([
        espeak_bin, "-v", "en+f3", "-s", "130", "-p", "40",
        "-w", wav_tmp, VOICEOVER_TEXT
    ], check=True)

    # Convert WAV to MP3
    seg = AudioSegment.from_wav(wav_tmp)
    seg.export(output_path, format="mp3", bitrate="192k")
    os.remove(wav_tmp)
    print(f"  ✓ Voiceover saved (espeak-ng fallback): {output_path}")


# ── 2. Ambient Drone + Rain ───────────────────────────────────────────────
def generate_ambient(output_path):
    """Generate 174Hz sine drone + band-pass filtered rain noise, 40 seconds."""
    print("[2/4] Generating ambient drone + rain layer...")
    num_samples = SAMPLE_RATE * DURATION
    t = np.linspace(0, DURATION, num_samples, endpoint=False)

    # 174 Hz drone with slow amplitude wobble
    drone = np.sin(2 * np.pi * 174 * t) * 0.3
    drone *= 0.85 + 0.15 * np.sin(2 * np.pi * 0.05 * t)  # subtle wobble

    # Rain: white noise → FFT bandpass 2kHz–8kHz
    noise = np.random.normal(0, 1, num_samples)
    spectrum = np.fft.rfft(noise)
    freqs = np.fft.rfftfreq(num_samples, d=1 / SAMPLE_RATE)
    mask = (freqs >= 2000) & (freqs <= 8000)
    spectrum[~mask] = 0
    rain = np.fft.irfft(spectrum, n=num_samples)
    rain = rain / np.max(np.abs(rain)) * 0.15  # normalize + scale

    # Fade in/out (2 seconds each)
    fade_samples = SAMPLE_RATE * 2
    fade_in = np.linspace(0, 1, fade_samples)
    fade_out = np.linspace(1, 0, fade_samples)

    ambient = drone + rain
    ambient[:fade_samples] *= fade_in
    ambient[-fade_samples:] *= fade_out

    seg = numpy_to_audio_segment(ambient)
    seg.export(output_path, format="mp3", bitrate="192k")
    print(f"  ✓ Ambient saved: {output_path}")


# ── 3. Lo-fi Music Pad ────────────────────────────────────────────────────
def generate_music(output_path):
    """Generate warm sine pad (174Hz + 261Hz + 348Hz) with breathing modulation."""
    print("[3/4] Generating lo-fi music pad...")
    num_samples = SAMPLE_RATE * DURATION
    t = np.linspace(0, DURATION, num_samples, endpoint=False)

    # Three tones — slight detuning for warmth
    tone_base = np.sin(2 * np.pi * 174.0 * t)
    tone_fifth = 0.7 * np.sin(2 * np.pi * 261.3 * t)   # slight detune
    tone_octave = 0.5 * np.sin(2 * np.pi * 348.2 * t)   # slight detune

    pad = tone_base + tone_fifth + tone_octave
    pad = pad / np.max(np.abs(pad))  # normalize to -1..1

    # Breathing modulation: ~6.7 second cycle
    breath_rate = 0.15  # Hz
    envelope = 0.35 + 0.65 * np.sin(2 * np.pi * breath_rate * t)
    envelope = np.clip(envelope, 0.0, 1.0)
    pad *= envelope * 0.4  # master level

    # Gentle high-frequency rolloff for lo-fi character
    spectrum = np.fft.rfft(pad)
    freqs = np.fft.rfftfreq(num_samples, d=1 / SAMPLE_RATE)
    rolloff = np.ones_like(freqs)
    high_mask = freqs > 3000
    rolloff[high_mask] = np.exp(-0.001 * (freqs[high_mask] - 3000))
    spectrum *= rolloff
    pad = np.fft.irfft(spectrum, n=num_samples)
    pad = pad / np.max(np.abs(pad)) * 0.4  # re-normalize

    # Fade in/out
    fade_samples = SAMPLE_RATE * 3
    pad[:fade_samples] *= np.linspace(0, 1, fade_samples)
    pad[-fade_samples:] *= np.linspace(1, 0, fade_samples)

    seg = numpy_to_audio_segment(pad)
    seg.export(output_path, format="mp3", bitrate="192k")
    print(f"  ✓ Music pad saved: {output_path}")


# ── 4. Mix All Layers ─────────────────────────────────────────────────────
def mix_all(voiceover_path, music_path, ambient_path, output_path):
    """Mix voiceover (-3dB), music (-22dB), ambient (-25dB)."""
    print("[4/4] Mixing all audio layers...")
    vo = AudioSegment.from_mp3(voiceover_path)
    music = AudioSegment.from_mp3(music_path)
    ambient = AudioSegment.from_mp3(ambient_path)

    # Apply gain levels
    vo = vo.apply_gain(-3)
    music = music.apply_gain(-22)
    ambient = ambient.apply_gain(-25)

    # Use ambient (40s) as base, overlay music, then voiceover
    mixed = ambient.overlay(music)
    mixed = mixed.overlay(vo)

    mixed.export(output_path, format="mp3", bitrate="192k")
    print(f"  ✓ Mixed audio saved: {output_path}")


# ── Main ───────────────────────────────────────────────────────────────────
async def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    vo_path = os.path.join(OUTPUT_DIR, "ep01_voiceover.mp3")
    ambient_path = os.path.join(OUTPUT_DIR, "ep01_ambient.mp3")
    music_path = os.path.join(OUTPUT_DIR, "ep01_music.mp3")
    mixed_path = os.path.join(OUTPUT_DIR, "ep01_mixed_audio.mp3")

    # Generate all assets
    await generate_voiceover(vo_path)
    generate_ambient(ambient_path)
    generate_music(music_path)
    mix_all(vo_path, music_path, ambient_path, mixed_path)

    # Report
    print("\n" + "=" * 60)
    print("AKIRA EP01 AUDIO PIPELINE — COMPLETE")
    print("=" * 60)
    for label, path in [
        ("Voiceover", vo_path),
        ("Ambient", ambient_path),
        ("Music Pad", music_path),
        ("Final Mix", mixed_path),
    ]:
        seg = AudioSegment.from_mp3(path)
        print(f"  {label:12s} → {os.path.basename(path):30s} "
              f"duration={seg.duration_seconds:.1f}s")

    print("\n[SKIP] Video muxing — no source video on this system.")
    print("  Run this on your Windows machine to combine:")
    print(f'  ffmpeg -y -i akira_ep01_video.mp4 -i ep01_mixed_audio.mp3 '
          f'-map 0:v -map 1:a -c:v copy -c:a aac -b:a 192k -shortest '
          f'akira_ep01_the_node_COMPLETE.mp4')


if __name__ == "__main__":
    asyncio.run(main())
