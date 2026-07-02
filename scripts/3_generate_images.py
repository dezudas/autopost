"""
Step 3: Generate guitar images using Unsplash API
- FREE (50 requests/hour, no credit card)
- Real professional photography (much better than AI generated!)
- Fast CDN — images download in 1-2 seconds
- High resolution — 1080x1920 vertical format

SETUP:
1. Go to unsplash.com/developers
2. Register as developer (free, no card)
3. Create new application
4. Copy Access Key
5. Add to GitHub Secrets as UNSPLASH_ACCESS_KEY
"""

import json
import os
import time
import requests
from PIL import Image, ImageDraw, ImageFilter, ImageFont
import io
import urllib.parse


# ── Font utilities ────────────────────────────────────────────────────────────
_BEBAS_PATH = None  # cached after first download


def _download_bebas():
    path = "output/fonts/BebasNeue-Regular.ttf"
    if os.path.exists(path):
        return path
    os.makedirs("output/fonts", exist_ok=True)
    url = "https://github.com/google/fonts/raw/main/ofl/bebasnew/BebasNeue-Regular.ttf"
    try:
        r = requests.get(url, timeout=15)
        if r.status_code == 200 and len(r.content) > 10000:
            with open(path, "wb") as f:
                f.write(r.content)
            print(f"  Bebas Neue downloaded → {path}")
            return path
    except Exception as e:
        print(f"  Bebas Neue download failed: {e}")
    return None


def get_display_font(size):
    """Bebas Neue for punchy display numbers/headlines; falls back to Poppins Bold."""
    global _BEBAS_PATH
    if _BEBAS_PATH is None:
        _BEBAS_PATH = _download_bebas() or ""
    candidates = ([_BEBAS_PATH] if _BEBAS_PATH else []) + [
        "/usr/share/fonts/truetype/poppins/Poppins-Bold.ttf",
        "/usr/share/fonts/truetype/manrope/Manrope-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    ]
    for p in candidates:
        if p and os.path.exists(p):
            try:
                return ImageFont.truetype(p, size)
            except Exception:
                continue
    return ImageFont.load_default()


def get_body_font(size, bold=False):
    """Poppins / Manrope for readable badge and body text."""
    w = "Bold" if bold else "Regular"
    candidates = [
        f"/usr/share/fonts/truetype/poppins/Poppins-{w}.ttf",
        f"/usr/share/fonts/truetype/manrope/Manrope-{w}.ttf",
        "/usr/share/fonts/opentype/noto/NotoSans-Bold.ttf" if bold
            else "/usr/share/fonts/opentype/noto/NotoSans-Regular.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold
            else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    for p in candidates:
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, size)
            except Exception:
                continue
    return ImageFont.load_default()


def draw_strings(base_rgba, y_center, n=6, spacing=13, opacity=55, color=(255, 193, 7)):
    """Overlay n horizontal guitar-string lines centered at y_center (the channel's signature mark)."""
    W, H = base_rgba.size
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    for i in range(n):
        y = int(y_center + (i - n / 2 + 0.5) * spacing)
        d.line([(0, y), (W, y)], fill=(*color, opacity), width=1)
    return Image.alpha_composite(base_rgba, ov)


def load_video_data():
    with open("output/video_data.json", "r") as f:
        return json.load(f)


def hex_to_rgb(hex_str, default=(255, 193, 7)):  # default: #FFC107 (design.md primary)
    try:
        h = hex_str.lstrip("#")
        return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))
    except:
        return default


# ── Search and download image from Unsplash ──────────────────────────────────
def get_unsplash_image(query, output_path, access_key, orientation="portrait", index=0):
    """
    Search Unsplash for high quality fruit photos.
    Downloads as 1080x1920 vertical (portrait) for Shorts.
    """
    headers = {
        "Authorization": f"Client-ID {access_key}",
        "Accept-Version": "v1"
    }

    # Search for photos
    search_url = "https://api.unsplash.com/search/photos"
    params = {
        "query":       query,
        "orientation": orientation,   # portrait = vertical (best for Shorts)
        "per_page":    10,
        "page":        1,
        "order_by":    "relevant",
        "content_filter": "high"      # only safe, high-quality images
    }

    print(f"  Searching Unsplash: '{query}'...")
    r = requests.get(search_url, headers=headers, params=params, timeout=15)
    print(f"  Search status: {r.status_code}")

    if r.status_code == 401:
        print("  Invalid UNSPLASH_ACCESS_KEY — check GitHub Secret!")
        return False
    if r.status_code == 403:
        print("  Rate limit reached (50/hour) — using fallback")
        return False
    if r.status_code != 200:
        print(f"  Search error: {r.text[:200]}")
        return False

    results = r.json().get("results", [])
    if not results:
        print(f"  No results for '{query}' — trying broader search")
        return False

    # Pick different image for each scene (cycle through results)
    photo = results[index % len(results)]
    photo_id   = photo["id"]
    photo_url  = photo["urls"]["regular"]  # 1080px wide
    photo_user = photo["user"]["name"]

    print(f"  Found: {photo_id} by {photo_user}")

    # Download the actual image
    # Add size params for vertical format
    download_url = f"{photo_url}&w=1080&h=1920&fit=crop&crop=entropy"

    img_resp = requests.get(download_url, timeout=30)
    if img_resp.status_code != 200 or len(img_resp.content) < 5000:
        print(f"  Download failed: {img_resp.status_code}")
        return False

    # Resize to exactly 1080x1920
    img = Image.open(io.BytesIO(img_resp.content)).convert("RGB")
    img = img.resize((1080, 1920), Image.LANCZOS)
    img.save(output_path, "PNG", quality=95)

    print(f"  Saved: {output_path} ({os.path.getsize(output_path)//1024}KB) — Photo by {photo_user}")

    # Return attribution info
    return {
        "photographer": photo_user,
        "photo_id":     photo_id,
        "unsplash_url": photo["links"]["html"]
    }


# ── Fallback: Pollinations AI image ──────────────────────────────────────────
def get_pollinations_image(prompt, output_path, index):
    """Fallback if Unsplash fails"""
    import urllib.parse
    enhanced = f"{prompt}, ultra realistic, vibrant colors, professional photography, 4k"
    encoded  = urllib.parse.quote(enhanced)

    urls = [
        f"https://image.pollinations.ai/prompt/{encoded}?width=1080&height=1920&seed={index*77}&nologo=true&model=flux",
        f"https://image.pollinations.ai/prompt/{encoded}?width=1080&height=1920&seed={index*77+1}&nologo=true",
    ]

    for url in urls:
        try:
            r = requests.get(url, timeout=90)
            if r.status_code == 200 and len(r.content) > 5000:
                img = Image.open(io.BytesIO(r.content))
                img = img.resize((1080, 1920), Image.LANCZOS)
                img.save(output_path, "PNG", quality=95)
                print(f"  Pollinations fallback saved: {output_path}")
                return True
        except Exception as e:
            print(f"  Pollinations error: {e}")
            time.sleep(10)
    return False


# ── Create gradient fallback ──────────────────────────────────────────────────
def create_fallback_image(output_path, index, width=1080, height=1920):
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
    print(f"  Gradient fallback saved: {output_path}")
    return True


# ── Create beautiful thumbnails ───────────────────────────────────────────────
def draw_outlined_text(draw, pos, text, font, fill=(255,255,255),
                       outline=(0,0,0), outline_width=4, anchor="mm"):
    x, y = pos
    for dx in range(-outline_width, outline_width+1):
        for dy in range(-outline_width, outline_width+1):
            if dx*dx + dy*dy <= outline_width*outline_width:
                draw.text((x+dx, y+dy), text, font=font, fill=outline, anchor=anchor)
    draw.text((x, y), text, font=font, fill=fill, anchor=anchor)


def create_vertical_thumbnail(fruit_name, emoji, primary, accent, secondary,
                               bg_image_path, output_path):
    W, H = 1080, 1920
    try:
        bg = Image.open(bg_image_path).convert("RGB").resize((W, H), Image.LANCZOS)
    except Exception:
        bg = Image.new("RGB", (W, H), (18, 16, 8))

    # Dark stage overlay: heavy strips at top/bottom, light tint in centre
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 90))
    ovd = ImageDraw.Draw(ov)
    ovd.rectangle([(0, 0),       (W, 370)],  fill=(0, 0, 0, 170))
    ovd.rectangle([(0, H - 310), (W, H)],    fill=(0, 0, 0, 180))
    img = Image.alpha_composite(bg.convert("RGBA"), ov)

    # Guitar string lines — the channel's visual signature
    AMBER    = primary
    ELECTRIC = (0, 229, 255)
    WHITE    = (255, 255, 255)
    SMOKE    = (155, 155, 155)
    DARK     = (18, 16, 8)

    img = draw_strings(img, y_center=175,  opacity=55, color=AMBER)
    img = draw_strings(img, y_center=1085, opacity=50, color=AMBER)
    img = draw_strings(img, y_center=1110, opacity=25, color=WHITE)
    img = img.convert("RGB")
    draw = ImageDraw.Draw(img)

    f_huge    = get_display_font(320)
    f_sub     = get_display_font(88)
    f_eyebrow = get_body_font(36, bold=True)
    f_badge   = get_body_font(74, bold=True)
    f_teaser  = get_body_font(46)
    f_footer  = get_body_font(30)

    # Channel eyebrow
    draw_outlined_text(draw, (W//2, 120), "GUITAR  WITH  FACTS",
                       font=f_eyebrow, fill=SMOKE, outline=(0, 0, 0),
                       outline_width=2, anchor="mm")

    # Hero number — the dominant visual element
    draw_outlined_text(draw, (W//2, 620), "5",
                       font=f_huge, fill=AMBER, outline=(0, 0, 0),
                       outline_width=8, anchor="mm")

    # "WILD FACTS" subtitle
    draw_outlined_text(draw, (W//2, 825), "WILD  FACTS",
                       font=f_sub, fill=WHITE, outline=(0, 0, 0),
                       outline_width=4, anchor="mm")

    # Topic pill — clean, no border clutter
    py, ph = 920, 130
    draw.rounded_rectangle([(55, py), (W - 55, py + ph)], radius=65, fill=AMBER)
    topic_disp = fruit_name.upper()
    if len(topic_disp) > 18:
        topic_disp = topic_disp[:17] + "…"
    draw.text((W // 2, py + ph // 2), topic_disp,
              font=f_badge, fill=DARK, anchor="mm")

    # Teaser in electric cyan
    draw_outlined_text(draw, (W//2, 1290), "#3  WILL  SURPRISE  YOU",
                       font=f_teaser, fill=ELECTRIC, outline=(0, 0, 0),
                       outline_width=3, anchor="mm")
    draw.rounded_rectangle([(W//2 - 105, 1370), (W//2 + 105, 1380)],
                           radius=4, fill=ELECTRIC)

    # Footer
    draw.text((W//2, 1855), "#Shorts  •  #GuitarFacts",
              font=f_footer, fill=SMOKE, anchor="mm")

    img.save(output_path, "PNG", quality=95)
    print(f"Vertical thumbnail saved: {output_path}")


def create_horizontal_thumbnail(fruit_name, emoji, primary, accent, secondary,
                                bg_image_path, output_path):
    W, H = 1280, 720
    AMBER    = primary
    ELECTRIC = (0, 229, 255)
    WHITE    = (255, 255, 255)
    SMOKE    = (155, 155, 155)
    DARK     = (18, 16, 8)

    try:
        bg = Image.open(bg_image_path).convert("RGB").resize((W, H), Image.LANCZOS)
    except Exception:
        bg = Image.new("RGB", (W, H), DARK)

    ov = Image.new("RGBA", (W, H), (0, 0, 0, 140))
    img = Image.alpha_composite(bg.convert("RGBA"), ov)
    img = draw_strings(img, y_center=340, n=6, opacity=45, color=AMBER)
    img = draw_strings(img, y_center=385, n=6, opacity=25, color=WHITE)
    img = img.convert("RGB")
    draw = ImageDraw.Draw(img)

    f_giant  = get_display_font(260)
    f_xl     = get_display_font(88)
    f_medium = get_body_font(48, bold=True)
    f_small  = get_body_font(30)

    # Left: huge "5" hero
    draw_outlined_text(draw, (270, 330), "5",
                       font=f_giant, fill=AMBER, outline=(0, 0, 0),
                       outline_width=7, anchor="mm")
    draw_outlined_text(draw, (270, 510), "FACTS",
                       font=f_xl, fill=WHITE, outline=(0, 0, 0),
                       outline_width=4, anchor="mm")

    # Amber divider line
    draw.line([(510, 50), (510, 670)], fill=AMBER, width=2)

    # Right: channel eyebrow + topic name + subtitle
    draw_outlined_text(draw, (660, 110), "GUITAR WITH FACTS",
                       font=f_medium, fill=SMOKE, outline=(0, 0, 0),
                       outline_width=2, anchor="lm")

    topic_disp = fruit_name.upper()
    topic_size = max(65, int(95 * min(1.0, 10 / max(len(topic_disp), 1))))
    draw_outlined_text(draw, (660, 290), topic_disp,
                       font=get_display_font(topic_size), fill=AMBER,
                       outline=(0, 0, 0), outline_width=5, anchor="lm")

    draw_outlined_text(draw, (660, 440), "5  WILD  FACTS",
                       font=f_xl, fill=WHITE, outline=(0, 0, 0),
                       outline_width=4, anchor="lm")

    # Electric underline accent
    draw.line([(660, 500), (900, 502)], fill=ELECTRIC, width=3)

    draw.text((640, 670), "#Shorts  •  #GuitarFacts",
              font=f_small, fill=SMOKE, anchor="mm")

    img.save(output_path, "JPEG", quality=95)
    print(f"Horizontal thumbnail saved: {output_path}")


# ── Main ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    data       = load_video_data()
    topic      = data["topic"]
    emoji      = data.get("emoji", "🎸")
    colors     = data.get("colors", {})

    # design.md: primary #FFC107, active #E0A800, light #FFF3CD
    primary   = hex_to_rgb(colors.get("primary",   "#FFC107"))
    accent    = hex_to_rgb(colors.get("accent",    "#FFF3CD"))
    secondary = hex_to_rgb(colors.get("secondary", "#E0A800"))

    access_key = os.environ.get("UNSPLASH_ACCESS_KEY", "")

    os.makedirs("output/images", exist_ok=True)

    # Search queries for 5 different angles of the guitar topic
    search_queries = [
        f"{topic} guitar white background",
        f"{topic} guitar close up photography",
        f"guitarist playing {topic} stage",
        f"{topic} guitar fretboard macro",
        f"acoustic electric guitar {topic}",
    ]

    image_paths  = []
    attributions = []

    print(f"=== Generating images for: {topic} ===")

    if access_key:
        print(f"Using Unsplash API (professional photos)")
    else:
        print(f"UNSPLASH_ACCESS_KEY not set — using Pollinations fallback")
        print(f"Add UNSPLASH_ACCESS_KEY to GitHub Secrets for better images!")

    for i, query in enumerate(search_queries):
        out = f"output/images/scene_{i+1}.png"
        print(f"\nImage {i+1}/5:")
        success = False

        # Try Unsplash first
        if access_key:
            result = get_unsplash_image(query, out, access_key, index=i)
            if result:
                attributions.append(result)
                success = True
            else:
                print(f"  Unsplash failed, trying Pollinations...")

        # Fallback to Pollinations
        if not success:
            success = get_pollinations_image(query, out, i)

        # Final fallback
        if not success or not os.path.exists(out) or os.path.getsize(out) < 5000:
            create_fallback_image(out, i)

        image_paths.append(out)
        time.sleep(1)   # Respect rate limits

    # Save attribution info for description
    if attributions:
        with open("output/image_credits.json", "w") as f:
            json.dump(attributions, f, indent=2)
        print(f"\nSaved {len(attributions)} photo attributions")

    # Create thumbnails
    print("\nCreating thumbnails...")
    create_vertical_thumbnail(topic, emoji, primary, accent, secondary,
                              image_paths[0], "output/thumbnail_vertical.png")
    create_horizontal_thumbnail(topic, emoji, primary, accent, secondary,
                                image_paths[0], "output/thumbnail.jpg")

    print(f"\nDone! {len(image_paths)} images ready")
    for p in image_paths:
        size = os.path.getsize(p) // 1024 if os.path.exists(p) else 0
        print(f"  {p} ({size}KB)")
