import json
import os
import random

from google import genai


def generate_post_content():
    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

    with open("topics.json") as f:
        topics = json.load(f)["topics"]
    topic = random.choice(topics)

    prompt = f"""Create viral social media content about: "{topic}"
Return ONLY JSON no extra text:
{{
    "title": "Pattern interrupt hook, max 5 words, all caps",
    "hook_subtitle": "One short curiosity line that makes people keep watching",
    "points": ["short punchy point 1", "short punchy point 2", "short punchy point 3", "short punchy point 4", "short punchy point 5"],
    "video_prompt": "Vertical 9:16 cinematic AI video prompt with scene, subject, motion, lighting, camera movement, mood, and no on-screen text",
    "caption": "caption with emojis and hashtags",
    "image_keyword": "keyword",
    "youtube_title": "YouTube title max 60 chars",
    "youtube_description": "description with hashtags",
    "youtube_tags": ["tag1", "tag2", "tag3", "tag4", "tag5"]
}}

Rules:
- Title must feel like a scrolling stop hook.
- hook_subtitle must create curiosity or promise a payoff.
- Each point must be 3 to 8 words, simple and visual.
- Prefer strong, surprising wording over generic advice.
"""

    response = client.models.generate_content(
        model="models/gemini-2.5-flash",
        contents=prompt,
    )

    text = response.text.strip()
    text = text.replace("```json", "").replace("```", "").strip()
    content = json.loads(text)

    if "video_prompt" not in content or not content["video_prompt"].strip():
        points_text = ", ".join(content.get("points", []))
        content["video_prompt"] = (
            f"Create a high-energy vertical 9:16 social video about {topic}. "
            f"Open with a striking visual hook inspired by '{content.get('title', topic)}'. "
            f"Show cinematic scenes that represent these ideas: {points_text}. "
            f"Use dynamic camera motion, crisp lighting, modern tech aesthetics, fast-paced cuts, "
            f"and expressive detail. No subtitles, no logos, no on-screen text."
        )

    if "hook_subtitle" not in content or not content["hook_subtitle"].strip():
        content["hook_subtitle"] = "These tools save money fast."

    return content
