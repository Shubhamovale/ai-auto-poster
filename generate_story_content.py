import json
import os
import re
import time

from google import genai
from google.genai import errors
import requests
from trending_topics import get_random_topic


OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "").strip()
OPENAI_CONTENT_MODEL = os.environ.get("OPENAI_CONTENT_MODEL", "gpt-4o-mini")
OPENAI_MAX_RETRIES = int(os.environ.get("OPENAI_MAX_RETRIES", "") or "3")
OPENAI_RETRY_BASE_SECONDS = int(os.environ.get("OPENAI_RETRY_BASE_SECONDS", "") or "5")
OPENAI_TIMEOUT_SECONDS = int(os.environ.get("OPENAI_TIMEOUT_SECONDS", "") or "90")
GEMINI_CONTENT_MODEL = os.environ.get("GEMINI_CONTENT_MODEL", "models/gemini-2.5-flash")
GEMINI_MAX_RETRIES = int(os.environ.get("GEMINI_MAX_RETRIES", "") or "4")
GEMINI_RETRY_BASE_SECONDS = int(os.environ.get("GEMINI_RETRY_BASE_SECONDS", "") or "6")


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
    {{
      "line": "spoken beat 1",
      "subtitle": "short caption 1",
      "scene_type": "product_reveal",
      "visual_keyword": "specific stock video keyword 1",
      "visual_direction": "what should be visible in this scene",
      "transition": "cut"
    }},
    {{
      "line": "spoken beat 2",
      "subtitle": "short caption 2",
      "scene_type": "interface",
      "visual_keyword": "specific stock video keyword 2",
      "visual_direction": "what should be visible in this scene",
      "transition": "push"
    }}
  ],
  "youtube_description": "2 to 4 sentence English description with hashtags",
  "youtube_tags": ["tag1", "tag2", "tag3", "tag4", "tag5"]
}}

Rules:
- Make the pacing feel like a story, not a listicle.
- The hook must create curiosity in the first 1.5 seconds.
- The first 3 scenes must escalate fast: hook, reveal, consequence.
- The voiceover should sound natural when spoken out loud, but fast and energetic like a premium shorts narrator.
- Use short, punchy spoken lines. Avoid slow filler words.
- Make the narration feel like rapid spoken beats, not long explanatory sentences.
- Most lines should be 5 to 12 words.
- Scene keywords must be visually searchable for stock footage.
- Build `scene_plan` so each spoken beat has its own matching visual idea.
- For every scene add a `scene_type` chosen from: hook, product_reveal, interface, reaction, feature_demo, stage, social_proof, consequence, abstract, cta.
- Create 8 to 10 scenes so the visuals can change quickly with the speech.
- Visual changes should feel frequent, roughly every 1 to 1.8 seconds.
- Prefer tight closeups, action details, interface overlays, reaction shots, and product reveals over generic wide shots.
- Make each scene visually distinct from the one before it.
- Each `subtitle` should be 2 to 6 words only.
- Each `line` should feel like one short spoken beat, not a paragraph.
- The final scene should end with a viral CTA beat like "would you try this?", "part 2?", "comment now", or "follow for more".
- If the story mentions a brand or copyrighted title, use brand-safe proxy visuals.
- Example: for Netflix use streaming app UI, couch watching, TV thumbnails, remote control, red interface glow.
- Subtitle lines must be short and readable on mobile.
- Focus strictly on Netflix releases, upcoming movies, trailer updates, and exciting entertainment news tailored for the US audience. Make it feel personal, engaging, and oriented toward what people are excited about.
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
            scene.get("scene_type", ""),
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


def _classify_scene_type(line, subtitle="", visual_direction="", index=0, total=0):
    text = " ".join([line or "", subtitle or "", visual_direction or ""]).lower()
    if index == total - 1:
        return "cta"
    if index == 0:
        return "hook"
    if any(term in text for term in ["app", "interface", "screen", "ui", "display", "dashboard", "menu"]):
        return "interface"
    if any(term in text for term in ["phone", "device", "product", "glasses", "console", "controller", "launch"]):
        return "product_reveal"
    if any(term in text for term in ["reaction", "fans", "people", "crowd", "everyone", "users"]):
        return "reaction"
    if any(term in text for term in ["feature", "lets you", "can now", "comes with", "built for", "packed with"]):
        return "feature_demo"
    if any(term in text for term in ["stage", "event", "keynote", "announcement"]):
        return "stage"
    if any(term in text for term in ["viral", "trending", "millions", "huge", "online"]):
        return "social_proof"
    if any(term in text for term in ["problem", "change", "bigger", "means", "because", "next"]):
        return "consequence"
    return "abstract"


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


def _boost_hook_line(text, index):
    cleaned = " ".join((text or "").split())
    if not cleaned:
        return cleaned

    templates = [
        lambda value: value,
        lambda value: f"Then this happened: {value}" if not value.lower().startswith("then") else value,
        lambda value: f"And it got bigger fast: {value}" if "bigger" not in value.lower() else value,
    ]
    return templates[min(index, len(templates) - 1)](cleaned)


def _boost_hook_subtitle(text, index):
    cleaned = _subtitle_from_beat(text, text)
    presets = ["WAIT WHAT", "THEN THIS", "IT GETS BIGGER"]
    return presets[index] if index < len(presets) else cleaned


def _viral_cta_line(content):
    title = " ".join((content.get("title") or "").split())
    hook = " ".join((content.get("hook") or "").split())
    source = title or hook or "this story"
    return f"Would you try this yourself? Follow for part two on {source}."


def _viral_cta_subtitle():
    return "FOLLOW FOR PART 2"


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
        line = _trim_line(fallback_line, content["hook"])
        subtitle = _subtitle_from_beat(
            content["subtitle_lines"][index] if index < len(content["subtitle_lines"]) else fallback_line,
            fallback_line,
        )

        scene_type = _classify_scene_type(line, subtitle, raw_keyword, index, scene_count)

        if index < 3:
            line = _boost_hook_line(line, index)
            subtitle = _boost_hook_subtitle(subtitle, index)
            if index == 0:
                scene_type = "hook"
        elif index == scene_count - 1:
            line = _viral_cta_line(content)
            subtitle = _viral_cta_subtitle()
            scene_type = "cta"

        keyword = _build_search_keyword(
            topic,
            focus_terms,
            fallback_line,
            {"visual_keyword": raw_keyword, "visual_direction": raw_keyword, "scene_type": scene_type},
            index,
        )
        plan.append(
            {
                "line": line,
                "subtitle": subtitle,
                "scene_type": scene_type,
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
        line = _trim_line(scene.get("line"), fallback_line)
        subtitle = _subtitle_from_beat(scene.get("subtitle"), fallback_line)
        scene_type = scene.get("scene_type") or _classify_scene_type(
            line,
            subtitle,
            scene.get("visual_direction") or raw_keyword,
            index,
            len(scene_plan[:10]) or 10,
        )
        if index < 3:
            line = _boost_hook_line(line, index)
            subtitle = _boost_hook_subtitle(subtitle, index)
            if index == 0:
                scene_type = "hook"
        normalized_scene_plan.append(
            {
                "line": line,
                "subtitle": subtitle,
                "scene_type": scene_type,
                "visual_keyword": _build_search_keyword(
                    topic,
                    focus_terms,
                    fallback_line,
                    {
                        "scene_type": scene_type,
                        "visual_keyword": scene.get("visual_keyword"),
                        "visual_direction": scene.get("visual_direction"),
                    },
                    index,
                ),
                "visual_direction": scene.get("visual_direction") or raw_keyword,
                "transition": (scene.get("transition") or "cut").lower(),
            }
        )
    expanded_scene_plan = []
    for scene in normalized_scene_plan:
        beats = _split_into_micro_beats(scene["line"]) or [scene["line"]]
        for beat_index, beat in enumerate(beats):
            scene_type = scene["scene_type"]
            if beat_index > 0 and scene_type == "hook":
                scene_type = "consequence"
            expanded_scene_plan.append(
                {
                    "line": _trim_line(beat, scene["line"]),
                    "subtitle": _subtitle_from_beat(
                        scene["subtitle"] if beat_index == 0 else beat,
                        beat,
                    ),
                    "scene_type": scene_type,
                    "visual_keyword": _build_search_keyword(
                        topic,
                        focus_terms,
                        beat,
                        {
                            "scene_type": scene_type,
                            "visual_keyword": scene["visual_keyword"],
                            "visual_direction": scene["visual_direction"],
                        },
                        beat_index,
                    ),
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

    if content["scene_plan"]:
        last_index = len(content["scene_plan"]) - 1
        content["scene_plan"][last_index]["line"] = _viral_cta_line(content)
        content["scene_plan"][last_index]["subtitle"] = _viral_cta_subtitle()
        content["scene_plan"][last_index]["scene_type"] = "cta"
        content["scene_plan"][last_index]["visual_keyword"] = _build_search_keyword(
            topic,
            focus_terms,
            content["scene_plan"][last_index]["line"],
            content["scene_plan"][last_index],
            last_index,
        )

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


def _extract_openai_output_text(response_json):
    output_text = " ".join((response_json.get("output_text") or "").split())
    if output_text:
        return output_text

    chunks = []
    for item in response_json.get("output", []):
        for content_item in item.get("content", []):
            text = content_item.get("text")
            if text:
                chunks.append(text)
    return "\n".join(chunks).strip()


def _generate_story_content_with_openai(topic):
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": OPENAI_CONTENT_MODEL,
        "input": [
            {
                "role": "system",
                "content": [
                    {
                        "type": "input_text",
                        "text": "You create structured YouTube Shorts story packages. Return valid JSON only.",
                    }
                ],
            },
            {
                "role": "user",
                "content": [{"type": "input_text", "text": build_story_prompt(topic)}],
            },
        ],
        "text": {"format": {"type": "json_object"}},
    }

    last_error = None
    for attempt in range(1, OPENAI_MAX_RETRIES + 1):
        try:
            response = requests.post(
                "https://api.openai.com/v1/responses",
                headers=headers,
                json=payload,
                timeout=OPENAI_TIMEOUT_SECONDS,
            )
            response.raise_for_status()
            response_json = response.json()
            text = _extract_openai_output_text(response_json)
            if not text:
                raise RuntimeError("OpenAI response did not contain any output text.")
            return json.loads(text)
        except (requests.RequestException, json.JSONDecodeError, RuntimeError) as exc:
            last_error = exc
            if attempt == OPENAI_MAX_RETRIES:
                raise
            wait_seconds = OPENAI_RETRY_BASE_SECONDS * attempt
            print(
                f"OpenAI content generation failed on attempt {attempt}/"
                f"{OPENAI_MAX_RETRIES}. Retrying in {wait_seconds}s..."
            )
            time.sleep(wait_seconds)

    raise last_error or RuntimeError("OpenAI content generation failed without an exception.")


def _generate_story_content_with_gemini(topic):
    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

    response = None
    last_error = None
    for attempt in range(1, GEMINI_MAX_RETRIES + 1):
        try:
            response = client.models.generate_content(
                model=GEMINI_CONTENT_MODEL,
                contents=build_story_prompt(topic),
            )
            break
        except errors.ServerError as exc:
            last_error = exc
            if attempt == GEMINI_MAX_RETRIES:
                raise
            wait_seconds = GEMINI_RETRY_BASE_SECONDS * attempt
            print(
                f"Gemini content generation unavailable on attempt {attempt}/"
                f"{GEMINI_MAX_RETRIES}. Retrying in {wait_seconds}s..."
            )
            time.sleep(wait_seconds)

    if response is None:
        raise last_error or RuntimeError("Gemini content generation failed without a response.")

    text = response.text.strip()
    text = text.replace("```json", "").replace("```", "").strip()
    return json.loads(text)


def _generate_story_content_from_template(topic):
    clean_topic = " ".join((topic or "This story").split())
    summary = f"{clean_topic} is trending right now and pulling people in fast."
    story_beats = [
        f"{clean_topic} just popped off online.",
        "The reaction started building almost immediately.",
        "People are sharing clips and breaking down the details.",
        "Every new update is making the story feel bigger.",
        "Now more viewers are jumping in to see what happened.",
        "The conversation keeps getting louder across platforms.",
        "This is turning into one of those stories people binge fast.",
        "And it still feels like there is more to come.",
    ]
    subtitle_lines = [
        "JUST DROPPED",
        "REACTION STARTS",
        "CLIPS EVERYWHERE",
        "GETTING BIGGER",
        "MORE PEOPLE WATCH",
        "LOUDER ONLINE",
        "BINGE THIS",
        "MORE TO COME",
    ]
    return {
        "title": clean_topic[:60],
        "hook": f"Wait, {clean_topic} is blowing up fast.",
        "summary": summary,
        "story_beats": story_beats,
        "voiceover_script": " ".join(
            [
                f"Wait, {clean_topic} is blowing up fast.",
                summary,
                *story_beats,
                "Would you watch this? Follow for part two.",
            ]
        ),
        "scene_keywords": [
            clean_topic,
            f"{clean_topic} reaction",
            f"{clean_topic} close up",
            f"{clean_topic} online buzz",
            f"{clean_topic} dramatic reveal",
            f"{clean_topic} audience reaction",
            f"{clean_topic} trending feed",
            f"{clean_topic} finale",
        ],
        "subtitle_lines": subtitle_lines,
        "scene_plan": [],
        "youtube_description": (
            f"{summary} This short breaks down why {clean_topic} is moving so fast online. "
            "#shorts #trending #viral"
        ),
        "youtube_tags": ["Shorts", "Trending", "Viral", "Story", "News"],
    }


def generate_story_content():
    topic_info = get_random_topic()
    topic = topic_info["topic"]

    content = None
    openai_error = None
    gemini_error = None
    if OPENAI_API_KEY:
        try:
            print(f"Using OpenAI model {OPENAI_CONTENT_MODEL} for story generation...")
            content = _generate_story_content_with_openai(topic)
        except Exception as exc:
            openai_error = exc
            print(
                f"OpenAI story generation failed ({type(exc).__name__}: {exc}). "
                "Falling back to Gemini..."
            )

    if content is None:
        try:
            content = _generate_story_content_with_gemini(topic)
        except Exception as exc:
            gemini_error = exc
            print(
                f"Gemini story generation failed ({type(exc).__name__}: {exc}). "
                "Using template fallback story package..."
            )
            content = _generate_story_content_from_template(topic)

    try:
        return normalize_story_content(topic, topic_info, content)
    except Exception:
        if openai_error is not None:
            raise RuntimeError(
                f"Story generation failed to normalize after OpenAI fallback attempt: {openai_error}"
            )
        if gemini_error is not None:
            raise RuntimeError(
                f"Story generation failed to normalize after Gemini fallback attempt: {gemini_error}"
            )
        raise
