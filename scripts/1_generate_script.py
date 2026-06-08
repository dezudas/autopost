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


def get_next_fruit():
    with open("fruits_list.txt", "r") as f:
        all_fruits = [l.strip() for l in f if l.strip() and not l.startswith("#")]
    done = []
    if os.path.exists("fruits_done.txt"):
        with open("fruits_done.txt", "r") as f:
            done = [l.strip() for l in f if l.strip() and not l.startswith("#")]
    remaining = [f for f in all_fruits if f not in done]
    if not remaining:
        print("All fruits completed!")
        sys.exit(0)
    print(f"Next fruit: {remaining[0]}")
    return remaining[0]


def build_prompt(fruit_name):
    return f"""You are a YouTube Shorts script writer for "Fruits with Facts" channel.

Create a punchy 60-second script about: {fruit_name}

Return ONLY raw valid JSON, no markdown, no backticks:

{{
  "fruit": "{fruit_name}",
  "title": "5 Wild Facts About {fruit_name} #Shorts #FruitFacts",
  "description": "Write 80-100 words about {fruit_name} facts with hashtags at end",
  "tags": ["{fruit_name}", "fruit facts", "shorts", "did you know", "healthy food", "nutrition facts", "food facts", "fruits with facts", "5 facts", "educational shorts"],
  "voiceover": {{
    "hook": "One punchy hook sentence about {fruit_name} max 12 words",
    "fact_1": "One surprising fact about {fruit_name} max 20 words",
    "fact_2": "One health benefit of {fruit_name} max 20 words",
    "fact_3": "One history fact about {fruit_name} max 20 words",
    "fact_4": "One weird fact about {fruit_name} max 20 words",
    "fact_5": "One record or unique use of {fruit_name} max 20 words",
    "outro": "Follow for more fruity facts! Like and subscribe to Fruits with Facts!"
  }},
  "image_prompts": [
    "Professional photo of fresh {fruit_name} on white background",
    "{fruit_name} cut open showing inside macro photography",
    "{fruit_name} growing naturally on tree or plant",
    "{fruit_name} with water droplets dark background",
    "{fruit_name} in wooden bowl warm rustic lighting"
  ],
  "colors": {{
    "primary": "vibrant hex color matching {fruit_name}",
    "secondary": "complementary darker hex color",
    "accent": "bright accent hex color"
  }},
  "emoji": "best emoji for {fruit_name}"
}}

Write REAL facts only. All fields must have actual content."""


def call_gemini(prompt, api_key):
    """
    Try lightest models first (less demand), heavy models last.
    Smart backoff: 5s, 15s, 30s between retries.
    """
    # Lightest to heaviest — less popular = less overloaded
    models = [
        "gemini-2.0-flash-lite",
        "gemini-2.5-flash-lite",
        "gemini-2.0-flash",
        "gemini-2.5-flash",
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
                "topP": 0.9
            }
        }

        print(f"\nTrying: {model}")

        for attempt in range(3):
            total_attempts += 1
            try:
                print(f"  Attempt {attempt+1}/3...", end=" ", flush=True)
                r = requests.post(url, json=payload, timeout=45)

                if r.status_code == 200:
                    print("SUCCESS!")
                    return r.json()

                err = r.text.lower()
                print(f"HTTP {r.status_code}")

                # Auth error - fail immediately
                if r.status_code == 401:
                    raise Exception("Invalid GEMINI_API_KEY — check GitHub Secret!")

                # Model not found - skip to next model
                if r.status_code == 404:
                    print(f"  Model unavailable, trying next...")
                    last_error = f"{model} not found"
                    break

                # Rate limit or overloaded - wait and retry
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
    raw = result["candidates"][0]["content"]["parts"][0]["text"].strip()
    if "```" in raw:
        parts = raw.split("```")
        for part in parts:
            cleaned = part.strip().lstrip("json").strip()
            if cleaned.startswith("{"):
                raw = cleaned
                break
    start, end = raw.find("{"), raw.rfind("}") + 1
    if start != -1 and end > start:
        raw = raw[start:end]
    return json.loads(raw)


def generate_script(fruit_name):
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY not set in GitHub Secrets!")
    prompt = build_prompt(fruit_name)
    result = call_gemini(prompt, api_key)
    data = parse_response(result)
    assert len(data.get("description", "")) > 30, "Description too short"
    assert len(data.get("voiceover", {}).get("fact_1", "")) > 10, "Fact 1 missing"
    print(f"\nScript generated for: {fruit_name}")
    return data


def save_output(data):
    os.makedirs("output", exist_ok=True)
    with open("output/video_data.json", "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"Title: {data.get('title')}")
    print(f"Hook:  {data.get('voiceover', {}).get('hook')}")


if __name__ == "__main__":
    fruit = get_next_fruit()
    data = generate_script(fruit)
    save_output(data)
