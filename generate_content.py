import json
import os
import random

from google import genai


def generate_post_content():
    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

    with open("topics.json", encoding="utf-8") as f:
        topics = json.load(f)["topics"]
    topic = random.choice(topics)

    prompt = f'''Create viral social media content about: "{topic}"
Return ONLY JSON no extra text:
{{
    "title": "English viral hook, max 5 words, all caps",
    "hook_subtitle": "One short English curiosity line that makes people keep watching",
    "points": ["short punchy point 1", "short punchy point 2", "short punchy point 3", "short punchy point 4"],
    "video_keywords": ["hook visual keyword", "point 1 visual keyword", "point 2 visual keyword", "point 3 visual keyword", "point 4 visual keyword"],
    "voiceover_script": "Short natural English reel narration that says the hook and all 4 points clearly in under 18 seconds",
    "subtitle_lines": ["Hook subtitle line", "Point 1 subtitle", "Point 2 subtitle", "Point 3 subtitle", "Point 4 subtitle", "Call to action subtitle"],
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
- Return exactly 4 points.
- `video_keywords` should be useful for finding real stock clips.
- `voiceover_script` should sound like an English viral short narrator.
- `subtitle_lines` must be short English captions for each beat.
- Prefer strong, surprising wording over generic advice.
'''

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
            "Use dynamic camera motion, crisp lighting, modern tech aesthetics, fast-paced cuts, "
            "and expressive detail. No subtitles, no logos, no on-screen text."
        )

    if "hook_subtitle" not in content or not content["hook_subtitle"].strip():
        content["hook_subtitle"] = "These tools save money fast."

    if "video_keywords" not in content or len(content["video_keywords"]) < 5:
        content["video_keywords"] = [
            content.get("image_keyword", topic),
            *content.get("points", [])[:4],
        ]

    if "voiceover_script" not in content or not content["voiceover_script"].strip():
        numbered_points = " ".join(
            f"Number {index + 1}: {point}."
            for index, point in enumerate(content.get("points", [])[:4])
        )
        content["voiceover_script"] = (
            f"Did you know these 4 AI tools exist? {numbered_points} "
            "Follow for more AI tools and secrets."
        )

    if "subtitle_lines" not in content or len(content["subtitle_lines"]) < 6:
        points = content.get("points", [])[:4]
        content["subtitle_lines"] = [
            content.get("title", "AI TOOLS YOU NEED"),
            *(point.upper() for point in points),
            "FOLLOW FOR MORE AI TOOLS",
        ]

    return content
