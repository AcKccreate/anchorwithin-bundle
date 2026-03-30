"""
Visual Generator — creates background images, character cards, and slide frames.
Uses Pillow only (no external dependencies).
"""

import math
from PIL import Image, ImageDraw, ImageFont
from pathlib import Path


def _get_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    """Get a font, falling back to default if no TTF available."""
    font_paths = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        "C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf",
        "C:/Windows/Fonts/calibrib.ttf" if bold else "C:/Windows/Fonts/calibri.ttf",
    ]
    for fp in font_paths:
        try:
            return ImageFont.truetype(fp, size)
        except (OSError, IOError):
            continue
    return ImageFont.load_default()


def _draw_sacred_geometry(draw: ImageDraw.Draw, cx: int, cy: int,
                          radius: int, color: tuple, num_circles: int = 6):
    """Draw subtle sacred geometry (Flower of Life pattern) circles."""
    # Central circle
    draw.ellipse([cx - radius, cy - radius, cx + radius, cy + radius],
                 outline=color, width=1)
    # Surrounding circles
    for i in range(num_circles):
        angle = 2 * math.pi * i / num_circles
        x = cx + int(radius * math.cos(angle))
        y = cy + int(radius * math.sin(angle))
        draw.ellipse([x - radius, y - radius, x + radius, y + radius],
                     outline=color, width=1)


def generate_frequency_background(freq_hz: float, output_path: str,
                                  width: int = 1920, height: int = 1080) -> str:
    """
    Generate a dark gradient background with frequency text and sacred geometry.

    Returns path to saved PNG.
    """
    img = Image.new("RGB", (width, height))
    draw = ImageDraw.Draw(img)

    # Dark gradient background (deep purple to dark blue)
    for y in range(height):
        ratio = y / height
        r = int(10 + 15 * ratio)
        g = int(5 + 10 * (1 - ratio))
        b = int(30 + 40 * ratio)
        draw.line([(0, y), (width, y)], fill=(r, g, b))

    # Sacred geometry in center (subtle)
    geo_color = (40, 30, 80)
    _draw_sacred_geometry(draw, width // 2, height // 2, 200, geo_color)
    _draw_sacred_geometry(draw, width // 2, height // 2, 120, geo_color)

    # Glowing frequency number — large centered text
    freq_text = f"{int(freq_hz)}Hz"
    font_large = _get_font(180, bold=True)
    font_sub = _get_font(36)

    # Draw glow effect (multiple layers of text with decreasing opacity)
    bbox = draw.textbbox((0, 0), freq_text, font=font_large)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    tx = (width - tw) // 2
    ty = (height - th) // 2 - 40

    # Glow layers
    for offset in [6, 4, 2]:
        glow_color = (80, 60, 180)
        draw.text((tx - offset, ty), freq_text, fill=glow_color, font=font_large)
        draw.text((tx + offset, ty), freq_text, fill=glow_color, font=font_large)
        draw.text((tx, ty - offset), freq_text, fill=glow_color, font=font_large)
        draw.text((tx, ty + offset), freq_text, fill=glow_color, font=font_large)

    # Main text (bright white-purple)
    draw.text((tx, ty), freq_text, fill=(220, 200, 255), font=font_large)

    # Subtitle
    subtitle = "Deep Healing Frequency"
    bbox_s = draw.textbbox((0, 0), subtitle, font=font_sub)
    sw = bbox_s[2] - bbox_s[0]
    draw.text(((width - sw) // 2, ty + th + 20), subtitle,
              fill=(160, 140, 200), font=font_sub)

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    img.save(output_path, "PNG")
    return output_path


def generate_character_card(name: str, output_path: str,
                            width: int = 1080, height: int = 1920) -> str:
    """
    Generate a vertical character card for Global Council shorts.
    Dark background with character name and colored accent.
    """
    # Character color map
    colors = {
        "mia": (255, 120, 180),
        "sora": (120, 200, 255),
        "hoshi": (255, 200, 100),
        "julian": (100, 255, 150),
        "mateo": (200, 130, 255),
    }
    accent = colors.get(name.lower(), (200, 200, 200))

    img = Image.new("RGB", (width, height))
    draw = ImageDraw.Draw(img)

    # Dark gradient
    for y in range(height):
        ratio = y / height
        r = int(15 + 10 * ratio)
        g = int(12 + 8 * ratio)
        b = int(25 + 15 * ratio)
        draw.line([(0, y), (width, y)], fill=(r, g, b))

    # Accent bar at top
    draw.rectangle([0, 0, width, 8], fill=accent)

    # Large circle avatar placeholder
    cx, cy, cr = width // 2, height // 3, 180
    draw.ellipse([cx - cr, cy - cr, cx + cr, cy + cr], outline=accent, width=4)
    # Initial letter inside circle
    initial_font = _get_font(140, bold=True)
    initial = name[0].upper()
    bbox = draw.textbbox((0, 0), initial, font=initial_font)
    iw, ih = bbox[2] - bbox[0], bbox[3] - bbox[1]
    draw.text((cx - iw // 2, cy - ih // 2), initial, fill=accent, font=initial_font)

    # Character name below circle
    name_font = _get_font(72, bold=True)
    bbox = draw.textbbox((0, 0), name.upper(), font=name_font)
    nw = bbox[2] - bbox[0]
    draw.text(((width - nw) // 2, cy + cr + 40), name.upper(), fill=(240, 240, 240), font=name_font)

    # "THE GLOBAL COUNCIL" label
    label_font = _get_font(28)
    label = "THE GLOBAL COUNCIL"
    bbox = draw.textbbox((0, 0), label, font=label_font)
    lw = bbox[2] - bbox[0]
    draw.text(((width - lw) // 2, cy + cr + 130), label, fill=(120, 120, 140), font=label_font)

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    img.save(output_path, "PNG")
    return output_path


def generate_explainer_frame(title: str, bullet_points: list, frame_num: int,
                             output_path: str, width: int = 1920, height: int = 1080) -> str:
    """
    Generate a slide-style frame for explainer videos.
    Dark background with title and bullet points.
    """
    img = Image.new("RGB", (width, height))
    draw = ImageDraw.Draw(img)

    # Gradient background (dark teal to dark)
    for y in range(height):
        ratio = y / height
        r = int(8 + 12 * ratio)
        g = int(15 + 25 * ratio)
        b = int(25 + 20 * ratio)
        draw.line([(0, y), (width, y)], fill=(r, g, b))

    # Slide number badge
    badge_font = _get_font(24)
    badge_text = f"STEP {frame_num}"
    draw.rounded_rectangle([60, 50, 200, 90], radius=15, fill=(50, 180, 120))
    bbox = draw.textbbox((0, 0), badge_text, font=badge_font)
    bw = bbox[2] - bbox[0]
    draw.text((130 - bw // 2, 55), badge_text, fill=(255, 255, 255), font=badge_font)

    # Title
    title_font = _get_font(64, bold=True)
    # Word-wrap title
    words = title.split()
    lines = []
    current = ""
    for word in words:
        test = f"{current} {word}".strip()
        bbox = draw.textbbox((0, 0), test, font=title_font)
        if bbox[2] - bbox[0] > width - 160:
            lines.append(current)
            current = word
        else:
            current = test
    if current:
        lines.append(current)

    y_pos = 120
    for line in lines:
        draw.text((80, y_pos), line, fill=(255, 255, 255), font=title_font)
        y_pos += 80

    # Bullet points
    bullet_font = _get_font(36)
    y_pos += 40
    for bp in bullet_points:
        draw.text((100, y_pos), f"▸  {bp}", fill=(180, 220, 200), font=bullet_font)
        y_pos += 60

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    img.save(output_path, "PNG")
    return output_path


if __name__ == "__main__":
    generate_frequency_background(528, "/tmp/test_freq_bg.png")
    print("Generated frequency background: /tmp/test_freq_bg.png")
    generate_character_card("Mia", "/tmp/test_card_mia.png")
    print("Generated character card: /tmp/test_card_mia.png")
    generate_explainer_frame("How to Build an AI App", ["Use Python", "Add an API", "Deploy to cloud"], 1, "/tmp/test_slide.png")
    print("Generated explainer frame: /tmp/test_slide.png")
