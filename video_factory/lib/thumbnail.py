"""
Thumbnail Generator — creates 1280x720 YouTube thumbnails.
"""

import math
from PIL import Image, ImageDraw, ImageFont
from pathlib import Path


def _get_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    font_paths = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        "C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf",
    ]
    for fp in font_paths:
        try:
            return ImageFont.truetype(fp, size)
        except (OSError, IOError):
            continue
    return ImageFont.load_default()


def generate_thumbnail(title: str, subtitle: str, output_path: str,
                       style: str = "frequency", accent_color: tuple = None) -> str:
    """
    Generate a 1280x720 YouTube thumbnail.

    Args:
        title: Main text (large)
        subtitle: Secondary text (smaller)
        output_path: Where to save the .jpg
        style: "frequency", "explainer", or "shorts"
        accent_color: RGB tuple override for accent color

    Returns:
        Path to saved thumbnail.
    """
    width, height = 1280, 720
    img = Image.new("RGB", (width, height))
    draw = ImageDraw.Draw(img)

    if style == "frequency":
        # Dark purple gradient + glowing number
        for y in range(height):
            ratio = y / height
            r = int(12 + 18 * ratio)
            g = int(5 + 8 * (1 - ratio))
            b = int(35 + 50 * ratio)
            draw.line([(0, y), (width, y)], fill=(r, g, b))

        # Sacred geometry circles (subtle)
        geo_color = (45, 35, 90)
        cx, cy = width // 2, height // 2
        for radius in [250, 170, 100]:
            draw.ellipse([cx - radius, cy - radius, cx + radius, cy + radius],
                         outline=geo_color, width=1)

        title_font = _get_font(140, bold=True)
        sub_font = _get_font(32)
        title_color = (230, 210, 255)
        glow_color = accent_color or (100, 70, 200)

    elif style == "explainer":
        # Dark teal gradient + bold text
        for y in range(height):
            ratio = y / height
            r = int(10 + 15 * ratio)
            g = int(25 + 35 * ratio)
            b = int(35 + 25 * ratio)
            draw.line([(0, y), (width, y)], fill=(r, g, b))

        title_font = _get_font(80, bold=True)
        sub_font = _get_font(36)
        title_color = (255, 255, 255)
        glow_color = accent_color or (50, 200, 130)

    elif style == "shorts":
        # Dark with character accent
        for y in range(height):
            ratio = y / height
            draw.line([(0, y), (width, y)], fill=(20, 18, 30))

        # Accent stripe
        ac = accent_color or (255, 120, 180)
        draw.rectangle([0, 0, width, 10], fill=ac)
        draw.rectangle([0, height - 10, width, height], fill=ac)

        title_font = _get_font(72, bold=True)
        sub_font = _get_font(36)
        title_color = (255, 255, 255)
        glow_color = ac

    else:
        for y in range(height):
            draw.line([(0, y), (width, y)], fill=(20, 20, 30))
        title_font = _get_font(80, bold=True)
        sub_font = _get_font(32)
        title_color = (255, 255, 255)
        glow_color = (100, 100, 200)

    # Word-wrap title
    words = title.split()
    lines = []
    current = ""
    max_w = width - 120
    for word in words:
        test = f"{current} {word}".strip()
        bbox = draw.textbbox((0, 0), test, font=title_font)
        if bbox[2] - bbox[0] > max_w:
            if current:
                lines.append(current)
            current = word
        else:
            current = test
    if current:
        lines.append(current)

    # Calculate total text block height
    line_h = draw.textbbox((0, 0), "Ay", font=title_font)[3] + 10
    total_h = len(lines) * line_h
    start_y = (height - total_h) // 2 - 30

    # Draw title lines with glow
    for i, line in enumerate(lines):
        bbox = draw.textbbox((0, 0), line, font=title_font)
        lw = bbox[2] - bbox[0]
        x = (width - lw) // 2
        y = start_y + i * line_h

        # Glow
        for off in [4, 2]:
            draw.text((x - off, y), line, fill=glow_color, font=title_font)
            draw.text((x + off, y), line, fill=glow_color, font=title_font)
            draw.text((x, y - off), line, fill=glow_color, font=title_font)
            draw.text((x, y + off), line, fill=glow_color, font=title_font)

        draw.text((x, y), line, fill=title_color, font=title_font)

    # Subtitle
    bbox = draw.textbbox((0, 0), subtitle, font=sub_font)
    sw = bbox[2] - bbox[0]
    sub_y = start_y + len(lines) * line_h + 20
    draw.text(((width - sw) // 2, sub_y), subtitle, fill=(180, 180, 200), font=sub_font)

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    img.save(output_path, "JPEG", quality=92)
    return output_path


if __name__ == "__main__":
    generate_thumbnail("432Hz", "Deep Healing Frequency | Sleep Music", "/tmp/test_thumb.jpg", style="frequency")
    print("Generated: /tmp/test_thumb.jpg")
