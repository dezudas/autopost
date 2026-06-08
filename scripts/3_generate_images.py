"""
Step 3: Generate fruit images + thumbnails using Pollinations AI
Fixed: explicit fonts, verified image paths, larger text, fruit picture visible
"""

import json
import os
import time
import requests
from PIL import Image, ImageDraw, ImageFilter, ImageFont
import io
import urllib.parse


# ── Find a usable TTF font on the system ─────────────────────────────────────
def find_font(size, bold=False):
    """
    GitHub Actions Ubuntu has DejaVu fonts at known paths.
    These render text at any size (PIL default font is tiny and limited).
    """
    candidates = []
    if bold:
        candidates = [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
            "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
        ]
    else:
        candidates = [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
            "/usr/share/fonts/truetype/freefont/FreeSans.ttf",
        ]

    for path in candidates:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except:
                continue
    # Last resort
    return ImageFont.load_default()


def load_video_data():
    with open("output/video_data.json", "r") as f:
        return json.load(f)


def generate_image(prompt, output_path, index, width=1080, height=1920):
    enhanced = (
        f"{prompt}, ultra realistic, vibrant colors, "
        "professional photography, high detail, 4k"
    )
    encoded = urllib.parse.quote(enhanced)
    url = (
        f"https://image.pollinations.ai/prompt/{encoded}"
        f"?width={width}&height={height}&seed={index*77}"
        f"&nologo=true&enhance=true&model=flux"
    )

    for attempt in range(3):
        try:
            print(f"  Image {index+1} attempt {attempt+1}...")
            r = requests.get(url, timeout=30)
            if r.status_code == 200 and len(r.content) > 1000:
                img = Image.open(io.BytesIO(r.content))
                img = img.resize((width, height), Image.LANCZOS)
                img.save(output_path, "PNG", quality=95)
                # Verify file actually saved
                if os.path.exists(output_path) and os.path.getsize(output_path) > 5000:
                    print(f"  Saved: {output_path} ({os.path.getsize(output_path)//1024}KB)")
                    return True
            time.sleep(5)
        except Exception as e:
            print(f"  Error: {e}")
            time.sleep(5)

    return create_fallback_image(output_path, index, width, height)


def create_fallback_image(output_path, index, width, height):
    gradients = [
        [(255,107,53),(255,180,50)],
        [(50,205,50),(0,168,107)],
        [(255,20,147),(255,105,180)],
        [(100,149,237),(65,105,225)],
        [(255,215,0),(255,140,0)],
    ]
    c = gradients[index % len(gradients)]
    img = Image.new("RGB", (width, height))
    draw = ImageDraw.Draw(img)
    for i in range(height):
        ratio = i / height
        r = int(c[0][0]*(1-ratio) + c[1][0]*ratio)
        g = int(c[0][1]*(1-ratio) + c[1][1]*ratio)
        b = int(c[0][2]*(1-ratio) + c[1][2]*ratio)
        draw.line([(0,i),(width,i)], fill=(r,g,b))
    img.save(output_path, "PNG")
    print(f"  Fallback saved: {output_path}")
    return True


# ── Hex color to RGB tuple ────────────────────────────────────────────────────
def hex_to_rgb(hex_str, default=(255,107,53)):
    try:
        h = hex_str.lstrip("#")
        return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))
    except:
        return default


# ── Draw text with thick black outline for visibility ────────────────────────
def draw_outlined_text(draw, position, text, font, fill=(255,255,255),
                       outline=(0,0,0), outline_width=4, anchor="mm"):
    x, y = position
    # Draw outline by drawing text multiple times at offsets
    for dx in range(-outline_width, outline_width+1):
        for dy in range(-outline_width, outline_width+1):
            if dx == 0 and dy == 0:
                continue
            draw.text((x+dx, y+dy), text, font=font, fill=outline, anchor=anchor)
    # Draw main text on top
    draw.text((x, y), text, font=font, fill=fill, anchor=anchor)


# ── Create vertical thumbnail (1080x1920) ─────────────────────────────────────
def create_vertical_thumbnail(fruit_name, emoji, primary, accent, secondary,
                              bg_image_path, output_path):
    W, H = 1080, 1920

    # ── Load fruit image as background (this MUST be visible) ─────────────────
    bg_loaded = False
    if bg_image_path and os.path.exists(bg_image_path) and os.path.getsize(bg_image_path) > 5000:
        try:
            bg = Image.open(bg_image_path).convert("RGB").resize((W, H), Image.LANCZOS)
            print(f"  Using fruit image as thumbnail bg: {bg_image_path}")
            bg_loaded = True
        except Exception as e:
            print(f"  Could not load bg image: {e}")
            bg = create_gradient(W, H, primary, secondary)
    else:
        print(f"  No bg image available, using gradient")
        bg = create_gradient(W, H, primary, secondary)

    # Light overlay so text is readable but fruit image still very visible
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 90))
    img = Image.alpha_composite(bg.convert("RGBA"), overlay).convert("RGB")
    draw = ImageDraw.Draw(img)

    # Load fonts at proper sizes
    font_huge   = find_font(280, bold=True)
    font_xl     = find_font(120, bold=True)
    font_large  = find_font(85,  bold=True)
    font_medium = find_font(60,  bold=True)
    font_small  = find_font(45,  bold=True)
    font_tiny   = find_font(35,  bold=True)

    # ── Top banner moved DOWN (no longer flush with top) ─────────────────────
    # Add some space at top, then the banner sits at y=80 to y=260
    banner_top = 80
    banner_bot = 260
    # Round the corners a bit for a more polished look
    draw.rounded_rectangle([(40, banner_top), (W-40, banner_bot)],
                           radius=30, fill=primary, outline=accent, width=4)
    draw_outlined_text(draw, (W//2, banner_top + 60),  "FRUITS WITH FACTS",
                       font=font_medium, fill=(255,255,255), outline_width=3)
    draw_outlined_text(draw, (W//2, banner_top + 130), "Educational Shorts",
                       font=font_small, fill=(255,230,180), outline_width=2)

    # ── Compact "5 FACTS" badge ────────────────────────────────────────────
    badge_y = 560  # moved down a bit since top yellow box also moved
    # Smaller outer ring
    draw.ellipse([(W//2-180, badge_y-180), (W//2+180, badge_y+180)],
                 fill=accent, outline=(0,0,0), width=7)
    # Smaller inner circle
    draw.ellipse([(W//2-160, badge_y-160), (W//2+160, badge_y+160)],
                 fill=accent)

    # Proportional text inside circle
    font_5 = find_font(140, bold=True)
    font_facts = find_font(55, bold=True)

    draw_outlined_text(draw, (W//2, badge_y - 25), "5",
                       font=font_5, fill=(20,20,20),
                       outline=(255,255,255), outline_width=4)
    draw_outlined_text(draw, (W//2, badge_y + 90), "FACTS",
                       font=font_facts, fill=(20,20,20),
                       outline=(255,255,255), outline_width=3)

    # ── Big fruit name in coloured bar ────────────────────────────────────────
    bar_y = 1080
    bar_h = 220
    draw.rounded_rectangle(
        [(40, bar_y), (W-40, bar_y + bar_h)],
        radius=40, fill=primary, outline=accent, width=10
    )
    draw_outlined_text(draw, (W//2, bar_y + 60), "ABOUT",
                       font=font_medium, fill=(255,255,255), outline_width=3)
    draw_outlined_text(draw, (W//2, bar_y + 150), fruit_name.upper(),
                       font=font_xl, fill=accent, outline=(0,0,0), outline_width=4)

    # ── Yellow attention banner ───────────────────────────────────────────────
    banner_y = 1380
    draw.rounded_rectangle(
        [(60, banner_y), (W-60, banner_y + 140)],
        radius=30, fill=accent
    )
    draw_outlined_text(draw, (W//2, banner_y + 70), "FACT #3 IS WILD!",
                       font=font_large, fill=secondary, outline=(0,0,0), outline_width=3)

    # ── Bottom CTA ────────────────────────────────────────────────────────────
    draw_outlined_text(draw, (W//2, 1620), "WATCH NOW",
                       font=font_large, fill=accent, outline=(0,0,0), outline_width=4)

    # ── Footer ────────────────────────────────────────────────────────────────
    draw.rectangle([(0, 1810), (W, H)], fill=primary)
    draw_outlined_text(draw, (W//2, 1865), "#Shorts #FruitFacts",
                       font=font_small, fill=(255,255,255), outline_width=2)

    img.save(output_path, "PNG", quality=95)
    print(f"  Vertical thumbnail saved: {output_path}")


# ── Create horizontal thumbnail (1280x720) ────────────────────────────────────
def create_horizontal_thumbnail(fruit_name, emoji, primary, accent, secondary,
                                bg_image_path, output_path):
    W, H = 1280, 720

    bg_loaded = False
    if bg_image_path and os.path.exists(bg_image_path) and os.path.getsize(bg_image_path) > 5000:
        try:
            bg = Image.open(bg_image_path).convert("RGB").resize((W, H), Image.LANCZOS)
            bg_loaded = True
        except:
            bg = create_gradient(W, H, primary, secondary)
    else:
        bg = create_gradient(W, H, primary, secondary)

    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 100))
    img = Image.alpha_composite(bg.convert("RGBA"), overlay).convert("RGB")
    draw = ImageDraw.Draw(img)

    font_huge   = find_font(180, bold=True)
    font_xl     = find_font(90,  bold=True)
    font_large  = find_font(70,  bold=True)
    font_medium = find_font(50,  bold=True)

    # Top banner
    draw.rectangle([(0, 0), (W, 70)], fill=primary)
    draw_outlined_text(draw, (W//2, 35), "FRUITS WITH FACTS",
                       font=font_medium, fill=(255,255,255), outline_width=2)

    # Smaller left circle with "5"
    draw.ellipse([(120, 200), (480, 560)], fill=accent, outline=(0,0,0), width=6)
    font_5h = find_font(140, bold=True)
    font_factsh = find_font(60, bold=True)
    draw_outlined_text(draw, (300, 350), "5",
                       font=font_5h, fill=(20,20,20),
                       outline=(255,255,255), outline_width=3)
    draw_outlined_text(draw, (300, 480), "FACTS",
                       font=font_factsh, fill=(20,20,20),
                       outline=(255,255,255), outline_width=2)

    # Right side text
    draw_outlined_text(draw, (620, 200), "ABOUT",
                       font=font_xl, fill=(255,255,255), outline_width=4, anchor="lm")
    draw_outlined_text(draw, (620, 320), fruit_name.upper(),
                       font=font_huge, fill=accent, outline=(0,0,0), outline_width=4, anchor="lm")
    draw_outlined_text(draw, (620, 470), "YOU MUST",
                       font=font_large, fill=(255,255,255), outline_width=3, anchor="lm")
    draw_outlined_text(draw, (620, 560), "KNOW!",
                       font=font_large, fill=accent, outline=(0,0,0), outline_width=3, anchor="lm")

    # Bottom banner
    draw.rectangle([(0, 660), (W, H)], fill=primary)
    draw_outlined_text(draw, (W//2, 690), "#Shorts #FruitFacts",
                       font=font_medium, fill=(255,255,255), outline_width=2)

    img.save(output_path, "JPEG", quality=95)
    print(f"  Horizontal thumbnail saved: {output_path}")


def create_gradient(width, height, color_top, color_bottom):
    img = Image.new("RGB", (width, height))
    draw = ImageDraw.Draw(img)
    for i in range(height):
        ratio = i / height
        r = int(color_top[0]*(1-ratio) + color_bottom[0]*ratio)
        g = int(color_top[1]*(1-ratio) + color_bottom[1]*ratio)
        b = int(color_top[2]*(1-ratio) + color_bottom[2]*ratio)
        draw.line([(0,i),(width,i)], fill=(r,g,b))
    return img


# ── Main thumbnail orchestrator ──────────────────────────────────────────────
def create_beautiful_thumbnails(fruit_name, emoji, colors, image_paths):
    primary   = hex_to_rgb(colors.get("primary",   "#FF6B35"), (255,107,53))
    accent    = hex_to_rgb(colors.get("accent",    "#FFE66D"), (255,230,109))
    secondary = hex_to_rgb(colors.get("secondary", "#C44A1F"), (196,74,31))

    # Use the FIRST scene image (clean fruit on white background) as backdrop
    bg_image = image_paths[0] if image_paths else None

    create_vertical_thumbnail(
        fruit_name, emoji, primary, accent, secondary,
        bg_image, "output/thumbnail_vertical.png"
    )

    create_horizontal_thumbnail(
        fruit_name, emoji, primary, accent, secondary,
        bg_image, "output/thumbnail.jpg"
    )


# ── Main ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    data = load_video_data()
    fruit = data["fruit"]
    emoji = data.get("emoji", "🍎")
    colors = data.get("colors", {})
    prompts = data["image_prompts"]

    os.makedirs("output/images", exist_ok=True)

    image_paths = []
    for i, prompt in enumerate(prompts):
        out = f"output/images/scene_{i+1}.png"
        print(f"Generating image {i+1}/5...")
        generate_image(prompt, out, i, width=1080, height=1920)
        image_paths.append(out)
        time.sleep(2)

    print("\nCreating beautiful thumbnails...")
    create_beautiful_thumbnails(fruit, emoji, colors, image_paths)

    print(f"\nAll {len(image_paths)} images + 2 thumbnails ready!")
    # List final files for debugging
    print("\nFinal output files:")
    for root, dirs, files in os.walk("output"):
        for fn in files:
            path = os.path.join(root, fn)
            size = os.path.getsize(path)
            print(f"  {path} ({size//1024}KB)")
