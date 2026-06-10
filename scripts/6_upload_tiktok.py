"""
Step 6: Upload video to TikTok using correct internal API flow
Based on reverse-engineered working endpoints from MiniGlome/Tiktok-uploader
Flow: sessionid → passport/user_id → video upload auth → AWS S3 upload → item/create
"""

import json
import os
import sys
import datetime
import hashlib
import hmac
import requests


def load_video_data():
    with open("output/video_data.json", "r") as f:
        return json.load(f)


def build_description(fruit_name, title, tags):
    hashtags = [
        "GuitarWithFacts", "GuitarFacts",
        fruit_name.replace(" ", ""),
        "DidYouKnow", "LearnOnTikTok",
        "Guitar", "MusicTheory",
        "fyp", "foryoupage",
    ]
    for tag in tags[:5]:
        h = tag.replace(" ", "").replace("-", "")
        if h not in hashtags:
            hashtags.append(h)

    tag_str = " ".join(f"#{h}" for h in hashtags[:15])
    return f"{title}\n\n{tag_str}"[:2200]


# ── AWS Signature v4 helper ──────────────────────────────────────────────────
def sign(key, msg):
    return hmac.new(key, msg.encode("utf-8"), hashlib.sha256).digest()


def get_aws_signature_key(key, date_stamp, region, service):
    k_date    = sign(("AWS4" + key).encode("utf-8"), date_stamp)
    k_region  = sign(k_date, region)
    k_service = sign(k_region, service)
    k_signing = sign(k_service, "aws4_request")
    return k_signing


def aws_sign_request(access_key, secret_key, session_token,
                     method, endpoint, params, payload=b"",
                     service="vod", region="us-east-1"):
    t         = datetime.datetime.utcnow()
    amzdate   = t.strftime("%Y%m%dT%H%M%SZ")
    datestamp = t.strftime("%Y%m%d")

    canonical_uri    = "/"
    canonical_qs     = "&".join(f"{k}={v}" for k, v in sorted(params.items()))
    payload_hash     = hashlib.sha256(payload).hexdigest()
    canonical_headers = (
        f"x-amz-content-sha256:{payload_hash}\n"
        f"x-amz-date:{amzdate}\n"
        f"x-amz-security-token:{session_token}\n"
    )
    signed_headers = "x-amz-content-sha256;x-amz-date;x-amz-security-token"

    canonical_req = "\n".join([
        method, canonical_uri, canonical_qs,
        canonical_headers, signed_headers, payload_hash
    ])

    cred_scope    = f"{datestamp}/{region}/{service}/aws4_request"
    string_to_sign = "\n".join([
        "AWS4-HMAC-SHA256", amzdate, cred_scope,
        hashlib.sha256(canonical_req.encode()).hexdigest()
    ])

    signing_key = get_aws_signature_key(secret_key, datestamp, region, service)
    signature   = hmac.new(signing_key, string_to_sign.encode(), hashlib.sha256).hexdigest()

    authorization = (
        f"AWS4-HMAC-SHA256 Credential={access_key}/{cred_scope}, "
        f"SignedHeaders={signed_headers}, Signature={signature}"
    )

    return {
        "x-amz-date":             amzdate,
        "x-amz-security-token":   session_token,
        "x-amz-content-sha256":   payload_hash,
        "Authorization":          authorization,
    }


# ── Main upload flow ──────────────────────────────────────────────────────────
def upload_to_tiktok(video_path, description, session_id):
    session = requests.Session()
    session.cookies.set("sessionid",    session_id, domain=".tiktok.com")
    session.cookies.set("sessionid_ss", session_id, domain=".tiktok.com")
    session.headers.update({
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        "Referer": "https://www.tiktok.com/upload/",
    })

    # ── Step 1: Visit upload page (establishes session) ───────────────────────
    print("Step 1: Establishing session...")
    r = session.get("https://www.tiktok.com/upload/", timeout=20)
    print(f"  Upload page: {r.status_code}")

    # ── Step 2: Get user_id from passport ────────────────────────────────────
    print("Step 2: Getting user ID...")
    r = session.get(
        "https://www.tiktok.com/passport/web/account/info/",
        timeout=20
    )
    print(f"  Passport: {r.status_code}")

    if r.status_code != 200:
        print(f"  Failed: {r.text[:200]}")
        print("  Likely cause: sessionid expired — get a fresh one")
        return False

    try:
        user_id = r.json()["data"]["user_id_str"]
        print(f"  User ID: {user_id[:8]}...")
    except Exception as e:
        print(f"  Could not get user_id: {e} | Response: {r.text[:200]}")
        return False

    # ── Step 3: Get AWS upload credentials ───────────────────────────────────
    print("Step 3: Getting upload credentials...")
    r = session.get(
        "https://www.tiktok.com/api/v1/video/upload/auth/",
        params={"aid": "1988"},
        timeout=20
    )
    print(f"  Auth: {r.status_code}")

    if r.status_code != 200:
        print(f"  Failed: {r.text[:200]}")
        return False

    try:
        auth_data     = r.json()["video_token_v5"]
        access_key    = auth_data["access_key_id"]
        secret_key    = auth_data["secret_acess_key"]   # Note: TikTok typo "acess"
        session_token = auth_data["session_token"]
        print(f"  AWS credentials obtained!")
    except Exception as e:
        print(f"  Could not parse credentials: {e} | Response: {r.text[:300]}")
        return False

    # ── Step 4: Apply upload (get S3 upload URL) ──────────────────────────────
    print("Step 4: Applying for upload slot...")
    with open(video_path, "rb") as f:
        video_content = f.read()
    file_size = len(video_content)

    apply_params = {
        "Action":    "ApplyUploadInner",
        "FileSize":  str(file_size),
        "FileType":  "video",
        "IsInner":   "1",
        "SpaceName": "tiktok",
        "Version":   "2020-11-19",
        "s":         "zdxefu8qvq8",
    }

    aws_headers = aws_sign_request(
        access_key, secret_key, session_token,
        "GET", "https://vod-us-east-1.bytevcloudapi.com/",
        apply_params, payload=b""
    )

    r = requests.get(
        "https://vod-us-east-1.bytevcloudapi.com/",
        params=apply_params,
        headers=aws_headers,
        timeout=30
    )
    print(f"  Apply upload: {r.status_code}")

    if r.status_code != 200:
        print(f"  Failed: {r.text[:300]}")
        return False

    try:
        apply_data  = r.json()["Result"]["InnerUploadAddress"]["UploadNodes"][0]
        upload_host = apply_data["UploadHost"]
        store_uri   = apply_data["StoreUri"]
        auth_header = apply_data["Auth"]
        oid         = apply_data["Oid"]
        video_id    = r.json()["Result"]["Vid"]
        print(f"  Video ID: {video_id}")
    except Exception as e:
        print(f"  Could not parse apply response: {e} | {r.text[:400]}")
        return False

    # ── Step 5: Upload video to S3 ───────────────────────────────────────────
    print(f"Step 5: Uploading video ({file_size // 1024 // 1024}MB)...")

    upload_params = {
        "Action":    "UploadPart",
        "FileSize":  str(file_size),
        "FileType":  "video",
        "IsInner":   "1",
        "SpaceName": "tiktok",
        "Version":   "2020-11-19",
        "s":         "zdxefu8qvq8",
        "Oid":       oid,
        "PartNumber": "1",
        "UploadID":  video_id,
    }

    aws_upload_headers = aws_sign_request(
        access_key, secret_key, session_token,
        "POST", f"https://{upload_host}/",
        upload_params, payload=video_content
    )
    aws_upload_headers["Content-Type"] = "video/mp4"

    r = requests.post(
        f"https://{upload_host}/",
        params=upload_params,
        headers=aws_upload_headers,
        data=video_content,
        timeout=300
    )
    print(f"  Upload: {r.status_code}")

    if r.status_code != 200:
        print(f"  Failed: {r.text[:300]}")
        return False

    # ── Step 6: Commit upload ─────────────────────────────────────────────────
    print("Step 6: Committing upload...")
    commit_params = {
        "Action":    "CommitUploadInner",
        "SpaceName": "tiktok",
        "Version":   "2020-11-19",
        "s":         "zdxefu8qvq8",
    }
    commit_body = json.dumps({
        "Vid": video_id,
        "Functions": []
    }).encode()

    aws_commit_headers = aws_sign_request(
        access_key, secret_key, session_token,
        "POST", "https://vod-us-east-1.bytevcloudapi.com/",
        commit_params, payload=commit_body
    )
    aws_commit_headers["Content-Type"] = "application/json"

    r = requests.post(
        "https://vod-us-east-1.bytevcloudapi.com/",
        params=commit_params,
        headers=aws_commit_headers,
        data=commit_body,
        timeout=60
    )
    print(f"  Commit: {r.status_code}")

    # ── Step 7: Publish video ─────────────────────────────────────────────────
    print("Step 7: Publishing video...")

    # Build text_extra (hashtag metadata) for description
    text_extra = []
    pos = 0
    for word in description.split():
        if word.startswith("#"):
            tag = word[1:]
            start = description.find(word, pos)
            end = start + len(word)
            text_extra.append({
                "start": start,
                "end": end,
                "user_id": "",
                "type": 1,
                "hashtag_name": tag
            })
            pos = end

    publish_data = {
        "video_id":       video_id,
        "text":           description,
        "text_extra":     text_extra,
        "privacy_level":  "0",     # 0=public, 1=friends, 2=private
        "disable_duet":   False,
        "disable_comment": False,
        "disable_stitch": False,
        "video_editor_info": {},
    }

    r = session.post(
        "https://www.tiktok.com/api/v1/item/create/",
        data=publish_data,
        timeout=30
    )
    print(f"  Publish: {r.status_code}")
    print(f"  Response: {r.text[:300]}")

    try:
        resp = r.json()
        status = resp.get("status_code", -1)
        if status == 0:
            item_id = resp.get("aweme_id", "unknown")
            print(f"\nSUCCESS! Video ID: {item_id}")
            print(f"Check your TikTok profile — it may take 1-2 minutes to appear.")
            return True
        else:
            print(f"\nPublish failed. Status: {status}, Message: {resp.get('status_msg')}")
            return False
    except Exception as e:
        print(f"  Could not parse publish response: {e}")
        return False


def main():
    session_id = os.environ.get("TIKTOK_SESSION_ID", "").strip()

    if not session_id:
        print("ERROR: TIKTOK_SESSION_ID not set in GitHub Secrets!")
        sys.exit(1)

    print(f"Session ID: {session_id[:8]}...{session_id[-4:]}")

    data       = load_video_data()
    fruit      = data["topic"]
    title      = data["title"]
    tags       = data.get("tags", [])
    video_path = "output/final_video.mp4"

    if not os.path.exists(video_path):
        print(f"ERROR: Video not found: {video_path}")
        sys.exit(1)

    description = build_description(fruit, title, tags)

    print(f"\n=== Uploading to TikTok ===")
    print(f"Topic: {fruit}")
    print(f"Caption: {description[:100]}...\n")

    success = upload_to_tiktok(video_path, description, session_id)

    if not success:
        print("\nTikTok upload failed.")
        print("Most common fixes:")
        print("  1. Get a FRESH sessionid from your browser (F12 → Application → Cookies)")
        print("  2. Make sure your TikTok account is verified")
        print("  3. Check if your account has any restrictions")
        print("\nYouTube upload was still successful!")
        sys.exit(0)   # Don't fail the whole workflow


if __name__ == "__main__":
    main()
