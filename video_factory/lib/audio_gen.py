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


def numpy_to_audio_segment(samples: np.ndarray, sample_rate: int = 44100,
                           channels: int = 1) -> AudioSegment:
    """Convert a numpy float array (-1..1) to a pydub AudioSegment.
    For stereo, pass a (2, N) array or interleaved (N*2,) array with channels=2.
    """
    if channels == 2 and samples.ndim == 2:
        # Interleave L/R channels: shape (2, N) -> (N*2,)
        samples = np.column_stack((samples[0], samples[1])).flatten()
    pcm = (samples * 32767).astype(np.int16)
    return AudioSegment(
        data=pcm.tobytes(),
        sample_width=2,
        frame_rate=sample_rate,
        channels=channels,
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


def generate_binaural_beat(base_freq: float, beat_freq: float, duration_secs: float,
                           output_path: str, undertone: bool = True,
                           fade_secs: float = 5.0) -> str:
    """
    Generate a stereo binaural beat audio file.
    Left ear hears base_freq, right ear hears base_freq + beat_freq.
    The brain perceives the difference as a binaural beat.
    """
    sample_rate = 44100
    output_path = str(output_path)

    left = generate_sine_wave(base_freq, duration_secs, sample_rate, amplitude=0.7)
    right = generate_sine_wave(base_freq + beat_freq, duration_secs, sample_rate, amplitude=0.7)

    # Add 432Hz undertone to both channels
    if undertone:
        ut = generate_sine_wave(BRAND_UNDERTONE_HZ, duration_secs, sample_rate, amplitude=0.12)
        left = np.clip(left + ut, -1.0, 1.0)
        right = np.clip(right + ut, -1.0, 1.0)

    stereo = np.array([left, right])
    audio = numpy_to_audio_segment(stereo, sample_rate, channels=2)

    fade_ms = int(fade_secs * 1000)
    audio = audio.fade_in(fade_ms).fade_out(fade_ms)

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    audio.export(output_path, format="mp3", bitrate="192k")
    return output_path


def generate_noise(color: str, duration_secs: float, output_path: str,
                   undertone: bool = True, fade_secs: float = 5.0) -> str:
    """
    Generate colored noise (white, pink, or brown) and save as MP3.
    """
    sample_rate = 44100
    output_path = str(output_path)
    n_samples = int(sample_rate * duration_secs)

    rng = np.random.default_rng(42)
    white = rng.standard_normal(n_samples)

    if color == "white":
        noise = white
    elif color == "pink":
        # Approximate pink noise via spectral shaping
        freqs = np.fft.rfftfreq(n_samples, d=1.0 / sample_rate)
        freqs[0] = 1  # avoid division by zero
        spectrum = np.fft.rfft(white)
        pink_filter = 1.0 / np.sqrt(freqs)
        noise = np.fft.irfft(spectrum * pink_filter, n=n_samples)
    elif color == "brown":
        noise = np.cumsum(white)
        noise = noise - np.mean(noise)
    else:
        noise = white

    # Normalize to -1..1 range with headroom
    noise = noise / (np.max(np.abs(noise)) + 1e-8) * 0.6

    if undertone:
        ut = generate_sine_wave(BRAND_UNDERTONE_HZ, duration_secs, sample_rate, amplitude=0.1)
        noise = np.clip(noise + ut, -1.0, 1.0)

    audio = numpy_to_audio_segment(noise, sample_rate)
    fade_ms = int(fade_secs * 1000)
    audio = audio.fade_in(fade_ms).fade_out(fade_ms)

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    audio.export(output_path, format="mp3", bitrate="192k")
    return output_path


def mix_audio_layers(layers: list, output_path: str) -> str:
    """
    Mix multiple audio files together at specified volumes.
    layers: list of {"path": str, "volume_db": float} dicts.
    The first layer sets the base duration.
    """
    output_path = str(output_path)
    base = None
    for layer in layers:
        seg = AudioSegment.from_file(layer["path"])
        vol = layer.get("volume_db", 0)
        seg = seg + vol  # pydub volume adjustment in dB
        if base is None:
            base = seg
        else:
            # Loop shorter layer to match base duration
            if len(seg) < len(base):
                repeats = (len(base) // len(seg)) + 1
                seg = seg * repeats
            base = base.overlay(seg[:len(base)])

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    base.export(output_path, format="mp3", bitrate="192k")
    return output_path


def generate_background_pad(freq: float, duration_secs: float, output_path: str) -> str:
    """
    Generate a very quiet ambient pad (432Hz tone + subtle pink noise floor).
    Designed to sit under TTS narration without competing.
    """
    sample_rate = 44100
    output_path = str(output_path)
    n_samples = int(sample_rate * duration_secs)

    # Quiet sustained tone
    tone = generate_sine_wave(freq, duration_secs, sample_rate, amplitude=0.04)

    # Very subtle pink noise floor
    rng = np.random.default_rng(99)
    white = rng.standard_normal(n_samples)
    freqs = np.fft.rfftfreq(n_samples, d=1.0 / sample_rate)
    freqs[0] = 1
    spectrum = np.fft.rfft(white)
    pink = np.fft.irfft(spectrum / np.sqrt(freqs), n=n_samples)
    pink = pink / (np.max(np.abs(pink)) + 1e-8) * 0.02

    combined = np.clip(tone + pink, -1.0, 1.0)
    audio = numpy_to_audio_segment(combined, sample_rate)
    audio = audio.fade_in(3000).fade_out(3000)

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    audio.export(output_path, format="mp3", bitrate="128k")
    return output_path


def generate_singing_bowl_tone(freq_hz: float, duration_secs: float,
                               output_path: str, undertone: bool = True,
                               fade_secs: float = 5.0) -> str:
    """
    Generate a singing bowl-style tone with harmonic overtones and decay envelope.
    """
    sample_rate = 44100
    output_path = str(output_path)
    t = np.linspace(0, duration_secs, int(sample_rate * duration_secs), endpoint=False)

    # Fundamental + harmonics with decreasing amplitude
    harmonics = [
        (1.0, 0.6),    # fundamental
        (2.0, 0.25),   # 2nd harmonic
        (3.0, 0.12),   # 3rd
        (5.0, 0.06),   # 5th
    ]
    wave = np.zeros_like(t)
    for mult, amp in harmonics:
        wave += amp * np.sin(2 * np.pi * freq_hz * mult * t)

    # Repeating strike-and-decay pattern (every 30 seconds)
    strike_period = 30.0
    decay_envelope = np.exp(-0.8 * (t % strike_period))
    # Blend: 70% sustained + 30% decay pattern for organic feel
    envelope = 0.7 + 0.3 * decay_envelope
    wave = wave * envelope

    # Normalize
    wave = wave / (np.max(np.abs(wave)) + 1e-8) * 0.65

    if undertone and abs(freq_hz - BRAND_UNDERTONE_HZ) > 1.0:
        ut = generate_sine_wave(BRAND_UNDERTONE_HZ, duration_secs, sample_rate, amplitude=0.12)
        wave = np.clip(wave + ut, -1.0, 1.0)

    audio = numpy_to_audio_segment(wave, sample_rate)
    fade_ms = int(fade_secs * 1000)
    audio = audio.fade_in(fade_ms).fade_out(fade_ms)

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    audio.export(output_path, format="mp3", bitrate="192k")
    return output_path


if __name__ == "__main__":
    out = generate_frequency_tone(432, 30, "/tmp/test_432hz.mp3")
    print(f"Frequency tone: {out} ({os.path.getsize(out)/1024:.0f} KB)")
    out = generate_binaural_beat(200, 10, 30, "/tmp/test_binaural.mp3")
    print(f"Binaural beat: {out} ({os.path.getsize(out)/1024:.0f} KB)")
    out = generate_noise("brown", 30, "/tmp/test_brown_noise.mp3")
    print(f"Brown noise: {out} ({os.path.getsize(out)/1024:.0f} KB)")
    out = generate_singing_bowl_tone(528, 30, "/tmp/test_bowl.mp3")
    print(f"Singing bowl: {out} ({os.path.getsize(out)/1024:.0f} KB)")
