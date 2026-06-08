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
    r = requests.post("https://oauth2.googleapis.com/token", data={
        "client_id":     os.environ["YOUTUBE_CLIENT_ID"],
        "client_secret": os.environ["YOUTUBE_CLIENT_SECRET"],
        "refresh_token": os.environ["YOUTUBE_REFRESH_TOKEN"],
        "grant_type":    "refresh_token"
    })
    data = r.json()
    if "access_token" not in data:
        raise Exception(f"Token error: {data}")
    print("Access token ready")
    return data["access_token"]


def build_description(fruit_name, raw_desc, tags):
    lines = [l for l in raw_desc.strip().split("\n") if not l.strip().startswith("#")]
    clean = "\n".join(lines).strip()

    hashtags = [
        "Shorts", "GuitarWithFacts", fruit_name.replace(" ",""),
        "GuitarFacts", "DidYouKnow", "GuitarChords",
        "MusicTheory", "GuitarTips", "Educational", "LearnOnShorts"
    ]
    for tag in tags[:5]:
        h = tag.replace(" ","").replace("-","")
        if h not in hashtags:
            hashtags.append(h)

    return f"{clean}\n\n" + " ".join(f"#{h}" for h in hashtags[:15])


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
            chunk = f.read(chunk_size)
            end   = uploaded + len(chunk) - 1
            r = requests.put(
                upload_url,
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type":  "video/mp4",
                    "Content-Range": f"bytes {uploaded}-{end}/{size}"
                },
                data=chunk
            )
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
          else f"Thumbnail failed: {r.status_code}")


def mark_done(fruit):
    with open("done.txt", "a") as f:
        f.write(f"{fruit}\n")
    print(f"Marked done: {fruit}")


if __name__ == "__main__":
    data   = load_video_data()
    fruit  = data["topic"]
    title  = data["title"]
    tags   = data["tags"]
    desc   = build_description(fruit, data["description"], tags)

    print(f"Uploading Short for: {fruit}")

    token    = get_access_token()
    video_id = upload_video(token, title, desc, tags)

    if video_id:
        print(f"URL: https://www.youtube.com/shorts/{video_id}")
        time.sleep(5)
        upload_thumbnail(token, video_id)
        mark_done(fruit)
        print(f"\nSUCCESS! '{title}' is live as a YouTube Short!")
    else:
        raise Exception("No video ID returned")
