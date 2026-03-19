import os
import json
import random
import requests

def generate_post_content():
    api_key = os.environ["GEMINI_API_KEY"]
    
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

    # Using REST API directly - no package needed!
    response = requests.post(
        f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={api_key}",
        json={"contents": [{"parts": [{"text": prompt}]}]}
    )
    
    result = response.json()
    print(f"Gemini response status: {response.status_code}")
    
    text = result["candidates"][0]["content"]["parts"][0]["text"]
    text = text.replace("```json", "").replace("```", "").strip()
    return json.loads(text)

cloudinary
