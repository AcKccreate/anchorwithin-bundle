#!/usr/bin/env python3
"""
AnchorWithin — Universal Episode Assembly Pipeline
Takes a JSON config and produces a fully mixed episode:
  1. Find & concatenate Kling clips (with crossfade)
  2. Generate voiceover (edge-tts → espeak-ng fallback)
  3. Generate ambient layer (drone + atmosphere)
  4. Generate music pad (harmonic tones + breathing)
  5. Mix audio layers (voice -3dB, music -22dB, ambient -25dB)
  6. Extend video if voiceover is longer (freeze last frame)
  7. Mux video + audio
  8. Add brand intro/outro
  9. Stage to ready_to_upload/ or mark as waiting for clips

Usage:
  python assemble_episode.py configs/akira_ep02.json
  python assemble_episode.py configs/*.json          # batch mode
"""

import asyncio
import glob
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import wave

import numpy as np
import edge_tts
from pydub import AudioSegment

SAMPLE_RATE = 44100
BASE_DIR = os.path.dirname(os.path.abspath(__file__))


# ═══════════════════════════════════════════════════════════════════════════
# AUDIO GENERATION
# ═══════════════════════════════════════════════════════════════════════════

def numpy_to_segment(samples, sr=SAMPLE_RATE):
    """float64 numpy array (-1..1) → pydub AudioSegment."""
    samples = np.clip(samples, -1.0, 1.0)
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes((samples * 32767).astype(np.int16).tobytes())
    buf.seek(0)
    return AudioSegment.from_wav(buf)


async def generate_voiceover(text, voice, rate, pitch, output_path):
    """Generate voiceover via edge-tts, falling back to espeak-ng."""
    print("  [VO] Generating voiceover...")

    # Try edge-tts first
    try:
        kwargs = {"text": text, "voice": voice, "rate": rate}
        if pitch:
            kwargs["pitch"] = pitch
        comm = edge_tts.Communicate(**kwargs)
        await comm.save(output_path)
        print(f"  [VO] ✓ edge-tts ({voice}): {os.path.basename(output_path)}")
        return
    except Exception as e:
        print(f"  [VO] ⚠ edge-tts failed ({e.__class__.__name__}), using espeak-ng...")

    # Fallback: espeak-ng
    espeak = shutil.which("espeak-ng") or shutil.which("espeak")
    if not espeak:
        raise RuntimeError("No TTS engine available")
    wav_tmp = output_path.replace(".mp3", "_tmp.wav")
    subprocess.run(
        [espeak, "-v", "en+f3", "-s", "130", "-p", "35", "-w", wav_tmp, text],
        check=True,
    )
    AudioSegment.from_wav(wav_tmp).export(output_path, format="mp3", bitrate="192k")
    os.remove(wav_tmp)
    print(f"  [VO] ✓ espeak-ng fallback: {os.path.basename(output_path)}")


def generate_ambient(freq, ambient_type, duration, output_path):
    """Generate drone + atmosphere layer."""
    print(f"  [AMB] Generating {freq}Hz drone + {ambient_type} ({duration}s)...")
    n = SAMPLE_RATE * duration
    t = np.linspace(0, duration, n, endpoint=False)

    # Base drone at specified frequency
    drone = np.sin(2 * np.pi * freq * t) * 0.3
    drone *= 0.85 + 0.15 * np.sin(2 * np.pi * 0.05 * t)  # wobble

    # Atmosphere layer depends on type
    if ambient_type == "rain":
        atmo = _make_rain(n, t)
    elif ambient_type == "ocean":
        atmo = _make_ocean(n, t)
    elif ambient_type == "piano":
        atmo = _make_soft_piano(n, t, freq)
    else:
        atmo = _make_rain(n, t)  # default

    ambient = drone + atmo
    # Fade in/out
    fade = SAMPLE_RATE * 2
    ambient[:fade] *= np.linspace(0, 1, fade)
    ambient[-fade:] *= np.linspace(1, 0, fade)

    numpy_to_segment(ambient).export(output_path, format="mp3", bitrate="192k")
    print(f"  [AMB] ✓ {os.path.basename(output_path)}")


def _make_rain(n, t):
    """Band-pass filtered white noise (2-8kHz) simulating rain."""
    noise = np.random.normal(0, 1, n)
    spectrum = np.fft.rfft(noise)
    freqs = np.fft.rfftfreq(n, d=1 / SAMPLE_RATE)
    spectrum[(freqs < 2000) | (freqs > 8000)] = 0
    rain = np.fft.irfft(spectrum, n=n)
    return rain / np.max(np.abs(rain)) * 0.15


def _make_ocean(n, t):
    """Low-frequency filtered noise with slow surge modulation for ocean waves."""
    noise = np.random.normal(0, 1, n)
    spectrum = np.fft.rfft(noise)
    freqs = np.fft.rfftfreq(n, d=1 / SAMPLE_RATE)
    # Ocean: 200Hz-3kHz band
    spectrum[(freqs < 200) | (freqs > 3000)] = 0
    ocean = np.fft.irfft(spectrum, n=n)
    ocean = ocean / np.max(np.abs(ocean))
    # Slow wave surge (0.08Hz ≈ 12s cycle)
    surge = 0.3 + 0.7 * (0.5 + 0.5 * np.sin(2 * np.pi * 0.08 * t))
    return ocean * surge * 0.18


def _make_soft_piano(n, t, base_freq):
    """Gentle piano-like tones using decaying harmonics."""
    piano = np.zeros(n)
    # Play soft chords every ~4 seconds
    chord_interval = 4.0
    note_duration = 3.5
    note_samples = int(SAMPLE_RATE * note_duration)
    # Piano frequencies: root, major third, fifth
    ratios = [1.0, 1.25, 1.5]
    for start_sec in np.arange(0, t[-1] - note_duration, chord_interval):
        start = int(start_sec * SAMPLE_RATE)
        end = min(start + note_samples, n)
        length = end - start
        t_note = np.linspace(0, note_duration, length, endpoint=False)
        # Exponential decay envelope
        env = np.exp(-1.5 * t_note)
        chord = np.zeros(length)
        for r in ratios:
            f = base_freq * r
            chord += np.sin(2 * np.pi * f * t_note) * env
        chord = chord / np.max(np.abs(chord)) * 0.12
        piano[start:end] += chord
    return piano


def generate_music(freq, duration, output_path):
    """Generate warm harmonic pad with breathing modulation."""
    print(f"  [MUS] Generating {freq}Hz music pad ({duration}s)...")
    n = SAMPLE_RATE * duration
    t = np.linspace(0, duration, n, endpoint=False)

    # Three tones: root, fifth (~1.5x), octave (2x) — slight detuning
    pad = (np.sin(2 * np.pi * freq * t)
           + 0.7 * np.sin(2 * np.pi * (freq * 1.498) * t)
           + 0.5 * np.sin(2 * np.pi * (freq * 2.003) * t))
    pad = pad / np.max(np.abs(pad))

    # Breathing envelope
    envelope = 0.35 + 0.65 * np.sin(2 * np.pi * 0.15 * t)
    envelope = np.clip(envelope, 0.0, 1.0)
    pad *= envelope * 0.4

    # Lo-fi rolloff
    spectrum = np.fft.rfft(pad)
    freqs = np.fft.rfftfreq(n, d=1 / SAMPLE_RATE)
    rolloff = np.ones_like(freqs)
    hi = freqs > 3000
    rolloff[hi] = np.exp(-0.001 * (freqs[hi] - 3000))
    spectrum *= rolloff
    pad = np.fft.irfft(spectrum, n=n)
    pad = pad / np.max(np.abs(pad)) * 0.4

    # Fade
    fade = SAMPLE_RATE * 3
    pad[:fade] *= np.linspace(0, 1, fade)
    pad[-fade:] *= np.linspace(1, 0, fade)

    numpy_to_segment(pad).export(output_path, format="mp3", bitrate="192k")
    print(f"  [MUS] ✓ {os.path.basename(output_path)}")


def mix_audio(vo_path, music_path, ambient_path, output_path):
    """Mix voiceover (-3dB), music (-22dB), ambient (-25dB)."""
    print("  [MIX] Mixing audio layers...")
    vo = AudioSegment.from_mp3(vo_path).apply_gain(-3)
    music = AudioSegment.from_mp3(music_path).apply_gain(-22)
    ambient = AudioSegment.from_mp3(ambient_path).apply_gain(-25)

    mixed = ambient.overlay(music).overlay(vo)
    mixed.export(output_path, format="mp3", bitrate="192k")
    print(f"  [MIX] ✓ {os.path.basename(output_path)}")
    return mixed.duration_seconds


# ═══════════════════════════════════════════════════════════════════════════
# VIDEO ASSEMBLY
# ═══════════════════════════════════════════════════════════════════════════

def find_clips(series, episode_num):
    """Find Kling clips in assets/{series}/ep{nn}_*.mp4."""
    pattern = os.path.join(BASE_DIR, "assets", series, f"ep{episode_num:02d}_*.mp4")
    clips = sorted(glob.glob(pattern))
    return clips


def strip_and_concat(clips, output_path, crossfade_sec=1):
    """Strip Kling audio from clips and concatenate with crossfade."""
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        print("  [VID] ⚠ ffmpeg not found, skipping video assembly")
        return False

    print(f"  [VID] Concatenating {len(clips)} clips (crossfade={crossfade_sec}s)...")
    tmpdir = tempfile.mkdtemp(prefix="aw_concat_")

    try:
        # Strip audio from each clip
        silent_clips = []
        for i, clip in enumerate(clips):
            out = os.path.join(tmpdir, f"clip_{i:02d}.mp4")
            subprocess.run(
                [ffmpeg, "-y", "-i", clip, "-c:v", "copy", "-an", out],
                check=True, capture_output=True,
            )
            silent_clips.append(out)

        if len(silent_clips) == 1:
            shutil.copy2(silent_clips[0], output_path)
        else:
            # Build ffmpeg xfade filter chain
            inputs = []
            for c in silent_clips:
                inputs.extend(["-i", c])

            # Get durations for xfade offsets
            durations = []
            for c in silent_clips:
                result = subprocess.run(
                    ["ffprobe", "-v", "error", "-show_entries",
                     "format=duration", "-of", "csv=p=0", c],
                    capture_output=True, text=True, check=True,
                )
                durations.append(float(result.stdout.strip()))

            # Build xfade filter chain for N clips
            if len(silent_clips) == 2:
                offset = durations[0] - crossfade_sec
                filt = f"[0:v][1:v]xfade=transition=fade:duration={crossfade_sec}:offset={offset}"
                subprocess.run(
                    [ffmpeg, "-y"] + inputs + ["-filter_complex", filt, output_path],
                    check=True, capture_output=True,
                )
            else:
                # For 3+ clips, chain xfades
                filt_parts = []
                running_dur = durations[0]
                prev = "[0:v]"
                for i in range(1, len(silent_clips)):
                    offset = running_dur - crossfade_sec
                    out_label = f"[v{i}]" if i < len(silent_clips) - 1 else ""
                    filt_parts.append(
                        f"{prev}[{i}:v]xfade=transition=fade:"
                        f"duration={crossfade_sec}:offset={offset:.3f}{out_label}"
                    )
                    running_dur = offset + durations[i]
                    prev = f"[v{i}]"
                filt = ";".join(filt_parts)
                subprocess.run(
                    [ffmpeg, "-y"] + inputs + ["-filter_complex", filt, output_path],
                    check=True, capture_output=True,
                )

        print(f"  [VID] ✓ Concatenated: {os.path.basename(output_path)}")
        return True
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


def extend_video_freeze(video_path, output_path, extra_seconds=8):
    """Extend video by freezing its last frame."""
    ffmpeg = shutil.which("ffmpeg")
    ffprobe = shutil.which("ffprobe")
    if not ffmpeg or not ffprobe:
        return False

    print(f"  [VID] Extending video +{extra_seconds}s (freeze frame)...")
    tmpdir = tempfile.mkdtemp(prefix="aw_freeze_")

    try:
        # Get fps
        result = subprocess.run(
            [ffprobe, "-v", "error", "-select_streams", "v:0",
             "-show_entries", "stream=r_frame_rate", "-of", "csv=p=0",
             video_path],
            capture_output=True, text=True, check=True,
        )
        fps_str = result.stdout.strip()
        fps = eval(fps_str) if "/" in fps_str else float(fps_str)

        last_frame = os.path.join(tmpdir, "last.png")
        freeze = os.path.join(tmpdir, "freeze.mp4")
        noaudio = os.path.join(tmpdir, "noaudio.mp4")
        concat_txt = os.path.join(tmpdir, "concat.txt")

        subprocess.run(
            [ffmpeg, "-y", "-sseof", "-0.1", "-i", video_path,
             "-frames:v", "1", "-q:v", "2", last_frame],
            check=True, capture_output=True,
        )
        subprocess.run(
            [ffmpeg, "-y", "-loop", "1", "-i", last_frame,
             "-c:v", "libx264", "-t", str(extra_seconds),
             "-pix_fmt", "yuv420p", "-r", str(fps), "-an", freeze],
            check=True, capture_output=True,
        )
        subprocess.run(
            [ffmpeg, "-y", "-i", video_path, "-c:v", "copy", "-an", noaudio],
            check=True, capture_output=True,
        )
        with open(concat_txt, "w") as f:
            f.write(f"file '{noaudio}'\nfile '{freeze}'\n")
        subprocess.run(
            [ffmpeg, "-y", "-f", "concat", "-safe", "0", "-i", concat_txt,
             "-c:v", "libx264", "-pix_fmt", "yuv420p", output_path],
            check=True, capture_output=True,
        )
        print(f"  [VID] ✓ Extended: {os.path.basename(output_path)}")
        return True
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


def mux_video_audio(video_path, audio_path, output_path):
    """Replace video audio with mixed audio."""
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        return False
    print("  [MUX] Muxing video + audio...")
    subprocess.run(
        [ffmpeg, "-y", "-i", video_path, "-i", audio_path,
         "-map", "0:v", "-map", "1:a", "-c:v", "copy",
         "-c:a", "aac", "-b:a", "192k", "-shortest", output_path],
        check=True, capture_output=True,
    )
    print(f"  [MUX] ✓ {os.path.basename(output_path)}")
    return True


def add_brand_wrapping(video_path, intro_path, outro_path, output_path):
    """Prepend brand intro and append outro if they exist."""
    ffmpeg = shutil.which("ffmpeg")
    parts = []
    if intro_path and os.path.isfile(intro_path):
        parts.append(intro_path)
    parts.append(video_path)
    if outro_path and os.path.isfile(outro_path):
        parts.append(outro_path)

    if len(parts) == 1:
        print("  [BRAND] No intro/outro found, skipping brand wrapping")
        shutil.copy2(video_path, output_path)
        return

    tmpdir = tempfile.mkdtemp(prefix="aw_brand_")
    try:
        concat_txt = os.path.join(tmpdir, "concat.txt")
        with open(concat_txt, "w") as f:
            for p in parts:
                f.write(f"file '{os.path.abspath(p)}'\n")
        subprocess.run(
            [ffmpeg, "-y", "-f", "concat", "-safe", "0", "-i", concat_txt,
             "-c", "copy", output_path],
            check=True, capture_output=True,
        )
        print(f"  [BRAND] ✓ Added intro/outro: {os.path.basename(output_path)}")
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


# ═══════════════════════════════════════════════════════════════════════════
# MAIN PIPELINE
# ═══════════════════════════════════════════════════════════════════════════

async def assemble_episode(config_path):
    """Run the full assembly pipeline for one episode."""
    with open(config_path) as f:
        cfg = json.load(f)

    series = cfg["series"]
    ep_num = cfg["episode"]
    title = cfg["title"]
    text = cfg["voiceover_text"]
    voice = cfg["voice"]
    rate = cfg.get("rate", "-15%")
    pitch = cfg.get("pitch", "")
    drone_freq = cfg["drone_freq"]
    ambient_type = cfg.get("ambient_type", "rain")
    duration = cfg.get("duration", 48)
    intro = cfg.get("brand_intro", os.path.join(BASE_DIR, "assets", "brand_intro.mp4"))
    outro = cfg.get("brand_outro", os.path.join(BASE_DIR, "assets", "brand_outro.mp4"))

    out_dir = os.path.join(BASE_DIR, "output", series)
    os.makedirs(out_dir, exist_ok=True)
    prefix = f"{series}_ep{ep_num:02d}"

    print(f"\n{'=' * 60}")
    print(f"  {series.upper()} EP{ep_num:02d} — \"{title}\"")
    print(f"{'=' * 60}")

    # Paths
    vo_path = os.path.join(out_dir, f"{prefix}_voiceover.mp3")
    amb_path = os.path.join(out_dir, f"{prefix}_ambient.mp3")
    mus_path = os.path.join(out_dir, f"{prefix}_music.mp3")
    mix_path = os.path.join(out_dir, f"{prefix}_mixed_audio.mp3")

    # ── Audio ──
    await generate_voiceover(text, voice, rate, pitch, vo_path)
    generate_ambient(drone_freq, ambient_type, duration, amb_path)
    generate_music(drone_freq, duration, mus_path)
    mix_dur = mix_audio(vo_path, mus_path, amb_path, mix_path)

    # ── Video ──
    clips = find_clips(series, ep_num)
    has_video = False

    if clips:
        print(f"  [VID] Found {len(clips)} clips")
        concat_path = os.path.join(out_dir, f"{prefix}_concat.mp4")
        has_video = strip_and_concat(clips, concat_path, crossfade_sec=1)

        if has_video:
            # Check if voiceover is longer than video
            result = subprocess.run(
                ["ffprobe", "-v", "error", "-show_entries",
                 "format=duration", "-of", "csv=p=0", concat_path],
                capture_output=True, text=True,
            )
            vid_dur = float(result.stdout.strip()) if result.stdout.strip() else 0
            vo_seg = AudioSegment.from_mp3(vo_path)

            if vo_seg.duration_seconds > vid_dur:
                extra = int(vo_seg.duration_seconds - vid_dur) + 2
                ext_path = os.path.join(out_dir, f"{prefix}_extended.mp4")
                extend_video_freeze(concat_path, ext_path, extra_seconds=extra)
                concat_path = ext_path

            # Mux
            muxed = os.path.join(out_dir, f"{prefix}_muxed.mp4")
            mux_video_audio(concat_path, mix_path, muxed)

            # Brand wrap
            final = os.path.join(out_dir, f"{prefix}_FINAL.mp4")
            add_brand_wrapping(muxed, intro, outro, final)

            # Stage to ready_to_upload
            upload_dir = os.path.join(BASE_DIR, "ready_to_upload")
            os.makedirs(upload_dir, exist_ok=True)
            dest = os.path.join(upload_dir, f"{prefix}_FINAL.mp4")
            shutil.copy2(final, dest)
            print(f"  [UPLOAD] ✓ Queued: ready_to_upload/{prefix}_FINAL.mp4")
    else:
        print("  [VID] No clips found — audio-only mode (staged for later)")

    # ── Report ──
    print(f"\n  {'─' * 50}")
    print(f"  RESULTS for {series.upper()} EP{ep_num:02d}:")
    for label, path in [("Voiceover", vo_path), ("Ambient", amb_path),
                        ("Music", mus_path), ("Mix", mix_path)]:
        if os.path.isfile(path):
            seg = AudioSegment.from_mp3(path)
            print(f"    {label:12s} → {os.path.basename(path):40s} {seg.duration_seconds:.1f}s")

    if not clips:
        print(f"\n  ⏳ STAGED — Waiting for Kling clips in:")
        print(f"    assets/{series}/ep{ep_num:02d}_*.mp4")
        print(f"    Re-run this script after adding clips to produce final video.")

    return has_video


async def main():
    if len(sys.argv) < 2:
        print("Usage: python assemble_episode.py <config.json> [config2.json ...]")
        print("       python assemble_episode.py configs/*.json")
        sys.exit(1)

    configs = sys.argv[1:]
    results = {}
    for cfg in configs:
        if not os.path.isfile(cfg):
            print(f"[WARN] Config not found: {cfg}")
            continue
        has_video = await assemble_episode(cfg)
        name = os.path.basename(cfg).replace(".json", "")
        results[name] = "READY" if has_video else "STAGED (no clips)"

    print(f"\n{'=' * 60}")
    print("  BATCH SUMMARY")
    print(f"{'=' * 60}")
    for name, status in results.items():
        print(f"    {name:30s} → {status}")


if __name__ == "__main__":
    asyncio.run(main())
