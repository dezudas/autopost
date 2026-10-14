"""
Step 5: Upload YouTube Short with proper Shorts metadata
Adds #Shorts to title, sets vertical format flags
"""

import json
import os
import requests
import time


def load_video_data():
    with open("output/video_data.json", "r") as f:
        return json.load(f)


def get_access_token():
    client_id = os.environ.get("YOUTUBE_CLIENT_ID")
    client_secret = os.environ.get("YOUTUBE_CLIENT_SECRET")
    refresh_token = os.environ.get("YOUTUBE_REFRESH_TOKEN")

    missing = [k for k, v in [
        ("YOUTUBE_CLIENT_ID", client_id),
        ("YOUTUBE_CLIENT_SECRET", client_secret),
        ("YOUTUBE_REFRESH_TOKEN", refresh_token)
    ] if not v]
    if missing:
        raise ValueError(f"Missing required YouTube secrets: {', '.join(missing)}")

    client_id = client_id.strip()
    client_secret = client_secret.strip()
    refresh_token = refresh_token.strip()

    r = requests.post("https://oauth2.googleapis.com/token", data={
        "client_id":     client_id,
        "client_secret": client_secret,
        "refresh_token": refresh_token,
        "grant_type":    "refresh_token"
    }, timeout=30)
    data = r.json()
    if "access_token" not in data:
        if data.get("error") == "invalid_grant":
            raise Exception(
                f"Token error: invalid_grant ({data}).\n"
                "Your YOUTUBE_REFRESH_TOKEN is invalid, expired, or revoked.\n"
                "Common causes:\n"
                "1. In Google Cloud Console, your OAuth consent screen is set to 'Testing' status. "
                "Tokens in Testing status expire after 7 days! Switch it to 'In production' (Publish App).\n"
                "2. The token expired due to 6 months of inactivity or password change.\n"
                "To fix: Run 'python scripts/get_youtube_token.py' locally to generate a fresh token, "
                "then update the YOUTUBE_REFRESH_TOKEN secret in GitHub."
            )
        raise Exception(f"Token error: {data}")
    print("Access token ready")
    return data["access_token"]


def build_description(topic, raw_desc, tags):
    lines = [l for l in raw_desc.strip().split("\n") if not l.strip().startswith("#")]
    clean = "\n".join(lines).strip()

    hashtags = [
        "Shorts", "GuitarWithFacts", topic.replace(" ",""),
        "GuitarFacts", "DidYouKnow", "GuitarChords",
        "MusicTheory", "GuitarTips", "Educational", "LearnOnShorts"
    ]
    for tag in tags[:5]:
        h = tag.replace(" ","").replace("-","")
        if h not in hashtags:
            hashtags.append(h)

    return f"{clean}\n\n" + " ".join(f"#{h}" for h in hashtags[:15])


def get_resume_offset(upload_url, token, size):
    """Query current byte offset from YouTube for interrupted uploads."""
    try:
        r = requests.put(
            upload_url,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Range": f"bytes */{size}"
            },
            timeout=30
        )
        if r.status_code == 308:
            range_hdr = r.headers.get("Range")
            if range_hdr:
                # Format: "bytes=0-12345"
                return int(range_hdr.split("-")[1]) + 1
        elif r.status_code in [200, 201]:
            return size
    except Exception as e:
        print(f"  Warning: Failed to query resume offset: {e}")
    return None


def upload_video(token, title, description, tags):
    path = "output/final_video.mp4"
    size = os.path.getsize(path)

    # Ensure #Shorts is in title (required for YouTube Shorts)
    if "#Shorts" not in title and "#shorts" not in title:
        title = title + " #Shorts"

    # Truncate title to 100 chars
    title = title[:100]

    print(f"Uploading: {title}")
    print(f"Size: {size/1024/1024:.1f} MB")

    meta = {
        "snippet": {
            "title":       title,
            "description": description,
            "tags":        tags + ["Shorts", "YouTubeShorts"],
            "categoryId":  "27",
            "defaultLanguage":      "en",
            "defaultAudioLanguage": "en"
        },
        "status": {
            "privacyStatus":           "public",
            "selfDeclaredMadeForKids": False,
            "madeForKids":             False
        }
    }

    init = requests.post(
        "https://www.googleapis.com/upload/youtube/v3/videos"
        "?uploadType=resumable&part=snippet,status",
        headers={
            "Authorization":           f"Bearer {token}",
            "Content-Type":            "application/json",
            "X-Upload-Content-Type":   "video/mp4",
            "X-Upload-Content-Length": str(size)
        },
        json=meta
    )
    if init.status_code != 200:
        raise Exception(f"Init failed {init.status_code}: {init.text}")

    upload_url = init.headers["Location"]
    chunk_size = 5 * 1024 * 1024
    uploaded, video_id = 0, None

    with open(path, "rb") as f:
        while uploaded < size:
            f.seek(uploaded)
            chunk = f.read(chunk_size)
            end   = uploaded + len(chunk) - 1

            r = None
            backoffs = [2, 5, 10]
            for attempt, wait in enumerate([0] + backoffs):
                if wait:
                    print(f"\n  Chunk retry in {wait}s...", end="", flush=True)
                    time.sleep(wait)
                    # Check if server received bytes before replaying chunk
                    current_server_offset = get_resume_offset(upload_url, token, size)
                    if current_server_offset is not None and current_server_offset > uploaded:
                        uploaded = current_server_offset
                        f.seek(uploaded)
                        chunk = f.read(chunk_size)
                        end = uploaded + len(chunk) - 1

                try:
                    r = requests.put(
                        upload_url,
                        headers={
                            "Authorization": f"Bearer {token}",
                            "Content-Type":  "video/mp4",
                            "Content-Range": f"bytes {uploaded}-{end}/{size}"
                        },
                        data=chunk,
                        timeout=120
                    )
                except requests.exceptions.RequestException as e:
                    print(f"\n  Chunk network error: {e}")
                    r = None
                    continue
                if r.status_code in [200, 201, 308] or r.status_code < 500:
                    break

            if r is None:
                raise Exception("Chunk failed: no response after retries (network error)")

            if r.status_code in [200, 201]:
                video_id = r.json().get("id")
                print(f"\nUploaded! Video ID: {video_id}")
                break
            elif r.status_code == 308:
                uploaded = end + 1
                print(f"\rUploading: {uploaded/size*100:.1f}%", end="", flush=True)
            else:
                raise Exception(f"Chunk failed: {r.status_code} {r.text[:200]}")

    return video_id


def upload_thumbnail(token, video_id):
    path = "output/thumbnail.jpg"
    if not os.path.exists(path):
        return
    with open(path, "rb") as f:
        r = requests.post(
            f"https://www.googleapis.com/upload/youtube/v3/thumbnails/set"
            f"?videoId={video_id}&uploadType=media",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "image/jpeg"},
            data=f.read()
        )
    print("Thumbnail uploaded!" if r.status_code == 200
          else f"Thumbnail status: {r.status_code}")


def mark_done(topic):
    content = ""
    if os.path.exists("done.txt"):
        with open("done.txt", "r") as f:
            content = f.read()
    prefix = "" if not content or content.endswith("\n") else "\n"
    with open("done.txt", "a") as f:
        f.write(f"{prefix}{topic}\n")
    print(f"Marked done: {topic}")


if __name__ == "__main__":
    data   = load_video_data()
    topic  = data["topic"]
    title  = data["title"]
    tags   = data["tags"]
    desc   = build_description(topic, data["description"], tags)

    print(f"Uploading Short for: {topic}")

    token    = get_access_token()
    video_id = upload_video(token, title, desc, tags)

    if video_id:
        print(f"URL: https://www.youtube.com/shorts/{video_id}")
        time.sleep(5)
        upload_thumbnail(token, video_id)
        mark_done(topic)
        print(f"\nSUCCESS! '{title}' is live as a YouTube Short!")
    else:
        raise Exception("No video ID returned")
