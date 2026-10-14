"""
Step 3: Generate clean, modern thumbnail assets locally
- No external image APIs (Unsplash/Pollinations removed)
- 100% reliable, runs instantly in 0.2s
- Generates high-contrast, modern dark-themed thumbnail cards
"""

import json
import os
from PIL import Image, ImageDraw, ImageFont

FONTS_DIR = "assets/fonts"
W_VERT, H_VERT = 1080, 1920
W_HORIZ, H_HORIZ = 1280, 720

# Luxury modern dark palette
BG_DARK = (11, 15, 25)          # Deep obsidian slate
BG_CARD = (21, 29, 42)          # Surface charcoal
BORDER_COLOR = (40, 53, 72)     # Hairline border
GOLD = (245, 158, 11)           # Accent amber/gold
WHITE = (248, 250, 252)         # Crisp primary text
MUTED = (148, 163, 184)         # Secondary text
CYAN = (6, 182, 212)            # Highlight cyan


def get_display_font(size):
    p = os.path.join(FONTS_DIR, "Montserrat-Black.ttf")
    if os.path.exists(p):
        return ImageFont.truetype(p, size)
    fb = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
    return ImageFont.truetype(fb, size) if os.path.exists(fb) else ImageFont.load_default()


def get_body_font(size, bold=False):
    f_name = "Inter_18pt-Medium.ttf" if bold else "Inter_18pt-Regular.ttf"
    p = os.path.join(FONTS_DIR, f_name)
    if os.path.exists(p):
        return ImageFont.truetype(p, size)
    fb = f"/usr/share/fonts/truetype/dejavu/DejaVuSans{'-Bold' if bold else ''}.ttf"
    return ImageFont.truetype(fb, size) if os.path.exists(fb) else ImageFont.load_default()


def load_video_data():
    with open("output/video_data.json", "r") as f:
        return json.load(f)


def draw_modern_canvas(w, h):
    """Deep slate background with subtle luxury frame."""
    img = Image.new("RGB", (w, h), BG_DARK)
    draw = ImageDraw.Draw(img)

    # Hairline frame inset by 36px
    pad = 36
    draw.rounded_rectangle(
        [(pad, pad), (w - pad, h - pad)],
        radius=28,
        outline=BORDER_COLOR,
        width=2
    )
    return img, draw


def create_vertical_thumbnail(data, output_path):
    """9:16 Vertical thumbnail for Shorts / TikTok."""
    img, draw = draw_modern_canvas(W_VERT, H_VERT)
    topic = data.get("topic", "Guitar Lesson").upper()
    specs = data.get("specs", {})
    notes = specs.get("notes", "A • C • E")
    tab = specs.get("tab", "X 0 2 2 1 0")

    # Brand badge at top
    f_brand = get_body_font(34, bold=True)
    draw.text((W_VERT // 2, 240), "GUITAR WITH FACTS", font=f_brand, fill=MUTED, anchor="mm")

    # Main Center Card
    card_x0, card_y0 = 80, 480
    card_x1, card_y1 = W_VERT - 80, 1440
    draw.rounded_rectangle([(card_x0, card_y0), (card_x1, card_y1)], radius=36, fill=BG_CARD, outline=BORDER_COLOR, width=2)

    # Accent pill
    pill_w, pill_h = 380, 68
    px0 = (W_VERT - pill_w) // 2
    draw.rounded_rectangle([(px0, card_y0 + 70), (px0 + pill_w, card_y0 + 70 + pill_h)], radius=34, fill=GOLD)
    draw.text((W_VERT // 2, card_y0 + 70 + pill_h // 2), "60-SECOND LESSON", font=get_body_font(30, bold=True), fill=(0, 0, 0), anchor="mm")

    # Title
    f_title = get_display_font(84)
    words = topic.split()
    if len(words) > 3:
        ln1 = " ".join(words[:2])
        ln2 = " ".join(words[2:])
        draw.text((W_VERT // 2, card_y0 + 260), ln1, font=f_title, fill=WHITE, anchor="mm")
        draw.text((W_VERT // 2, card_y0 + 360), ln2, font=f_title, fill=WHITE, anchor="mm")
    else:
        draw.text((W_VERT // 2, card_y0 + 300), topic, font=f_title, fill=WHITE, anchor="mm")

    # Spec Callout Box inside card
    box_y0 = card_y0 + 490
    box_y1 = box_y0 + 240
    draw.rounded_rectangle([(card_x0 + 50, box_y0), (card_x1 - 50, box_y1)], radius=24, fill=(15, 21, 32), outline=(35, 48, 68), width=2)

    draw.text((W_VERT // 2, box_y0 + 60), f"NOTES:  {notes}", font=get_body_font(38, bold=True), fill=GOLD, anchor="mm")
    draw.text((W_VERT // 2, box_y0 + 130), f"TAB:  {tab}", font=get_body_font(38, bold=True), fill=WHITE, anchor="mm")
    draw.text((W_VERT // 2, box_y0 + 190), specs.get("formula", "Root • Flat 3rd • 5th"), font=get_body_font(28), fill=MUTED, anchor="mm")

    # Call to action footer
    draw.text((W_VERT // 2, H_VERT - 260), "WATCH NOW • TAP FOR LESSON", font=get_body_font(32, bold=True), fill=CYAN, anchor="mm")

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    img.save(output_path, "PNG")
    print(f"Saved modern vertical thumbnail: {output_path}")


def create_horizontal_thumbnail(data, output_path):
    """16:9 Landscape thumbnail for YouTube metadata."""
    img, draw = draw_modern_canvas(W_HORIZ, H_HORIZ)
    topic = data.get("topic", "Guitar Lesson").upper()
    specs = data.get("specs", {})

    # Left accent bar
    draw.rounded_rectangle([(60, 60), (74, H_HORIZ - 60)], radius=7, fill=GOLD)

    # Title & Badge
    draw.text((110, 110), "GUITAR WITH FACTS • 60S BREAKDOWN", font=get_body_font(26, bold=True), fill=GOLD)
    draw.text((110, 240), topic, font=get_display_font(72), fill=WHITE)

    # Specs
    notes = specs.get("notes", "A • C • E")
    tab = specs.get("tab", "X 0 2 2 1 0")
    draw.text((110, 360), f"NOTES: {notes}   |   TAB: {tab}", font=get_body_font(34, bold=True), fill=MUTED)

    # Bottom pill
    draw.text((110, 560), "5 ESSENTIAL FACTS YOU NEED TO KNOW", font=get_body_font(28, bold=True), fill=CYAN)

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    img.convert("RGB").save(output_path, "JPEG", quality=92)
    print(f"Saved modern horizontal thumbnail: {output_path}")


if __name__ == "__main__":
    os.makedirs("output", exist_ok=True)
    data = load_video_data()
    create_vertical_thumbnail(data, "output/thumbnail_vertical.png")
    create_horizontal_thumbnail(data, "output/thumbnail.jpg")
    print("Modern thumbnail assets ready!")
