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
DURATION = 48  # seconds (40s video + 8s freeze-frame extension)
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
            VOICEOVER_TEXT, voice="en-US-GuyNeural", rate="-20%"
        )
        await communicate.save(output_path)
        print(f"  ✓ Voiceover saved (edge-tts, GuyNeural): {output_path}")
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

    # Deep mature male voice: en+m3, slow speed (115 wpm), low pitch (25)
    subprocess.run([
        espeak_bin, "-v", "en+m3", "-s", "115", "-p", "25",
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


# ── 5. Freeze-Frame Video Extension ────────────────────────────────────────
def extend_video_freeze(video_path, output_path, extra_seconds=8):
    """Extend video by freezing its last frame for extra_seconds."""
    import subprocess
    import shutil
    import tempfile

    if not os.path.isfile(video_path):
        print(f"\n[SKIP] Freeze-frame extension — source video not found: {video_path}")
        return False

    ffmpeg_bin = shutil.which("ffmpeg")
    ffprobe_bin = shutil.which("ffprobe")
    if not ffmpeg_bin or not ffprobe_bin:
        print("[ERROR] ffmpeg/ffprobe not found.")
        return False

    print(f"[5/6] Extending video with {extra_seconds}s freeze frame...")
    tmpdir = tempfile.mkdtemp(prefix="akira_freeze_")

    try:
        # Get source video fps
        result = subprocess.run(
            [ffprobe_bin, "-v", "error", "-select_streams", "v:0",
             "-show_entries", "stream=r_frame_rate", "-of", "csv=p=0",
             video_path],
            capture_output=True, text=True, check=True
        )
        fps_str = result.stdout.strip()  # e.g. "30/1" or "24000/1001"
        if "/" in fps_str:
            num, den = fps_str.split("/")
            fps = float(num) / float(den)
        else:
            fps = float(fps_str)

        last_frame = os.path.join(tmpdir, "last_frame.png")
        freeze_clip = os.path.join(tmpdir, "freeze.mp4")
        concat_list = os.path.join(tmpdir, "concat.txt")

        # 1. Extract last frame
        subprocess.run([
            ffmpeg_bin, "-y", "-sseof", "-0.1", "-i", video_path,
            "-frames:v", "1", "-q:v", "2", last_frame
        ], check=True, capture_output=True)

        # 2. Create freeze clip from last frame (match fps, no audio)
        subprocess.run([
            ffmpeg_bin, "-y", "-loop", "1", "-i", last_frame,
            "-c:v", "libx264", "-t", str(extra_seconds),
            "-pix_fmt", "yuv420p", "-r", str(fps),
            "-an", freeze_clip
        ], check=True, capture_output=True)

        # 3. Create concat list and join
        # First, strip audio from original to avoid concat issues
        orig_noaudio = os.path.join(tmpdir, "orig_noaudio.mp4")
        subprocess.run([
            ffmpeg_bin, "-y", "-i", video_path,
            "-c:v", "copy", "-an", orig_noaudio
        ], check=True, capture_output=True)

        with open(concat_list, "w") as f:
            f.write(f"file '{orig_noaudio}'\n")
            f.write(f"file '{freeze_clip}'\n")

        subprocess.run([
            ffmpeg_bin, "-y", "-f", "concat", "-safe", "0",
            "-i", concat_list, "-c:v", "libx264", "-pix_fmt", "yuv420p",
            output_path
        ], check=True, capture_output=True)

        print(f"  ✓ Extended video saved: {output_path}")
        return True

    finally:
        # Cleanup temp files
        import shutil as sh
        sh.rmtree(tmpdir, ignore_errors=True)


# ── 6. Video Mux ──────────────────────────────────────────────────────────
def mux_video(video_path, audio_path, output_path):
    """Strip existing audio from video and replace with mixed audio."""
    import subprocess
    import shutil

    if not os.path.isfile(video_path):
        print(f"\n[SKIP] Video muxing — source video not found: {video_path}")
        print("  Copy your video to that path and re-run, or run manually:")
        print(f'  ffmpeg -y -i "{video_path}" -i "{audio_path}" '
              f'-map 0:v -map 1:a -c:v copy -c:a aac -b:a 192k -shortest '
              f'"{output_path}"')
        return False

    ffmpeg_bin = shutil.which("ffmpeg")
    if not ffmpeg_bin:
        print("[ERROR] ffmpeg not found. Install it and re-run.")
        return False

    print("[5/5] Muxing video + audio...")
    subprocess.run([
        ffmpeg_bin, "-y",
        "-i", video_path,
        "-i", audio_path,
        "-map", "0:v",
        "-map", "1:a",
        "-c:v", "copy",
        "-c:a", "aac",
        "-b:a", "192k",
        "-shortest",
        output_path,
    ], check=True)
    print(f"  ✓ Final video saved: {output_path}")
    return True


# ── Main ───────────────────────────────────────────────────────────────────
async def main():
    import sys

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    vo_path = os.path.join(OUTPUT_DIR, "ep01_voice_deep.mp3")
    ambient_path = os.path.join(OUTPUT_DIR, "ep01_ambient.mp3")
    music_path = os.path.join(OUTPUT_DIR, "ep01_music.mp3")
    mixed_path = os.path.join(OUTPUT_DIR, "ep01_mixed_audio_v2.mp3")
    video_out = os.path.join(OUTPUT_DIR, "akira_ep01_the_node_FINAL_v2.mp4")

    # Accept source video path as CLI argument, or use default
    default_video = os.path.join(OUTPUT_DIR, "akira_ep01_video.mp4")
    video_src = sys.argv[1] if len(sys.argv) > 1 else default_video

    # Generate all audio assets
    await generate_voiceover(vo_path)
    generate_ambient(ambient_path)
    generate_music(music_path)
    mix_all(vo_path, music_path, ambient_path, mixed_path)

    # Extend video with freeze frame, then mux
    extended_video = os.path.join(OUTPUT_DIR, "akira_ep01_extended.mp4")
    if os.path.isfile(video_src):
        extend_video_freeze(video_src, extended_video, extra_seconds=8)
        mux_video(extended_video, mixed_path, video_out)
    else:
        mux_video(video_src, mixed_path, video_out)

    # Report
    print("\n" + "=" * 60)
    print("AKIRA EP01 AUDIO PIPELINE v2 — COMPLETE")
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

    if os.path.isfile(video_out):
        import subprocess
        result = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries",
             "format=duration", "-of", "csv=p=0", video_out],
            capture_output=True, text=True
        )
        dur = float(result.stdout.strip()) if result.stdout.strip() else 0
        size_mb = os.path.getsize(video_out) / (1024 * 1024)
        print(f"  {'FINAL VIDEO':12s} → {os.path.basename(video_out):30s} "
              f"duration={dur:.1f}s  size={size_mb:.1f}MB")
    else:
        print(f"\n  To produce the final v2 video on Windows, run these steps:")
        print(f"")
        print(f"  Step 1 — Freeze last frame (+8s):")
        print(f'  ffmpeg -sseof -0.1 -i "C:\\Users\\acase\\Downloads\\akira_ep01_the_node_FINAL.mp4" -frames:v 1 -q:v 2 last_frame.png')
        print(f'  ffmpeg -loop 1 -i last_frame.png -c:v libx264 -t 8 -pix_fmt yuv420p -r 30 freeze.mp4')
        print(f'  (echo file akira_ep01_the_node_FINAL.mp4 & echo file freeze.mp4) > concat.txt')
        print(f'  ffmpeg -f concat -safe 0 -i concat.txt -c:v libx264 akira_ep01_extended.mp4')
        print(f"")
        print(f"  Step 2 — Mux with new audio mix:")
        print(f'  ffmpeg -y -i akira_ep01_extended.mp4 -i ep01_mixed_audio_v2.mp3 ^')
        print(f'    -map 0:v -map 1:a -c:v copy -c:a aac -b:a 192k -shortest ^')
        print(f'    akira_ep01_the_node_FINAL_v2.mp4')


if __name__ == "__main__":
    asyncio.run(main())
