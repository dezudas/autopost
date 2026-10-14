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
    return f"""You are a YouTube Shorts script writer for "Guitar with Facts" channel.

Create a punchy 60-second script about: {topic_name}

Return ONLY raw valid JSON, no markdown, no backticks:

{{
  "topic": "{topic_name}",
  "title": "5 Wild Facts About {topic_name} #Shorts #GuitarFacts",
  "description": "Write 80-100 words about {topic_name} facts with hashtags at end",
  "tags": ["{topic_name}", "guitar facts", "shorts", "did you know", "guitar chords", "music theory", "guitar tips", "guitar with facts", "5 facts", "educational shorts"],
  "voiceover": {{
    "hook": "One punchy hook sentence about {topic_name} max 12 words",
    "fact_1": "One surprising fact about {topic_name} max 20 words",
    "fact_2": "One technique or playing tip about {topic_name} max 20 words",
    "fact_3": "One history or origin fact about {topic_name} max 20 words",
    "fact_4": "One famous player or song using {topic_name} max 20 words",
    "fact_5": "One record or unique use of {topic_name} max 20 words",
    "outro": "Follow for more guitar facts! Like and subscribe to Guitar with Facts!"
  }},
  "image_prompts": [
    "Professional photo of guitarist demonstrating {topic_name} on white background",
    "Close-up macro of guitar fretboard showing {topic_name} hand position",
    "Acoustic guitar with {topic_name} chord shape, warm studio lighting",
    "Electric guitar neck showing {topic_name} with dark dramatic background",
    "Guitarist playing {topic_name} on stage with concert lighting"
  ],
  "colors": {{
    "primary": "vibrant hex color matching guitar or music theme",
    "secondary": "complementary darker hex color",
    "accent": "bright accent hex color"
  }},
  "emoji": "best emoji for {topic_name}"
}}

Write REAL facts only. All fields must have actual content."""


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
                "temperature": 0.7,
                "maxOutputTokens": 2000,
                "topP": 0.9,
                "response_mime_type": "application/json"
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
                    print("SUCCESS!")
                    return r.json()

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
    parts = candidate.get("content", {}).get("parts", [])
    if not parts:
        finish_reason = candidate.get("finishReason", "UNKNOWN")
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
    return json.loads(raw)


def generate_script(topic_name):
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY not set in GitHub Secrets!")
    prompt = build_prompt(topic_name)
    result = call_gemini(prompt, api_key)
    data = parse_response(result)
    assert len(data.get("description", "")) > 30, "Description too short"
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
