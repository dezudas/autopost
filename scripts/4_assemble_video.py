"""
Step 4: Assemble Shorts video with FAST animations
Uses scale animations instead of slow zoompan filter
~3x faster than zoompan, same cinematic feel
"""

import json
import math
import os
import subprocess
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
from PIL import Image, ImageDraw, ImageFont


W, H = 1080, 1920
FPS = 24

# ── Canva "Fun Fact" reference palette ────────────────────────────────────────
PEACH      = (255, 224, 199)   # card background
PEACH_BLOB = (255, 213, 177)   # organic blobs on peach
MINT       = (162, 229, 211)   # outro background
MINT_BLOB  = (145, 208, 192)
ACCENT     = (207, 64, 26)     # orange-red heading/body
CHARCOAL   = (60, 60, 80)
PERIWINKLE = (126, 134, 210)
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
def blob_canvas(bg, blob):
    """Solid background with soft organic corner blobs, per the Canva reference."""
    img = Image.new("RGB", (W, H), bg)
    d = ImageDraw.Draw(img)
    for box in [(-380, -260, 420, 330), (720, -200, 1420, 320),
                (-300, 1430, 360, 2120), (800, 1480, 1480, 2080)]:
        d.ellipse(box, fill=blob)
    return img


def draw_bubble(draw, x0, y0, x1, y1, radius=200, tail="speech"):
    """Big white speech/thought bubble, per the Canva reference."""
    draw.rounded_rectangle([(x0, y0), (x1, y1)], radius=radius, fill=WHITE)
    if tail == "speech":
        tx = x1 - 320
        draw.polygon([(tx, y1 - 6), (tx + 150, y1 - 6), (tx + 125, y1 + 100)], fill=WHITE)
    else:  # thought bubble
        draw.ellipse([(x1 - 300, y1 - 20), (x1 - 215, y1 + 65)], fill=WHITE)
        draw.ellipse([(x1 - 190, y1 + 85), (x1 - 135, y1 + 140)], fill=WHITE)


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


def wrap_text(draw, text, font, max_w):
    words, lines, cur = text.split(), [], ""
    for w0 in words:
        t = (cur + " " + w0).strip()
        if draw.textlength(t, font=font) <= max_w:
            cur = t
        else:
            lines.append(cur)
            cur = w0
    if cur:
        lines.append(cur)
    return lines


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


# ── Card creation functions (Canva "Fun Fact" reference) ─────────────────────
def create_fact_card(fruit_name, fact_num, total_facts, fact_text,
                     emoji, colors, bg_image_path, output_path):
    """Full-bleed photo with a soft dark overlay and a letterspaced FUN FACT
    label, per the Canva reference. Subtitles carry the fact text."""
    try:
        bg = Image.open(bg_image_path).resize((W, H), Image.LANCZOS).convert("RGB")
    except Exception:
        bg = Image.new("RGB", (W, H), CHARCOAL)

    # Darker toward the bottom so captions stay readable — built with a single
    # stretched gradient + LUT instead of 500 per-row draw calls.
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 70))
    band_h = 500
    grad = Image.linear_gradient("L").resize((W, band_h))
    lut = [70 + v * 110 // 255 for v in range(256)]
    alpha_band = grad.point(lut)
    r, g, b, a = ov.split()
    a.paste(alpha_band, (0, H - band_h))
    ov = Image.merge("RGBA", (r, g, b, a))
    card = Image.alpha_composite(bg.convert("RGBA"), ov).convert("RGB")
    draw = ImageDraw.Draw(card)

    label = " ".join(f"FUN FACT {fact_num} OF {total_facts}")
    draw.text((W // 2 + 3, 173), label, font=get_body_font(38), fill=(0, 0, 0), anchor="mm")
    draw.text((W // 2, 170), label, font=get_body_font(38), fill=WHITE, anchor="mm")
    draw.text((W // 2, 245), "@guitarwithfacts",
              font=get_body_font(30), fill=(235, 235, 235), anchor="mm")

    card.save(output_path, "PNG", optimize=False)


def create_hook_card(fruit_name, hook_text, emoji, colors, bg_image_path, output_path):
    """Peach FUN FACT speech-bubble card with lightbulb doodle, per the Canva reference."""
    card = blob_canvas(PEACH, PEACH_BLOB)
    draw = ImageDraw.Draw(card)

    draw_bubble(draw, 70, 420, W - 70, 1480, tail="speech")
    draw_bulb(draw, W // 2, 620)
    draw.text((W // 2, 850), "FUN FACT", font=get_display_font(125), fill=ACCENT, anchor="mm")

    f_body = get_body_font(52)
    for i, ln in enumerate(wrap_text(draw, hook_text, f_body, 720)[:6]):
        draw.text((W // 2, 990 + i * 78), ln, font=f_body, fill=ACCENT, anchor="mm")

    draw.text((W // 2, H - 60), "Guitar with Facts",
              font=get_body_font(36), fill=ACCENT, anchor="mm")
    card.save(output_path, "PNG", optimize=False)


def create_outro_card(fruit_name, emoji, colors, output_path):
    """Mint thought-bubble outro card, per the Canva reference."""
    card = blob_canvas(MINT, MINT_BLOB)
    draw = ImageDraw.Draw(card)

    draw_bubble(draw, 90, 500, W - 90, 1420, tail="thought")
    draw.text((W // 2, 710), "THANKS FOR", font=get_display_font(95), fill=CHARCOAL, anchor="mm")
    draw.text((W // 2, 855), "WATCHING!", font=get_display_font(140), fill=ACCENT, anchor="mm")

    f_body = get_body_font(50)
    for i, ln in enumerate(["Like & Subscribe", "for more guitar facts!"]):
        draw.text((W // 2, 1060 + i * 80), ln, font=f_body, fill=PERIWINKLE, anchor="mm")

    draw.text((W // 2, H - 60), "Guitar with Facts",
              font=get_body_font(36), fill=CHARCOAL, anchor="mm")
    card.save(output_path, "PNG", optimize=False)


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

    # ── PASS 1: Render each card as animated clip (independent ffmpeg calls) ──
    print("\n=== Pass 1: Animating each clip (parallel) ===")

    def render_one(i, card, dur, anim):
        clip_path = f"output/clips/clip_{i}.mp4"
        print(f"  [clip {i+1}/{len(cards_data)}] {anim}, {dur:.1f}s...")
        create_animated_clip(card, dur, clip_path, anim)
        return i, clip_path if os.path.exists(clip_path) else None

    rendered = {}
    with ThreadPoolExecutor(max_workers=min(4, len(cards_data))) as executor:
        futures = [
            executor.submit(render_one, i, card, dur, anim)
            for i, (card, dur, anim) in enumerate(cards_data)
        ]
        for future in as_completed(futures):
            i, clip_path = future.result()
            rendered[i] = clip_path
            if clip_path is None:
                print(f"  WARNING: clip {i} failed")

    # Preserve original card order (thumbnail->hook->facts->outro) for the concat file
    clip_paths = [rendered[i] for i in range(len(cards_data)) if rendered[i]]

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
    fonts_dir = os.path.abspath("assets/fonts").replace("\\", "/").replace(":", "\\:")
    sub_style = (
        "FontName=Inter 18pt,FontSize=17,Bold=0,"
        "PrimaryColour=&H00FFFFFF,"        # white, per Canva caption style
        "OutlineColour=&H60000000,"        # soft dark outline
        "BackColour=&H80000000,"           # soft shadow
        "BorderStyle=1,"
        "Outline=1,Shadow=2,"
        "Spacing=3,"                       # letterspaced captions
        "Alignment=2,"                     # Bottom center
        "MarginV=140,"
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
        f"[0:v]subtitles='{srt_esc}':fontsdir='{fonts_dir}':force_style='{sub_style}'[vout];"
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
