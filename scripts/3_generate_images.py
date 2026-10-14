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
import math
import os
import time
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
from PIL import Image, ImageDraw, ImageEnhance, ImageFont
import io
import urllib.parse


# ── Canva "Fun Fact" reference palette ────────────────────────────────────────
PEACH      = (255, 224, 199)
PEACH_BLOB = (255, 213, 177)
MINT       = (162, 229, 211)
MINT_BLOB  = (145, 208, 192)
ACCENT     = (207, 64, 26)
CHARCOAL   = (60, 60, 80)
WHITE      = (255, 255, 255)


# ── Font utilities (Montserrat display + Inter body, vendored in assets/fonts) ──
FONTS_DIR = "assets/fonts"


def get_display_font(size):
    """Montserrat Black — bold sans-serif display font."""
    p = os.path.join(FONTS_DIR, "Montserrat-Black.ttf")
    if os.path.exists(p):
        return ImageFont.truetype(p, size)
    fb = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
    return ImageFont.truetype(fb, size) if os.path.exists(fb) else ImageFont.load_default()


def get_body_font(size, bold=False):
    """Inter Regular/Medium — clean sans-serif body font."""
    p = os.path.join(FONTS_DIR, "Inter_18pt-Medium.ttf" if bold else "Inter_18pt-Regular.ttf")
    if os.path.exists(p):
        return ImageFont.truetype(p, size)
    fb = f"/usr/share/fonts/truetype/dejavu/DejaVuSans{'-Bold' if bold else ''}.ttf"
    return ImageFont.truetype(fb, size) if os.path.exists(fb) else ImageFont.load_default()


# ── Canva-style drawing helpers ───────────────────────────────────────────────
def blob_canvas(w, h, bg=PEACH, blob=PEACH_BLOB):
    """Solid background with soft organic corner blobs, per the Canva reference."""
    img = Image.new("RGB", (w, h), bg)
    d = ImageDraw.Draw(img)
    for fx0, fy0, fx1, fy1 in [(-0.35, -0.14, 0.39, 0.17), (0.67, -0.10, 1.31, 0.17),
                               (-0.28, 0.74, 0.33, 1.10), (0.74, 0.77, 1.37, 1.08)]:
        d.ellipse([fx0 * w, fy0 * h, fx1 * w, fy1 * h], fill=blob)
    return img


def draw_bubble(draw, x0, y0, x1, y1, radius=200):
    """Big white speech bubble with tail, per the Canva reference."""
    draw.rounded_rectangle([(x0, y0), (x1, y1)], radius=radius, fill=WHITE)
    tx = x1 - 320
    draw.polygon([(tx, y1 - 6), (tx + 150, y1 - 6), (tx + 125, y1 + 100)], fill=WHITE)


def draw_bulb(draw, cx, cy, r=75, color=ACCENT):
    """Hand-drawn lightbulb doodle, per the Canva reference."""
    draw.ellipse([(cx - r, cy - r), (cx + r, cy + r)], outline=color, width=9)
    draw.line([(cx - 34, cy + 22), (cx - 17, cy - 12), (cx, cy + 22),
               (cx + 17, cy - 12), (cx + 34, cy + 22)],
              fill=color, width=7, joint="curve")
    draw.rounded_rectangle([(cx - 30, cy + r + 10), (cx + 30, cy + r + 50)],
                           radius=12, fill=color)
    for ang in range(-170, -9, 20):   # rays over the top half
        a = math.radians(ang)
        draw.line([(cx + (r + 20) * math.cos(a), cy + (r + 20) * math.sin(a)),
                   (cx + (r + 48) * math.cos(a), cy + (r + 48) * math.sin(a))],
                  fill=color, width=8)


def warm_grade(img):
    """Warm, slightly darkened grade so every photo matches the Canva mood."""
    r, g, b = img.split()
    r = r.point(lambda v: min(255, int(v * 1.07)))
    b = b.point(lambda v: int(v * 0.90))
    return ImageEnhance.Brightness(Image.merge("RGB", (r, g, b))).enhance(0.93)


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
def get_unsplash_image(query, output_path, access_key, fallback_query=None, orientation="portrait", index=0, tag=""):
    """
    Search Unsplash for high quality guitar photos.
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

    print(f"{tag}  Searching Unsplash: '{query}'...")
    r = requests.get(search_url, headers=headers, params=params, timeout=15)
    print(f"{tag}  Search status: {r.status_code}")

    if r.status_code == 401:
        print(f"{tag}  Invalid UNSPLASH_ACCESS_KEY — check GitHub Secret!")
        return False
    if r.status_code == 403:
        print(f"{tag}  Rate limit reached (50/hour) — using fallback")
        return False
    if r.status_code != 200:
        print(f"{tag}  Search error: {r.text[:200]}")
        return False

    results = r.json().get("results", [])
    if not results and fallback_query and fallback_query != query:
        print(f"{tag}  No results for '{query}' — trying broader search: '{fallback_query}'...")
        params["query"] = fallback_query
        try:
            r_fallback = requests.get(search_url, headers=headers, params=params, timeout=15)
            if r_fallback.status_code == 200:
                results = r_fallback.json().get("results", [])
        except Exception as e:
            print(f"{tag}  Broader search failed: {e}")

    if not results:
        print(f"{tag}  No photos found for '{query}' or fallback")
        return False

    # Pick different image for each scene (cycle through results)
    photo = results[index % len(results)]
    photo_id   = photo["id"]
    photo_url  = photo["urls"]["regular"]  # 1080px wide
    photo_user = photo["user"]["name"]

    print(f"{tag}  Found: {photo_id} by {photo_user}")

    # Download the actual image
    # 1.2x oversize so step 4's zoom/pan has real pixels to crop into
    download_url = f"{photo_url}&w=1296&h=2304&fit=crop&crop=entropy"

    img_resp = requests.get(download_url, timeout=30)
    if img_resp.status_code != 200 or len(img_resp.content) < 5000:
        print(f"{tag}  Download failed: {img_resp.status_code}")
        return False

    img = Image.open(io.BytesIO(img_resp.content)).convert("RGB")
    img = warm_grade(img.resize((1296, 2304), Image.LANCZOS))
    img.save(output_path, "PNG")

    print(f"{tag}  Saved: {output_path} ({os.path.getsize(output_path)//1024}KB) — Photo by {photo_user}")

    # Return attribution info
    return {
        "photographer": photo_user,
        "photo_id":     photo_id,
        "unsplash_url": photo["links"]["html"]
    }


# ── Fallback: Pollinations AI image ──────────────────────────────────────────
def get_pollinations_image(prompt, output_path, index, tag=""):
    """Fallback if Unsplash fails"""
    import urllib.parse
    enhanced = (f"{prompt}, warm golden hour light, soft cozy mood, "
                f"cinematic, professional photography, 4k")
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
                img.save(output_path, "PNG")
                print(f"{tag}  Pollinations fallback saved: {output_path}")
                return True
        except Exception as e:
            print(f"{tag}  Pollinations error: {e}")
            time.sleep(10)
    return False


# ── Create on-palette blob-card fallback ──────────────────────────────────────
def create_fallback_image(output_path, index, width=1080, height=1920, tag=""):
    """Peach/mint blob card, per the Canva reference, so worst case stays on brand."""
    palettes = [(PEACH, PEACH_BLOB), (MINT, MINT_BLOB)]
    bg, blob = palettes[index % len(palettes)]
    blob_canvas(width, height, bg, blob).save(output_path, "PNG")
    print(f"{tag}  Blob-card fallback saved: {output_path}")
    return True


# ── Thumbnails (Canva "Fun Fact" bubble card style) ───────────────────────────
def create_vertical_thumbnail(topic_name, emoji, primary, accent, secondary,
                              bg_image_path, output_path):
    """Peach speech-bubble card with lightbulb doodle, per the Canva reference."""
    W, H = 1080, 1920
    img = blob_canvas(W, H)
    draw = ImageDraw.Draw(img)

    draw_bubble(draw, 70, 380, W - 70, 1520)
    draw_bulb(draw, W // 2, 570)
    draw.text((W // 2, 800), "5 FUN FACTS",
              font=get_display_font(125), fill=ACCENT, anchor="mm")

    # Topic pill
    topic_disp = topic_name.upper()
    if len(topic_disp) > 18:
        topic_disp = topic_disp[:17] + "…"
    py, ph = 930, 150
    draw.rounded_rectangle([(150, py), (W - 150, py + ph)], radius=75, fill=ACCENT)
    draw.text((W // 2, py + ph // 2), topic_disp,
              font=get_display_font(76), fill=WHITE, anchor="mm")

    draw.text((W // 2, 1240), "#3 will surprise you",
              font=get_body_font(48), fill=ACCENT, anchor="mm")
    draw.text((W // 2, 1340), "Watch till the end!",
              font=get_body_font(40), fill=CHARCOAL, anchor="mm")

    draw.text((W // 2, H - 60), "Guitar with Facts",
              font=get_body_font(36), fill=ACCENT, anchor="mm")

    img.save(output_path, "PNG")
    print(f"Vertical thumbnail saved: {output_path}")


def create_horizontal_thumbnail(topic_name, emoji, primary, accent, secondary,
                                bg_image_path, output_path):
    """Peach card, landscape layout, per the Canva reference."""
    W, H = 1280, 720
    img = blob_canvas(W, H)
    draw = ImageDraw.Draw(img)

    draw.rounded_rectangle([(60, 60), (W - 60, H - 60)], radius=90, fill=WHITE)

    # Left: lightbulb + fact count
    draw_bulb(draw, 250, 290, r=65)
    draw.text((250, 500), "5 FACTS", font=get_display_font(80), fill=ACCENT, anchor="mm")

    draw.line([(480, 130), (480, H - 130)], fill=PEACH_BLOB, width=4)

    # Right: channel + topic + teaser
    draw.text((540, 190), "GUITAR WITH FACTS",
              font=get_body_font(38), fill=CHARCOAL, anchor="lm")
    topic_disp = topic_name.upper()
    topic_size = max(60, int(95 * min(1.0, 12 / max(len(topic_disp), 1))))
    draw.text((540, 320), topic_disp,
              font=get_display_font(topic_size), fill=ACCENT, anchor="lm")
    draw.text((540, 460), "5 fun facts inside!",
              font=get_body_font(44), fill=CHARCOAL, anchor="lm")

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

    # Specific topic queries paired with reliable guitar photography fallbacks
    search_queries = [
        (f"{topic} guitar", "acoustic guitar close up"),
        (f"guitar fretboard {topic}", "guitar fretboard hand position"),
        (f"acoustic guitar {topic}", "acoustic guitar warm lighting"),
        (f"electric guitar {topic}", "electric guitar neck close up"),
        (f"guitarist playing {topic}", "guitarist playing on stage"),
    ]

    print(f"=== Generating images for: {topic} ===")

    if access_key:
        print(f"Using Unsplash API (professional photos)")
    else:
        print(f"UNSPLASH_ACCESS_KEY not set — using Pollinations fallback")
        print(f"Add UNSPLASH_ACCESS_KEY to GitHub Secrets for better images!")

    def fetch_one(i, query_pair):
        query, fallback_q = query_pair
        tag = f"[img {i+1}]"
        out = f"output/images/scene_{i+1}.png"
        success = False
        attribution = None

        # Try Unsplash first
        if access_key:
            result = get_unsplash_image(query, out, access_key, fallback_query=fallback_q, index=i, tag=tag)
            if result:
                attribution = result
                success = True
            else:
                print(f"{tag}  Unsplash failed, trying Pollinations...")

        # Fallback to Pollinations
        if not success:
            success = get_pollinations_image(query, out, i, tag=tag)

        # Final fallback
        if not success or not os.path.exists(out) or os.path.getsize(out) < 5000:
            create_fallback_image(out, i, tag=tag)

        return i, out, attribution

    # 5 independent fetches — nowhere near Unsplash's 50 req/hour limit in parallel
    results = {}
    with ThreadPoolExecutor(max_workers=len(search_queries)) as executor:
        futures = [executor.submit(fetch_one, i, q) for i, q in enumerate(search_queries)]
        for future in as_completed(futures):
            i, out, attribution = future.result()
            results[i] = (out, attribution)

    image_paths  = [results[i][0] for i in range(len(search_queries))]
    attributions = [results[i][1] for i in range(len(search_queries)) if results[i][1]]

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
