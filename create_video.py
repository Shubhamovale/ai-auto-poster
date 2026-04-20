import json
import hashlib
import os
import random
import re
import textwrap
import time
from io import BytesIO

import numpy as np
import requests
from gtts import gTTS
from google import genai
from google.genai import types
from PIL import Image, ImageDraw, ImageFont
from moviepy.audio.AudioClip import AudioArrayClip
from moviepy.editor import (
    AudioFileClip,
    ColorClip,
    CompositeAudioClip,
    CompositeVideoClip,
    ImageClip,
    VideoFileClip,
    concatenate_videoclips,
)
from moviepy.video.fx.all import speedx
from moviepy.video.fx.fadein import fadein
from moviepy.video.fx.fadeout import fadeout

if not hasattr(Image, "ANTIALIAS"):
    Image.ANTIALIAS = Image.Resampling.LANCZOS


VOICEOVER_SPEED = float(os.environ.get("VOICEOVER_SPEED", "1.12"))
DEFAULT_ELEVENLABS_VOICE_ID = "EXAVITQu4vr4xnSDxMaL"
ALLOW_STOCK_FALLBACK = os.environ.get("ALLOW_STOCK_FALLBACK", "false").strip().lower() in {
    "1",
    "true",
    "yes",
}
HERA_API_KEY = os.environ.get("HERA_API_KEY", "").strip()
HERA_RESOLUTION = os.environ.get("HERA_RESOLUTION", "720p")
HERA_FPS = os.environ.get("HERA_FPS", "30")
HERA_POLL_SECONDS = int(os.environ.get("HERA_POLL_SECONDS", "10"))
HERA_MAX_POLLS = int(os.environ.get("HERA_MAX_POLLS", "36"))
VEO_MODEL = os.environ.get("VEO_MODEL", "veo-3.1-generate-preview")
VEO_RESOLUTION = os.environ.get("VEO_RESOLUTION", "720p")
VEO_DURATION_SECONDS = int(os.environ.get("VEO_DURATION_SECONDS", "8"))
VEO_POLL_SECONDS = int(os.environ.get("VEO_POLL_SECONDS", "10"))


def fetch_background_image(keyword):
    try:
        url = (
            f"https://api.unsplash.com/photos/random"
            f"?query={keyword}&orientation=portrait"
            f"&client_id={os.environ['UNSPLASH_ACCESS_KEY']}"
        )
        resp = requests.get(url, timeout=10)
        data = resp.json()
        print(f"Unsplash response keys: {list(data.keys())}")

        if "urls" in data:
            img_url = data["urls"]["regular"]
        elif "errors" in data:
            print(f"Unsplash error: {data['errors']}")
            return Image.new("RGB", (1080, 1920), color=(30, 30, 50))
        else:
            print(f"Unexpected response: {data}")
            return Image.new("RGB", (1080, 1920), color=(30, 30, 50))

        img_data = requests.get(img_url, timeout=10).content
        img = Image.open(BytesIO(img_data)).convert("RGB")
        return img.resize((1080, 1920))
    except Exception as e:
        print(f"Image fetch failed: {e}, using fallback")
        return Image.new("RGB", (1080, 1920), color=(30, 30, 50))


def get_genai_client():
    return genai.Client(api_key=os.environ["GEMINI_API_KEY"])


def create_text_frame(
    background_img,
    text,
    subtitle="",
    text_color="white",
    font_size=70,
    accent_color=(29, 161, 242),
    layout="standard",
):
    img = background_img.copy()
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 125))
    img = img.convert("RGBA")
    img = Image.alpha_composite(img, overlay)
    img = img.convert("RGB")
    draw = ImageDraw.Draw(img)

    try:
        font_big = ImageFont.truetype(
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", font_size
        )
        font_sub = ImageFont.truetype(
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 45
        )
        font_brand = ImageFont.truetype(
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 40
        )
    except Exception:
        font_big = ImageFont.load_default()
        font_sub = ImageFont.load_default()
        font_brand = ImageFont.load_default()

    draw.rectangle([0, 0, 1080, 110], fill=accent_color)
    draw.text((30, 30), "AI AUTO POSTER", font=font_brand, fill="white")

    wrap_width = 14 if layout == "hook" else 18
    wrapped = textwrap.fill(text, width=wrap_width)
    lines = wrapped.split("\n")
    y_start = 520 if layout == "hook" else 760
    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font_big)
        w = bbox[2] - bbox[0]
        x = (1080 - w) // 2
        draw.rounded_rectangle(
            [x - 28, y_start - 18, x + w + 28, y_start + font_size + 18],
            radius=24,
            fill=(0, 0, 0, 165),
        )
        draw.text((x + 3, y_start + 3), line, font=font_big, fill="black")
        draw.text((x, y_start), line, font=font_big, fill=text_color)
        y_start += font_size + 26

    if subtitle:
        wrapped_sub = textwrap.fill(subtitle, width=24 if layout == "hook" else 28)
        sub_lines = wrapped_sub.split("\n")
        y_sub = y_start + 34
        for line in sub_lines:
            bbox = draw.textbbox((0, 0), line, font=font_sub)
            w = bbox[2] - bbox[0]
            x = (1080 - w) // 2
            draw.rounded_rectangle(
                [x - 24, y_sub - 12, x + w + 24, y_sub + 54],
                radius=20,
                fill=(20, 20, 20, 180),
            )
            draw.text((x, y_sub), line, font=font_sub, fill="#FFD700")
            y_sub += 55

    draw.rectangle([0, 1815, 1080, 1920], fill=accent_color)
    draw.text((30, 1844), "FOLLOW FOR DAILY AI SHORTS", font=font_brand, fill="white")

    return np.array(img)


def create_subtitle_overlay(text, duration, size=(1080, 1920)):
    width, height = size
    canvas = Image.new("RGBA", size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(canvas)

    try:
        font = ImageFont.truetype(
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 66
        )
    except Exception:
        font = ImageFont.load_default()

    wrapped = textwrap.fill(text.upper(), width=16)
    lines = wrapped.split("\n")
    line_height = 80
    total_height = len(lines) * line_height + 44
    top = height - 620

    draw.rounded_rectangle(
        [80, top, width - 80, top + total_height],
        radius=28,
        fill=(0, 0, 0, 210),
    )

    y = top + 22
    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font)
        line_width = bbox[2] - bbox[0]
        x = (width - line_width) // 2
        draw.text((x + 3, y + 3), line, font=font, fill="black")
        draw.text((x, y), line, font=font, fill="white")
        y += line_height

    base = ImageClip(np.array(canvas)).set_duration(duration)

    def subtitle_position(t):
        progress = min(max(t / max(duration, 0.001), 0), 1)
        settle = min(progress / 0.18, 1)
        lift = int((1 - settle) * 44)
        pulse = int(max(0, np.sin(progress * np.pi * 1.2)) * 6)
        return ("center", top - lift - pulse)

    return base.set_position(subtitle_position).fadein(min(0.12, duration / 4))


def create_youtube_style_subtitle(text, duration, size=(1080, 1920)):
    from moviepy.editor import ImageClip, concatenate_videoclips
    from PIL import Image, ImageDraw, ImageFont
    import numpy as np
    import textwrap

    words = (text or "").upper().split()
    if not words:
        words = [""]
        
    word_duration = duration / len(words)
    clips = []

    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 60)
    except Exception:
        font = ImageFont.load_default()

    wrapped_lines = textwrap.wrap(" ".join(words), width=18)
    line_height = 85
    total_height = len(wrapped_lines) * line_height
    start_y = (size[1] - total_height) // 2 + 350
    
    current_word_global = 0
    
    for word_idx in range(len(words)):
        canvas = Image.new("RGBA", size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(canvas)
        
        drawn_y = start_y
        word_counter = 0
        
        for line in wrapped_lines:
            line_words = line.split()
            line_w = 0
            word_boxes = []
            
            for lw in line_words:
                bbox = draw.textbbox((0, 0), lw, font=font)
                w = bbox[2] - bbox[0]
                word_boxes.append(w)
                line_w += w + 20
                
            line_w -= 20
            start_x = (size[0] - line_w) // 2
            drawn_x = start_x
            
            for i, lw in enumerate(line_words):
                is_active = (word_counter == word_idx)
                w = word_boxes[i]
                
                if is_active:
                    draw.rounded_rectangle(
                        [drawn_x - 15, drawn_y - 10, drawn_x + w + 15, drawn_y + 85],
                        radius=15, fill=(0, 0, 0, 230)
                    )
                else:
                    draw.rounded_rectangle(
                        [drawn_x - 15, drawn_y - 10, drawn_x + w + 15, drawn_y + 85],
                        radius=15, fill=(0, 0, 0, 120)
                    )
                    
                draw.text((drawn_x + 4, drawn_y + 4), lw, font=font, fill="black")
                color = "#FFD700" if is_active else "white"
                draw.text((drawn_x, drawn_y), lw, font=font, fill=color)
                
                drawn_x += w + 20
                word_counter += 1
                
            drawn_y += line_height
            
        clip = ImageClip(np.array(canvas)).set_duration(word_duration)
        clips.append(clip)

    if not clips:
        canvas = Image.new("RGBA", size, (0, 0, 0, 0))
        return ImageClip(np.array(canvas)).set_duration(duration)

    return concatenate_videoclips(clips, method="compose").set_duration(duration)


def create_transition_flash(duration, color=(255, 255, 255), opacity=0.16, size=(1080, 1920)):
    flash_duration = max(0.04, min(0.14, duration))
    flash = ColorClip(size, color=color).set_duration(flash_duration).set_opacity(opacity)
    return flash.fx(fadeout, min(0.12, flash_duration))


def create_hud_overlay(duration, motif, visual_world, size=(1080, 1920)):
    if motif not in {"interface", "product", "stage"}:
        return None

    width, height = size
    canvas = Image.new("RGBA", size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(canvas)
    accent = visual_world["accent"]

    if motif == "interface":
        draw.rounded_rectangle((90, 180, width - 90, 430), radius=28, outline=(*accent, 110), width=3)
        draw.rounded_rectangle((130, 230, width - 180, 266), radius=12, fill=(255, 255, 255, 36))
        draw.rounded_rectangle((130, 292, width - 260, 324), radius=10, fill=(255, 255, 255, 24))
        draw.rounded_rectangle((130, 348, width - 340, 380), radius=10, fill=(255, 255, 255, 20))
        draw.arc((width - 320, 520, width - 100, 740), start=210, end=340, fill=(*accent, 120), width=5)
        draw.arc((width - 350, 490, width - 70, 770), start=205, end=345, fill=(255, 255, 255, 60), width=2)
    elif motif == "product":
        draw.rounded_rectangle((110, 220, width - 110, height - 260), radius=42, outline=(*accent, 75), width=3)
        draw.line((160, 280, width - 160, 280), fill=(255, 255, 255, 45), width=2)
        draw.line((160, height - 320, width - 160, height - 320), fill=(255, 255, 255, 45), width=2)
        draw.ellipse((width - 260, 180, width - 140, 300), outline=(*accent, 120), width=4)
    elif motif == "stage":
        draw.line((120, height - 420, width - 120, height - 420), fill=(*accent, 90), width=4)
        draw.line((190, height - 360, width - 190, height - 360), fill=(255, 255, 255, 45), width=2)
        draw.arc((120, 120, width - 120, height - 520), start=18, end=162, fill=(*accent, 85), width=4)

    clip = ImageClip(np.array(canvas)).set_duration(duration)

    def overlay_position(t):
        progress = min(max(t / max(duration, 0.001), 0), 1)
        drift = int((1 - progress) * 12)
        return (0, -drift)

    return clip.set_position(overlay_position).fadein(min(0.12, duration / 4)).set_opacity(0.82)


def _seed_from_text(*parts):
    payload = "||".join(part or "" for part in parts)
    return int(hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16], 16)


def _build_visual_world(keyword, visual_direction):
    seed = _seed_from_text(keyword, visual_direction, "visual-world")
    rng = random.Random(seed)
    color_a = (
        rng.randint(18, 70),
        rng.randint(42, 120),
        rng.randint(78, 220),
    )
    color_b = (
        rng.randint(110, 240),
        rng.randint(60, 170),
        rng.randint(38, 140),
    )
    accent = (
        rng.randint(210, 255),
        rng.randint(170, 245),
        rng.randint(120, 220),
    )
    shadow = (
        rng.randint(4, 20),
        rng.randint(6, 24),
        rng.randint(10, 34),
    )
    return {
        "seed": seed,
        "color_a": color_a,
        "color_b": color_b,
        "accent": accent,
        "shadow": shadow,
    }


def _gradient_background(size, seed, visual_world):
    width, height = size
    rng = random.Random(seed)
    base = np.zeros((height, width, 3), dtype=np.uint8)
    color_a = np.array(visual_world["color_a"], dtype=np.float32)
    color_b = np.array(visual_world["color_b"], dtype=np.float32)
    # Keep scene-to-scene continuity while allowing subtle per-scene drift.
    drift = np.array(
        [rng.randint(-8, 8), rng.randint(-10, 10), rng.randint(-12, 12)],
        dtype=np.float32,
    )
    color_a = np.clip(color_a + drift, 0, 255)
    color_b = np.clip(color_b - drift, 0, 255)
    vertical = np.linspace(0.0, 1.0, height, dtype=np.float32)[:, None, None]
    horizontal = np.linspace(0.0, 1.0, width, dtype=np.float32)[None, :, None]
    blend = np.clip((0.68 * vertical) + (0.32 * horizontal), 0.0, 1.0)
    base[:] = (color_a * (1.0 - blend) + color_b * blend).astype(np.uint8)
    return Image.fromarray(base, mode="RGB")


def _draw_scene_shapes(draw, size, seed, visual_world):
    width, height = size
    rng = random.Random(seed)

    for _ in range(10):
        x0 = rng.randint(-140, width - 120)
        y0 = rng.randint(-160, height - 120)
        x1 = x0 + rng.randint(180, 520)
        y1 = y0 + rng.randint(160, 500)
        color = (
            min(255, visual_world["accent"][0] + rng.randint(-24, 12)),
            min(255, visual_world["accent"][1] + rng.randint(-30, 10)),
            min(255, visual_world["accent"][2] + rng.randint(-38, 8)),
            rng.randint(40, 95),
        )
        draw.ellipse((x0, y0, x1, y1), fill=color)

    for _ in range(12):
        y = rng.randint(140, height - 180)
        draw.rounded_rectangle(
            (rng.randint(-40, 220), y, rng.randint(700, width + 60), y + rng.randint(8, 18)),
            radius=9,
            fill=(255, 255, 255, rng.randint(18, 55)),
        )


def _draw_cinematic_panels(draw, size, seed, visual_world):
    width, height = size
    rng = random.Random(seed + 17)
    panel_count = 2 + (seed % 2)
    for index in range(panel_count):
        panel_w = rng.randint(420, 760)
        panel_h = rng.randint(300, 620)
        x0 = rng.randint(-40, width - panel_w + 40)
        y0 = rng.randint(140, height - panel_h - 240)
        x1 = x0 + panel_w
        y1 = y0 + panel_h
        fill = (
            max(0, min(255, visual_world["shadow"][0] + rng.randint(8, 32))),
            max(0, min(255, visual_world["shadow"][1] + rng.randint(14, 42))),
            max(0, min(255, visual_world["shadow"][2] + rng.randint(20, 56))),
            rng.randint(135, 210),
        )
        outline = (
            min(255, visual_world["accent"][0] + rng.randint(-12, 18)),
            min(255, visual_world["accent"][1] + rng.randint(-14, 16)),
            min(255, visual_world["accent"][2] + rng.randint(-16, 14)),
            rng.randint(55, 120),
        )
        draw.rounded_rectangle((x0, y0, x1, y1), radius=34, fill=fill, outline=outline, width=3)

        inner_lines = 3 + ((index + seed) % 4)
        for line_index in range(inner_lines):
            line_y = y0 + 34 + (line_index * rng.randint(46, 72))
            if line_y >= y1 - 24:
                break
            draw.rounded_rectangle(
                (x0 + 28, line_y, x1 - rng.randint(60, 180), line_y + rng.randint(10, 18)),
                radius=8,
                fill=(255, 255, 255, rng.randint(26, 66)),
            )


def _draw_light_flares(draw, size, seed, visual_world):
    width, height = size
    rng = random.Random(seed + 41)
    for _ in range(3):
        flare_w = rng.randint(320, 780)
        flare_h = rng.randint(120, 260)
        x0 = rng.randint(-180, width - 120)
        y0 = rng.randint(-40, height - 160)
        x1 = x0 + flare_w
        y1 = y0 + flare_h
        color = (
            min(255, visual_world["accent"][0] + rng.randint(-8, 22)),
            min(255, visual_world["accent"][1] + rng.randint(-30, 28)),
            min(255, visual_world["accent"][2] + rng.randint(-46, 24)),
            rng.randint(18, 42),
        )
        draw.ellipse((x0, y0, x1, y1), fill=color)


def _draw_silhouette(draw, size, seed, visual_world):
    width, height = size
    rng = random.Random(seed + 89)
    center_x = rng.randint(int(width * 0.25), int(width * 0.75))
    base_y = rng.randint(int(height * 0.62), int(height * 0.82))
    body_w = rng.randint(160, 260)
    body_h = rng.randint(300, 520)
    head_r = rng.randint(44, 72)

    silhouette = (
        visual_world["shadow"][0],
        visual_world["shadow"][1],
        visual_world["shadow"][2],
        rng.randint(150, 220),
    )
    glow = (
        min(255, visual_world["accent"][0] + 14),
        min(255, visual_world["accent"][1] + 8),
        min(255, visual_world["accent"][2] + 4),
        rng.randint(20, 45),
    )

    draw.ellipse(
        (center_x - head_r, base_y - body_h - (head_r * 2), center_x + head_r, base_y - body_h),
        fill=silhouette,
    )
    draw.rounded_rectangle(
        (center_x - body_w // 2, base_y - body_h, center_x + body_w // 2, base_y),
        radius=body_w // 4,
        fill=silhouette,
    )
    draw.ellipse(
        (center_x - head_r - 18, base_y - body_h - (head_r * 2) - 18, center_x + head_r + 18, base_y - body_h + 18),
        outline=glow,
        width=4,
    )


def _directional_motif(keyword, visual_direction):
    text = " ".join([keyword or "", visual_direction or ""]).lower()
    if any(term in text for term in ["interface", "screen", "ui", "display", "overlay", "app"]):
        return "interface"
    if any(term in text for term in ["reaction", "face", "portrait", "people", "fans", "crowd"]):
        return "portrait"
    if any(term in text for term in ["product", "device", "phone", "glasses", "console", "controller"]):
        return "product"
    if any(term in text for term in ["event", "stage", "launch", "keynote", "announcement"]):
        return "stage"
    return "abstract"


def build_veo_scene_prompt(scene_type, keyword, visual_direction, subtitle="", scene_index=0):
    scene_type = (scene_type or "abstract").lower()
    beat = " ".join((visual_direction or keyword or "").split())
    subtitle = " ".join((subtitle or "").split())

    cinematic_rules = (
        "Create a cinematic vertical 9:16 shot with realistic lighting, premium camera movement, "
        "high detail, filmic contrast, shallow depth of field where appropriate, and no text overlays."
    )

    scene_recipes = {
        "hook": "Open with an immediate visual hook and a premium reveal moment.",
        "product_reveal": "Show a dramatic product-style reveal with close details and sleek motion.",
        "interface": "Show a modern app or interface scene with layered screen motion and futuristic UI energy.",
        "reaction": "Show a believable human reaction shot with expressive body language and mood.",
        "feature_demo": "Show a feature demonstration in action with clear visual cause and effect.",
        "stage": "Show a keynote or launch-stage mood with presentation energy and spotlight lighting.",
        "social_proof": "Show momentum, buzz, reactions, and a sense that many people are paying attention.",
        "consequence": "Show the impact or next-step consequence of what just happened.",
        "cta": "End on a bold, memorable cinematic final beat that feels like a short-form video closer.",
        "abstract": "Show a stylized cinematic visual that matches the sentence without looking like a graphic card.",
    }
    recipe = scene_recipes.get(scene_type, scene_recipes["abstract"])

    return (
        f"{cinematic_rules} {recipe} "
        f"Scene {scene_index + 1}. "
        f"Primary concept: {keyword}. "
        f"Story beat: {beat}. "
        f"Emotional cue: {subtitle}. "
        "No captions, no subtitles burned in, no floating info cards, no flat poster layout."
    )


def build_hera_scene_prompt(scene_type, keyword, visual_direction, subtitle="", scene_index=0):
    scene_type = (scene_type or "abstract").lower()
    beat = " ".join((visual_direction or keyword or "").split())
    subtitle = " ".join((subtitle or "").split())
    recipes = {
        "hook": "Start with a sharp animated hook and immediate motion-graphics impact.",
        "product_reveal": "Use sleek reveal animation, layered lighting, and premium product-style motion.",
        "interface": "Use UI-inspired motion graphics, layered panels, animated interface cues, and screen-energy.",
        "reaction": "Use expressive silhouette, pulse energy, kinetic typography-safe motion, and social buzz mood.",
        "feature_demo": "Show feature-explainer motion graphics with cause-and-effect animation and visual clarity.",
        "stage": "Use launch-event energy, spotlight motion, bold framing, and keynote-style presentation cues.",
        "social_proof": "Show momentum, community energy, trending motion, and fast-moving attention signals.",
        "consequence": "Show escalation and aftermath with more intensity and larger animated motion cues.",
        "cta": "End with a strong closer beat, bold motion, and short-form final-hit energy.",
        "abstract": "Use cinematic motion-graphics background visuals that match the story beat without on-screen text.",
    }
    recipe = recipes.get(scene_type, recipes["abstract"])
    return (
        "Create a premium vertical 9:16 motion-graphics background video for a YouTube Short. "
        f"{recipe} "
        f"Scene {scene_index + 1}. "
        f"Primary concept: {keyword}. "
        f"Story beat: {beat}. "
        f"Mood cue: {subtitle}. "
        "No captions, no subtitles, no embedded text, no logos, no watermarks. "
        "Focus on animated background visuals that can sit behind narration."
    )


def generate_veo_scene_video(prompt, output_path):
    client = get_genai_client()
    operation = client.models.generate_videos(
        model=VEO_MODEL,
        prompt=prompt,
        config=types.GenerateVideosConfig(
            aspect_ratio="9:16",
            duration_seconds=VEO_DURATION_SECONDS,
            resolution=VEO_RESOLUTION,
            number_of_videos=1,
        ),
    )

    while not operation.done:
        print("Waiting for Veo scene generation...")
        time.sleep(VEO_POLL_SECONDS)
        operation = client.operations.get(operation)

    generated_video = operation.response.generated_videos[0]
    client.files.download(file=generated_video.video)
    generated_video.video.save(output_path)
    return output_path


def generate_hera_scene_video(prompt, output_path, duration_seconds=4):
    if not HERA_API_KEY:
        raise RuntimeError("HERA_API_KEY is required for Hera background video generation.")

    headers = {
        "Content-Type": "application/json",
        "x-api-key": HERA_API_KEY,
    }
    payload = {
        "prompt": prompt,
        "outputs": [
            {
                "format": "mp4",
                "aspect_ratio": "9:16",
                "fps": HERA_FPS,
                "resolution": HERA_RESOLUTION,
            }
        ],
        "duration_seconds": max(1, min(60, int(round(duration_seconds)))),
    }

    create_response = requests.post(
        "https://api.hera.video/v1/videos",
        headers=headers,
        json=payload,
        timeout=60,
    )
    create_response.raise_for_status()
    video_id = create_response.json()["video_id"]

    status_url = f"https://api.hera.video/v1/videos/{video_id}"
    last_payload = None
    for poll_index in range(HERA_MAX_POLLS):
        time.sleep(HERA_POLL_SECONDS if poll_index else 0)
        status_response = requests.get(status_url, headers={"x-api-key": HERA_API_KEY}, timeout=60)
        status_response.raise_for_status()
        last_payload = status_response.json()
        status = (last_payload.get("status") or "").lower()
        if status == "success":
            break
        if status == "failed":
            output_errors = [
                output.get("error")
                for output in last_payload.get("outputs", [])
                if output.get("error")
            ]
            raise RuntimeError(
                f"Hera video generation failed for {video_id}: "
                f"{'; '.join(output_errors) if output_errors else 'unknown error'}"
            )
    else:
        raise RuntimeError(f"Hera video generation timed out for {video_id}.")

    outputs = last_payload.get("outputs", []) if last_payload else []
    file_url = next((item.get("file_url") for item in outputs if item.get("file_url")), None)
    if not file_url:
        raise RuntimeError(f"Hera video generation succeeded for {video_id} but no file_url was returned.")

    download_file(file_url, output_path)
    return output_path


def _draw_hero_reveal(draw, size, visual_world):
    width, height = size
    center_x = width // 2
    center_y = int(height * 0.44)

    accent = visual_world["accent"]
    shadow = visual_world["shadow"]

    draw.ellipse(
        (center_x - 250, center_y - 250, center_x + 250, center_y + 250),
        fill=(accent[0], accent[1], accent[2], 34),
    )
    draw.ellipse(
        (center_x - 180, center_y - 180, center_x + 180, center_y + 180),
        outline=(255, 255, 255, 80),
        width=5,
    )
    draw.rounded_rectangle(
        (center_x - 190, center_y - 320, center_x + 190, center_y + 320),
        radius=72,
        fill=(shadow[0] + 8, shadow[1] + 10, shadow[2] + 14, 165),
        outline=(accent[0], accent[1], accent[2], 92),
        width=4,
    )
    draw.rounded_rectangle(
        (center_x - 130, center_y - 240, center_x + 130, center_y + 160),
        radius=48,
        fill=(255, 255, 255, 20),
        outline=(255, 255, 255, 52),
        width=3,
    )


def create_generated_scene_frame(keyword, visual_direction="", scene_index=0, size=(1080, 1920), visual_world=None):
    width, height = size
    visual_world = visual_world or _build_visual_world(keyword, visual_direction)
    seed = _seed_from_text(keyword, visual_direction, str(scene_index))
    bg = _gradient_background(size, seed, visual_world).convert("RGBA")
    overlay = Image.new("RGBA", size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    _draw_scene_shapes(draw, size, seed, visual_world)
    _draw_light_flares(draw, size, seed, visual_world)

    motif = _directional_motif(keyword, visual_direction)
    if motif in {"interface", "stage"}:
        _draw_cinematic_panels(draw, size, seed, visual_world)
    if motif in {"portrait", "stage", "abstract"}:
        _draw_silhouette(draw, size, seed, visual_world)
    if motif == "product":
        _draw_cinematic_panels(draw, size, seed + 101, visual_world)
    if scene_index == 0:
        _draw_hero_reveal(draw, size, visual_world)

    vignette = Image.new("RGBA", size, (0, 0, 0, 0))
    vignette_draw = ImageDraw.Draw(vignette)
    vignette_draw.rectangle((0, 0, width, 220), fill=(0, 0, 0, 65))
    vignette_draw.rectangle((0, height - 260, width, height), fill=(0, 0, 0, 78))
    vignette_draw.rounded_rectangle((26, 26, width - 26, height - 26), radius=38, outline=(255, 255, 255, 22), width=2)

    frame = Image.alpha_composite(bg, overlay)
    frame = Image.alpha_composite(frame, vignette)
    draw = ImageDraw.Draw(frame)

    try:
        label_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 28)
        small_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 30)
    except Exception:
        label_font = ImageFont.load_default()
        small_font = ImageFont.load_default()

    badge = "REVEAL" if scene_index == 0 else motif.upper()
    badge_w = 86 + (len(badge) * 14)
    draw.rounded_rectangle((58, 72, 58 + badge_w, 124), radius=22, fill=(255, 255, 255, 38))
    draw.text((82, 85), badge, font=label_font, fill="white")

    descriptor = " ".join((visual_direction or keyword or "").split())[:80].upper()
    if descriptor:
        descriptor = textwrap.shorten(descriptor, width=42, placeholder="...")
        bbox = draw.textbbox((0, 0), descriptor, font=small_font)
        line_w = bbox[2] - bbox[0]
        x = (width - line_w) // 2
        draw.rounded_rectangle(
            (x - 20, height - 170, x + line_w + 20, height - 118),
            radius=20,
            fill=(255, 255, 255, 24),
        )
        draw.text((x, height - 158), descriptor, font=small_font, fill="#F7F2D0")

    return np.array(frame.convert("RGB"))


def create_generated_scene_clip(keyword, visual_direction, duration, scene_index, visual_world=None):
    frame = create_generated_scene_frame(
        keyword,
        visual_direction,
        scene_index,
        visual_world=visual_world,
    )
    motion_variants = [
        "push_in",
        "pan_left",
        "pan_right",
        "tilt_up",
        "tilt_down",
        "drift_left",
        "drift_right",
    ]
    if scene_index == 0:
        zoom_start = 1.04
        zoom_end = 1.13
        motion_variant = "push_in"
    else:
        zoom_start = 1.0 + (0.01 * (scene_index % 3))
        zoom_end = 1.08 + (0.015 * (scene_index % 4))
        motion_variant = motion_variants[(scene_index - 1) % len(motion_variants)]
    return build_motion_clip(
        frame,
        duration=duration,
        zoom_start=zoom_start,
        zoom_end=zoom_end,
        fade=0.08,
        motion_variant=motion_variant,
    )


def build_scene_durations(target_duration, scene_count):
    if scene_count < 2:
        return [target_duration]

    hook_duration = 3.0
    cta_duration = 2.0
    middle_count = scene_count - 2
    remaining = max(target_duration - hook_duration - cta_duration, middle_count * 2.3)
    middle_duration = remaining / max(middle_count, 1)
    return [hook_duration] + [middle_duration] * middle_count + [cta_duration]


def create_background_music(duration, sample_rate=44100):
    timeline = np.linspace(0, duration, int(sample_rate * duration), endpoint=False)

    bpm = 108
    beats_per_second = bpm / 60.0
    beat_phase = timeline * beats_per_second
    beat_fraction = beat_phase - np.floor(beat_phase)

    kick = np.sin(2 * np.pi * 55 * timeline) * np.exp(-10 * beat_fraction)
    snare_mask = ((np.floor(beat_phase) % 2) == 1).astype(np.float32)
    snare = snare_mask * np.random.normal(0, 0.22, len(timeline)) * np.exp(-20 * beat_fraction)
    hat = np.random.normal(0, 0.08, len(timeline)) * np.exp(-55 * beat_fraction)

    progression = np.array([110.0, 146.83, 164.81, 130.81], dtype=np.float32)
    chord_index = ((timeline / 2.0).astype(int)) % len(progression)
    root = progression[chord_index]
    pad = (
        0.12 * np.sin(2 * np.pi * root * timeline)
        + 0.08 * np.sin(2 * np.pi * (root * 1.25) * timeline)
        + 0.06 * np.sin(2 * np.pi * (root * 1.5) * timeline)
    )
    bass = 0.10 * np.sin(2 * np.pi * (root / 2.0) * timeline)
    lead = 0.04 * np.sin(2 * np.pi * (root * 2.0) * timeline + np.sin(2 * np.pi * 0.35 * timeline))

    sidechain = 1.0 - 0.22 * np.exp(-18 * beat_fraction)
    audio = ((0.34 * kick) + (0.20 * snare) + (0.12 * hat) + pad + bass + lead) * sidechain
    audio = np.clip(audio * 0.58, -0.95, 0.95)
    stereo = np.stack([audio, audio], axis=1).astype(np.float32)
    return AudioArrayClip(stereo, fps=sample_rate)


def build_video_prompt(title, points, image_keyword, video_prompt=None):
    if video_prompt and video_prompt.strip():
        return video_prompt.strip()

    points_text = ", ".join(points[:4])
    return (
        f"Create a cinematic vertical 9:16 short video about '{title}'. "
        f"Use {image_keyword} inspired environments and visuals. "
        f"Show scenes that communicate these beats: {points_text}. "
        f"Fast pacing, strong visual hook, dramatic lighting, smooth camera motion, "
        f"modern AI-tech mood, realistic detail, no text overlays, no watermarks."
    )


def save_video_assets(output_dir, content, video_prompt):
    os.makedirs(output_dir, exist_ok=True)

    prompt_path = os.path.join(output_dir, "reel_video_prompt.txt")
    with open(prompt_path, "w", encoding="utf-8") as f:
        f.write(video_prompt + "\n")

    metadata = dict(content)
    metadata["video_prompt"] = video_prompt
    metadata_path = os.path.join(output_dir, "reel_video_metadata.json")
    with open(metadata_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)

    return prompt_path, metadata_path


def build_motion_clip(
    frame,
    duration,
    zoom_start=1.0,
    zoom_end=1.08,
    fade=0.2,
    motion_variant="zoom_in",
    size=(1080, 1920),
):
    width, height = size
    clip = ImageClip(frame).set_duration(duration)
    max_zoom = max(zoom_start, zoom_end, 1.0)
    animated = clip.resize(lambda t: zoom_start + (zoom_end - zoom_start) * (t / max(duration, 0.001)))

    def position(t):
        progress = min(max(t / max(duration, 0.001), 0), 1)
        scaled_w = width * max_zoom
        scaled_h = height * max_zoom
        x_room = max(scaled_w - width, 0)
        y_room = max(scaled_h - height, 0)

        if motion_variant == "pan_left":
            x = -x_room * progress
            y = -y_room * 0.15
        elif motion_variant == "pan_right":
            x = -x_room * (1 - progress)
            y = -y_room * 0.2
        elif motion_variant == "tilt_up":
            x = -x_room * 0.5
            y = -y_room * progress
        elif motion_variant == "tilt_down":
            x = -x_room * 0.45
            y = -y_room * (1 - progress)
        elif motion_variant == "push_in":
            x = -x_room * 0.5
            y = -y_room * 0.5
        elif motion_variant == "drift_left":
            x = -x_room * (0.2 + (0.5 * progress))
            y = -y_room * (0.35 + (0.15 * progress))
        elif motion_variant == "drift_right":
            x = -x_room * (0.65 - (0.35 * progress))
            y = -y_room * (0.22 + (0.18 * progress))
        else:
            x = -x_room * 0.5
            y = -y_room * 0.5
        return (x, y)

    moving = animated.set_position(position)
    composed = CompositeVideoClip([moving], size=size).set_duration(duration)
    if fade:
        composed = composed.fx(fadein, fade).fx(fadeout, fade)
    return composed


def has_pexels_access():
    return bool(os.environ.get("PEXELS_API_KEY"))


def fetch_ai_image(prompt, path):
    import urllib.parse
    import requests
    import random
    import time
    
    seed = random.randint(1, 999999)
    safe_prompt = urllib.parse.quote(prompt)
    
    print("Waiting slightly to avoid Pollinations rate limit...")
    time.sleep(2)
    
    for attempt in range(4):
        url = f"https://image.pollinations.ai/prompt/{safe_prompt}?width=1080&height=1920&nologo=true&seed={seed}&model=flux"
        try:
            response = requests.get(url, timeout=30)
            if response.status_code == 200:
                with open(path, "wb") as f:
                    f.write(response.content)
                return path
            elif response.status_code == 429:
                print(f"Pollinations rate limit hit. Sleeping {6 * (attempt + 1)}s...")
                time.sleep(6 * (attempt + 1))
            else:
                response.raise_for_status()
        except requests.exceptions.RequestException as e:
            print(f"AI Image fetch error: {e}. Retrying...")
            time.sleep(3)
            
    raise RuntimeError("Failed to fetch AI image after retries due to rate limits.")


def fetch_pexels_video(query):
    headers = {"Authorization": os.environ["PEXELS_API_KEY"]}
    response = requests.get(
        "https://api.pexels.com/videos/search",
        headers=headers,
        params={"query": query, "orientation": "portrait", "per_page": 15},
        timeout=20,
    )
    response.raise_for_status()
    videos = response.json().get("videos", [])
    import random
    random.shuffle(videos)
    for video in videos:
        files = sorted(
            video.get("video_files", []),
            key=lambda item: item.get("height", 0) * item.get("width", 0),
            reverse=True,
        )
        for file_info in files:
            if file_info.get("width", 0) >= 720 and file_info.get("height", 0) >= 1200:
                return file_info["link"]
    return None


def download_file(url, path):
    response = requests.get(url, timeout=60)
    response.raise_for_status()
    with open(path, "wb") as f:
        f.write(response.content)
    return path


def has_elevenlabs_access():
    return bool(os.environ.get("ELEVENLABS_API_KEY"))


def create_elevenlabs_voiceover(script, output_path):
    voice_id = os.environ.get("ELEVENLABS_VOICE_ID", "").strip() or DEFAULT_ELEVENLABS_VOICE_ID
    response = requests.post(
        f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}",
        headers={
            "xi-api-key": os.environ["ELEVENLABS_API_KEY"],
            "Content-Type": "application/json",
            "Accept": "audio/mpeg",
        },
        json={
            "text": script,
            "model_id": "eleven_multilingual_v2",
            "voice_settings": {
                "stability": 0.36,
                "similarity_boost": 0.84,
                "style": 0.42,
                "use_speaker_boost": True,
            },
        },
        timeout=120,
    )
    response.raise_for_status()
    with open(output_path, "wb") as f:
        f.write(response.content)
    return output_path


def apply_voiceover_speed(output_path, speed=VOICEOVER_SPEED):
    speed = float(speed or 1.0)
    if abs(speed - 1.0) < 0.01:
        return output_path

    sped_path = os.path.splitext(output_path)[0] + "_sped.mp3"
    clip = AudioFileClip(output_path)
    sped_clip = clip.fx(speedx, speed)
    sped_clip.write_audiofile(sped_path, logger=None)
    sped_clip.close()
    clip.close()
    return sped_path


def create_voiceover(script, output_path):
    if has_elevenlabs_access():
        try:
            print("🎙️ Using ElevenLabs voiceover...")
            generated_path = create_elevenlabs_voiceover(script, output_path)
            return apply_voiceover_speed(generated_path)
        except Exception as e:
            print(f"ElevenLabs voiceover failed: {e}. Falling back to gTTS.")

    gTTS(text=script, lang="en", slow=False).save(output_path)
    return apply_voiceover_speed(output_path)


def split_sentences(text):
    sentences = re.split(r"(?<=[.!?])\s+", (text or "").strip())
    return [sentence.strip() for sentence in sentences if sentence.strip()]


def fit_vertical_clip(clip, duration):
    clip = clip.without_audio().subclip(0, min(duration, clip.duration))
    target_w, target_h = 1080, 1920
    scale = max(target_w / clip.w, target_h / clip.h)
    clip = clip.resize(scale)
    x_center = clip.w / 2
    y_center = clip.h / 2
    clip = clip.crop(
        x_center=x_center,
        y_center=y_center,
        width=target_w,
        height=target_h,
    )
    return clip.set_duration(duration).fx(fadein, 0.12).fx(fadeout, 0.12)


def create_stock_video_reel(content, output_dir):
    points = content["points"][:4]
    keywords = content.get("video_keywords") or [content["image_keyword"], *points]
    subtitle_lines = content.get("subtitle_lines") or []
    voice_path = create_voiceover(
        content["voiceover_script"],
        os.path.join(output_dir, "voiceover.mp3"),
    )
    voiceover = AudioFileClip(voice_path)
    target_duration = max(15.0, voiceover.duration + 0.8)
    scene_durations = build_scene_durations(target_duration, 6)

    scene_specs = [
        {"query": keywords[0], "duration": scene_durations[0], "subtitle": subtitle_lines[0] if len(subtitle_lines) > 0 else content["title"]},
        {"query": keywords[1] if len(keywords) > 1 else points[0], "duration": scene_durations[1], "subtitle": subtitle_lines[1] if len(subtitle_lines) > 1 else points[0]},
        {"query": keywords[2] if len(keywords) > 2 else points[1], "duration": scene_durations[2], "subtitle": subtitle_lines[2] if len(subtitle_lines) > 2 else points[1]},
        {"query": keywords[3] if len(keywords) > 3 else points[2], "duration": scene_durations[3], "subtitle": subtitle_lines[3] if len(subtitle_lines) > 3 else points[2]},
        {"query": keywords[4] if len(keywords) > 4 else points[3], "duration": scene_durations[4], "subtitle": subtitle_lines[4] if len(subtitle_lines) > 4 else points[3]},
        {"query": keywords[0], "duration": scene_durations[5], "subtitle": subtitle_lines[5] if len(subtitle_lines) > 5 else "FOLLOW FOR MORE AI TOOLS"},
    ]

    downloaded = []
    clips = []
    for index, spec in enumerate(scene_specs):
        link = fetch_pexels_video(spec["query"])
        if not link:
            raise RuntimeError(f"No stock video found for query: {spec['query']}")
        clip_path = os.path.join(output_dir, f"scene_{index + 1}.mp4")
        downloaded.append(download_file(link, clip_path))

    for index, clip_path in enumerate(downloaded):
        base_clip = VideoFileClip(clip_path)
        clip = fit_vertical_clip(base_clip, scene_specs[index]["duration"])
        subtitle_clip = create_subtitle_overlay(
            scene_specs[index]["subtitle"], scene_specs[index]["duration"]
        )
        clip = CompositeVideoClip([clip, subtitle_clip.set_position(("center", "bottom"))]).set_duration(
            scene_specs[index]["duration"]
        )
        clips.append(clip)

    final_video = concatenate_videoclips(clips, method="compose")

    target_duration = max(15.0, voiceover.duration + 0.8)
    final_video = final_video.set_duration(target_duration)
    voiceover = voiceover.set_start(0).volumex(1.0)
    music = create_background_music(target_duration).set_duration(target_duration).volumex(0.22)
    mixed_audio = CompositeAudioClip([music, voiceover]).set_duration(target_duration)
    final_video = final_video.set_audio(mixed_audio)

    output_path = os.path.join(output_dir, "reel_video.mp4")
    final_video.write_videofile(
        output_path,
        fps=30,
        codec="libx264",
        audio_codec="aac",
        temp_audiofile=os.path.join(output_dir, "temp_audio.m4a"),
        remove_temp=True,
        logger=None,
    )

    for clip in clips:
        clip.close()
    for path in downloaded:
        if os.path.exists(path):
            os.remove(path)
    mixed_audio.close()
    voiceover.close()
    final_video.close()

    return output_path


def create_slideshow_reel(content, output_dir):
    bg_img = fetch_background_image(content["image_keyword"])
    points = content["points"][:4]
    hook_subtitle = content.get("hook_subtitle") or "Wait till you see the last one."
    subtitle_lines = content.get("subtitle_lines") or []
    voice_path = create_voiceover(
        content["voiceover_script"],
        os.path.join(output_dir, "voiceover.mp3"),
    )
    voiceover = AudioFileClip(voice_path)
    target_duration = max(15.0, voiceover.duration + 0.8)
    scene_durations = build_scene_durations(target_duration, 6)
    clips = []
    colors = ["#FF4D6D", "#FFD166", "#06D6A0", "#4CC9F0"]
    accent_colors = [
        (255, 77, 109),
        (255, 209, 102),
        (6, 214, 160),
        (76, 201, 240),
    ]

    hook_frame = create_text_frame(
        bg_img,
        content["title"],
        subtitle=hook_subtitle,
        text_color="#FFD700",
        font_size=88,
        accent_color=(255, 77, 109),
        layout="hook",
    )
    hook_subtitles = create_subtitle_overlay(
        subtitle_lines[0] if len(subtitle_lines) > 0 else content["title"],
        scene_durations[0],
    )
    hook_clip = build_motion_clip(hook_frame, duration=scene_durations[0], zoom_start=1.0, zoom_end=1.12)
    clips.append(CompositeVideoClip([hook_clip, hook_subtitles.set_position(("center", "bottom"))]).set_duration(scene_durations[0]))

    for i, point in enumerate(points):
        frame = create_text_frame(
            bg_img,
            f"#{i + 1} {point.upper()}",
            subtitle=point,
            text_color=colors[i],
            font_size=92,
            accent_color=accent_colors[i],
        )
        point_duration = scene_durations[i + 1]
        point_clip = build_motion_clip(
            frame,
            duration=point_duration,
            zoom_start=1.01,
            zoom_end=1.09,
            fade=0.16,
        )
        subtitle_clip = create_subtitle_overlay(
            subtitle_lines[i + 1] if len(subtitle_lines) > i + 1 else point,
            point_duration,
        )
        clips.append(
            CompositeVideoClip([point_clip, subtitle_clip.set_position(("center", "bottom"))]).set_duration(point_duration)
        )

    cta_frame = create_text_frame(
        bg_img,
        "FOLLOW FOR PART 2",
        subtitle="More AI tools coming daily",
        text_color="#00FF88",
        font_size=78,
        accent_color=(6, 214, 160),
        layout="hook",
    )
    cta_clip = build_motion_clip(cta_frame, duration=scene_durations[5], zoom_start=1.0, zoom_end=1.06)
    cta_subtitles = create_subtitle_overlay(
        subtitle_lines[5] if len(subtitle_lines) > 5 else "FOLLOW FOR MORE AI TOOLS",
        scene_durations[5],
    )
    clips.append(CompositeVideoClip([cta_clip, cta_subtitles.set_position(("center", "bottom"))]).set_duration(scene_durations[5]))

    final_video = concatenate_videoclips(clips, method="compose")
    final_video = final_video.set_duration(target_duration)
    voiceover = voiceover.set_start(0).volumex(1.0)
    music = create_background_music(target_duration).set_duration(target_duration).volumex(0.22)
    mixed_audio = CompositeAudioClip([music, voiceover]).set_duration(target_duration)
    final_video = final_video.set_audio(mixed_audio)

    output_path = os.path.join(output_dir, "reel_video.mp4")
    final_video.write_videofile(
        output_path,
        fps=30,
        codec="libx264",
        audio_codec="aac",
        temp_audiofile=os.path.join(output_dir, "temp_audio.m4a"),
        remove_temp=True,
        logger=None,
    )
    mixed_audio.close()
    voiceover.close()
    final_video.close()
    return output_path


def create_reel_video(
    title,
    points,
    image_keyword,
    video_prompt=None,
    hook_subtitle=None,
    voiceover_script=None,
    video_keywords=None,
    subtitle_lines=None,
):
    content = {
        "title": title,
        "points": points,
        "image_keyword": image_keyword,
        "hook_subtitle": hook_subtitle,
        "video_keywords": video_keywords,
        "subtitle_lines": subtitle_lines,
    }
    output_dir = os.path.join(os.getcwd(), "output")
    video_prompt = build_video_prompt(title, points, image_keyword, video_prompt)
    content["video_prompt"] = video_prompt
    content["voiceover_script"] = voiceover_script or (
        f"Did you know these {len(points[:4])} AI tools exist? "
        + " ".join(
            f"Number {index + 1}: {point}."
            for index, point in enumerate(points[:4])
        )
        + " Follow for more AI tools."
    )
    prompt_path, metadata_path = save_video_assets(output_dir, content, video_prompt)

    print("🎥 AI video prompt ready:")
    print(video_prompt)
    print(f"📝 Saved prompt: {prompt_path}")
    print(f"🗂️ Saved metadata: {metadata_path}")

    if not has_pexels_access():
        if ALLOW_STOCK_FALLBACK:
            print("🎞️ Pexels key missing, falling back to slideshow reel...")
            output_path = create_slideshow_reel(content, output_dir)
        else:
            raise RuntimeError(
                "PEXELS_API_KEY missing and fallback stock/slideshow generation is disabled."
            )
    else:
        try:
            print("🎞️ Creating reel from real stock video clips...")
            output_path = create_stock_video_reel(content, output_dir)
        except Exception as e:
            if ALLOW_STOCK_FALLBACK:
                print(f"Stock video reel failed: {e}")
                print("🎞️ Falling back to slideshow reel...")
                output_path = create_slideshow_reel(content, output_dir)
            else:
                raise RuntimeError(
                    f"Strict production mode: stock fallback disabled after video failure: {e}"
                ) from e

    print(f"✅ Video created: {output_path}")
    return output_path, prompt_path, metadata_path
