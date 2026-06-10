# Product Requirements Document — Guitar with Facts

**Channel:** Guitar with Facts (YouTube Shorts + TikTok)
**Purpose:** Fully automated, zero-touch faceless short-form video channel
**Updated:** 2026-06-10

---

## 1. Product Overview

An automated pipeline that publishes educational YouTube Shorts (and optionally TikTok) about guitar chords and techniques — one video per scheduled run — entirely without human intervention. The bot picks the next topic from a list, generates a script with AI, synthesises a voiceover, downloads professional guitar photos, assembles an MP4, and uploads it. After a successful upload it records the topic as done so it is never repeated.

### Target audience
Casual viewers on YouTube Shorts / TikTok interested in quick educational content about guitar, music theory, and chords.

### Success metric
One published Short per scheduled run with zero manual steps required.

---

## 2. Pipeline Architecture

```
list.txt
    │
    ▼
[Step 1] 1_generate_script.py  ──►  output/video_data.json
    │         (Gemini AI)
    ▼
[Step 2] 2_generate_voice.py   ──►  output/audio/final_voiceover.mp3
    │         (HF Kokoro → gTTS → espeak)
    ▼
[Step 3] 3_generate_images.py  ──►  output/images/scene_N.png
    │         (Unsplash → Pollinations → gradient)       output/thumbnail_vertical.png
    ▼                                                     output/thumbnail.jpg
[Step 4] 4_assemble_video.py   ──►  output/final_video.mp4
    │         (FFmpeg two-pass)
    ▼
[Step 5] 5_upload_youtube.py   ──►  YouTube Shorts (public)
    │         (YouTube Data API v3)
    ▼
done.txt  ◄── git commit (marks topic complete)

[Step 6 — optional, not in CI]
         6_upload_tiktok.py    ──►  TikTok (session-cookie auth)
```

### Shared data bus
`output/video_data.json` is the single source of truth passed between steps. Schema:

| Field | Type | Description |
|---|---|---|
| `topic` | string | The guitar topic (e.g. "C Major Chord") |
| `title` | string | YouTube title (≤100 chars, includes #Shorts) |
| `description` | string | 80–100 word video description with hashtags |
| `tags` | string[] | YouTube/TikTok tags |
| `voiceover.hook` | string | Opening hook (≤12 words) |
| `voiceover.fact_1..5` | string | Five educational facts (≤20 words each) |
| `voiceover.outro` | string | CTA / subscribe line |
| `image_prompts` | string[5] | Prompts for visual search / AI gen |
| `colors.primary` | hex | Main brand color for this video |
| `colors.accent` | hex | Highlight / badge color |
| `colors.secondary` | hex | Darker complement for gradients |
| `emoji` | string | Best-fit emoji for the topic |

---

## 3. Step-by-Step Requirements

### Step 1 — Script Generation (`1_generate_script.py`)

**Inputs:** `list.txt`, `done.txt`, `GEMINI_API_KEY`

**Behaviour:**
- Reads `list.txt` and skips lines already in `done.txt`.
- Exits with code 0 (no failure) if all topics are exhausted.
- Calls the Gemini API with a structured JSON prompt; tries 4 models in order of ascending weight (`gemini-2.0-flash-lite` → `gemini-2.5-flash`), with exponential backoff (5 s / 15 s / 30 s) per model and 3 attempts per model.
- Parses the raw response, strips markdown fences, and validates that `description` and `fact_1` are non-empty.
- Writes `output/video_data.json`.

**Prompt structure:** Generates guitar-specific facts — technique, playing tip, history/origin, famous player or song, and a world record or unique use.

---

### Step 2 — Voice Generation (`2_generate_voice.py`)

**Inputs:** `output/video_data.json`, `HF_API_KEY` (optional)

**Voice fallback chain:**
1. HuggingFace Kokoro-82M (`hexgrad/Kokoro-82M`) — near-human quality
2. gTTS (Google Text-to-Speech) — robotic but intelligible
3. espeak-ng — last resort

**Current voice:** `am_michael` (American male, warm narrator)

**Segment order:** hook → fact_1..5 (prefixed "Fact N!") → outro

**Outputs:**
- `output/audio/segments/{name}.mp3` — 7 individual segments
- `output/audio/final_voiceover.mp3` — concatenated with 0.25 s silence between segments

**CI:** `HF_API_KEY` is passed as an env var to Step 2 in `generate_video.yml`; Kokoro will be used when the secret is set.

---

### Step 3 — Image Generation (`3_generate_images.py`)

**Inputs:** `output/video_data.json`, `UNSPLASH_ACCESS_KEY` (optional)

**Image source fallback chain:**
1. Unsplash API (professional photography, portrait orientation, 1080×1920)
2. Pollinations AI (AI-generated, flux model)
3. Gradient PNG (solid colour gradient, always succeeds)

**Search query strategy:** 5 angle-specific queries per topic (e.g. `"{topic} guitar white background"`, `"{topic} guitar close up photography"`, `"guitarist playing {topic} stage"`, etc.) to get diverse scene images.

**Outputs (all 1080×1920 PNG):**
- `output/images/scene_1..5.png` — 5 scene images
- `output/thumbnail_vertical.png` — 1080×1920 YouTube thumbnail
- `output/thumbnail.jpg` — 1280×720 horizontal thumbnail
- `output/image_credits.json` — Unsplash photographer attribution

---

### Step 4 — Video Assembly (`4_assemble_video.py`)

**Inputs:** `output/video_data.json`, `output/audio/`, `output/images/`, `output/thumbnail_vertical.png`

**Two-pass approach:**
- Pass 1: Each card image → animated MP4 clip (zoom-in / zoom-out / pan-left / pan-right) via FFmpeg `scale+crop`. ~3-5× faster than `zoompan` filter.
- Pass 2: Concat clips (stream copy, no re-encode) → single FFmpeg pass adds voiceover + background music + burned-in SRT subtitles.

**Card sequence:**
1. Thumbnail card (1.5 s, static — so YouTube captures a crisp thumbnail frame)
2. Hook card (zoom_out)
3. Fact 1–5 cards (cycling animations: pan_right → zoom_in → pan_left → zoom_out → zoom_in)
4. Outro card (zoom_in, gradient background, no subtitle — text baked in)

**Background music:** Downloads from Pixabay CDN (CC0); on failure, synthesises a C-major soft ambient pad with FFmpeg sine waves. Volume held at 10–12% of voice level.

**Subtitle style:** Bright yellow, bold, 4-word chunks, bottom-center, black outline, ~1 cm from edge.

**Video spec:** 1080×1920, H.264 yuv420p, 24 fps, AAC 192 kbps 44.1 kHz, `+faststart` for streaming.

---

### Step 5 — YouTube Upload (`5_upload_youtube.py`)

**Inputs:** `output/video_data.json`, `output/final_video.mp4`, `output/thumbnail.jpg`
**Auth:** OAuth2 refresh-token flow (`YOUTUBE_CLIENT_ID`, `YOUTUBE_CLIENT_SECRET`, `YOUTUBE_REFRESH_TOKEN`)

**Behaviour:**
- Ensures `#Shorts` is in the title.
- Truncates title to 100 chars.
- Uploads via resumable upload (5 MB chunks), logs progress.
- Sets category 27 (Education), language `en`, `privacyStatus: public`, `madeForKids: false`.
- Uploads horizontal thumbnail after video is live.
- Appends topic to `done.txt`.

**Hashtag list in description:** `GuitarWithFacts`, `GuitarFacts`, `GuitarChords`, `MusicTheory`, `GuitarTips`, `DidYouKnow`, `LearnOnShorts`.

---

### Step 6 — TikTok Upload (`6_upload_tiktok.py`) *(Optional / not in CI)*

**Auth:** Browser `sessionid` cookie (`TIKTOK_SESSION_ID`)

**Upload flow:** 7-step reverse-engineered internal API:
1. Establish session via upload page
2. Resolve `user_id` from passport endpoint
3. Obtain temporary AWS S3 credentials via `/api/v1/video/upload/auth/`
4. Apply for upload slot → get S3 upload URL
5. Upload video binary to S3 (AWS Signature v4 signed)
6. Commit upload
7. Publish via `/api/v1/item/create/`

**Known issues:**
1. Not included in `generate_video.yml` — TikTok uploads never run in CI.
2. Session-cookie auth is fragile; tokens expire frequently.

---

## 4. Automation (GitHub Actions)

**File:** `generate_video.yml`
**Schedule:** `0 9 * * 1,3,5` — Monday, Wednesday, Friday at 09:00 UTC
**Trigger:** Also supports `workflow_dispatch` for manual runs
**Runner:** `ubuntu-latest`, timeout 60 min

**Post-upload git commit:**
```
git add done.txt && git commit -m "Auto: marked topic as done" && git push
```

**Env vars:** Both `HF_API_KEY` (Step 2) and `UNSPLASH_ACCESS_KEY` (Step 3) are wired into their respective workflow steps.

---

## 5. Topic Management

- **`list.txt`** — ordered list of guitar topics; add new chords or techniques here (one per line, `#` to comment).
- **`done.txt`** — auto-appended after each successful upload; bot skips any topic found here.
- **Exhaustion:** Step 1 exits cleanly with `sys.exit(0)` when no topics remain; workflow succeeds without uploading.

---

## 6. Identified Bugs & Inconsistencies

| # | File | Severity | Status | Description |
|---|---|---|---|---|
| 1 | `generate_video.yml` | Medium | ✅ Fixed | `HF_API_KEY` not passed to Step 2 → Kokoro TTS never used in CI |
| 2 | `generate_video.yml` | Low | ✅ Fixed | `UNSPLASH_ACCESS_KEY` not passed to Step 3 → professional photos never fetched in CI |
| 3 | `generate_video.yml` | Low | Open | Step 6 (TikTok) commented out in workflow — not run in CI |

---

## 7. Environment Variables & Secrets

| Secret | Required | Step | Notes |
|---|---|---|---|
| `GEMINI_API_KEY` | Yes | 1 | aistudio.google.com — free tier sufficient |
| `HF_API_KEY` | No | 2 | Enables Kokoro TTS; falls back to gTTS without it |
| `UNSPLASH_ACCESS_KEY` | No | 3 | Enables professional photos; falls back to AI/gradient |
| `YOUTUBE_CLIENT_ID` | Yes | 5 | Google Cloud Console OAuth app |
| `YOUTUBE_CLIENT_SECRET` | Yes | 5 | Google Cloud Console OAuth app |
| `YOUTUBE_REFRESH_TOKEN` | Yes | 5 | One-time OAuth flow; refresh if `invalid_grant` error |
| `TIKTOK_SESSION_ID` | No | 6 | Browser cookie; expires regularly |

---

## 8. Dependencies

```
requests==2.31.0
Pillow==10.3.0
gTTS==2.5.4
```

System: `ffmpeg`, `espeak-ng` (installed in CI via `apt-get`)

---

## 9. Output Directory Layout

```
output/
├── video_data.json            # Shared data bus
├── audio/
│   ├── segments/
│   │   ├── hook.mp3
│   │   ├── fact_1..5.mp3
│   │   └── outro.mp3
│   ├── silence.mp3
│   ├── final_voiceover.mp3
│   ├── voiceover_with_intro.mp3
│   ├── background_music.mp3
│   └── background_trimmed.mp3
├── images/
│   ├── scene_1..5.png         # 1080×1920 scene images
├── cards/
│   ├── hook.png
│   ├── fact_1..5.png
│   └── outro.png
├── clips/
│   ├── clip_0..N.mp4          # Per-card animated clips
│   ├── concat.txt
│   └── concat_video.mp4       # Intermediate (no audio)
├── subtitles.srt
├── thumbnail_vertical.png     # 1080×1920
├── thumbnail.jpg              # 1280×720
├── image_credits.json
└── final_video.mp4            # ← published to YouTube
```

---

## 10. Roadmap / Recommended Next Steps

1. ~~**Wire missing env vars in CI** (Bugs #1–2)~~ — Done. `HF_API_KEY` and `UNSPLASH_ACCESS_KEY` are now wired into the workflow.
2. **Add TikTok to CI** (Bug #3): Add Step 6 to the workflow (non-blocking — already exits 0 on failure so YouTube upload is never skipped).
3. **Unsplash attribution compliance**: Unsplash requires crediting the photographer. Consider appending attribution from `image_credits.json` to the YouTube video description.
4. **TikTok auth improvement**: Replace session-cookie auth with the official TikTok Creator API for more reliable, non-expiring uploads.
