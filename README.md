# Guitar with Facts — Automation Setup Guide

> **Fully automated faceless YouTube Shorts channel about guitar chords, theory, and techniques.**
> Posts 3 videos/week automatically with zero manual steps. 100% free options available.

---

## 🛠️ Pipeline Architecture

Every Monday, Wednesday, and Friday at 9AM UTC (or via manual workflow dispatch), this pipeline runs automatically:

```
GitHub Actions (Ubuntu Runner)
       ↓
[Step 1] Google Gemini AI     →  Writes structured JSON script (title, description, tags, facts)
       ↓
[Step 2] Hugging Face Kokoro  →  High-quality neural voiceover (fallback: gTTS → espeak-ng)
       ↓
[Step 3] Unsplash API         →  Downloads 1080×1920 guitar photos (fallback: Pollinations AI)
       ↓
[Step 4] FFmpeg (Two-Pass)    →  Pass 1: Clip animation (pan/zoom) → Pass 2: Audio mix & burnt-in yellow subtitles
       ↓
[Step 5] YouTube API          →  Uploads Short with category, hashtags, and thumbnail
       ↓
GitHub Actions Commit         →  Appends topic to done.txt and pushes to repository
```

---

## 📁 Repository Structure

```
autopost/
│
├── .github/
│   └── workflows/
│       └── generate_video.yml       ← Automation workflow (Mon/Wed/Fri 9AM UTC)
│
├── assets/
│   └── fonts/                       ← Montserrat and Inter typography
│
├── scripts/
│   ├── 1_generate_script.py         ← Gemini AI script generator
│   ├── 2_generate_voice.py          ← Kokoro neural voice generator (gTTS / espeak backup)
│   ├── 3_generate_images.py         ← Unsplash guitar image fetcher + thumbnail generator
│   ├── 4_assemble_video.py          ← FFmpeg two-pass animation, audio mix, and subtitles
│   ├── 5_upload_youtube.py          ← Resumable YouTube Shorts uploader
│   └── 6_upload_tiktok.py           ← TikTok uploader (optional)
│
├── list.txt                         ← List of guitar chords, scales, and techniques to cover
├── done.txt                         ← Tracks completed topics to prevent repeats
├── requirements.txt                 ← Python dependencies
├── PRD.md                           ← Product Requirements Document
└── CLAUDE.md                        ← Developer guidelines
```

---

## 🔑 GitHub Secrets Setup

Configure these secrets in **Repository Settings → Secrets and variables → Actions**:

| Secret Name | Required? | Step | Description |
|---|---|---|---|
| `GEMINI_API_KEY` | **Yes** | 1 | Google Gemini API key from [aistudio.google.com](https://aistudio.google.com) |
| `YOUTUBE_CLIENT_ID` | **Yes** | 5 | Google Cloud Console OAuth 2.0 Client ID |
| `YOUTUBE_CLIENT_SECRET` | **Yes** | 5 | Google Cloud Console OAuth 2.0 Client Secret |
| `YOUTUBE_REFRESH_TOKEN` | **Yes** | 5 | Google OAuth refresh token for YouTube Data API v3 |
| `HF_API_KEY` | Optional | 2 | Hugging Face token for Kokoro-82M neural TTS (falls back to gTTS) |
| `UNSPLASH_ACCESS_KEY` | Optional | 3 | Unsplash API Access Key (50 req/hr free tier; falls back to AI) |
| `EMAIL_ADDRESS` | Optional | CI | Git commit author email (defaults to GitHub Actions Bot if omitted) |
| `TIKTOK_SESSION_ID` | Optional | 6 | TikTok browser session cookie for optional TikTok uploads |

---

## 📋 One-Time Setup Walkthrough

### 1. Google Gemini AI Key
1. Go to [aistudio.google.com](https://aistudio.google.com).
2. Sign in with your Google account.
3. Click **Get API key → Create API key**.
4. Add the key as `GEMINI_API_KEY` in GitHub Secrets.

### 2. YouTube Data API Setup
1. Open [console.cloud.google.com](https://console.cloud.google.com).
2. Create a new project (e.g., `GuitarWithFacts`).
3. Enable **YouTube Data API v3** in **APIs & Services → Library**.
4. Configure the **OAuth Consent Screen**:
   - User Type: **External**
   - App Name: `GuitarWithFacts`
   - **Important:** Click **"Publish App"** to set the publishing status to **"In production"**. (If left in "Testing" mode, Google will invalidate your refresh token every 7 days, causing `invalid_grant` errors!).
5. Create Credentials:
   - Go to **APIs & Services → Credentials → Create Credentials → OAuth Client ID**.
   - Application Type: **Desktop App**.
   - Copy the generated **Client ID** and **Client Secret**.
6. Generate Refresh Token:
   - Run the included token generator helper script locally:
     ```bash
     python scripts/get_youtube_token.py
     ```
   - Enter your Client ID and Client Secret when prompted.
   - It will open a browser window for you to log in and authorize.
   - The script will output your `YOUTUBE_REFRESH_TOKEN`.
7. Save `YOUTUBE_CLIENT_ID`, `YOUTUBE_CLIENT_SECRET`, and `YOUTUBE_REFRESH_TOKEN` to GitHub Secrets (**Settings → Secrets and variables → Actions**).

### 3. Optional: High-Quality Voice & Photos
- **Hugging Face (`HF_API_KEY`):** Sign up free at [huggingface.co](https://huggingface.co/settings/tokens) and create an Access Token with read permissions. This enables Kokoro-82M neural voiceover.
- **Unsplash (`UNSPLASH_ACCESS_KEY`):** Register a developer app at [unsplash.com/developers](https://unsplash.com/developers) to fetch professional 1080×1920 guitar photography.

---

## 📅 Schedule & Operation

- **Runs automatically:** Mondays, Wednesdays, and Fridays at 09:00 UTC.
- **Manual Trigger:** In GitHub under **Actions → Generate & Upload Guitar Short → Run workflow**.
- **Topic Queue:** Add topics to `list.txt` (one per line). The bot automatically pulls the next unfinished topic.
- **Topic Exhaustion:** When all topics are completed, Step 1 exits cleanly without running unnecessary downstream steps.

---

## 🆘 Troubleshooting

- **`invalid_grant` during upload:** Your refresh token has expired or was revoked. This commonly happens if the Google Cloud OAuth Consent Screen is in "Testing" mode (which automatically expires tokens after 7 days) or after 6 months of inactivity. Set your Consent Screen to "In production", run `python scripts/get_youtube_token.py` to get a fresh token, and update `YOUTUBE_REFRESH_TOKEN` in GitHub Secrets.
- **White subtitles / audio cut off:** Ensure you have the latest `scripts/4_assemble_video.py` which synchronizes segment silences and renders yellow high-contrast captions.
- **Missing photos:** If `UNSPLASH_ACCESS_KEY` is not provided or rate limited, the pipeline automatically falls back to Pollinations AI and branded background cards.
