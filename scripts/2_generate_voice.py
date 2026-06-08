"""
Step 2: Generate natural voice using Hugging Face Inference API
- FREE with email signup at huggingface.co (no credit card needed)
- Uses Kokoro-82M - #1 ranked open-source TTS, near-ElevenLabs quality
- Truly natural-sounding neural voices
"""

import json
import os
import subprocess
import sys
import time
import requests


def load_video_data():
    with open("output/video_data.json", "r") as f:
        return json.load(f)


def translate_text(text, target_lang):
    if target_lang == "en":
        return text
    url = "https://translate.googleapis.com/translate_a/single"
    params = {"client": "gtx", "sl": "en", "tl": target_lang, "dt": "t", "q": text}
    try:
        r = requests.get(url, params=params, timeout=15)
        if r.status_code == 200:
            data = r.json()
            translated = "".join([chunk[0] for chunk in data[0] if chunk[0]])
            print(f"  Translated: {text[:40]}...")
            return translated
    except Exception as e:
        print(f"  Translation error: {e}")
    return text


# ── HuggingFace Kokoro TTS — natural neural voice ───────────────────────────
# Available voices for Kokoro:
KOKORO_VOICES = {
    "af_bella":  "American female, warm and clear (RECOMMENDED)",
    "af_sarah":  "American female, professional",
    "af_nicole": "American female, friendly",
    "af_sky":    "American female, energetic",
    "am_adam":   "American male, deep confident",
    "am_michael":"American male, warm narrator",
    "bf_emma":   "British female, sophisticated",
    "bf_isabella": "British female, elegant",
    "bm_george": "British male, classic",
    "bm_lewis":  "British male, modern",
}


def huggingface_tts(text, output_path, voice="af_bella", api_key=None):
    """
    Use Hugging Face Inference API with Kokoro-82M model.
    Tries the newer router endpoint first, falls back to legacy endpoint.
    """
    if not api_key:
        print(f"  No HF_API_KEY set, skipping Hugging Face")
        return False

    # Try newer router endpoint first, then legacy endpoint
    API_URLS = [
        "https://router.huggingface.co/hf-inference/models/hexgrad/Kokoro-82M",
        "https://api-inference.huggingface.co/models/hexgrad/Kokoro-82M",
    ]

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    payload = {
        "inputs": text,
        "parameters": {
            "voice": voice
        }
    }

    for api_url in API_URLS:
        print(f"    Trying: {api_url}")
        for attempt in range(3):
            try:
                print(f"    HF attempt {attempt+1}/3 (voice={voice})")
                r = requests.post(api_url, headers=headers, json=payload, timeout=120)
                print(f"    Status: {r.status_code}, Size: {len(r.content)} bytes")

                if r.status_code == 200 and len(r.content) > 1000:
                    if r.content[:4] in [b'RIFF', b'OggS', b'\xff\xfb', b'\xff\xf3', b'ID3\x04']:
                        with open(output_path, "wb") as f:
                            f.write(r.content)
                        return True
                    else:
                        try:
                            err = r.json()
                            print(f"    HF response: {err}")
                        except:
                            with open(output_path, "wb") as f:
                                f.write(r.content)
                            return True

                elif r.status_code == 503:
                    print(f"    Model loading, waiting 20s...")
                    time.sleep(20)
                else:
                    try:
                        err = r.json()
                        print(f"    HF error: {err}")
                    except:
                        print(f"    HF error: {r.text[:300]}")
                    break  # non-retriable error, try next URL

            except requests.exceptions.ConnectionError as e:
                # DNS failure or unreachable — no point retrying same URL
                print(f"    Connection failed (DNS/network): {e}")
                break
            except Exception as e:
                print(f"    Exception: {e}")
                time.sleep(5)

    return False


def gtts_fallback(text, output_path, lang="en", tld="com"):
    try:
        from gtts import gTTS
        if lang == "en":
            tts = gTTS(text=text, lang=lang, tld=tld, slow=False)
        else:
            tts = gTTS(text=text, lang=lang, slow=False)
        tts.save(output_path)
        return os.path.exists(output_path) and os.path.getsize(output_path) > 1000
    except Exception as e:
        print(f"  gTTS error: {e}")
        return False


def espeak_fallback(text, output_path):
    wav = output_path.replace(".mp3", ".wav")
    r = subprocess.run([
        "espeak-ng", "-v", "en-us+m3",
        "-s", "155", "-p", "55", "-a", "180",
        "-w", wav, text
    ], capture_output=True)
    if r.returncode == 0:
        subprocess.run([
            "ffmpeg", "-y", "-i", wav,
            "-codec:a", "libmp3lame", "-qscale:a", "2",
            output_path
        ], capture_output=True)
        if os.path.exists(wav):
            os.remove(wav)
        return True
    return False


def generate_segment(text, output_path, voice="af_bella", lang="en", hf_key=None):
    """Try Hugging Face Kokoro first, fall back to gTTS, then espeak."""
    if lang == "en" and hf_key:
        print(f"  Trying Hugging Face Kokoro ({voice})...")
        if huggingface_tts(text, output_path, voice, hf_key):
            print(f"  SUCCESS (HuggingFace {voice})")
            return f"hf_{voice}"

    # gTTS fallback
    print(f"  Trying gTTS...")
    if gtts_fallback(text, output_path, lang=lang):
        print(f"  SUCCESS (gTTS)")
        return "gtts"

    # Last resort
    print(f"  WARNING: Using espeak (robotic)")
    if espeak_fallback(text, output_path):
        return "espeak"
    return "failed"


def combine_audio(segment_files, output_path):
    os.makedirs("output/audio", exist_ok=True)
    silence = "output/audio/silence.mp3"
    subprocess.run([
        "ffmpeg", "-y", "-f", "lavfi",
        "-i", "anullsrc=r=44100:cl=mono",
        "-t", "0.25", "-codec:a", "libmp3lame", silence
    ], capture_output=True)

    list_file = "output/audio/concat_list.txt"
    with open(list_file, "w") as f:
        for i, seg in enumerate(segment_files):
            abs_seg = os.path.abspath(seg)
            abs_sil = os.path.abspath(silence)
            f.write(f"file '{abs_seg}'\n")
            if i < len(segment_files) - 1:
                f.write(f"file '{abs_sil}'\n")

    subprocess.run([
        "ffmpeg", "-y", "-f", "concat", "-safe", "0",
        "-i", list_file,
        "-codec:a", "libmp3lame", "-qscale:a", "2",
        output_path
    ], capture_output=True)

    probe = subprocess.run([
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1", output_path
    ], capture_output=True, text=True)
    duration = float(probe.stdout.strip() or "0")
    print(f"\nCombined audio: {output_path} ({duration:.1f}s)")
    return duration


if __name__ == "__main__":
    data = load_video_data()
    vo = data["voiceover"]
    topic = data["topic"]

    os.makedirs("output/audio/segments", exist_ok=True)

    # ── VOICE CONFIGURATION ───────────────────────────────────────────────────
    # Available Kokoro voices (Hugging Face):
    #   Female:  af_bella, af_sarah, af_nicole, af_sky, bf_emma, bf_isabella
    #   Male:    am_adam, am_michael, bm_george, bm_lewis
    VOICE_NAME = "am_michael"   # Warm narrator male voice
    VOICE_LANG = "en"

    # Hugging Face API key from environment
    HF_API_KEY = os.environ.get("HF_API_KEY")

    print(f"=== Generating voice for: {topic} ===")
    if HF_API_KEY:
        print(f"Engine: Hugging Face Kokoro (high-quality neural)")
        print(f"Voice: {VOICE_NAME} ({KOKORO_VOICES.get(VOICE_NAME, 'N/A')})")
    else:
        print(f"Engine: gTTS (HF_API_KEY not set, using fallback)")
    print()

    segments = [
        ("hook",   vo["hook"]),
        ("fact_1", f"Fact 1! {vo['fact_1']}"),
        ("fact_2", f"Fact 2! {vo['fact_2']}"),
        ("fact_3", f"Fact 3! {vo['fact_3']}"),
        ("fact_4", f"Fact 4! {vo['fact_4']}"),
        ("fact_5", f"Fact 5! {vo['fact_5']}"),
        ("outro",  vo["outro"]),
    ]

    if VOICE_LANG != "en":
        print(f"Translating to {VOICE_LANG}...")
        segments = [(name, translate_text(text, VOICE_LANG)) for name, text in segments]

    segment_files = []
    methods_used = []
    for name, text in segments:
        out = f"output/audio/segments/{name}.mp3"
        print(f"\nSegment: {name}")
        method = generate_segment(text, out, voice=VOICE_NAME,
                                  lang=VOICE_LANG, hf_key=HF_API_KEY)
        methods_used.append(method)
        segment_files.append(out)

    duration = combine_audio(segment_files, "output/audio/final_voiceover.mp3")

    print("\n=== Voice Generation Report ===")
    hf_count = sum(1 for m in methods_used if m.startswith("hf_"))
    gtts_count = methods_used.count("gtts")
    espeak_count = methods_used.count("espeak")

    print(f"HuggingFace Kokoro: {hf_count}/{len(segments)}")
    print(f"gTTS (backup):      {gtts_count}/{len(segments)}")
    print(f"espeak (robotic):   {espeak_count}/{len(segments)}")

    if hf_count == len(segments):
        print(f"\nAll segments natural Kokoro voice!")
    elif hf_count > 0:
        print(f"\nMostly Kokoro, some gTTS fallback")
    else:
        print(f"\nNo Kokoro - check HF_API_KEY secret in GitHub")
