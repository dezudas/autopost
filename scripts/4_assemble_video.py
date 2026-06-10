"""
Step 4: Assemble Shorts video with FAST animations
Uses scale animations instead of slow zoompan filter
~3x faster than zoompan, same cinematic feel
"""

import json
import os
import subprocess
import requests
from PIL import Image, ImageDraw, ImageFilter, ImageFont
import textwrap


W, H = 1080, 1920
FPS = 24


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
    """
    Minimal fact card — just shows the fruit image with:
    - Small "FACT N/5" badge at top-left
    - Channel name + hashtag at top-right
    - Small progress dots at the bottom
    - NO big circle or white rectangle covering the fruit!
    Subtitles handle the actual fact text.
    """
    try:
        primary = tuple(int(colors.get("primary","#FFC107").lstrip("#")[i:i+2],16) for i in (0,2,4))
        accent  = tuple(int(colors.get("accent", "#FFF3CD").lstrip("#")[i:i+2],16) for i in (0,2,4))
    except:
        primary, accent = (255,193,7), (255,243,205)  # #FFC107, #FFF3CD

    try:
        bg = Image.open(bg_image_path).resize((W, H), Image.LANCZOS)
    except:
        bg = Image.new("RGB", (W, H), primary)

    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    od = ImageDraw.Draw(overlay)
    od.rectangle([(0, 0), (W, 180)], fill=(0, 0, 0, 130))
    od.rectangle([(0, H-180), (W, H)], fill=(0, 0, 0, 130))

    card = Image.alpha_composite(bg.convert("RGBA"), overlay).convert("RGB")
    draw = ImageDraw.Draw(card)

    # Small "FACT N/5" badge — on-primary text #333333
    draw.rounded_rectangle([(30, 50), (260, 130)], radius=20, fill=accent)
    draw.text((145, 90), f"FACT {fact_num}/{total_facts}",
              fill=(51, 51, 51), anchor="mm")  # on-primary #333333

    # Channel name top-right
    draw.text((W-30, 90), "Guitar with Facts",
              fill=(255, 255, 255), anchor="rm")

    # Small progress dots at bottom
    dy = H - 200  # leave room for subtitles below
    spacing = 50
    total_w = (total_facts - 1) * spacing
    sx = W//2 - total_w//2
    for i in range(total_facts):
        cx = sx + i * spacing
        if i + 1 == fact_num:
            draw.ellipse([(cx-14, dy-14), (cx+14, dy+14)], fill=accent)
        else:
            draw.ellipse([(cx-8, dy-8), (cx+8, dy+8)], fill=(180, 180, 180))

    card.save(output_path, "PNG", optimize=False)


def create_hook_card(fruit_name, hook_text, emoji, colors, bg_image_path, output_path):
    """Minimal hook card — just fruit image with small badge. No big shapes."""
    try:
        primary = tuple(int(colors.get("primary","#FFC107").lstrip("#")[i:i+2],16) for i in (0,2,4))
        accent  = tuple(int(colors.get("accent", "#FFF3CD").lstrip("#")[i:i+2],16) for i in (0,2,4))
    except:
        primary, accent = (255,193,7), (255,243,205)  # #FFC107, #FFF3CD

    try:
        bg = Image.open(bg_image_path).resize((W, H), Image.LANCZOS)
    except:
        bg = Image.new("RGB", (W, H), primary)

    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    od = ImageDraw.Draw(overlay)
    od.rectangle([(0, 0), (W, 180)], fill=(0, 0, 0, 130))
    od.rectangle([(0, H-180), (W, H)], fill=(0, 0, 0, 130))

    card = Image.alpha_composite(bg.convert("RGBA"), overlay).convert("RGB")
    draw = ImageDraw.Draw(card)

    # Badge — on-primary text #333333
    draw.rounded_rectangle([(30, 50), (260, 130)], radius=20, fill=accent)
    draw.text((145, 90), "INTRO", fill=(51, 51, 51), anchor="mm")  # on-primary #333333

    # Channel name top-right
    draw.text((W-30, 90), "Guitar with Facts", fill=(255, 255, 255), anchor="rm")

    # Bottom CTA (small)
    draw.text((W//2, H-90), "Watch till the end!",
              fill=(255, 255, 255), anchor="mm")

    card.save(output_path, "PNG", optimize=False)


def create_outro_card(fruit_name, emoji, colors, output_path):
    """Stylish outro with BIG bold text and proper fonts."""
    try:
        primary   = tuple(int(colors.get("primary",  "#FFC107").lstrip("#")[i:i+2],16) for i in (0,2,4))
        accent    = tuple(int(colors.get("accent",   "#FFF3CD").lstrip("#")[i:i+2],16) for i in (0,2,4))
        secondary = tuple(int(colors.get("secondary","#E0A800").lstrip("#")[i:i+2],16) for i in (0,2,4))
    except:
        primary, accent = (255,193,7), (255,243,205)   # #FFC107, #FFF3CD
        secondary = (224, 168, 0)                       # #E0A800

    # Gradient background (primary → secondary)
    img = Image.new("RGB", (W, H), primary)
    draw = ImageDraw.Draw(img)
    for i in range(H):
        ratio = i / H
        r = int(primary[0]*(1-ratio) + secondary[0]*ratio)
        g = int(primary[1]*(1-ratio) + secondary[1]*ratio)
        b = int(primary[2]*(1-ratio) + secondary[2]*ratio)
        draw.line([(0,i),(W,i)], fill=(r,g,b))

    # Load bold fonts — prefer Poppins/Manrope (design.md), fall back to DejaVu
    _bold_fonts = [
        "/usr/share/fonts/truetype/poppins/Poppins-Bold.ttf",
        "/usr/share/fonts/truetype/manrope/Manrope-Bold.ttf",
        "/usr/share/fonts/opentype/noto/NotoSans-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    ]
    _bold_path = next((p for p in _bold_fonts if os.path.exists(p)), None)
    try:
        font_huge   = ImageFont.truetype(_bold_path, 130)
        font_xl     = ImageFont.truetype(_bold_path, 95)
        font_large  = ImageFont.truetype(_bold_path, 80)
        font_medium = ImageFont.truetype(_bold_path, 60)
    except:
        font_huge = font_xl = font_large = font_medium = ImageFont.load_default()

    # Helper for outlined text (looks stylish)
    def styled_text(pos, text, font, fill, outline=(0,0,0), outline_width=4):
        x, y = pos
        for dx in range(-outline_width, outline_width+1):
            for dy in range(-outline_width, outline_width+1):
                if dx*dx + dy*dy > outline_width*outline_width:
                    continue
                draw.text((x+dx, y+dy), text, font=font, fill=outline, anchor="mm")
        draw.text((x, y), text, font=font, fill=fill, anchor="mm")

    # ── BIG stylish text layout ──────────────────────────────────────────────
    # "Thanks for" — big white
    styled_text((W//2, 320), "Thanks for", font=font_xl,
                fill=(255,255,255), outline=(0,0,0), outline_width=5)
    # "WATCHING!" — HUGE accent color
    styled_text((W//2, 460), "WATCHING!", font=font_huge,
                fill=accent, outline=(0,0,0), outline_width=6)

    # Decorative emoji line
    styled_text((W//2, 670), "★ ★ ★ ★ ★", font=font_large,
                fill=accent, outline=(0,0,0), outline_width=3)

    # "LIKE & SUBSCRIBE" — bold yellow
    styled_text((W//2, 840), "LIKE & SUBSCRIBE", font=font_xl,
                fill=accent, outline=(0,0,0), outline_width=5)

    # "for more guitar facts!" — medium white
    styled_text((W//2, 1000), "for more guitar facts!", font=font_medium,
                fill=(255,255,255), outline=(0,0,0), outline_width=3)

    # Decorative line
    draw.rectangle([(200, 1180), (W-200, 1190)], fill=(255,255,255))

    # Channel name — biggest at the bottom
    styled_text((W//2, 1330), "Guitar", font=font_huge,
                fill=(255,255,255), outline=(0,0,0), outline_width=5)
    styled_text((W//2, 1480), "with FACTS", font=font_huge,
                fill=accent, outline=(0,0,0), outline_width=5)

    # Hashtag at very bottom
    styled_text((W//2, 1700), "#Shorts #GuitarFacts", font=font_medium,
                fill=(255,255,255,200), outline=(0,0,0), outline_width=2)

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
        "FontName=Arial,FontSize=14,Bold=1,"
        "PrimaryColour=&H0000FFFF,"       # Bright YELLOW (colorful)
        "OutlineColour=&H00000000,"        # Black outline
        "BackColour=&H00000000,"           # Transparent
        "BorderStyle=1,"                   # Outline only
        "Outline=3,Shadow=1,"              # Strong outline
        "Alignment=2,"                     # Bottom center
        "MarginV=50,"                      # ~1cm from bottom edge
        "MarginL=80,MarginR=80"            # ~1cm side margins
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
