# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Project Does

Fully automated faceless YouTube Shorts channel ("Guitar with Facts"). Every Monday, Wednesday, and Friday at 9AM UTC, GitHub Actions runs a 5-step Python pipeline that picks the next guitar topic from `list.txt`, generates a script via Gemini AI, synthesises a voiceover, fetches images, assembles an MP4 with burned-in subtitles, and uploads the Short to YouTube. After upload, `done.txt` is committed back to the repo so the bot remembers where it left off.

## Pipeline Steps (run in order)

```
python scripts/1_generate_script.py   # Gemini AI → output/video_data.json
python scripts/2_generate_voice.py    # HF Kokoro / gTTS / espeak → output/audio/
python scripts/3_generate_images.py   # Unsplash API (Pollinations fallback) → output/images/ + thumbnails
python scripts/4_assemble_video.py    # FFmpeg → output/final_video.mp4
python scripts/5_upload_youtube.py    # YouTube Data API v3 → marks topic done
```

Each script reads from the previous step's `output/` directory. Run them sequentially; they don't accept CLI arguments.

## Running Locally

Install system deps (Ubuntu/GitHub Actions environment):
```
sudo apt-get install -y ffmpeg espeak-ng
pip install -r requirements.txt
```

Required environment variables:
| Variable | Used by | Source |
|---|---|---|
| `GEMINI_API_KEY` | step 1 | aistudio.google.com |
| `HF_API_KEY` | step 2 (optional) | huggingface.co — enables Kokoro neural TTS; falls back to gTTS then espeak without it |
| `UNSPLASH_ACCESS_KEY` | step 3 (optional) | unsplash.com/developers — free, 50 req/hour; falls back to Pollinations then gradient |
| `YOUTUBE_CLIENT_ID` | step 5 | Google Cloud Console |
| `YOUTUBE_CLIENT_SECRET` | step 5 | Google Cloud Console |
| `YOUTUBE_REFRESH_TOKEN` | step 5 | One-time OAuth flow |

## Architecture

**`output/` directory** (created at runtime, not committed):
- `video_data.json` — shared data bus between all steps; contains topic name, title, description, tags, voiceover lines, image prompts, colors, and emoji
- `audio/segments/*.mp3` — one file per voiceover segment (hook + 5 facts + outro)
- `audio/final_voiceover.mp3` — concatenated segments with 0.25s silence between each
- `images/scene_N.png` — 5 vertical (1080×1920) guitar images
- `thumbnail_vertical.png` / `thumbnail.jpg` — composed thumbnails (PIL)
- `cards/*.png` — per-segment background frames used in video assembly
- `clips/clip_N.mp4` — animated clips (zoom/pan) before final concat
- `final_video.mp4` — finished Short

**Topic tracking:**
- `list.txt` — ordered list of guitar topics; add new topics here (one per line)
- `done.txt` — auto-appended after each successful upload; the bot skips any topic already in this file

**Voice fallback chain** (step 2): HuggingFace Kokoro-82M → gTTS → espeak-ng

**Image fallback chain** (step 3): Unsplash API → Pollinations AI → coloured gradient PNG

**Gemini model cascade** (step 1): tries `gemini-2.0-flash-lite` → `gemini-2.5-flash-lite` → `gemini-2.0-flash` → `gemini-2.5-flash`; exponential backoff (5s / 15s / 30s) per model before moving on.

**Video assembly** (step 4): Two-pass approach — Pass 1 renders each card as an animated clip (scale/crop, no slow `zoompan`), Pass 2 concatenates clips then adds voiceover + background music + subtitles in a single FFmpeg encode.

## Utility Scripts

- `scripts/2_generate_english_voice.py` — alternate voice generator (English-only variant)
- `scripts/generate_voice_samples.py` — local test tool; generates sample audio for each Kokoro voice so you can pick one
- `scripts/6_upload_tiktok.py` — TikTok upload (exists but commented out in the workflow; requires `TIKTOK_SESSION_ID` secret)

## Key Customisations

**Schedule** — edit cron in `.github/workflows/generate_video.yml`:
```yaml
- cron: '0 9 * * 1,3,5'   # Mon/Wed/Fri (current)
```

**Voice** — edit `VOICE_NAME` in `scripts/2_generate_voice.py` (Kokoro voices: `af_bella`, `am_michael`, `bf_emma`, etc.)

**Subtitle style** — edit `sub_style` dict in `scripts/4_assemble_video.py`

**Upload privacy** — edit `"privacyStatus"` in `scripts/5_upload_youtube.py` (`"public"` / `"unlisted"` / `"private"`)

## GitHub Secrets Required

`GEMINI_API_KEY`, `HF_API_KEY` (optional), `UNSPLASH_ACCESS_KEY` (optional), `YOUTUBE_CLIENT_ID`, `YOUTUBE_CLIENT_SECRET`, `YOUTUBE_REFRESH_TOKEN`

## Common Issues

- **`invalid_grant` on YouTube upload** — refresh token expired; repeat the OAuth flow and update the secret
- **Gradient images instead of guitar photos** — Unsplash key missing or rate-limited (50/hour), and Pollinations timed out; re-run the workflow or add `UNSPLASH_ACCESS_KEY`
- **All topics completed** — add more lines to `list.txt`
- **`GEMINI_API_KEY not set`** — secret missing or misnamed in GitHub repo settings
- **All Gemini models fail** — Gemini is overloaded; the workflow will auto-retry on the next scheduled run
