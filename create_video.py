import json
import os
import random
import re
import textwrap
from io import BytesIO

import numpy as np
import requests
from gtts import gTTS
from PIL import Image, ImageDraw, ImageFont
from moviepy.audio.AudioClip import AudioArrayClip
from moviepy.audio.fx.all import audio_speedx
from moviepy.editor import (
    AudioFileClip,
    CompositeAudioClip,
    CompositeVideoClip,
    ImageClip,
    VideoFileClip,
    concatenate_videoclips,
)
from moviepy.video.fx.fadein import fadein
from moviepy.video.fx.fadeout import fadeout

if not hasattr(Image, "ANTIALIAS"):
    Image.ANTIALIAS = Image.Resampling.LANCZOS


VOICEOVER_SPEED = float(os.environ.get("VOICEOVER_SPEED", "1.12"))


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

    wrapped = textwrap.fill(text.upper(), width=18)
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

    return ImageClip(np.array(canvas)).set_duration(duration)


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


def build_motion_clip(frame, duration, zoom_start=1.0, zoom_end=1.08, fade=0.2):
    clip = ImageClip(frame).set_duration(duration)
    clip = clip.resize(lambda t: zoom_start + (zoom_end - zoom_start) * (t / duration))
    if fade:
        clip = clip.fx(fadein, fade).fx(fadeout, fade)
    return clip


def has_pexels_access():
    return bool(os.environ.get("PEXELS_API_KEY"))


def fetch_pexels_video(query):
    headers = {"Authorization": os.environ["PEXELS_API_KEY"]}
    response = requests.get(
        "https://api.pexels.com/videos/search",
        headers=headers,
        params={"query": query, "orientation": "portrait", "per_page": 10},
        timeout=20,
    )
    response.raise_for_status()
    videos = response.json().get("videos", [])
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
    voice_id = os.environ.get("ELEVENLABS_VOICE_ID", "EXAVITQu4vr4xnSDxMaL")
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
    sped_clip = clip.fx(audio_speedx, speed)
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

    try:
        if has_pexels_access():
            print("🎞️ Creating reel from real stock video clips...")
            output_path = create_stock_video_reel(content, output_dir)
        else:
            print("🎞️ Pexels key missing, falling back to slideshow reel...")
            output_path = create_slideshow_reel(content, output_dir)
    except Exception as e:
        print(f"Stock video reel failed: {e}")
        print("🎞️ Falling back to slideshow reel...")
        output_path = create_slideshow_reel(content, output_dir)

    print(f"✅ Video created: {output_path}")
    return output_path, prompt_path, metadata_path
