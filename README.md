# AutoPost — Full Automation Setup Guide

> **Fully automated faceless YouTube channel. Zero human involvement after setup.**
> Posts 3 videos/week automatically. 100% free. No watermarks. No credit card.

---

## 🛠️ What Gets Built

Every Monday, Wednesday, and Friday at 9AM UTC, this pipeline runs automatically:

```
GitHub Actions (Free)
       ↓
Google Gemini AI  →  Writes script + title + description + tags
       ↓
espeak-ng         →  Converts script to MP3 voiceover (no account needed)
       ↓
Pollinations AI   →  Generates 5 fruit images + thumbnail (no account needed)
       ↓
FFmpeg            →  Assembles MP4 with burned-in English subtitles
       ↓
YouTube API       →  Uploads video with title, description, tags, hashtags
```

---

## 📁 Repository File Structure

```
autopost/
│
├── .github/
│   └── workflows/
│       └── generate_video.yml       ← Scheduler (Mon/Wed/Fri 9AM)
│
├── scripts/
│   ├── 1_generate_script.py         ← Gemini AI writes the script
│   ├── 2_generate_voice.py          ← espeak-ng generates voiceover
│   ├── 3_generate_images.py         ← Pollinations AI generates images
│   ├── 4_assemble_video.py          ← FFmpeg builds MP4 + subtitles
│   └── 5_upload_youtube.py          ← Uploads to YouTube
│
├── list.txt                  ← 100 fruits to cover (pre-filled)
├── done.txt                  ← Auto-updated after each video
└── requirements.txt                 ← Python dependencies
```

---

## 💰 Cost Summary — Everything Free

| Tool | Purpose | Account? | Card? |
|------|---------|----------|-------|
| GitHub Actions | Runs automation | GitHub account | ❌ None |
| Google Gemini API | Script writing | Google account | ❌ None |
| espeak-ng | Voice generation | ❌ None at all | ❌ None |
| Pollinations AI | Image generation | ❌ None at all | ❌ None |
| FFmpeg | Video assembly | ❌ None at all | ❌ None |
| YouTube Data API | Video upload | Google account | ❌ None |

**Total cost: $0 forever.**

---

## 🔑 GitHub Secrets You Need (Only 4)

| Secret Name | Where To Get It |
|-------------|----------------|
| `GEMINI_API_KEY` | aistudio.google.com |
| `YOUTUBE_CLIENT_ID` | Google Cloud Console → Credentials |
| `YOUTUBE_CLIENT_SECRET` | Google Cloud Console → Credentials |
| `YOUTUBE_REFRESH_TOKEN` | One-time OAuth step (see Phase 3) |

---

## 📋 PHASE 1 — Create GitHub Repository (10 min)

### Step 1.1 — Create GitHub Account
1. Go to **github.com**
2. Click **Sign Up** and create your free account

### Step 1.2 — Create New Repository
1. Click **+** icon (top right) → **New repository**
2. Name: `fruits-with-facts`
3. Set to **Private** (protects your API keys)
4. Click **Create repository**

### Step 1.3 — Upload All Files
For each file, click **Add file → Create new file** in your repo:

| File path to type in GitHub | File to copy content from |
|-----------------------------|--------------------------|
| `.github/workflows/generate_video.yml` | generate_video.yml |
| `scripts/1_generate_script.py` | 1_generate_script.py |
| `scripts/2_generate_voice.py` | 2_generate_voice.py |
| `scripts/3_generate_images.py` | 3_generate_images.py |
| `scripts/4_assemble_video.py` | 4_assemble_video.py |
| `scripts/5_upload_youtube.py` | 5_upload_youtube.py |
| `requirements.txt` | requirements.txt |
| `list.txt` | list.txt |
| `done.txt` | Leave completely empty |

> ⚠️ For `.github/workflows/generate_video.yml` — type the full path
> including folders in the filename box. GitHub auto-creates the folders
> as you type the `/` slashes.

After uploading, click the **Actions** tab in your repo.
You should now see **Generate & Upload Fruits Video** listed.
If you don't see it, the workflow file is in the wrong location — recheck the path.

---

## 📋 PHASE 2 — Get Free Gemini API Key (5 min)

1. Go to **aistudio.google.com**
2. Sign in with your **Google account**
3. Click **Get API Key → Create API key**
4. Select your Google Cloud project → Click **Create**
5. Copy the key — it starts with `AIza...`

> ✅ Completely free. No credit card. 1,500 requests/day free tier.

---

## 📋 PHASE 3 — YouTube API Setup (25 min)

This is the most involved phase. Follow each step carefully.

### Step 3.1 — Create Google Cloud Project
1. Go to **console.cloud.google.com**
2. Click **Select a project** (top bar) → **New Project**
3. Name it `FruitsWithFacts` → Click **Create**
4. Make sure this new project is selected in the top bar

### Step 3.2 — Enable YouTube Data API
1. Go to **APIs & Services → Library**
2. Search **YouTube Data API v3**
3. Click it → Click **Enable**

### Step 3.3 — Configure OAuth Consent Screen
1. Go to **APIs & Services → OAuth consent screen**
2. Choose **External** → Click **Create**
3. Fill in:
   - App name: `FruitsWithFacts`
   - User support email: your Gmail
   - Developer contact email: your Gmail
4. Click **Save and Continue**
5. On the **Scopes** page → click **Save and Continue** (skip)
6. On the **Test Users** page:
   - Click **+ Add Users**
   - Enter your Gmail address
   - Click **Add** then **Save and Continue**
7. Click **Back to Dashboard**

### Step 3.4 — Create OAuth Credentials
1. Go to **APIs & Services → Credentials**
2. Click **+ Create Credentials → OAuth client ID**
3. Application type: **Desktop app**
4. Name: `FruitsBot`
5. Click **Create**
6. A popup shows your **Client ID** and **Client Secret** — save both

### Step 3.5 — Get Your Refresh Token

**Open this URL in your browser** (replace `YOUR_CLIENT_ID`):
```
https://accounts.google.com/o/oauth2/v2/auth?client_id=YOUR_CLIENT_ID&redirect_uri=urn:ietf:wg:oauth:2.0:oob&response_type=code&scope=https://www.googleapis.com/auth/youtube.upload+https://www.googleapis.com/auth/youtube&access_type=offline&prompt=consent
```

1. Sign in with your YouTube Google account
2. If you see **"This app isn't verified"** warning:
   - Click **Advanced**
   - Click **Go to FruitsWithFacts (unsafe)**
   - Click **Allow**
3. Copy the **authorization code** shown on screen

**Now exchange the code for a refresh token:**

Go to **reqbin.com/curl** and paste this (replace the 3 values):
```
curl -X POST https://oauth2.googleapis.com/token \
  -d "code=PASTE_AUTH_CODE_HERE" \
  -d "client_id=YOUR_CLIENT_ID" \
  -d "client_secret=YOUR_CLIENT_SECRET" \
  -d "redirect_uri=urn:ietf:wg:oauth:2.0:oob" \
  -d "grant_type=authorization_code"
```

Click **Run**. You'll get a JSON response:
```json
{
  "access_token": "...",
  "refresh_token": "1//0g...",
  "token_type": "Bearer"
}
```

Copy the **refresh_token** value.

> ⚠️ The authorization code expires in a few minutes.
> Complete the curl step immediately after copying the code.

---

## 📋 PHASE 4 — Add Secrets to GitHub (5 min)

1. Go to your GitHub repo
2. Click **Settings → Secrets and variables → Actions**
3. Click **New repository secret** for each of the 4 secrets:

| Name | Value |
|------|-------|
| `GEMINI_API_KEY` | Your `AIza...` key from Phase 2 |
| `YOUTUBE_CLIENT_ID` | From Step 3.4 |
| `YOUTUBE_CLIENT_SECRET` | From Step 3.4 |
| `YOUTUBE_REFRESH_TOKEN` | From Step 3.5 |

> ⚠️ Secret names must be EXACT — capital letters, underscores, no spaces.

---

## 📋 PHASE 5 — Test Your Pipeline (5 min)

1. In your GitHub repo click the **Actions** tab
2. Click **Generate & Upload Fruits Video** in the left sidebar
3. Click **Run workflow → Run workflow** (green button, top right)
4. Watch the live logs — each step should show a green checkmark
5. Check your YouTube channel — the first video appears within minutes!

### What Each Step Does in the Logs
```
Step 1 - Generate Script    → "Next fruit: Apple / Script generated successfully"
Step 2 - Generate Voice     → "All voice segments done!"
Step 3 - Generate Images    → "All 5 images generated!"
Step 4 - Assemble Video     → "Video ready: output/final_video.mp4"
Step 5 - Upload to YouTube  → "SUCCESS! ... is now live on YouTube!"
```

---

## 📅 Automatic Schedule

Once setup is complete, videos post with zero human involvement:

| Day | Time | Action |
|-----|------|--------|
| Monday | 9:00 AM UTC | Auto-generates + uploads video |
| Wednesday | 9:00 AM UTC | Auto-generates + uploads video |
| Friday | 9:00 AM UTC | Auto-generates + uploads video |

**3 videos/week = 12/month = 144/year**
At 3 per week, your 100 pre-loaded fruits cover **33 weeks of content**.

---

## 🔧 Customisation

### Change posting days/frequency
Edit `.github/workflows/generate_video.yml`:
```yaml
- cron: '0 9 * * 1,3,5'    # Mon, Wed, Fri (default)
- cron: '0 9 * * *'         # Every day
- cron: '0 9 * * 1'         # Once a week (Monday only)
```

### Change video voice style
Edit `scripts/2_generate_voice.py`:
```python
"-v", "en-us+f3"    # Female voice (default)
"-v", "en-us+m3"    # Male voice
"-v", "en-gb"       # British accent
"-s", "148"         # Speed (130=slow, 148=normal, 165=fast)
```

### Change subtitle appearance
Edit `scripts/4_assemble_video.py` — find `subtitle_style`:
```python
"FontSize=24"              # Bigger = 28, Smaller = 20
"PrimaryColour=&H00FFFF00" # Yellow text instead of white
"MarginV=50"               # Higher number = higher on screen
```

### Add more fruits
Simply add new lines to `list.txt` in GitHub.
The bot picks them up automatically on the next run.

### Change video privacy
Edit `scripts/5_upload_youtube.py`:
```python
"privacyStatus": "public"    # Live immediately (default)
"privacyStatus": "unlisted"  # Only via direct link
"privacyStatus": "private"   # Only you can see
```

---

## 🆘 Troubleshooting

### ❌ "GEMINI_API_KEY not set"
→ Add the secret in GitHub → Settings → Secrets and variables → Actions

### ❌ "invalid_grant / Bad Request" on YouTube upload
Your refresh token expired. Fix:
1. Go to myaccount.google.com/permissions → remove FruitsWithFacts access
2. Repeat Step 3.5 to get a new authorization code
3. Run the curl command immediately to get a new refresh token
4. Update `YOUTUBE_REFRESH_TOKEN` secret in GitHub
5. Re-run the workflow

### ❌ "This app isn't verified" on Google login
→ Click **Advanced → Go to FruitsWithFacts (unsafe) → Allow**
→ This is safe — you built the app yourself

### ❌ Workflow not showing in Actions tab
→ The `.github/workflows/generate_video.yml` file is missing or misplaced
→ It must be at exactly that path on the main branch

### ❌ "Simple and complex filtering cannot be used together"
→ You have an old version of `4_assemble_video.py`
→ Replace it with the latest version — all filters are now in one filter_complex

### ❌ Images look like plain colour gradients
→ Pollinations AI timed out — the script uses gradient fallback automatically
→ Re-run the workflow; Pollinations usually works on retry

### ❌ All fruits completed
→ Add more fruit names to `list.txt` (one per line)

---

## 🎉 You're Done!

After one-time setup, your channel runs itself forever:

✅ Picks next fruit from list automatically
✅ Writes real educational script with Gemini AI
✅ Generates natural voiceover audio
✅ Creates 5 AI fruit images + YouTube thumbnail
✅ Assembles MP4 with burned-in English subtitles
✅ Uploads with title, description, tags and hashtags
✅ Marks fruit as done, moves to next one

**3 videos per week. Zero effort. Forever. 🚀**
