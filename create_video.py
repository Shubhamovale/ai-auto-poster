import requests
import os
import textwrap
from PIL import Image, ImageDraw, ImageFont
from moviepy.editor import ImageClip, concatenate_videoclips, AudioFileClip
from moviepy.audio.AudioClip import AudioArrayClip
from moviepy.video.fx.fadein import fadein
from moviepy.video.fx.fadeout import fadeout
import numpy as np
from io import BytesIO

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
        
        # Handle both single photo and error response
        if "urls" in data:
            img_url = data["urls"]["regular"]
        elif "errors" in data:
            print(f"Unsplash error: {data['errors']}")
            # Fallback to a default image color
            img = Image.new("RGB", (1080, 1920), color=(30, 30, 50))
            return img
        else:
            print(f"Unexpected response: {data}")
            img = Image.new("RGB", (1080, 1920), color=(30, 30, 50))
            return img
            
        img_data = requests.get(img_url, timeout=10).content
        img = Image.open(BytesIO(img_data)).convert("RGB")
        img = img.resize((1080, 1920))
        return img
        
    except Exception as e:
        print(f"Image fetch failed: {e}, using fallback")
        img = Image.new("RGB", (1080, 1920), color=(30, 30, 50))
        return img

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
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 155))
    img = img.convert("RGBA")
    img = Image.alpha_composite(img, overlay)
    img = img.convert("RGB")
    draw = ImageDraw.Draw(img)

    try:
        font_big   = ImageFont.truetype(
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", font_size)
        font_sub   = ImageFont.truetype(
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 45)
        font_brand = ImageFont.truetype(
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 40)
    except:
        font_big   = ImageFont.load_default()
        font_sub   = ImageFont.load_default()
        font_brand = ImageFont.load_default()

    # Top branding bar
    draw.rectangle([0, 0, 1080, 110], fill=accent_color)
    draw.text((30, 30), "AI AUTO POSTER", font=font_brand, fill="white")

    # Main text
    wrap_width = 14 if layout == "hook" else 18
    wrapped = textwrap.fill(text, width=wrap_width)
    lines   = wrapped.split("\n")
    y_start = 520 if layout == "hook" else 760
    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font_big)
        w    = bbox[2] - bbox[0]
        x    = (1080 - w) // 2
        pad_x = 28
        pad_y = 18
        draw.rounded_rectangle(
            [x - pad_x, y_start - pad_y, x + w + pad_x, y_start + font_size + pad_y],
            radius=24,
            fill=(0, 0, 0, 165),
        )
        draw.text((x+3, y_start+3), line, font=font_big, fill="black")
        draw.text((x, y_start),     line, font=font_big, fill=text_color)
        y_start += font_size + 26

    # Subtitle
    if subtitle:
        wrapped_sub = textwrap.fill(subtitle, width=24 if layout == "hook" else 28)
        sub_lines   = wrapped_sub.split("\n")
        y_sub       = y_start + 34
        for line in sub_lines:
            bbox = draw.textbbox((0, 0), line, font=font_sub)
            w    = bbox[2] - bbox[0]
            x    = (1080 - w) // 2
            draw.rounded_rectangle(
                [x - 24, y_sub - 12, x + w + 24, y_sub + 54],
                radius=20,
                fill=(20, 20, 20, 180),
            )
            draw.text((x, y_sub), line, font=font_sub, fill="#FFD700")
            y_sub += 55

    # Bottom CTA bar
    draw.rectangle([0, 1815, 1080, 1920], fill=accent_color)
    draw.text((30, 1844), "FOLLOW FOR DAILY AI SHORTS",
              font=font_brand, fill="white")

    return np.array(img)

def create_background_music(duration, sample_rate=44100):
    timeline = np.linspace(0, duration, int(sample_rate * duration), endpoint=False)

    beat = (
        0.18 * np.sin(2 * np.pi * 110 * timeline)
        + 0.10 * np.sin(2 * np.pi * 220 * timeline)
        + 0.05 * np.sin(2 * np.pi * 330 * timeline)
    )
    pulse = np.sign(np.sin(2 * np.pi * 2.4 * timeline))
    envelope = 0.5 + 0.5 * pulse
    sweep = 0.05 * np.sin(2 * np.pi * (timeline * 40 + 180) * timeline)

    audio = ((beat * envelope) + sweep) * 0.55
    stereo = np.stack([audio, audio], axis=1).astype(np.float32)
    return AudioArrayClip(stereo, fps=sample_rate)

<<<<<<< Updated upstream
def create_reel_video(title, points, image_keyword):
=======
def build_video_prompt(title, points, image_keyword, video_prompt=None):
    if video_prompt and video_prompt.strip():
        return video_prompt.strip()

    points_text = ", ".join(points[:5])
    return (
        f"Create a cinematic vertical 9:16 short video about '{title}'. "
        f"Use {image_keyword} inspired environments and visuals. "
        f"Show scenes that communicate these beats: {points_text}. "
        f"Fast pacing, strong visual hook, dramatic lighting, smooth camera motion, "
        f"modern AI-tech mood, realistic detail, no text overlays, no watermarks."
    )


def save_video_assets(output_dir, title, points, image_keyword, video_prompt):
    os.makedirs(output_dir, exist_ok=True)

    prompt_path = os.path.join(output_dir, "reel_video_prompt.txt")
    with open(prompt_path, "w", encoding="utf-8") as f:
        f.write(video_prompt + "\n")

    metadata_path = os.path.join(output_dir, "reel_video_metadata.json")
    with open(metadata_path, "w", encoding="utf-8") as f:
        json.dump(
            {
                "title": title,
                "points": points,
                "image_keyword": image_keyword,
                "video_prompt": video_prompt,
            },
            f,
            indent=2,
        )

    return prompt_path, metadata_path


def build_motion_clip(frame, duration, zoom_start=1.0, zoom_end=1.08, fade=0.2):
    clip = ImageClip(frame).set_duration(duration)
    clip = clip.resize(lambda t: zoom_start + (zoom_end - zoom_start) * (t / duration))
    if fade:
        clip = clip.fx(fadein, fade).fx(fadeout, fade)
    return clip


def create_reel_video(title, points, image_keyword, video_prompt=None, hook_subtitle=None):
    output_dir = os.path.join(os.getcwd(), "output")
    video_prompt = build_video_prompt(title, points, image_keyword, video_prompt)
    prompt_path, metadata_path = save_video_assets(
        output_dir, title, points, image_keyword, video_prompt
    )

    print("🎥 AI video prompt ready:")
    print(video_prompt)
    print(f"📝 Saved prompt: {prompt_path}")
    print(f"🗂️ Saved metadata: {metadata_path}")

>>>>>>> Stashed changes
    print("🖼️  Fetching background image...")
    bg_img = fetch_background_image(image_keyword)

    clips  = []
    colors = ["#FF4D6D", "#FFD166", "#06D6A0", "#4CC9F0", "#F72585"]
    accent_colors = [
        (255, 77, 109),
        (255, 209, 102),
        (6, 214, 160),
        (76, 201, 240),
        (247, 37, 133),
    ]
    hook_subtitle = hook_subtitle or "Wait till you see the last one."

    # Hook clip
    hook_frame = create_text_frame(
        bg_img, title,
        subtitle=hook_subtitle,
        text_color="#FFD700",
        font_size=88,
        accent_color=(255, 77, 109),
        layout="hook",
    )
    clips.append(build_motion_clip(hook_frame, duration=2.2, zoom_start=1.0, zoom_end=1.12))

    # Points clips
    for i, point in enumerate(points[:5]):
        frame = create_text_frame(
            bg_img, f"#{i+1} {point.upper()}",
            subtitle=point,
            text_color=colors[i],
            font_size=92,
            accent_color=accent_colors[i],
        )
        clips.append(
            build_motion_clip(
                frame,
                duration=1.9 if i < 3 else 1.7,
                zoom_start=1.01,
                zoom_end=1.09,
                fade=0.16,
            )
        )

    # CTA clip
    cta_frame = create_text_frame(
        bg_img,
        "FOLLOW FOR PART 2",
        subtitle="More AI tools coming daily",
        text_color="#00FF88",
        font_size=78,
        accent_color=(6, 214, 160),
        layout="hook",
    )
    clips.append(build_motion_clip(cta_frame, duration=1.6, zoom_start=1.0, zoom_end=1.06))

    # Concatenate
    print("🎬 Generating video...")
    final_video = concatenate_videoclips(clips, method="compose")

    # Add built-in music bed for cloud runs without external downloads.
    final_video = final_video.set_audio(create_background_music(final_video.duration))

    # Export
    output_path = "/tmp/reel_video.mp4"
    final_video.write_videofile(
        output_path,
        fps=30,
        codec="libx264",
        audio_codec="aac",
        temp_audiofile="/tmp/temp_audio.m4a",
        remove_temp=True,
        logger=None
    )
    print(f"✅ Video created: {output_path}")
    return output_path
