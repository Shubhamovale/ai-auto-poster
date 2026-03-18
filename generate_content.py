import google.generativeai as genai
import os
import json
import random

def generate_post_content():
    genai.configure(api_key=os.environ["GEMINI_API_KEY"])
    model = genai.GenerativeModel("gemini-1.5-flash")

    with open("topics.json") as f:
        topics = json.load(f)["topics"]
    topic = random.choice(topics)

    prompt = f"""
    You are a viral social media content creator targeting USA audience.
    Create content for a 30-second viral Reel/Short about: "{topic}"

    Return ONLY this JSON format, no extra text:
    {{
        "title": "Hook title for video (max 6 words, ALL CAPS, shocking)",
        "points": [
            "Point 1 - short, punchy (max 8 words)",
            "Point 2 - short, punchy (max 8 words)",
            "Point 3 - short, punchy (max 8 words)",
            "Point 4 - short, punchy (max 8 words)",
            "Point 5 - short, punchy (max 8 words)"
        ],
        "caption": "Full Instagram/Facebook caption with emojis and hashtags (max 300 words)",
        "image_keyword": "single keyword for background image",
        "youtube_title": "YouTube Shorts title (max 60 chars)",
        "youtube_description": "YouTube description with hashtags",
        "youtube_tags": ["tag1", "tag2", "tag3", "tag4", "tag5"]
    }}
    """

    response = model.generate_content(prompt)
    text = response.text.strip()
    text = text.replace("```json", "").replace("```", "").strip()
    return json.loads(text)