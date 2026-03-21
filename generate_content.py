import os
import json
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
    "title": "SHOCKING HOOK TITLE MAX 6 WORDS",
    "points": ["point 1", "point 2", "point 3", "point 4", "point 5"],
    "caption": "caption with emojis and hashtags",
    "image_keyword": "keyword",
    "youtube_title": "YouTube title max 60 chars",
    "youtube_description": "description with hashtags",
    "youtube_tags": ["tag1", "tag2", "tag3", "tag4", "tag5"]
}}"""

    response = client.models.generate_content(
        model="gemini-1.5-flash",
        contents=prompt
    )

    text = response.text.strip()
    text = text.replace("```json", "").replace("```", "").strip()
    return json.loads(text)
