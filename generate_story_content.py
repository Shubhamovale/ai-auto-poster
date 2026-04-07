import json
import os
import re

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
    "Beat 6 in spoken English",
    "Beat 7 in spoken English",
    "Beat 8 in spoken English"
  ],
  "voiceover_script": "A natural, fast, human-sounding 30 to 45 second English narration for a Shorts video",
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
  "scene_plan": [
    {
      "line": "spoken beat 1",
      "subtitle": "short caption 1",
      "visual_keyword": "specific stock video keyword 1",
      "visual_direction": "what should be visible in this scene",
      "transition": "cut"
    },
    {
      "line": "spoken beat 2",
      "subtitle": "short caption 2",
      "visual_keyword": "specific stock video keyword 2",
      "visual_direction": "what should be visible in this scene",
      "transition": "push"
    }
  ],
  "youtube_description": "2 to 4 sentence English description with hashtags",
  "youtube_tags": ["tag1", "tag2", "tag3", "tag4", "tag5"]
}}

Rules:
- Make the pacing feel like a story, not a listicle.
- The hook must create curiosity in the first 1.5 seconds.
- The voiceover should sound natural when spoken out loud, but fast and energetic like a premium shorts narrator.
- Use short, punchy spoken lines. Avoid slow filler words.
- Make the narration feel like rapid spoken beats, not long explanatory sentences.
- Most lines should be 5 to 12 words.
- Scene keywords must be visually searchable for stock footage.
- Build `scene_plan` so each spoken beat has its own matching visual idea.
- Create 8 to 10 scenes so the visuals can change quickly with the speech.
- Visual changes should feel frequent, roughly every 1 to 1.8 seconds.
- Prefer tight closeups, action details, interface overlays, reaction shots, and product reveals over generic wide shots.
- Make each scene visually distinct from the one before it.
- Each `subtitle` should be 2 to 6 words only.
- Each `line` should feel like one short spoken beat, not a paragraph.
- If the story mentions a brand or copyrighted title, use brand-safe proxy visuals.
- Example: for Netflix use streaming app UI, couch watching, TV thumbnails, remote control, red interface glow.
- Subtitle lines must be short and readable on mobile.
- Focus on entertainment, movie, gaming, or viral-tech story framing.
"""


def _trim_subtitle(text, fallback):
    cleaned = " ".join((text or fallback or "").split())
    if not cleaned:
        return "WATCH THIS"
    words = cleaned.split()
    return " ".join(words[:6]).upper()


def _trim_line(text, fallback):
    cleaned = " ".join((text or fallback or "").split())
    if not cleaned:
        return fallback
    return cleaned


def _split_into_micro_beats(text):
    cleaned = " ".join((text or "").split())
    if not cleaned:
        return []

    chunks = re.split(r"(?<=[.!?])\s+|,\s+|;\s+|:\s+", cleaned)
    beats = []
    for chunk in chunks:
        chunk = " ".join(chunk.split())
        if not chunk:
            continue
        words = chunk.split()
        if len(words) <= 12:
            beats.append(chunk)
            continue

        while len(words) > 12:
            slice_size = 9 if len(words) > 18 else 10
            beats.append(" ".join(words[:slice_size]))
            words = words[slice_size:]
        if words:
            beats.append(" ".join(words))
    return beats


def _extract_focus_terms(topic, content):
    pool = " ".join(
        [
            topic,
            content.get("title", ""),
            content.get("hook", ""),
            content.get("summary", ""),
            " ".join(content.get("story_beats", [])),
        ]
    )
    normalized = pool.lower()
    mappings = [
        ("apple", "apple product close up"),
        ("iphone", "smartphone close up"),
        ("tesla", "electric car detail"),
        ("netflix", "streaming app interface"),
        ("marvel", "cinematic superhero silhouette"),
        ("youtube", "creator studio setup"),
        ("instagram", "social media phone scroll"),
        ("tiktok", "vertical video creator"),
        ("playstation", "gaming console controller close up"),
        ("xbox", "gaming console controller close up"),
        ("openai", "ai interface screen"),
        ("chatgpt", "ai chatbot interface"),
        ("google", "tech keynote stage"),
        ("meta", "ar glasses demo"),
        ("vr", "virtual reality headset close up"),
        ("ar", "augmented reality interface"),
        ("ai", "futuristic ai interface"),
        ("robot", "robotic hand close up"),
        ("startup", "office team laptop"),
        ("movie", "cinematic projector light"),
        ("trailer", "dramatic cinema screen"),
        ("gaming", "gamer rgb setup"),
    ]
    for trigger, replacement in mappings:
        if trigger in normalized:
            return replacement
    return topic


def _build_search_keyword(topic, focus_terms, beat, scene, index):
    direction = " ".join(
        [
            scene.get("visual_keyword", ""),
            scene.get("visual_direction", ""),
            beat,
        ]
    ).lower()

    if any(term in direction for term in ["close", "detail", "lens", "screen", "device", "product"]):
        suffix = "close up detail portrait"
    elif any(term in direction for term in ["reaction", "crowd", "fans", "people", "face"]):
        suffix = "reaction portrait vertical"
    elif any(term in direction for term in ["ui", "interface", "app", "overlay", "screen", "display"]):
        suffix = "interface screen close up"
    elif any(term in direction for term in ["launch", "event", "stage", "announcement", "keynote"]):
        suffix = "event stage lights vertical"
    elif any(term in direction for term in ["car", "drive", "vehicle"]):
        suffix = "cinematic driving detail"
    else:
        dynamic_suffixes = [
            "close up portrait",
            "cinematic detail shot",
            "reaction face portrait",
            "interface screen close up",
            "dramatic lighting close up",
            "product reveal vertical",
            "hands device close up",
            "modern tech portrait",
        ]
        suffix = dynamic_suffixes[index % len(dynamic_suffixes)]

    return " ".join([focus_terms, suffix]).strip()


def _subtitle_from_beat(text, fallback):
    cleaned = " ".join((text or fallback or "").split())
    if not cleaned:
        return "WATCH THIS"

    patterns = [
        (r"\b(shocking|wild|massive|huge|crazy|insane)\b", lambda m: m.group(1).upper()),
        (r"\b(first look|big reveal|real reason|what happened|why now|just dropped)\b", lambda m: m.group(1).upper()),
        (r"\b(\d+\s+\w+)\b", lambda m: m.group(1).upper()),
    ]
    for pattern, formatter in patterns:
        match = re.search(pattern, cleaned, flags=re.IGNORECASE)
        if match:
            return formatter(match)

    words = cleaned.split()
    if len(words) >= 2:
        return " ".join(words[: min(4, len(words))]).upper()
    return cleaned.upper()


def _build_default_scene_plan(topic, content):
    raw_lines = [content["hook"], content["summary"], *content["story_beats"]]
    lines = []
    for raw_line in raw_lines:
        lines.extend(_split_into_micro_beats(raw_line) or [raw_line])
    focus_terms = _extract_focus_terms(topic, content)
    keywords = content["scene_keywords"]
    transitions = ["cut", "push", "cut", "flash", "slide", "cut", "zoom", "cut", "flash", "fade"]
    scene_count = min(max(len(lines), len(keywords), 8), 10)
    plan = []
    for index in range(scene_count):
        fallback_line = lines[index] if index < len(lines) else content["hook"]
        raw_keyword = keywords[index] if index < len(keywords) else topic
        keyword = _build_search_keyword(topic, focus_terms, fallback_line, {"visual_keyword": raw_keyword}, index)
        plan.append(
            {
                "line": _trim_line(fallback_line, content["hook"]),
                "subtitle": _subtitle_from_beat(
                    content["subtitle_lines"][index] if index < len(content["subtitle_lines"]) else fallback_line,
                    fallback_line,
                ),
                "visual_keyword": keyword,
                "visual_direction": raw_keyword,
                "transition": transitions[index % len(transitions)],
            }
        )
    return plan


def normalize_story_content(topic, topic_info, content):
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
            "The clips are spreading everywhere.",
            "This is why everyone is watching.",
        ],
    )
    content["story_beats"] = [beat.strip() for beat in content["story_beats"] if beat and beat.strip()][:8]
    if len(content["story_beats"]) < 8:
        defaults = [
            "This story is trending fast.",
            "People did not expect this to happen.",
            "The reaction online has been huge.",
            "The numbers climbed very quickly.",
            "Now everyone is paying attention.",
            "This could get even bigger next.",
            "The clips are spreading everywhere.",
            "This is why everyone is watching.",
        ]
        for beat in defaults:
            if len(content["story_beats"]) >= 8:
                break
            content["story_beats"].append(beat)

    content.setdefault(
        "voiceover_script",
        " ".join([content["hook"], content["summary"], *content["story_beats"]]),
    )
    content["voiceover_script"] = re.sub(r"\s+", " ", content["voiceover_script"]).strip()

    scene_keywords = [item.strip() for item in (content.get("scene_keywords") or []) if item and item.strip()]
    if len(scene_keywords) < 8:
        scene_keywords = [topic, *content["story_beats"]]
    content["scene_keywords"] = scene_keywords[:10]

    subtitle_lines = [item.strip() for item in (content.get("subtitle_lines") or []) if item and item.strip()]
    if len(subtitle_lines) < 8:
        subtitle_lines = [
            content["hook"],
            content["summary"],
            *content["story_beats"][:6],
        ]
    content["subtitle_lines"] = [_subtitle_from_beat(line, content["hook"]) for line in subtitle_lines[:10]]

    scene_plan = content.get("scene_plan") or []
    normalized_scene_plan = []
    focus_terms = _extract_focus_terms(topic, content)
    for index, scene in enumerate(scene_plan[:10]):
        fallback_line = (
            scene.get("line")
            or scene.get("subtitle")
            or (content["story_beats"][index - 2] if index >= 2 and index - 2 < len(content["story_beats"]) else content["hook"])
        )
        raw_keyword = scene.get("visual_keyword") or scene.get("visual_direction") or topic
        normalized_scene_plan.append(
            {
                "line": _trim_line(scene.get("line"), fallback_line),
                "subtitle": _subtitle_from_beat(scene.get("subtitle"), fallback_line),
                "visual_keyword": _build_search_keyword(topic, focus_terms, fallback_line, scene, index),
                "visual_direction": scene.get("visual_direction") or raw_keyword,
                "transition": (scene.get("transition") or "cut").lower(),
            }
        )
    expanded_scene_plan = []
    for scene in normalized_scene_plan:
        beats = _split_into_micro_beats(scene["line"]) or [scene["line"]]
        for beat_index, beat in enumerate(beats):
            expanded_scene_plan.append(
                {
                    "line": _trim_line(beat, scene["line"]),
                    "subtitle": _subtitle_from_beat(
                        scene["subtitle"] if beat_index == 0 else beat,
                        beat,
                    ),
                    "visual_keyword": _build_search_keyword(topic, focus_terms, beat, scene, beat_index),
                    "visual_direction": scene["visual_direction"],
                    "transition": scene["transition"],
                }
            )

    content["scene_plan"] = (expanded_scene_plan[:10] or _build_default_scene_plan(topic, content))[:10]

    if len(content["scene_plan"]) < 8:
        fallback_plan = _build_default_scene_plan(topic, content)
        for scene in fallback_plan:
            if len(content["scene_plan"]) >= 8:
                break
            content["scene_plan"].append(scene)

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
    return normalize_story_content(topic, topic_info, content)
