import json
import os

from google import genai
from trending_topics import get_random_topic


def build_caption(base_caption, content):
    parts = [base_caption.strip()]

    if content.get("is_live_trend"):
        source_name = content.get("source_name", "Google News")
        source_query = content.get("source_query", "Trend")
        parts.append(f"Source: {source_name} ({source_query})")

    if content.get("source_link"):
        parts.append(content["source_link"])

    return "\n\n".join(part for part in parts if part)


def generate_post_content():
    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    topic_info = get_random_topic()
    topic = topic_info["topic"]

    prompt = f"""Create viral social media content about: "{topic}"
Return ONLY JSON no extra text:
{{
    "title": "BIG ALL-CAPS POSTER HOOK",
    "hook_subtitle": "Short supporting line",
    "points": ["short punchy point 1", "short punchy point 2", "short punchy point 3", "short punchy point 4"],
    "hero_keyword": "main visual keyword",
    "badge_left_keyword": "left badge visual keyword",
    "badge_right_keyword": "right badge visual keyword",
    "badge_left_value": "500M",
    "badge_left_label": "12 HOURS",
    "badge_right_value": "475M",
    "badge_right_label": "24 HOURS",
    "category_label": "NEWS",
    "headline": "Bold dramatic 2 to 4 line headline in all caps for a social news poster",
    "caption": "caption with emojis and hashtags",
    "image_keyword": "keyword",
    "youtube_title": "YouTube title max 60 chars",
    "youtube_description": "description with hashtags",
    "youtube_tags": ["tag1", "tag2", "tag3", "tag4", "tag5"]
}}

Rules:
- Make it feel like a dramatic trending-news social poster.
- Title and headline must be in English and highly clickable.
- Use realistic numeric comparison values for the two badges.
- `hero_keyword`, `badge_left_keyword`, and `badge_right_keyword` should describe visuals to search.
- Each point must be 3 to 8 words, simple and visual.
- The poster should reflect a current or recent trend when the topic sounds newsy.
- Prefer strong, surprising wording over generic advice.
"""

    response = client.models.generate_content(
        model="models/gemini-2.5-flash",
        contents=prompt,
    )

    text = response.text.strip()
    text = text.replace("```json", "").replace("```", "").strip()
    content = json.loads(text)

    if "hook_subtitle" not in content or not content["hook_subtitle"].strip():
        import random
        subtitles = [
            "These tools will save you hours.",
            "You need to see this right now.",
            "Wait till you see the last one.",
            "This will blow your mind.",
            "These tips are a game changer.",
            "Stop what you're doing and watch."
        ]
        content["hook_subtitle"] = random.choice(subtitles)

    content.setdefault("hero_keyword", content.get("image_keyword", topic))
    content.setdefault("badge_left_keyword", content.get("hero_keyword", topic))
    content.setdefault("badge_right_keyword", content.get("hero_keyword", topic))
    content.setdefault("badge_left_value", "500M")
    content.setdefault("badge_left_label", "12 HOURS")
    content.setdefault("badge_right_value", "475M")
    content.setdefault("badge_right_label", "24 HOURS")
    content.setdefault("category_label", "NEWS")
    content.setdefault("headline", content.get("title", topic).upper())
    content["topic"] = topic
    content["source_name"] = topic_info["source_name"]
    content["source_link"] = topic_info["source_link"]
    content["source_query"] = topic_info["source_query"]
    content["published_at"] = topic_info["published_at"]
    content["is_live_trend"] = topic_info["is_live_trend"]
    content["caption"] = build_caption(content.get("caption", ""), content)

    return content
