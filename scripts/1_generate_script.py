"""
Step 1: Generate YouTube Shorts script using Google Gemini
Smart retry: tries lightest models first, exponential backoff
"""

import json
import os
import sys
import time
import random
import requests


def set_github_output(key, value):
    if "GITHUB_OUTPUT" in os.environ:
        try:
            with open(os.environ["GITHUB_OUTPUT"], "a") as f:
                f.write(f"{key}={value}\n")
        except Exception as e:
            print(f"Warning: Failed to write to GITHUB_OUTPUT: {e}")


def get_next_topic():
    with open("list.txt", "r") as f:
        all_topics = [l.strip() for l in f if l.strip() and not l.startswith("#")]
    done = []
    if os.path.exists("done.txt"):
        with open("done.txt", "r") as f:
            done = [l.strip() for l in f if l.strip() and not l.startswith("#")]
    remaining = [t for t in all_topics if t not in done]
    if not remaining:
        print("All topics completed!")
        set_github_output("has_topic", "false")
        return None
    print(f"Next topic: {remaining[0]}")
    set_github_output("has_topic", "true")
    set_github_output("topic", remaining[0])
    return remaining[0]


def build_prompt(topic_name):
    return f"""You are an elite guitar instructor and creator for the "Guitar with Facts" channel.

Create an engaging, modern, elegant, and highly educational 60-second YouTube Shorts script about: {topic_name}
Tone: Modern, sleek, authoritative, engaging (like Vox or MasterClass for musicians).

Return ONLY raw valid JSON, no markdown, no backticks:

{{
  "topic": "{topic_name}",
  "title": "Master {topic_name} in 60 Seconds #GuitarTips #Shorts",
  "description": "Essential breakdown of {topic_name}: chord notes, fret tab, fingering tips, and iconic songs. Follow Guitar with Facts for daily guitar tips!",
  "tags": ["{topic_name}", "guitar lesson", "guitar tutorial", "guitar chords", "music theory", "guitar tips", "guitar with facts", "shorts", "learn guitar"],
  "specs": {{
    "notes": "A • C • E",
    "tab": "X 0 2 2 1 0",
    "formula": "Root • Flat 3rd • 5th",
    "difficulty": "Beginner / Intermediate"
  }},
  "facts": [
    {{
      "badge": "01 / CHORD FORMULA",
      "headline": "The Triad Anatomy",
      "box_title": "NOTES & INTERVALS",
      "box_content": "A (Root) • C (♭3) • E (5th)"
    }},
    {{
      "badge": "02 / FRET TAB & FINGERS",
      "headline": "Exact Hand Positioning",
      "box_title": "TAB & FINGERING",
      "box_content": "Tab: X 0 2 2 1 0 | Fingers: 2, 3, 1"
    }},
    {{
      "badge": "03 / GOLDEN PRO TIP",
      "headline": "Keep High E Ringing",
      "box_title": "CRITICAL TECHNIQUE",
      "box_content": "Arch index finger to prevent muting string 1"
    }},
    {{
      "badge": "04 / ICONIC SONGS",
      "headline": "Legendary Guitar Hits",
      "box_title": "HEARD IN TRACKS",
      "box_content": "Stairway to Heaven • House of the Rising Sun"
    }},
    {{
      "badge": "05 / SECRET VARIATION",
      "headline": "Instant Lush Am7 Voicing",
      "box_title": "PRO COLOR CHORD",
      "box_content": "Lift ring finger for an open, airy Am7"
    }}
  ],
  "voiceover": {{
    "hook": "Here is everything you need to master {topic_name} in 60 seconds.",
    "fact_1": "Explain the notes, formula, and the distinctive musical vibe of {topic_name} (max 20 words).",
    "fact_2": "Give exact string-by-string fingering and fret positions clearly (max 20 words).",
    "fact_3": "Reveal the #1 physical technique mistake beginners make and how to fix it (max 20 words).",
    "fact_4": "Name famous songs or legendary guitarists who made this chord iconic (max 20 words).",
    "fact_5": "Share an advanced variation, movable shape, or secret voicing (max 20 words).",
    "outro": "Save this Short for your guitar practice, and subscribe to Guitar with Facts for daily tips!"
  }}
}}

Write REAL, accurate guitar theory and facts tailored to {topic_name}. Output valid standard JSON only: do not use raw unescaped newlines or unescaped quotes within string values."""


def get_available_models(api_key):
    """Query Google API for active generateContent models supported by this key."""
    try:
        url = "https://generativelanguage.googleapis.com/v1beta/models"
        r = requests.get(
            url,
            headers={"x-goog-api-key": api_key},
            params={"key": api_key},
            timeout=15
        )
        if r.status_code == 200:
            data = r.json()
            models = []
            for item in data.get("models", []):
                methods = item.get("supportedGenerationMethods", [])
                if "generateContent" in methods:
                    name = item.get("name", "").replace("models/", "")
                    models.append(name)
            if models:
                # Prefer fast, lightweight Flash models first
                priority = [
                    "gemini-2.5-flash",
                    "gemini-2.5-flash-lite",
                    "gemini-2.0-flash",
                    "gemini-2.0-flash-lite",
                    "gemini-2.5-pro",
                ]
                sorted_models = [m for m in priority if m in models]
                for m in models:
                    if m not in sorted_models and "gemini" in m:
                        sorted_models.append(m)
                print(f"Discovered active models: {', '.join(sorted_models[:5])}")
                return sorted_models
        else:
            print(f"Model discovery note: HTTP {r.status_code} ({r.text[:120]})")
    except Exception as e:
        print(f"Model discovery note: {e}")
    return None


def call_gemini(prompt, api_key):
    """
    Try active, supported models: 2.5 Flash -> 2.5 Flash Lite -> 2.0 Flash -> 2.5 Pro.
    Smart backoff: 5s, 15s, 30s between retries.
    """
    api_key = api_key.strip()
    models = get_available_models(api_key)
    if not models:
        models = [
            "gemini-2.5-flash",
            "gemini-2.5-flash-lite",
            "gemini-2.0-flash",
            "gemini-2.0-flash-lite",
            "gemini-2.5-pro",
        ]

    last_error = None
    total_attempts = 0

    for model in models:
        url = (
            "https://generativelanguage.googleapis.com/v1beta/"
            f"models/{model}:generateContent?key={api_key}"
        )
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": 0.4,
                "maxOutputTokens": 4096,
                "topP": 0.9,
                "responseMimeType": "application/json"
            }
        }

        print(f"\nTrying: {model}")

        for attempt in range(3):
            total_attempts += 1
            try:
                print(f"  Attempt {attempt+1}/3...", end=" ", flush=True)
                r = requests.post(
                    url,
                    headers={"x-goog-api-key": api_key, "Content-Type": "application/json"},
                    json=payload,
                    timeout=45
                )

                if r.status_code == 200:
                    try:
                        data = parse_response(r.json())
                        print("SUCCESS!")
                        return data
                    except Exception as parse_err:
                        print(f"JSON parse error on {model} attempt {attempt+1}: {parse_err}")
                        last_error = f"JSON parse error on {model}: {parse_err}"
                        time.sleep(3)
                        continue

                err = r.text.lower()
                print(f"HTTP {r.status_code}")

                if r.status_code == 401 or "api_key_invalid" in err:
                    raise Exception(f"Invalid GEMINI_API_KEY — check GitHub Secret! Response: {r.text[:200]}")

                if r.status_code == 404:
                    print(f"  Model unavailable ({r.text[:100]}), trying next...")
                    last_error = f"{model} not found ({r.text[:80]})"
                    break

                if r.status_code in [429, 503] or \
                   any(x in err for x in ["quota", "overload", "demand", "busy"]):
                    waits = [5, 15, 30]
                    wait = waits[min(attempt, 2)] + random.uniform(0, 3)
                    print(f"  Busy — waiting {wait:.0f}s...")
                    time.sleep(wait)
                    last_error = f"Rate limit on {model}"
                    continue

                print(f"  Error: {r.text[:100]}")
                last_error = r.text[:100]
                time.sleep(3)

            except requests.exceptions.Timeout:
                print("Timeout")
                time.sleep(5)
                last_error = "timeout"
            except requests.exceptions.ConnectionError:
                print("Connection error")
                time.sleep(10)
                last_error = "connection error"
            except Exception as e:
                if "GEMINI_API_KEY" in str(e):
                    raise
                print(f"Exception: {e}")
                last_error = str(e)
                time.sleep(5)

    raise Exception(
        f"All models failed after {total_attempts} attempts. "
        f"Last error: {last_error}. "
        "Gemini is overloaded — will auto-retry next scheduled run."
    )


def parse_response(result):
    candidates = result.get("candidates", [])
    if not candidates:
        raise ValueError(f"No candidates in Gemini response: {result}")
    candidate = candidates[0]
    finish_reason = candidate.get("finishReason", "UNKNOWN")
    parts = candidate.get("content", {}).get("parts", [])
    if not parts:
        raise ValueError(f"No content parts returned (finishReason: {finish_reason})")
    raw = parts[0].get("text", "").strip()

    if "```" in raw:
        parts_split = raw.split("```")
        for part in parts_split:
            cleaned = part.strip().lstrip("json").strip()
            if cleaned.startswith("{"):
                raw = cleaned
                break

    start, end = raw.find("{"), raw.rfind("}") + 1
    if start != -1 and end > start:
        raw = raw[start:end]

    try:
        return json.loads(raw, strict=False)
    except Exception:
        # Fallback: clean any literal unescaped newlines inside string values
        import re
        sanitized = re.sub(r'[\r\n]+', ' ', raw)
        return json.loads(sanitized, strict=False)


def generate_script(topic_name):
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY not set in GitHub Secrets!")
    prompt = build_prompt(topic_name)
    data = call_gemini(prompt, api_key)
    assert len(data.get("description", "")) > 20, "Description too short"
    assert len(data.get("voiceover", {}).get("fact_1", "")) > 10, "Fact 1 missing"
    print(f"\nScript generated for: {topic_name}")
    return data


def save_output(data):
    os.makedirs("output", exist_ok=True)
    with open("output/video_data.json", "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"Title: {data.get('title')}")
    print(f"Hook:  {data.get('voiceover', {}).get('hook')}")


if __name__ == "__main__":
    topic = get_next_topic()
    if topic is None:
        sys.exit(0)
    data = generate_script(topic)
    save_output(data)
