
"""
Generates sample audio for ALL free natural voices.
Download the artifact and listen to pick your favorite!
"""

import asyncio
import os
import edge_tts

# Same sample text for fair comparison
SAMPLE_TEXT = (
    "Welcome to Fruits with Facts! Today we are exploring the amazing mango. "
    "Fact one! Mangoes are the national fruit of India, Pakistan, and the Philippines. "
    "Fact two! A single mango tree can produce fruit for over 300 years. "
    "Like and subscribe for more fruity facts!"
)

# Top 20 most natural-sounding free Edge TTS voices
VOICES = [
    # === ENGLISH (US) FEMALE ===
    ("en-US-AriaNeural",    "US-Female-Aria",         "Friendly, warm, news-style"),
    ("en-US-JennyNeural",   "US-Female-Jenny",        "Energetic, conversational"),
    ("en-US-MichelleNeural","US-Female-Michelle",     "Calm, professional"),
    ("en-US-EmmaNeural",    "US-Female-Emma",         "Bright, youthful"),
    ("en-US-AnaNeural",     "US-Female-Ana",          "Cheerful, child-like"),

    # === ENGLISH (US) MALE ===
    ("en-US-GuyNeural",     "US-Male-Guy",            "Confident, neutral"),
    ("en-US-DavisNeural",   "US-Male-Davis",          "Deep, mature"),
    ("en-US-TonyNeural",    "US-Male-Tony",           "Casual, friendly"),
    ("en-US-AndrewNeural",  "US-Male-Andrew",         "Conversational, warm"),
    ("en-US-BrianNeural",   "US-Male-Brian",          "Clear, professional"),

    # === ENGLISH (UK) ===
    ("en-GB-SoniaNeural",   "UK-Female-Sonia",        "British accent, polished"),
    ("en-GB-LibbyNeural",   "UK-Female-Libby",        "British, soft"),
    ("en-GB-RyanNeural",    "UK-Male-Ryan",           "British male, classy"),

    # === ENGLISH (AU/IN) ===
    ("en-AU-NatashaNeural", "AU-Female-Natasha",      "Australian female"),
    ("en-IN-NeerjaNeural",  "IN-Female-Neerja",       "Indian English female"),
    ("en-IN-PrabhatNeural", "IN-Male-Prabhat",        "Indian English male"),

    # === MULTILINGUAL FRIENDLY ===
    ("en-US-AvaMultilingualNeural",   "US-Female-Ava-Multi",    "Newest, very natural"),
    ("en-US-AndrewMultilingualNeural","US-Male-Andrew-Multi",   "Newest male, very natural"),
    ("en-US-EmmaMultilingualNeural",  "US-Female-Emma-Multi",   "Bright multilingual"),
    ("en-US-BrianMultilingualNeural", "US-Male-Brian-Multi",    "Pro multilingual male"),
]


async def generate_sample(voice_id, label, description):
    output_dir = "voice_samples"
    os.makedirs(output_dir, exist_ok=True)
    output_path = f"{output_dir}/{label}.mp3"

    try:
        tts = edge_tts.Communicate(
            text=SAMPLE_TEXT,
            voice=voice_id,
            rate="+15%",
            volume="+10%",
            pitch="+5Hz"
        )
        await tts.save(output_path)
        print(f"OK   {label} ({description})")
        return True
    except Exception as e:
        print(f"FAIL {label}: {e}")
        return False


async def main():
    print(f"Generating {len(VOICES)} voice samples...\n")
    print(f"Sample text: {SAMPLE_TEXT[:80]}...\n")

    for voice_id, label, description in VOICES:
        await generate_sample(voice_id, label, description)

    # Create a guide document
    with open("voice_samples/_GUIDE.txt", "w") as f:
        f.write("=" * 60 + "\n")
        f.write("VOICE SAMPLES — Guitar with Facts\n")
        f.write("=" * 60 + "\n\n")
        f.write("Listen to each MP3 file and pick your favorite!\n\n")
        f.write("Tell Claude the voice ID you want, e.g.:\n")
        f.write('"Use en-US-JennyNeural"\n\n')
        f.write("=" * 60 + "\n")
        f.write("VOICE LIST:\n")
        f.write("=" * 60 + "\n\n")
        for voice_id, label, description in VOICES:
            f.write(f"File: {label}.mp3\n")
            f.write(f"  Voice ID: {voice_id}\n")
            f.write(f"  Style:    {description}\n\n")

    print(f"\nDone! {len(VOICES)} samples generated in voice_samples/")
    print("Download the artifact from GitHub Actions to listen.")


if __name__ == "__main__":
    asyncio.run(main())
