"""
Step 4: Modern, Elegant Shorts Video Assembler
- Minimalist luxury dark aesthetic (Deep Slate & Amber Gold)
- Smooth ease-out text slide-up & fade-in animation for each fact entry
- Gentle low-volume background sound beneath crystal-clear voiceover
- Zero external image dependencies (pure Python PIL + FFmpeg)
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

# ── Luxury Modern Dark Palette ──────────────────────────────────────────────
BG_DARK      = (11, 15, 25)       # Deep slate midnight
BG_CARD      = (21, 29, 42)       # Sleek charcoal surface
BG_INNER_BOX = (15, 21, 32)       # Recessed callout box
BORDER_COLOR = (40, 53, 72)       # Subtle hairline border
BORDER_ACCENT= (65, 82, 108)      # Highlight border
GOLD         = (245, 158, 11)     # Accent amber/gold
WHITE        = (248, 250, 252)    # Crisp white
MUTED        = (148, 163, 184)    # Secondary muted text
CYAN         = (6, 182, 212)      # Accent cyan highlight

FONTS_DIR = "assets/fonts"


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


def wrap_text(draw, text, font, max_w):
    words, lines, cur = text.split(), [], ""
    for w0 in words:
        t = (cur + " " + w0).strip()
        if draw.textlength(t, font=font) <= max_w:
            cur = t
        else:
            if cur:
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
    except Exception:
        return 4.0


def to_srt(s):
    s = max(0.0, s)
    h, rem = divmod(s, 3600)
    m, sec = divmod(rem, 60)
    ms = int((sec % 1) * 1000)
    return f"{int(h):02d}:{int(m):02d}:{int(sec):02d},{ms:03d}"


# ── Gentle Low-Volume Background Sound ───────────────────────────────────────
def get_background_music(duration):
    """
    Generate warm, gentle acoustic ambient background music using FFmpeg synthesis.
    Soft harmonic intervals, bandpass-filtered to leave speech clear.
    """
    out = "output/audio/background_trimmed.mp3"
    os.makedirs("output/audio", exist_ok=True)

    fade_start = max(0, duration - 3)
    cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", "sine=frequency=220.00:sample_rate=44100",  # A3 (root)
        "-f", "lavfi", "-i", "sine=frequency=261.63:sample_rate=44100",  # C4 (minor 3rd)
        "-f", "lavfi", "-i", "sine=frequency=329.63:sample_rate=44100",  # E4 (5th)
        "-f", "lavfi", "-i", "sine=frequency=110.00:sample_rate=44100",  # A2 (sub bass)
        "-filter_complex",
        "[0][1][2][3]amix=inputs=4:duration=longest[mix];"
        "[mix]tremolo=f=0.4:d=0.25,"              # slow warm tremolo
        "volume=0.05,"                            # gentle low volume
        "highpass=f=180,"                         # avoid low boom
        "lowpass=f=2500,"                         # warm soft tone (leaves voice clear)
        f"afade=t=in:d=2,afade=t=out:st={fade_start}:d=3[out]",
        "-map", "[out]",
        "-t", str(duration + 1),
        "-codec:a", "libmp3lame",
        out
    ]
    subprocess.run(cmd, capture_output=True, timeout=60)
    print(f"Background ambient audio ready: {out}")
    return out


# ── Visual Canvas & Card Drawing ─────────────────────────────────────────────
def create_base_background(topic, specs, output_path):
    """
    Creates the permanent modern background:
    - Deep midnight slate with luxury frame
    - Brand header at top: @GUITARWITHFACTS
    - Topic title and quick specs banner
    """
    img = Image.new("RGB", (W, H), BG_DARK)
    draw = ImageDraw.Draw(img)

    # Luxury outer frame inset
    pad = 32
    draw.rounded_rectangle([(pad, pad), (W - pad, H - pad)], radius=24, outline=BORDER_COLOR, width=2)

    # Top brand bar
    draw.text((W // 2, 130), "@GUITARWITHFACTS  •  60-SECOND BREAKDOWN",
              font=get_body_font(26, bold=True), fill=GOLD, anchor="mm")

    # Main Topic Title
    f_title = get_display_font(74)
    words = topic.upper().split()
    if len(words) > 3:
        t1 = " ".join(words[:2])
        t2 = " ".join(words[2:])
        draw.text((W // 2, 230), t1, font=f_title, fill=WHITE, anchor="mm")
        draw.text((W // 2, 315), t2, font=f_title, fill=WHITE, anchor="mm")
        specs_y = 405
    else:
        draw.text((W // 2, 250), topic.upper(), font=f_title, fill=WHITE, anchor="mm")
        specs_y = 350

    # Quick Specs Header Banner (Notes & Tab pill)
    notes = specs.get("notes", "A • C • E")
    tab = specs.get("tab", "X 0 2 2 1 0")
    banner_text = f"NOTES: {notes}   |   TAB: {tab}"

    bw, bh = 780, 56
    bx0 = (W - bw) // 2
    draw.rounded_rectangle([(bx0, specs_y - bh // 2), (bx0 + bw, specs_y + bh // 2)],
                           radius=28, fill=BG_CARD, outline=BORDER_COLOR, width=1)
    draw.text((W // 2, specs_y), banner_text, font=get_body_font(27, bold=True), fill=MUTED, anchor="mm")

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    img.save(output_path, "PNG")


def create_fact_overlay(fact_idx, fact_data, total_facts, output_path):
    """
    Creates the transparent overlay card for each fact.
    This is what animates in smoothly during video assembly!
    """
    card_w, card_h = 920, 780
    img = Image.new("RGBA", (card_w, card_h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Main Card Body with rounded corners
    draw.rounded_rectangle([(0, 0), (card_w, card_h)], radius=36, fill=(21, 29, 42, 255), outline=BORDER_ACCENT, width=2)

    # Category Badge Pill at top of card
    badge_text = fact_data.get("badge", f"FACT {fact_idx} OF {total_facts}").upper()
    pill_w = int(draw.textlength(badge_text, font=get_body_font(26, bold=True)) + 44)
    pill_h = 48
    draw.rounded_rectangle([(48, 48), (48 + pill_w, 48 + pill_h)], radius=24, fill=(245, 158, 11, 255))
    draw.text((48 + pill_w // 2, 48 + pill_h // 2), badge_text, font=get_body_font(24, bold=True), fill=(0, 0, 0), anchor="mm")

    # Step progress indicator at right
    step_indicator = f"{fact_idx:02d} / {total_facts:02d}"
    draw.text((card_w - 48, 48 + pill_h // 2), step_indicator, font=get_body_font(26, bold=True), fill=MUTED, anchor="rm")

    # Headline
    headline = fact_data.get("headline", "Key Insight").strip()
    f_head = get_display_font(50)
    lines = wrap_text(draw, headline, f_head, card_w - 96)
    head_y = 150
    for i, ln in enumerate(lines[:2]):
        draw.text((48, head_y + i * 62), ln, font=f_head, fill=WHITE)

    # Informative Breakdown Box inside card
    box_y0 = 310
    box_y1 = card_h - 70
    draw.rounded_rectangle([(48, box_y0), (card_w - 48, box_y1)], radius=24, fill=(15, 21, 32, 255), outline=BORDER_COLOR, width=2)

    # Callout Box Header
    box_title = fact_data.get("box_title", "CORE DETAIL").upper()
    draw.text((80, box_y0 + 38), box_title, font=get_body_font(24, bold=True), fill=CYAN)

    # Callout Box Content (e.g. Chord Notes, Tab position, or Pro Tip)
    box_content = fact_data.get("box_content", "").strip()
    if box_content:
        f_box = get_body_font(34, bold=True)
        content_lines = wrap_text(draw, box_content, f_box, card_w - 160)
        for j, cln in enumerate(content_lines[:4]):
            draw.text((80, box_y0 + 95 + j * 48), cln, font=f_box, fill=GOLD if j == 0 else WHITE)

    # Subtle bottom branding dot
    draw.text((card_w // 2, card_h - 32), "Swipe up for next fact • @guitarwithfacts",
              font=get_body_font(20), fill=MUTED, anchor="mm")

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    img.save(output_path, "PNG")


def create_hook_overlay(topic, hook_text, specs, output_path):
    """Intro card overlay for the hook segment."""
    card_w, card_h = 920, 780
    img = Image.new("RGBA", (card_w, card_h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    draw.rounded_rectangle([(0, 0), (card_w, card_h)], radius=36, fill=(21, 29, 42, 255), outline=BORDER_ACCENT, width=2)

    # Badge
    draw.rounded_rectangle([(48, 48), (280, 96)], radius=24, fill=(245, 158, 11, 255))
    draw.text((164, 72), "TODAY'S LESSON", font=get_body_font(24, bold=True), fill=(0, 0, 0), anchor="mm")

    # Big Topic
    draw.text((48, 160), topic.upper(), font=get_display_font(58), fill=WHITE)

    # Hook message
    f_body = get_body_font(36)
    lines = wrap_text(draw, hook_text, f_body, card_w - 96)
    for i, ln in enumerate(lines[:4]):
        draw.text((48, 250 + i * 50), ln, font=f_body, fill=MUTED)

    # Specs box at bottom
    box_y0 = 500
    draw.rounded_rectangle([(48, box_y0), (card_w - 48, card_h - 50)], radius=24, fill=(15, 21, 32, 255), outline=BORDER_COLOR, width=2)
    notes = specs.get("notes", "A • C • E")
    formula = specs.get("formula", "Root • Flat 3rd • 5th")
    draw.text((80, box_y0 + 40), f"FORMULA:  {formula}", font=get_body_font(28, bold=True), fill=CYAN)
    draw.text((80, box_y0 + 95), f"NOTES:    {notes}", font=get_body_font(32, bold=True), fill=GOLD)

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    img.save(output_path, "PNG")


def create_outro_overlay(topic, output_path):
    """Outro card overlay."""
    card_w, card_h = 920, 780
    img = Image.new("RGBA", (card_w, card_h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    draw.rounded_rectangle([(0, 0), (card_w, card_h)], radius=36, fill=(21, 29, 42, 255), outline=BORDER_ACCENT, width=2)

    # Badge
    draw.rounded_rectangle([(48, 48), (300, 96)], radius=24, fill=(245, 158, 11, 255))
    draw.text((174, 72), "LESSON COMPLETE", font=get_body_font(24, bold=True), fill=(0, 0, 0), anchor="mm")

    # Title
    draw.text((48, 170), "PRACTICE THIS DAILY", font=get_display_font(52), fill=WHITE)

    # CTA Box
    box_y0 = 270
    draw.rounded_rectangle([(48, box_y0), (card_w - 48, card_h - 70)], radius=24, fill=(15, 21, 32, 255), outline=BORDER_COLOR, width=2)
    draw.text((card_w // 2, box_y0 + 80), "LIKE & SUBSCRIBE", font=get_display_font(48), fill=GOLD, anchor="mm")
    draw.text((card_w // 2, box_y0 + 150), "For daily guitar chords, theory & tips", font=get_body_font(30), fill=MUTED, anchor="mm")
    draw.text((card_w // 2, box_y0 + 230), "Save this Short for your guitar practice!", font=get_body_font(30, bold=True), fill=CYAN, anchor="mm")

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    img.save(output_path, "PNG")


# ── Simple Text Animation: Smooth Entry Slide-Up & Fade-In ───────────────────
def create_animated_fact_clip(bg_path, overlay_path, duration, output_path, target_y=510):
    """
    Renders an animated clip using FFmpeg:
    - Card smoothly slides up by 80px and fades in during first 0.45s (quarter-sine ease-out)
    - Stays completely locked and crisp for the remainder of the fact duration
    """
    cmd = [
        "ffmpeg", "-y",
        "-loop", "1", "-t", str(duration), "-i", bg_path,
        "-loop", "1", "-t", str(duration), "-i", overlay_path,
        "-filter_complex",
        f"[0:v][1:v]overlay=x='(W-w)/2':y='if(lt(t, 0.45), {target_y} + 80*(1 - sin(t/0.45*PI/2)), {target_y})':alpha='min(1, t/0.3)'[v]",
        "-map", "[v]",
        "-c:v", "libx264",
        "-preset", "ultrafast",
        "-crf", "23",
        "-pix_fmt", "yuv420p",
        "-r", str(FPS),
        "-an",
        output_path
    ]
    res = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    if res.returncode != 0:
        print(f"Animation failed, falling back to static overlay: {res.stderr[-200:]}")
        # Fallback static overlay
        subprocess.run([
            "ffmpeg", "-y",
            "-loop", "1", "-t", str(duration), "-i", bg_path,
            "-loop", "1", "-t", str(duration), "-i", overlay_path,
            "-filter_complex", f"[0:v][1:v]overlay=x='(W-w)/2':y={target_y}[v]",
            "-map", "[v]",
            "-c:v", "libx264", "-preset", "ultrafast", "-crf", "23",
            "-pix_fmt", "yuv420p", "-r", str(FPS), "-an",
            output_path
        ], capture_output=True, timeout=60)


def create_static_intro_clip(image_path, duration, output_path):
    """Static 1.5s clip for thumbnail so YouTube captures a sharp cover."""
    subprocess.run([
        "ffmpeg", "-y",
        "-loop", "1", "-t", str(duration),
        "-i", image_path,
        "-vf", f"scale={W}:{H},setsar=1,fps={FPS}",
        "-c:v", "libx264", "-preset", "ultrafast", "-crf", "23",
        "-pix_fmt", "yuv420p", "-an",
        output_path
    ], capture_output=True, timeout=60)


# ── Subtitles ─────────────────────────────────────────────────────────────────
def create_subtitles(data, thumbnail_offset=1.5):
    vo = data["voiceover"]
    seg_names = ["hook", "fact_1", "fact_2", "fact_3", "fact_4", "fact_5", "outro"]
    seg_texts = [
        vo["hook"],
        vo["fact_1"],
        vo["fact_2"],
        vo["fact_3"],
        vo["fact_4"],
        vo["fact_5"],
        "",  # No subtitles on outro card — outro has its own big stylish CTA
    ]

    SILENCE = 0.25
    WPL = 4
    srt, idx = [], 1
    cursor = thumbnail_offset

    for i, name in enumerate(seg_names):
        p = f"output/audio/segments/{name}.mp3"
        dur = get_duration(p) if os.path.exists(p) else 4.0
        text = seg_texts[i]

        if text.strip():
            words = text.split()
            chunk_cnt = math.ceil(len(words) / WPL)
            chunk_dur = (dur - 0.1) / max(1, chunk_cnt)
            for c in range(chunk_cnt):
                cwords = words[c * WPL: (c + 1) * WPL]
                cstart = cursor + c * chunk_dur
                cend = cursor + (c + 1) * chunk_dur
                srt.append(f"{idx}\n{to_srt(cstart)} --> {to_srt(cend)}\n{' '.join(cwords)}\n")
                idx += 1
        cursor += dur + SILENCE

    os.makedirs("output", exist_ok=True)
    out_path = "output/subtitles.srt"
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(srt))
    print(f"Subtitles generated: {len(srt)} chunks")
    return out_path, cursor


# ── Assembly Pipeline ────────────────────────────────────────────────────────
def assemble_video(data, srt_path, music_path):
    out = "output/final_video.mp4"
    topic = data.get("topic", "Guitar Lesson")
    specs = data.get("specs", {})
    facts_list = data.get("facts", [])
    vo = data["voiceover"]

    # Segment durations
    seg_names = ["hook", "fact_1", "fact_2", "fact_3", "fact_4", "fact_5", "outro"]
    seg_durs = [get_duration(f"output/audio/segments/{n}.mp3") for n in seg_names]

    os.makedirs("output/cards", exist_ok=True)
    os.makedirs("output/clips", exist_ok=True)

    # 1. Generate Base Canvas Background
    base_bg_path = "output/cards/base_bg.png"
    create_base_background(topic, specs, base_bg_path)

    # 2. Generate Overlay Cards
    hook_overlay = "output/cards/hook_overlay.png"
    create_hook_overlay(topic, vo["hook"], specs, hook_overlay)

    fact_overlays = []
    for i in range(5):
        fact_data = facts_list[i] if i < len(facts_list) else {
            "badge": f"0{i+1} / INSIGHT",
            "headline": f"Fact {i+1}",
            "box_title": "DETAILS",
            "box_content": vo[f"fact_{i+1}"]
        }
        ov_path = f"output/cards/fact_{i+1}_overlay.png"
        create_fact_overlay(i + 1, fact_data, 5, ov_path)
        fact_overlays.append(ov_path)

    outro_overlay = "output/cards/outro_overlay.png"
    create_outro_overlay(topic, outro_overlay)

    # 3. Build Clip Queue
    SILENCE_GAP = 0.25
    OUTRO_PAD = 2.0
    THUMB_DURATION = 1.5

    clips_plan = []  # (type, bg, overlay, duration, output_clip_path)

    # Thumbnail intro
    if os.path.exists("output/thumbnail_vertical.png"):
        clips_plan.append(("static", "output/thumbnail_vertical.png", None, THUMB_DURATION, "output/clips/clip_0.mp4"))

    # Hook
    clips_plan.append(("anim", base_bg_path, hook_overlay, seg_durs[0] + SILENCE_GAP, "output/clips/clip_1.mp4"))

    # Facts 1 to 5
    for i in range(5):
        clips_plan.append(("anim", base_bg_path, fact_overlays[i], seg_durs[i+1] + SILENCE_GAP, f"output/clips/clip_{i+2}.mp4"))

    # Outro
    clips_plan.append(("anim", base_bg_path, outro_overlay, seg_durs[6] + OUTRO_PAD, "output/clips/clip_7.mp4"))

    print(f"\n=== Pass 1: Rendering Animated Clips ({len(clips_plan)} segments) ===")

    def render_clip(item):
        ctype, bg, overlay, dur, clip_out = item
        if ctype == "static":
            create_static_intro_clip(bg, dur, clip_out)
        else:
            create_animated_fact_clip(bg, overlay, dur, clip_out)
        return clip_out if os.path.exists(clip_out) else None

    with ThreadPoolExecutor(max_workers=min(4, len(clips_plan))) as executor:
        results = list(executor.map(render_clip, clips_plan))

    clip_paths = [c for c in results if c]
    if not clip_paths:
        raise RuntimeError("Failed to create video clips")

    # 4. Concatenate All Clips
    print("\n=== Pass 2: Concat + Low-Volume Background Music + Subtitles ===")
    concat_file = "output/clips/concat.txt"
    with open(concat_file, "w") as f:
        for c in clip_paths:
            f.write(f"file '{os.path.abspath(c)}'\n")

    concat_video = "output/clips/concat_video.mp4"
    subprocess.run([
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0",
        "-i", concat_file,
        "-c", "copy",
        concat_video
    ], capture_output=True, timeout=120)

    # 5. Final Pass: Merge Subtitles + Audio Mix with Low-Volume Sound
    srt_esc = srt_path.replace("\\", "/").replace(":", "\\:")
    fonts_dir = os.path.abspath(FONTS_DIR).replace("\\", "/").replace(":", "\\:")

    # Clean, modern yellow subtitles with subtle rounded black backing box
    sub_style = (
        "FontName=Montserrat,FontSize=50,Bold=1,"
        "PrimaryColour=&H0000FFFF,"        # High-contrast bright yellow
        "OutlineColour=&H00000000,"        # Black outline
        "BackColour=&HA0000000,"           # Semi-transparent dark pill background
        "BorderStyle=3,"                   # Opaque box / backing
        "Outline=2,Shadow=0,"
        "Alignment=2,"                     # Bottom center
        "MarginV=250,"                     # Safe zone above Shorts UI
        "MarginL=60,MarginR=60"
    )

    audio_filter = (
        "highpass=f=80,"
        "loudnorm=I=-16:TP=-1.5:LRA=11"
    )

    cmd = [
        "ffmpeg", "-y",
        "-i", concat_video,
        "-i", "output/audio/final_voiceover.mp3",
        "-i", music_path,
        "-filter_complex",
        f"[0:v]subtitles='{srt_esc}':fontsdir='{fonts_dir}':original_size=1080x1920:force_style='{sub_style}'[vout];"
        f"[1:a]{audio_filter}[clean_voice];"
        # Mix voice with subtle background sound at 6% volume (weights: 1.0 vs 0.06)
        f"[clean_voice][2:a]amix=inputs=2:weights='1.0 0.06':duration=longest:dropout_transition=2[aout]",
        "-map", "[vout]",
        "-map", "[aout]",
        "-c:v", "libx264",
        "-preset", "ultrafast",
        "-crf", "23",
        "-c:a", "aac",
        "-b:a", "192k",
        "-ar", "44100",
        "-r", str(FPS),
        "-pix_fmt", "yuv420p",
        "-movflags", "+faststart",
        "-shortest",
        out
    ]

    print("Running final encode...")
    res = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    if res.returncode == 0:
        size = os.path.getsize(out) / 1024 / 1024
        dur = get_duration(out)
        print(f"\nSUCCESS! Modern Shorts Video ready: {out} ({size:.1f}MB, {dur:.1f}s)")
    else:
        print("FFmpeg assembly error:")
        print(res.stderr[-2000:])
        raise RuntimeError("Final assembly failed")


if __name__ == "__main__":
    data = load_video_data()
    print(f"=== Assembling Modern Short: {data['topic']} ===")
    srt_path, _ = create_subtitles(data, thumbnail_offset=1.5)
    vo_dur = get_duration("output/audio/final_voiceover.mp3")
    total_dur = vo_dur + 1.5 + 4.0
    music_path = get_background_music(total_dur)
    assemble_video(data, srt_path, music_path)
    print("\nAssembly complete!")
