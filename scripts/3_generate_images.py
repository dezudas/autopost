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


def find_font(size, bold=False):
    candidates = []
    if bold:
        candidates = [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        ]
    else:
        candidates = [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        ]
    for path in candidates:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except:
                continue
    return ImageFont.load_default()


def load_video_data():
    with open("output/video_data.json", "r") as f:
        return json.load(f)


def hex_to_rgb(hex_str, default=(255, 107, 53)):
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
    except:
        bg = Image.new("RGB", (W, H), primary)

    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 90))
    img = Image.alpha_composite(bg.convert("RGBA"), overlay).convert("RGB")
    draw = ImageDraw.Draw(img)

    font_huge   = find_font(220, bold=True)
    font_xl     = find_font(95,  bold=True)
    font_large  = find_font(75,  bold=True)
    font_medium = find_font(55,  bold=True)
    font_small  = find_font(40,  bold=True)

    # Top banner
    banner_top, banner_bot = 80, 250
    draw.rounded_rectangle([(40, banner_top), (W-40, banner_bot)],
                           radius=30, fill=primary, outline=accent, width=4)
    draw_outlined_text(draw, (W//2, banner_top+60), "GUITAR WITH FACTS",
                       font=font_medium, fill=(255,255,255), outline_width=3)
    draw_outlined_text(draw, (W//2, banner_top+130), "Educational Shorts",
                       font=font_small, fill=(255,230,180), outline_width=2)

    # Circle badge
    badge_y, cr = 540, 175
    draw.ellipse([(W//2-cr, badge_y-cr), (W//2+cr, badge_y+cr)],
                 fill=accent, outline=(0,0,0), width=7)
    draw_outlined_text(draw, (W//2, badge_y-25), "5",
                       font=font_huge, fill=(20,20,20),
                       outline=(255,255,255), outline_width=4)
    draw_outlined_text(draw, (W//2, badge_y+110), "FACTS",
                       font=find_font(55, bold=True), fill=(20,20,20),
                       outline=(255,255,255), outline_width=3)

    # Fruit name bar
    bar_y, bar_h = 1060, 210
    draw.rounded_rectangle([(40, bar_y), (W-40, bar_y+bar_h)],
                           radius=40, fill=primary, outline=accent, width=10)
    draw_outlined_text(draw, (W//2, bar_y+60), "ABOUT",
                       font=font_medium, fill=(255,255,255), outline_width=3)
    draw_outlined_text(draw, (W//2, bar_y+148), fruit_name.upper(),
                       font=font_xl, fill=accent, outline=(0,0,0), outline_width=4)

    # Attention banner
    bnr_y = 1360
    draw.rounded_rectangle([(60, bnr_y), (W-60, bnr_y+130)], radius=30, fill=accent)
    draw_outlined_text(draw, (W//2, bnr_y+65), "FACT #3 IS WILD!",
                       font=font_large, fill=secondary, outline=(0,0,0), outline_width=3)

    # CTA
    draw_outlined_text(draw, (W//2, 1600), "WATCH NOW",
                       font=font_large, fill=accent, outline=(0,0,0), outline_width=4)

    # Footer
    draw.rectangle([(0, 1810), (W, H)], fill=primary)
    draw_outlined_text(draw, (W//2, 1865), "#Shorts #GuitarFacts",
                       font=font_small, fill=(255,255,255), outline_width=2)

    img.save(output_path, "PNG", quality=95)
    print(f"Vertical thumbnail saved: {output_path}")


def create_horizontal_thumbnail(fruit_name, emoji, primary, accent, secondary,
                                bg_image_path, output_path):
    W, H = 1280, 720
    try:
        bg = Image.open(bg_image_path).convert("RGB").resize((W, H), Image.LANCZOS)
    except:
        bg = Image.new("RGB", (W, H), primary)

    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 100))
    img = Image.alpha_composite(bg.convert("RGBA"), overlay).convert("RGB")
    draw = ImageDraw.Draw(img)

    font_huge   = find_font(180, bold=True)
    font_xl     = find_font(90,  bold=True)
    font_medium = find_font(50,  bold=True)

    draw.rectangle([(0, 0), (W, 70)], fill=primary)
    draw_outlined_text(draw, (W//2, 35), "GUITAR WITH FACTS",
                       font=font_medium, fill=(255,255,255), outline_width=2)

    draw.ellipse([(120, 200), (480, 560)], fill=accent, outline=(0,0,0), width=6)
    draw_outlined_text(draw, (300, 350), "5",
                       font=font_huge, fill=(20,20,20),
                       outline=(255,255,255), outline_width=3)
    draw_outlined_text(draw, (300, 490), "FACTS",
                       font=find_font(60, bold=True), fill=(20,20,20),
                       outline=(255,255,255), outline_width=2)

    draw_outlined_text(draw, (620, 220), "ABOUT",
                       font=font_xl, fill=(255,255,255), outline_width=4, anchor="lm")
    draw_outlined_text(draw, (620, 340), fruit_name.upper(),
                       font=font_huge, fill=accent, outline=(0,0,0),
                       outline_width=4, anchor="lm")
    draw_outlined_text(draw, (620, 490), "YOU MUST KNOW!",
                       font=find_font(55, bold=True), fill=(255,255,255),
                       outline_width=3, anchor="lm")

    draw.rectangle([(0, 660), (W, H)], fill=primary)
    draw_outlined_text(draw, (W//2, 690), "#Shorts #GuitarFacts",
                       font=font_medium, fill=(255,255,255), outline_width=2)

    img.save(output_path, "JPEG", quality=95)
    print(f"Horizontal thumbnail saved: {output_path}")


# ── Main ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    data       = load_video_data()
    topic      = data["topic"]
    emoji      = data.get("emoji", "🎸")
    colors     = data.get("colors", {})

    primary   = hex_to_rgb(colors.get("primary",   "#FF6B35"))
    accent    = hex_to_rgb(colors.get("accent",    "#FFE66D"))
    secondary = hex_to_rgb(colors.get("secondary", "#C44A1F"))

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
