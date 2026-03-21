import requests
import os
import textwrap
from PIL import Image, ImageDraw, ImageFont
from moviepy.editor import ImageClip, concatenate_videoclips, AudioFileClip
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

def create_text_frame(background_img, text, subtitle="",
                       text_color="white", font_size=70):
    img = background_img.copy()
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 180))
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
    draw.rectangle([0, 0, 1080, 100], fill=(29, 161, 242))
    draw.text((30, 28), "⚡ SECRETS OF AI", font=font_brand, fill="white")

    # Main text
    wrapped = textwrap.fill(text, width=18)
    lines   = wrapped.split("\n")
    y_start = 750
    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font_big)
        w    = bbox[2] - bbox[0]
        x    = (1080 - w) // 2
        draw.text((x+3, y_start+3), line, font=font_big, fill="black")
        draw.text((x, y_start),     line, font=font_big, fill=text_color)
        y_start += font_size + 15

    # Subtitle
    if subtitle:
        wrapped_sub = textwrap.fill(subtitle, width=28)
        sub_lines   = wrapped_sub.split("\n")
        y_sub       = y_start + 30
        for line in sub_lines:
            bbox = draw.textbbox((0, 0), line, font=font_sub)
            w    = bbox[2] - bbox[0]
            x    = (1080 - w) // 2
            draw.text((x, y_sub), line, font=font_sub, fill="#FFD700")
            y_sub += 55

    # Bottom CTA bar
    draw.rectangle([0, 1820, 1080, 1920], fill=(29, 161, 242))
    draw.text((30, 1845), "👆 Follow @baymax_tech_ for daily AI tips!",
              font=font_brand, fill="white")

    return np.array(img)

def download_free_music():
    return None  # Skip music for now

def create_reel_video(title, points, image_keyword):
    print("🖼️  Fetching background image...")
    bg_img = fetch_background_image(image_keyword)

    clips  = []
    colors = ["#00FF88", "#FF6B6B", "#FFD700", "#00BFFF", "#FF69B4"]

    # Hook clip
    hook_frame = create_text_frame(
        bg_img, title,
        subtitle="Follow for more AI tips! 👆",
        text_color="#FFD700", font_size=65
    )
    clips.append(ImageClip(hook_frame).set_duration(4).fx(fadein, 0.5))

    # Points clips
    for i, point in enumerate(points[:5]):
        frame = create_text_frame(
            bg_img, f"#{i+1}",
            subtitle=point,
            text_color=colors[i], font_size=120
        )
        clips.append(ImageClip(frame).set_duration(4).fx(fadein, 0.3))

    # CTA clip
    cta_frame = create_text_frame(
        bg_img, "FOLLOW US!",
        subtitle="Daily AI secrets that will blow your mind 🤯",
        text_color="#00FF88", font_size=80
    )
    clips.append(ImageClip(cta_frame).set_duration(2).fx(fadeout, 0.5))

    # Concatenate
    print("🎬 Generating video...")
    final_video = concatenate_videoclips(clips, method="compose")

    # Add music
    music_path = download_free_music()
    if music_path:
        audio = (AudioFileClip(music_path)
                 .subclip(0, final_video.duration)
                 .volumex(0.3))
        final_video = final_video.set_audio(audio)

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
