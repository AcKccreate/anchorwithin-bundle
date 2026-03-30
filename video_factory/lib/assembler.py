"""
Video Assembler — wraps ffmpeg to combine audio + visuals into .mp4 files.
"""

import subprocess
import os
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from config import FFMPEG_BIN


def _run_ffmpeg(args: list, desc: str = "ffmpeg") -> bool:
    """Run an ffmpeg command, return True on success."""
    cmd = [FFMPEG_BIN] + args
    print(f"[assembler] Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=7200)
    if result.returncode != 0:
        print(f"[assembler] ERROR: {desc} failed")
        print(f"[assembler] stderr: {result.stderr[-500:]}")
        return False
    return True


def assemble_still_video(image_path: str, audio_path: str, output_path: str,
                         duration: int = None) -> str:
    """
    Create a video from a single still image + audio track.
    Used for frequency/healing videos.

    Args:
        image_path: Path to background image (PNG/JPG)
        audio_path: Path to audio file (MP3)
        output_path: Where to save the .mp4
        duration: Override duration in seconds (default: match audio length)

    Returns:
        Path to output file, or None on failure.
    """
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    args = [
        "-y",  # overwrite
        "-loop", "1",
        "-i", str(image_path),
        "-i", str(audio_path),
        "-c:v", "libx264",
        "-tune", "stillimage",
        "-c:a", "aac",
        "-b:a", "192k",
        "-pix_fmt", "yuv420p",
        "-movflags", "+faststart",
    ]

    if duration:
        args += ["-t", str(duration)]
    else:
        args += ["-shortest"]

    args.append(str(output_path))

    if _run_ffmpeg(args, "still video assembly"):
        return output_path
    return None


def assemble_slideshow(frame_paths: list, audio_path: str, output_path: str,
                       frame_duration: float = 5.0) -> str:
    """
    Create a video from a sequence of image frames + audio.
    Used for explainer videos.

    Args:
        frame_paths: Ordered list of image file paths
        audio_path: Path to audio file
        output_path: Where to save the .mp4
        frame_duration: Seconds per frame

    Returns:
        Path to output file, or None on failure.
    """
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    # Create a concat file for ffmpeg
    concat_path = str(Path(output_path).parent / "frames_concat.txt")
    with open(concat_path, "w") as f:
        for fp in frame_paths:
            f.write(f"file '{fp}'\n")
            f.write(f"duration {frame_duration}\n")
        # Repeat last frame to avoid cut
        if frame_paths:
            f.write(f"file '{frame_paths[-1]}'\n")

    args = [
        "-y",
        "-f", "concat",
        "-safe", "0",
        "-i", concat_path,
        "-i", str(audio_path),
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-b:a", "192k",
        "-movflags", "+faststart",
        "-shortest",
        str(output_path),
    ]

    if _run_ffmpeg(args, "slideshow assembly"):
        # Cleanup concat file
        try:
            os.remove(concat_path)
        except OSError:
            pass
        return output_path
    return None


def assemble_segments_video(segments: list, output_path: str,
                            width: int = 1080, height: int = 1920) -> str:
    """
    Assemble a vertical video from a list of (image, audio) segments.
    Used for Global Council shorts.

    Args:
        segments: List of dicts with "image_path" and "audio_path"
        output_path: Where to save the .mp4

    Returns:
        Path to output file, or None on failure.
    """
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    temp_dir = Path(output_path).parent / "temp_segments"
    temp_dir.mkdir(exist_ok=True)

    # Step 1: Create individual segment videos
    segment_videos = []
    for i, seg in enumerate(segments):
        seg_out = str(temp_dir / f"seg_{i:03d}.mp4")
        result = assemble_still_video(seg["image_path"], seg["audio_path"], seg_out)
        if result:
            segment_videos.append(seg_out)
        else:
            print(f"[assembler] WARNING: segment {i} failed, skipping")

    if not segment_videos:
        print("[assembler] ERROR: no segments produced")
        return None

    # Step 2: Concat all segments
    concat_path = str(temp_dir / "concat.txt")
    with open(concat_path, "w") as f:
        for sv in segment_videos:
            f.write(f"file '{sv}'\n")

    args = [
        "-y",
        "-f", "concat",
        "-safe", "0",
        "-i", concat_path,
        "-c", "copy",
        "-movflags", "+faststart",
        str(output_path),
    ]

    success = _run_ffmpeg(args, "segments concat")

    # Cleanup temp files
    for sv in segment_videos:
        try:
            os.remove(sv)
        except OSError:
            pass
    try:
        os.remove(concat_path)
        temp_dir.rmdir()
    except OSError:
        pass

    return output_path if success else None


def get_audio_duration(audio_path: str) -> float:
    """Get duration of an audio file in seconds using ffprobe."""
    from config import FFPROBE_BIN
    try:
        result = subprocess.run(
            [FFPROBE_BIN, "-v", "quiet", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", str(audio_path)],
            capture_output=True, text=True, timeout=30,
        )
        return float(result.stdout.strip())
    except (ValueError, subprocess.SubprocessError):
        return 0.0


if __name__ == "__main__":
    print("[assembler] Module loaded OK. Use assemble_still_video(), assemble_slideshow(), or assemble_segments_video().")
