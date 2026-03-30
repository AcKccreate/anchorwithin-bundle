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


def generate_binaural_background(beat_type: str, output_path: str,
                                  width: int = 1920, height: int = 1080) -> str:
    """Generate background for binaural beat videos with wave pattern."""
    type_colors = {
        "delta": ((5, 10, 40), (15, 20, 60), (30, 50, 150)),      # deep blue
        "theta": ((10, 5, 35), (25, 15, 65), (80, 50, 180)),      # indigo
        "alpha": ((5, 20, 15), (15, 40, 25), (50, 180, 100)),     # green
        "beta": ((20, 15, 5), (40, 30, 15), (180, 150, 50)),      # gold
        "gamma": ((25, 20, 5), (50, 40, 15), (220, 180, 50)),     # bright gold
    }
    colors = type_colors.get(beat_type.lower(), type_colors["alpha"])
    bg_top, bg_bot, accent = colors

    img = Image.new("RGB", (width, height))
    draw = ImageDraw.Draw(img)

    for y in range(height):
        r = ratio = y / height
        c = tuple(int(bg_top[i] + (bg_bot[i] - bg_top[i]) * r) for i in range(3))
        draw.line([(0, y), (width, y)], fill=c)

    # Wave pattern
    import math as _math
    cx, cy = width // 2, height // 2
    for i in range(5):
        points = []
        for x in range(0, width, 4):
            offset = 40 * (i + 1)
            y_wave = cy + int(offset * _math.sin(x * 0.008 + i * 1.2))
            points.append((x, y_wave))
        if len(points) > 1:
            wave_color = tuple(max(0, min(255, c // (i + 2))) for c in accent)
            draw.line(points, fill=wave_color, width=1)

    # "L" and "R" labels for stereo
    font = _get_font(48, bold=True)
    draw.text((80, cy - 24), "L", fill=(*accent, ), font=font)
    draw.text((width - 130, cy - 24), "R", fill=(*accent, ), font=font)

    # Beat type label
    label_font = _get_font(28)
    label = f"{beat_type.upper()} WAVES"
    bbox = draw.textbbox((0, 0), label, font=label_font)
    draw.text(((width - (bbox[2] - bbox[0])) // 2, height - 80), label,
              fill=accent, font=label_font)

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    img.save(output_path, "PNG")
    return output_path


def generate_ambient_background(theme: str, output_path: str,
                                width: int = 1920, height: int = 1080) -> str:
    """Generate dark themed background for sleep/nature ambient videos."""
    theme_colors = {
        "rain": ((12, 15, 25), (20, 25, 40)),
        "ocean": ((8, 18, 28), (15, 30, 45)),
        "forest": ((8, 18, 12), (15, 30, 20)),
        "night": ((5, 5, 15), (12, 10, 25)),
        "fire": ((20, 12, 5), (35, 20, 10)),
    }
    top, bot = theme_colors.get(theme.lower(), theme_colors["night"])

    img = Image.new("RGB", (width, height))
    draw = ImageDraw.Draw(img)

    for y in range(height):
        r = y / height
        c = tuple(int(top[i] + (bot[i] - top[i]) * r) for i in range(3))
        draw.line([(0, y), (width, y)], fill=c)

    # Subtle dot/particle overlay
    import random
    rng = random.Random(42)
    for _ in range(60):
        x, y = rng.randint(0, width), rng.randint(0, height)
        brightness = rng.randint(25, 55)
        size = rng.randint(1, 3)
        draw.ellipse([x - size, y - size, x + size, y + size],
                     fill=(brightness, brightness, brightness + 10))

    # Theme label at bottom
    label_font = _get_font(24)
    draw.text((width // 2 - 60, height - 50), theme.upper(),
              fill=(60, 60, 70), font=label_font)

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    img.save(output_path, "PNG")
    return output_path


def generate_chakra_background(chakra_name: str, freq_hz: float, output_path: str,
                               width: int = 1920, height: int = 1080) -> str:
    """Generate background with chakra-colored mandala and label."""
    chakra_colors = {
        "root": (180, 40, 40),
        "sacral": (200, 120, 40),
        "solar plexus": (200, 180, 40),
        "heart": (40, 170, 80),
        "throat": (40, 120, 200),
        "third eye": (80, 50, 180),
        "crown": (150, 50, 200),
    }
    accent = chakra_colors.get(chakra_name.lower(), (150, 50, 200))
    dim = tuple(c // 5 for c in accent)

    img = Image.new("RGB", (width, height))
    draw = ImageDraw.Draw(img)

    for y in range(height):
        r = y / height
        c = tuple(int(5 + dim[i] * r) for i in range(3))
        draw.line([(0, y), (width, y)], fill=c)

    # Mandala circles
    cx, cy = width // 2, height // 2
    ring_color = tuple(c // 3 for c in accent)
    for radius in [220, 170, 120, 70]:
        draw.ellipse([cx - radius, cy - radius, cx + radius, cy + radius],
                     outline=ring_color, width=1)
    _draw_sacred_geometry(draw, cx, cy, 150, ring_color)

    # Frequency text
    font_large = _get_font(120, bold=True)
    freq_text = f"{int(freq_hz)}Hz"
    bbox = draw.textbbox((0, 0), freq_text, font=font_large)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    tx, ty = (width - tw) // 2, (height - th) // 2 - 30
    for off in [4, 2]:
        draw.text((tx + off, ty), freq_text, fill=ring_color, font=font_large)
        draw.text((tx - off, ty), freq_text, fill=ring_color, font=font_large)
    draw.text((tx, ty), freq_text, fill=accent, font=font_large)

    # Chakra name
    name_font = _get_font(32)
    name_text = f"{chakra_name.upper()} CHAKRA"
    bbox = draw.textbbox((0, 0), name_text, font=name_font)
    draw.text(((width - (bbox[2] - bbox[0])) // 2, ty + th + 20),
              name_text, fill=tuple(min(255, c + 40) for c in accent), font=name_font)

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    img.save(output_path, "PNG")
    return output_path


def generate_gradient_background(color_top: tuple, color_bottom: tuple,
                                 title_text: str, output_path: str,
                                 width: int = 1920, height: int = 1080) -> str:
    """Generate a simple two-color gradient background with centered title text."""
    img = Image.new("RGB", (width, height))
    draw = ImageDraw.Draw(img)

    for y in range(height):
        r = y / height
        c = tuple(int(color_top[i] + (color_bottom[i] - color_top[i]) * r) for i in range(3))
        draw.line([(0, y), (width, y)], fill=c)

    if title_text:
        font = _get_font(60, bold=True)
        # Word wrap
        words = title_text.split()
        lines, current = [], ""
        for word in words:
            test = f"{current} {word}".strip()
            bbox = draw.textbbox((0, 0), test, font=font)
            if bbox[2] - bbox[0] > width - 200:
                if current:
                    lines.append(current)
                current = word
            else:
                current = test
        if current:
            lines.append(current)

        line_h = 75
        total_h = len(lines) * line_h
        start_y = (height - total_h) // 2
        for i, line in enumerate(lines):
            bbox = draw.textbbox((0, 0), line, font=font)
            lw = bbox[2] - bbox[0]
            draw.text(((width - lw) // 2, start_y + i * line_h), line,
                      fill=(230, 225, 215), font=font)

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    img.save(output_path, "PNG")
    return output_path


def generate_tool_tip_card(tool_name: str, tip_text: str, output_path: str,
                           width: int = 1080, height: int = 1920) -> str:
    """Generate a vertical tool tip card for AnchorWithin shorts."""
    img = Image.new("RGB", (width, height))
    draw = ImageDraw.Draw(img)

    # Dark background
    for y in range(height):
        r = y / height
        draw.line([(0, y), (width, y)], fill=(int(8 + 10 * r), int(10 + 6 * r), int(20 + 10 * r)))

    # Bronze accent bar
    bronze = (200, 168, 75)
    draw.rectangle([0, 0, width, 8], fill=bronze)

    # "ANCHORWITHIN" header
    header_font = _get_font(28)
    draw.text((width // 2 - 100, 60), "ANCHORWITHIN", fill=(120, 100, 55), font=header_font)

    # Tool name badge
    tool_font = _get_font(36, bold=True)
    bbox = draw.textbbox((0, 0), tool_name, font=tool_font)
    tw = bbox[2] - bbox[0]
    badge_x = (width - tw) // 2 - 20
    draw.rounded_rectangle([badge_x, 130, badge_x + tw + 40, 185], radius=12, fill=(35, 30, 50))
    draw.text(((width - tw) // 2, 138), tool_name, fill=bronze, font=tool_font)

    # Tip text — large, centered, word-wrapped
    tip_font = _get_font(48, bold=True)
    words = tip_text.split()
    lines, current = [], ""
    for word in words:
        test = f"{current} {word}".strip()
        bbox = draw.textbbox((0, 0), test, font=tip_font)
        if bbox[2] - bbox[0] > width - 120:
            if current:
                lines.append(current)
            current = word
        else:
            current = test
    if current:
        lines.append(current)

    line_h = 65
    total_h = len(lines) * line_h
    start_y = (height - total_h) // 2 + 50
    for i, line in enumerate(lines):
        bbox = draw.textbbox((0, 0), line, font=tip_font)
        lw = bbox[2] - bbox[0]
        draw.text(((width - lw) // 2, start_y + i * line_h), line,
                  fill=(240, 235, 220), font=tip_font)

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    img.save(output_path, "PNG")
    return output_path


def generate_recap_frame(week_label: str, section_title: str, items: list,
                         output_path: str, width: int = 1920, height: int = 1080) -> str:
    """Generate a weekly recap slide frame."""
    img = Image.new("RGB", (width, height))
    draw = ImageDraw.Draw(img)

    # Dark navy gradient
    for y in range(height):
        r = y / height
        draw.line([(0, y), (width, y)], fill=(int(8 + 12 * r), int(10 + 8 * r), int(25 + 15 * r)))

    # Week label badge (bronze)
    bronze = (200, 168, 75)
    badge_font = _get_font(22)
    draw.rounded_rectangle([60, 40, 350, 78], radius=12, fill=(40, 35, 25))
    draw.text((80, 46), week_label, fill=bronze, font=badge_font)

    # Section title
    title_font = _get_font(56, bold=True)
    draw.text((80, 110), section_title, fill=(240, 235, 220), font=title_font)

    # Items
    item_font = _get_font(34)
    y_pos = 210
    for item in items:
        draw.text((100, y_pos), f"▸  {item}", fill=(160, 180, 170), font=item_font)
        y_pos += 55

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    img.save(output_path, "PNG")
    return output_path


if __name__ == "__main__":
    generate_frequency_background(528, "/tmp/test_freq_bg.png")
    print("Generated: frequency background")
    generate_binaural_background("alpha", "/tmp/test_binaural_bg.png")
    print("Generated: binaural background")
    generate_ambient_background("night", "/tmp/test_ambient_bg.png")
    print("Generated: ambient background")
    generate_chakra_background("heart", 639, "/tmp/test_chakra_bg.png")
    print("Generated: chakra background")
    generate_gradient_background((8, 16, 30), (200, 168, 75), "Find Your Inner Compass", "/tmp/test_gradient_bg.png")
    print("Generated: gradient background")
    generate_tool_tip_card("AI Resume Optimizer", "This ONE keyword trick gets you past 90% of ATS filters", "/tmp/test_tool_tip.png")
    print("Generated: tool tip card")
    generate_character_card("Mia", "/tmp/test_card_mia.png")
    print("Generated: character card")
