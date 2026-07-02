"""
Step 4: Assemble Shorts video with FAST animations
Uses scale animations instead of slow zoompan filter
~3x faster than zoompan, same cinematic feel
"""

import json
import os
import subprocess
import requests
from PIL import Image, ImageDraw, ImageFont


W, H = 1080, 1920
FPS = 24


# ── Font utilities (Bebas Neue display + Poppins body) ────────────────────────
_BEBAS_PATH = None


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
            return path
    except Exception:
        pass
    return None


def get_display_font(size):
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
    """Overlay n horizontal guitar-string lines centered at y_center."""
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    for i in range(n):
        y = int(y_center + (i - n / 2 + 0.5) * spacing)
        d.line([(0, y), (W, y)], fill=(*color, opacity), width=1)
    return Image.alpha_composite(base_rgba, ov)


def _outlined(draw, pos, text, font, fill, outline=(0, 0, 0), w=4):
    x, y = pos
    for dx in range(-w, w + 1):
        for dy in range(-w, w + 1):
            if dx * dx + dy * dy <= w * w:
                draw.text((x + dx, y + dy), text, font=font, fill=outline, anchor="mm")
    draw.text((x, y), text, font=font, fill=fill, anchor="mm")


def load_video_data():
    with open("output/video_data.json", "r") as f:
        return json.load(f)


def get_duration(path):
    r = subprocess.run([
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1", path
    ], capture_output=True, text=True)
    try:
        return float(r.stdout.strip())
    except:
        return 4.0


def to_srt(s):
    s = max(0.0, s)
    h, rem = divmod(s, 3600)
    m, sec = divmod(rem, 60)
    ms = int((sec % 1) * 1000)
    return f"{int(h):02d}:{int(m):02d}:{int(sec):02d},{ms:03d}"


def get_background_music(duration):
    """
    Get soft royalty-free background music.
    Strategy: Try multiple sources, fall back to a synthesized soft pad.
    """
    out = "output/audio/background_music.mp3"
    trimmed = "output/audio/background_trimmed.mp3"
    os.makedirs("output/audio", exist_ok=True)

    # Reliable royalty-free music sources
    # These are CC0 (public domain) or royalty-free
    music_urls = [
        # Pixabay tracks (free for commercial use)
        "https://cdn.pixabay.com/audio/2023/06/14/audio_a3c61dca31.mp3",
        "https://cdn.pixabay.com/audio/2024/02/12/audio_ad2b71e6c4.mp3",
        "https://cdn.pixabay.com/audio/2022/05/27/audio_1808fbf07a.mp3",
    ]

    for url in music_urls:
        try:
            print(f"Trying music: {url[-40:]}")
            r = requests.get(url, timeout=20, headers={
                "User-Agent": "Mozilla/5.0"
            })
            if r.status_code == 200 and len(r.content) > 50000:
                with open(out, "wb") as f:
                    f.write(r.content)

                # Loop music if shorter than video duration, then trim to fit
                fade_start = max(0, duration - 3)
                result = subprocess.run([
                    "ffmpeg", "-y",
                    "-stream_loop", "-1",        # loop infinitely
                    "-i", out,
                    "-t", str(duration + 1),     # then trim to needed length
                    "-af",
                    f"volume=0.10,"
                    f"highpass=f=200,"
                    f"lowpass=f=8000,"
                    f"afade=t=in:d=2,"
                    f"afade=t=out:st={fade_start}:d=3",
                    "-codec:a", "libmp3lame", "-qscale:a", "4",
                    trimmed
                ], capture_output=True, timeout=120)

                if result.returncode == 0 and os.path.exists(trimmed) \
                   and os.path.getsize(trimmed) > 5000:
                    print(f"Music ready (downloaded): {trimmed}")
                    return trimmed
        except Exception as e:
            print(f"  Failed: {e}")
            continue

    # Generate soft ambient pad music (guaranteed to work)
    print("Using synthesized soft ambient music...")
    return generate_soft_ambient(duration, trimmed)


def generate_soft_ambient(duration, output_path):
    """
    Generate soft ambient pad music using FFmpeg synthesis.
    Sounds like gentle background music, not beeping tones.
    """
    fade_start = max(0, duration - 3)

    # Layered sine waves at musical intervals (C, E, G - C major chord)
    # With slow LFO modulation for organic feel
    cmd = [
        "ffmpeg", "-y",
        # Three pad layers at musical frequencies
        "-f", "lavfi", "-i", "sine=frequency=261.63:sample_rate=44100",  # C4
        "-f", "lavfi", "-i", "sine=frequency=329.63:sample_rate=44100",  # E4
        "-f", "lavfi", "-i", "sine=frequency=392.00:sample_rate=44100",  # G4
        "-f", "lavfi", "-i", "sine=frequency=130.81:sample_rate=44100",  # C3 (bass)
        "-filter_complex",
        # Mix all 4 layers, apply tremolo for organic sound
        f"[0][1][2][3]amix=inputs=4:duration=longest[mix];"
        f"[mix]tremolo=f=0.5:d=0.3,"           # gentle tremolo
        f"volume=0.06,"                         # very subtle
        f"highpass=f=150,"                      # cleaner sound
        f"lowpass=f=4000,"                      # warmer pad-like tone
        f"afade=t=in:d=3,"
        f"afade=t=out:st={fade_start}:d=3"
        f"[out]",
        "-map", "[out]",
        "-t", str(duration + 1),
        "-codec:a", "libmp3lame", output_path
    ]

    subprocess.run(cmd, capture_output=True, timeout=60)
    print(f"Soft ambient music generated: {output_path}")
    return output_path


# ── Pre-render animation frames as a video clip (FAST — no zoompan) ──────────
def create_animated_clip(card_image_path, duration, output_path, anim_type="zoom_in"):
    """
    Create animated video clip from a still image using simple scale+crop.
    This is 3-5x FASTER than zoompan filter!
    """
    total_frames = int(duration * FPS)

    # Pre-resize the image to a larger size for cropping
    img = Image.open(card_image_path)

    if anim_type == "zoom_in":
        # Slowly zoom from 100% to 110% (cropping inward)
        crop_filter = (
            f"scale={W}:-1,"
            f"crop=w='iw*(1-0.0008*n)':h='ih*(1-0.0008*n)':"
            f"x='(iw-iw*(1-0.0008*n))/2':y='(ih-ih*(1-0.0008*n))/2',"
            f"scale={W}:{H}"
        )
    elif anim_type == "zoom_out":
        # Reverse zoom: 110% to 100%
        crop_filter = (
            f"scale={int(W*1.12)}:-1,"
            f"crop=w='iw*(0.89+0.0008*n)':h='ih*(0.89+0.0008*n)':"
            f"x='(iw-iw*(0.89+0.0008*n))/2':y='(ih-ih*(0.89+0.0008*n))/2',"
            f"scale={W}:{H}"
        )
    elif anim_type == "pan_right":
        # Pan from left to right, slight zoom
        crop_filter = (
            f"scale={int(W*1.15)}:-1,"
            f"crop=w='iw*0.87':h='ih*0.87':"
            f"x='(iw-iw*0.87)*(n/{total_frames})':y='(ih-ih*0.87)/2',"
            f"scale={W}:{H}"
        )
    elif anim_type == "pan_left":
        crop_filter = (
            f"scale={int(W*1.15)}:-1,"
            f"crop=w='iw*0.87':h='ih*0.87':"
            f"x='(iw-iw*0.87)*(1-n/{total_frames})':y='(ih-ih*0.87)/2',"
            f"scale={W}:{H}"
        )
    else:  # static (no animation)
        crop_filter = f"scale={W}:{H}"

    cmd = [
        "ffmpeg", "-y",
        "-loop", "1",
        "-t", str(duration),
        "-i", card_image_path,
        "-vf", f"{crop_filter},setsar=1,fps={FPS}",
        "-c:v", "libx264",
        "-preset", "ultrafast",
        "-crf", "23",
        "-pix_fmt", "yuv420p",
        "-an",
        output_path
    ]

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
    if result.returncode != 0:
        # Fallback: just static image to video
        print(f"  Animation failed, using static: {result.stderr[-200:]}")
        subprocess.run([
            "ffmpeg", "-y", "-loop", "1", "-t", str(duration),
            "-i", card_image_path,
            "-vf", f"scale={W}:{H},setsar=1,fps={FPS}",
            "-c:v", "libx264", "-preset", "ultrafast", "-crf", "23",
            "-pix_fmt", "yuv420p", "-an",
            output_path
        ], capture_output=True, timeout=120)


# ── Card creation functions (unchanged) ──────────────────────────────────────
def create_fact_card(fruit_name, fact_num, total_facts, fact_text,
                     emoji, colors, bg_image_path, output_path):
    """Minimal fact card — photo with top/bottom dark strips, badge, and progress dots.
    Subtitles handle the actual fact text."""
    try:
        primary = tuple(int(colors.get("primary", "#FFC107").lstrip("#")[i:i+2], 16) for i in (0,2,4))
    except Exception:
        primary = (255, 193, 7)

    AMBER    = primary
    ELECTRIC = (0, 229, 255)
    WHITE    = (255, 255, 255)
    SMOKE    = (155, 155, 155)
    DARK     = (18, 16, 8)

    try:
        bg = Image.open(bg_image_path).resize((W, H), Image.LANCZOS)
    except Exception:
        bg = Image.new("RGB", (W, H), DARK)

    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    od = ImageDraw.Draw(ov)
    od.rectangle([(0, 0),       (W, 190)],  fill=(0, 0, 0, 155))
    od.rectangle([(0, H - 220), (W, H)],    fill=(0, 0, 0, 165))

    card = Image.alpha_composite(bg.convert("RGBA"), ov)
    card = draw_strings(card, y_center=55,      n=6, opacity=50, color=AMBER)
    card = draw_strings(card, y_center=H - 110, n=6, opacity=45, color=AMBER)
    card = card.convert("RGB")
    draw = ImageDraw.Draw(card)

    f_badge = get_body_font(38, bold=True)
    f_chan  = get_body_font(30)

    # Cyan "FACT N/5" pill — top left
    bw, bh = 220, 68
    draw.rounded_rectangle([(28, 28), (28 + bw, 28 + bh)], radius=34, fill=ELECTRIC)
    draw.text((28 + bw // 2, 28 + bh // 2), f"FACT {fact_num}/{total_facts}",
              font=f_badge, fill=DARK, anchor="mm")

    # Channel name — top right
    draw.text((W - 28, 62), "Guitar with Facts",
              font=f_chan, fill=WHITE, anchor="rm")

    # Progress dots — bottom right, above subtitle zone
    dot_y   = H - 140
    dot_gap = 42
    total_w = (total_facts - 1) * dot_gap
    sx = W - 50 - total_w
    for i in range(total_facts):
        cx = sx + i * dot_gap
        if i + 1 == fact_num:
            draw.ellipse([(cx - 12, dot_y - 12), (cx + 12, dot_y + 12)], fill=ELECTRIC)
        else:
            draw.ellipse([(cx - 7,  dot_y - 7),  (cx + 7,  dot_y + 7)],  fill=SMOKE)

    card.save(output_path, "PNG", optimize=False)


def create_hook_card(fruit_name, hook_text, emoji, colors, bg_image_path, output_path):
    """Hook card — photo with dark strips, amber INTRO badge, string lines."""
    try:
        primary = tuple(int(colors.get("primary", "#FFC107").lstrip("#")[i:i+2], 16) for i in (0,2,4))
    except Exception:
        primary = (255, 193, 7)

    AMBER = primary
    WHITE = (255, 255, 255)
    DARK  = (18, 16, 8)

    try:
        bg = Image.open(bg_image_path).resize((W, H), Image.LANCZOS)
    except Exception:
        bg = Image.new("RGB", (W, H), DARK)

    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    od = ImageDraw.Draw(ov)
    od.rectangle([(0, 0),       (W, 190)],  fill=(0, 0, 0, 155))
    od.rectangle([(0, H - 220), (W, H)],    fill=(0, 0, 0, 165))

    card = Image.alpha_composite(bg.convert("RGBA"), ov)
    card = draw_strings(card, y_center=55,      n=6, opacity=50, color=AMBER)
    card = draw_strings(card, y_center=H - 110, n=6, opacity=45, color=AMBER)
    card = card.convert("RGB")
    draw = ImageDraw.Draw(card)

    f_badge = get_body_font(38, bold=True)
    f_chan  = get_body_font(30)
    f_cta   = get_body_font(36)

    # Amber "INTRO" pill — top left
    bw, bh = 180, 68
    draw.rounded_rectangle([(28, 28), (28 + bw, 28 + bh)], radius=34, fill=AMBER)
    draw.text((28 + bw // 2, 28 + bh // 2), "INTRO",
              font=f_badge, fill=DARK, anchor="mm")

    # Channel name — top right
    draw.text((W - 28, 62), "Guitar with Facts",
              font=f_chan, fill=WHITE, anchor="rm")

    # Bottom CTA
    draw.text((W // 2, H - 140), "Watch till the end!",
              font=f_cta, fill=WHITE, anchor="mm")

    card.save(output_path, "PNG", optimize=False)


def create_outro_card(fruit_name, emoji, colors, output_path):
    """Dark-stage outro: near-black background, electric cyan WATCHING splash, amber brand."""
    try:
        primary = tuple(int(colors.get("primary", "#FFC107").lstrip("#")[i:i+2], 16) for i in (0,2,4))
    except Exception:
        primary = (255, 193, 7)

    AMBER    = primary
    ELECTRIC = (0, 229, 255)
    WHITE    = (255, 255, 255)
    SMOKE    = (140, 140, 140)
    BG       = (18, 15, 8)

    # Near-black warm background — subtle gradient
    img = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)
    for y in range(H):
        r = max(0, BG[0] - int(10 * y / H))
        g = max(0, BG[1] - int(9  * y / H))
        b = max(0, BG[2] - int(6  * y / H))
        draw.line([(0, y), (W, y)], fill=(r, g, b))

    img_rgba = img.convert("RGBA")
    img_rgba = draw_strings(img_rgba, y_center=280,  n=6, opacity=65, color=AMBER)
    img_rgba = draw_strings(img_rgba, y_center=920,  n=6, opacity=45, color=WHITE)
    img_rgba = draw_strings(img_rgba, y_center=1490, n=6, opacity=60, color=AMBER)
    img = img_rgba.convert("RGB")
    draw = ImageDraw.Draw(img)

    f_big    = get_display_font(200)
    f_huge   = get_display_font(130)
    f_xl     = get_display_font(95)
    f_medium = get_body_font(55, bold=True)
    f_small  = get_body_font(36)

    _outlined(draw, (W//2, 420),  "Thanks for",          f_xl,    SMOKE,    w=2)
    _outlined(draw, (W//2, 625),  "WATCHING",             f_big,   ELECTRIC, w=6)
    _outlined(draw, (W//2, 800),  "!",                    f_huge,  AMBER,    w=5)
    _outlined(draw, (W//2, 1055), "LIKE  &  SUBSCRIBE",  f_xl,    AMBER,    w=4)
    draw.text((W//2, 1190), "for more guitar facts!", font=f_medium, fill=WHITE, anchor="mm")
    _outlined(draw, (W//2, 1615), "GUITAR",               f_big,   WHITE,    w=6)
    _outlined(draw, (W//2, 1795), "with FACTS",           f_huge,  AMBER,    w=5)
    draw.text((W//2, 1900), "#Shorts  •  #GuitarFacts", font=f_small, fill=SMOKE, anchor="mm")

    img.save(output_path, "PNG", optimize=False)


def create_subtitles(data, thumbnail_offset=1.5):
    vo = data["voiceover"]
    seg_names = ["hook","fact_1","fact_2","fact_3","fact_4","fact_5","outro"]
    seg_texts = [
        vo["hook"],
        f"Fact 1! {vo['fact_1']}",
        f"Fact 2! {vo['fact_2']}",
        f"Fact 3! {vo['fact_3']}",
        f"Fact 4! {vo['fact_4']}",
        f"Fact 5! {vo['fact_5']}",
        "",  # No subtitle on outro card — outro has its own big stylish text
    ]

    SILENCE = 0.4
    WPL = 4
    srt, idx = [], 1
    cursor = thumbnail_offset

    for name, text in zip(seg_names, seg_texts):
        seg_path = f"output/audio/segments/{name}.mp3"
        dur = get_duration(seg_path) if os.path.exists(seg_path) \
              else max(2.0, len(text.split()) / 3.0 if text else 3.0)

        # Skip subtitle generation for empty text (outro card)
        if not text.strip():
            cursor += dur + SILENCE
            continue

        words = text.split()
        chunks = [words[i:i+WPL] for i in range(0, len(words), WPL)]
        card_d = dur / max(len(chunks), 1)
        for chunk in chunks:
            srt.append(
                f"{idx}\n{to_srt(cursor)} --> {to_srt(cursor + card_d - 0.05)}\n"
                f"{' '.join(chunk)}\n"
            )
            idx += 1
            cursor += card_d
        cursor += SILENCE

    srt_path = os.path.abspath("output/subtitles.srt")
    with open(srt_path, "w", encoding="utf-8") as f:
        f.write("\n".join(srt))
    print(f"Subtitles: {idx-1} cards")
    return srt_path, cursor


# ── Main video assembly with TWO-PASS approach (faster) ──────────────────────
def assemble_video(data, srt_path, music_path):
    fruit  = data["topic"]
    emoji  = data.get("emoji", "🍎")
    colors = data.get("colors", {})
    vo     = data["voiceover"]
    out    = "output/final_video.mp4"

    # Add 1.5s silence at start for thumbnail intro
    voiceover_mp3_orig = "output/audio/final_voiceover.mp3"
    voiceover_mp3 = "output/audio/voiceover_with_intro.mp3"
    THUMB_DURATION = 1.5  # short thumbnail intro

    subprocess.run([
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", "anullsrc=r=44100:cl=mono",
        "-i", voiceover_mp3_orig,
        "-filter_complex",
        f"[0:a]atrim=0:{THUMB_DURATION}[silence];[silence][1:a]concat=n=2:v=0:a=1[out]",
        "-map", "[out]",
        "-codec:a", "libmp3lame", "-qscale:a", "2",
        voiceover_mp3
    ], capture_output=True, timeout=60)

    if not os.path.exists(voiceover_mp3) or os.path.getsize(voiceover_mp3) < 1000:
        voiceover_mp3 = voiceover_mp3_orig

    total_dur = get_duration(voiceover_mp3)
    print(f"Duration: {total_dur:.1f}s")

    # Get audio segment durations
    seg_names = ["hook","fact_1","fact_2","fact_3","fact_4","fact_5","outro"]
    seg_durs = []
    for name in seg_names:
        p = f"output/audio/segments/{name}.mp3"
        seg_durs.append(get_duration(p) if os.path.exists(p) else 4.0)

    # Get fruit images
    scene_images = [f"output/images/scene_{i}.png" for i in range(1,6)
                    if os.path.exists(f"output/images/scene_{i}.png")]
    if not scene_images:
        scene_images = ["output/images/scene_1.png"]

    # Create cards
    print("Creating cards...")
    os.makedirs("output/cards", exist_ok=True)
    os.makedirs("output/clips", exist_ok=True)

    cards_data = []  # (card_path, duration, anim_type)

    # Thumbnail intro
    if os.path.exists("output/thumbnail_vertical.png"):
        # STATIC (no animation) for first frame so YouTube picks crisp thumbnail
        cards_data.append(("output/thumbnail_vertical.png", THUMB_DURATION, "static"))

    # Hook
    create_hook_card(fruit, vo["hook"], emoji, colors, scene_images[0], "output/cards/hook.png")
    cards_data.append(("output/cards/hook.png", seg_durs[0], "zoom_out"))

    # Facts with cycling animations
    animations = ["pan_right", "zoom_in", "pan_left", "zoom_out", "zoom_in"]
    for i in range(5):
        text = vo[f"fact_{i+1}"]
        img_path = scene_images[i % len(scene_images)]
        card_path = f"output/cards/fact_{i+1}.png"
        create_fact_card(fruit, i+1, 5, text, emoji, colors, img_path, card_path)
        cards_data.append((card_path, seg_durs[i+1], animations[i]))

    # Outro
    create_outro_card(fruit, emoji, colors, "output/cards/outro.png")
    cards_data.append(("output/cards/outro.png", seg_durs[6], "zoom_in"))

    print(f"Cards ready: {len(cards_data)}")

    # ── PASS 1: Render each card as animated clip (fast, parallel-friendly) ──
    print("\n=== Pass 1: Animating each clip ===")
    clip_paths = []
    for i, (card, dur, anim) in enumerate(cards_data):
        clip_path = f"output/clips/clip_{i}.mp4"
        print(f"  Animating clip {i+1}/{len(cards_data)} ({anim}, {dur:.1f}s)...")
        create_animated_clip(card, dur, clip_path, anim)
        if os.path.exists(clip_path):
            clip_paths.append(clip_path)
        else:
            print(f"  WARNING: clip {i} failed")

    if not clip_paths:
        raise RuntimeError("No clips were created!")

    # ── PASS 2: Concat all clips + add audio + subtitles ──────────────────────
    print("\n=== Pass 2: Combining clips + audio + subtitles ===")

    # Create concat list
    concat_file = "output/clips/concat.txt"
    with open(concat_file, "w") as f:
        for clip in clip_paths:
            f.write(f"file '{os.path.abspath(clip)}'\n")

    # First concat all video clips (no re-encode = super fast)
    concat_video = "output/clips/concat_video.mp4"
    subprocess.run([
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0",
        "-i", concat_file,
        "-c", "copy",
        concat_video
    ], capture_output=True, timeout=120)

    # Then add audio + subtitles in single pass
    srt_esc = srt_path.replace("\\", "/").replace(":", "\\:")
    sub_style = (
        "FontName=Arial,FontSize=18,Bold=1,"
        "PrimaryColour=&H00FFE500,"        # Electric cyan (#00E5FF in ASS BGR)
        "OutlineColour=&H00000000,"        # Black outline
        "BackColour=&H00000000,"           # Transparent
        "BorderStyle=1,"
        "Outline=4,Shadow=2,"
        "Alignment=2,"                     # Bottom center
        "MarginV=60,"
        "MarginL=80,MarginR=80"
    )

    # ── MINIMAL audio processing — gTTS is already clean ──────────────────
    # Over-processing causes "air blowing" noise and pumping artifacts
    # Just normalize loudness and gently clean very low rumble
    audio_filter = (
        # Light high-pass at 80Hz (cuts only true rumble, doesn't affect voice)
        "highpass=f=80,"
        # Loudness normalization to YouTube broadcast standard
        "loudnorm=I=-16:TP=-1.5:LRA=11"
    )

    cmd = [
        "ffmpeg", "-y",
        "-i", concat_video,
        "-i", voiceover_mp3,
        "-i", music_path,
        "-filter_complex",
        f"[0:v]subtitles='{srt_esc}':force_style='{sub_style}'[vout];"
        f"[1:a]{audio_filter}[clean_voice];"
        # Mix cleaned voice with subtle music (music at 12% volume)
        f"[clean_voice][2:a]amix=inputs=2:weights='1.0 0.12':"
        f"duration=longest:dropout_transition=0[aout]",
        "-map", "[vout]",
        "-map", "[aout]",
        "-c:v", "libx264",
        "-preset", "ultrafast",
        "-crf", "24",
        "-c:a", "aac",
        "-b:a", "192k",
        "-ar", "44100",
        "-r", str(FPS),
        "-pix_fmt", "yuv420p",
        "-movflags", "+faststart",
        "-shortest",
        out
    ]

    print("Final encoding...")
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)

    if result.returncode == 0:
        size = os.path.getsize(out) / 1024 / 1024
        dur = get_duration(out)
        print(f"\nVideo ready: {out} ({size:.1f}MB, {dur:.1f}s)")
    else:
        print("FFmpeg error:")
        print(result.stderr[-3000:])
        raise RuntimeError("Final assembly failed")


if __name__ == "__main__":
    data = load_video_data()
    print(f"=== Assembling: {data['topic']} ===")

    srt_path, _ = create_subtitles(data, thumbnail_offset=1.5)
    # Music must cover the FULL video duration
    # Voiceover + 3s thumbnail intro + 5s safety buffer for outro
    voiceover_raw_dur = get_duration("output/audio/final_voiceover.mp3")
    total_video_dur = voiceover_raw_dur + 1.5 + 5.0  # +intro +outro
    print(f"Voiceover: {voiceover_raw_dur:.1f}s, Total video: {total_video_dur:.1f}s")
    music_path = get_background_music(total_video_dur)
    assemble_video(data, srt_path, music_path)

    print("\nDone!")
