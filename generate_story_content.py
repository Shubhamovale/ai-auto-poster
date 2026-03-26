import json
import os

from google import genai
from trending_topics import get_random_topic


def build_story_prompt(topic):
    return f"""Create a YouTube Shorts story package about this trending topic: "{topic}"
Return ONLY JSON with no extra text:
{{
  "title": "Short YouTube Shorts title in English, max 60 chars",
  "hook": "One strong opening sentence",
  "summary": "One sentence explaining the core story",
  "story_beats": [
    "Beat 1 in spoken English",
    "Beat 2 in spoken English",
    "Beat 3 in spoken English",
    "Beat 4 in spoken English",
    "Beat 5 in spoken English",
    "Beat 6 in spoken English"
  ],
  "voiceover_script": "A natural 45 to 75 second English narration for a Shorts video",
  "scene_keywords": [
    "scene keyword 1",
    "scene keyword 2",
    "scene keyword 3",
    "scene keyword 4",
    "scene keyword 5",
    "scene keyword 6",
    "scene keyword 7",
    "scene keyword 8"
  ],
  "subtitle_lines": [
    "caption 1",
    "caption 2",
    "caption 3",
    "caption 4",
    "caption 5",
    "caption 6",
    "caption 7",
    "caption 8"
  ],
  "youtube_description": "2 to 4 sentence English description with hashtags",
  "youtube_tags": ["tag1", "tag2", "tag3", "tag4", "tag5"]
}}

Rules:
- Make the pacing feel like a story, not a listicle.
- The hook must create curiosity in the first 2 seconds.
- The voiceover should sound natural when spoken out loud.
- Scene keywords must be visually searchable for stock footage.
- Subtitle lines must be short and readable on mobile.
- Focus on entertainment, movie, gaming, or viral-tech story framing.
"""


def generate_story_content():
    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    topic_info = get_random_topic()
    topic = topic_info["topic"]

    response = client.models.generate_content(
        model="models/gemini-2.5-flash",
        contents=build_story_prompt(topic),
    )

    text = response.text.strip()
    text = text.replace("```json", "").replace("```", "").strip()
    content = json.loads(text)

    content.setdefault("title", topic[:60])
    content.setdefault("hook", topic)
    content.setdefault("summary", topic)
    content.setdefault(
        "story_beats",
        [
            "This story is trending fast.",
            "People did not expect this to happen.",
            "The reaction online has been huge.",
            "The numbers climbed very quickly.",
            "Now everyone is paying attention.",
            "This could get even bigger next.",
        ],
    )
    content.setdefault(
        "voiceover_script",
        " ".join([content["hook"], content["summary"], *content["story_beats"]]),
    )

    scene_keywords = content.get("scene_keywords") or []
    if len(scene_keywords) < 8:
        content["scene_keywords"] = [topic] + content["story_beats"][:7]

    subtitle_lines = content.get("subtitle_lines") or []
    if len(subtitle_lines) < 8:
        content["subtitle_lines"] = [
            content["hook"],
            *content["story_beats"][:6],
            "FOLLOW FOR MORE STORIES",
        ]

    content.setdefault("youtube_description", content["summary"])
    content.setdefault("youtube_tags", ["Shorts", "Trending", "News", "Entertainment", "Story"])
    content["topic"] = topic
    content["source_name"] = topic_info["source_name"]
    content["source_link"] = topic_info["source_link"]
    content["source_query"] = topic_info["source_query"]
    content["published_at"] = topic_info["published_at"]
    content["is_live_trend"] = topic_info["is_live_trend"]

    if content.get("source_link"):
        content["youtube_description"] = (
            f"{content['youtube_description']}\n\nSource: "
            f"{content['source_name']} ({content['source_query']})\n{content['source_link']}"
        )

    return content
