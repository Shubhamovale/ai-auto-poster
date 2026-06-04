import os
import textwrap
from io import BytesIO

import requests
from PIL import Image, ImageDraw, ImageFilter, ImageFont


WIDTH = 1080
HEIGHT = 1350


def fetch_background_image(keyword):
    try:
        url = (
            f"https://api.unsplash.com/photos/random"
            f"?query={keyword}&orientation=portrait"
            f"&client_id={os.environ['UNSPLASH_ACCESS_KEY']}"
        )
        resp = requests.get(url, timeout=10)
        data = resp.json()
        if "urls" in data:
            img_url = data["urls"]["regular"]
            img_data = requests.get(img_url, timeout=15).content
            img = Image.open(BytesIO(img_data)).convert("RGB")
            return img.resize((WIDTH, HEIGHT))
    except Exception as e:
        print(f"Image fetch failed: {e}, using fallback")
    return Image.new("RGB", (WIDTH, HEIGHT), color=(28, 30, 42))


def load_font(path, size):
    import os
    if os.name == "nt":
        font_dir = os.environ.get("WINDIR", "C:\\Windows") + "\\Fonts"
        is_bold = "Bold" in path or "bold" in path.lower()
        font_name = "arialbd.ttf" if is_bold else "arial.ttf"
        translated_path = os.path.join(font_dir, font_name)
        if os.path.exists(translated_path):
            path = translated_path
    try:
        return ImageFont.truetype(path, size)
    except Exception:
        return ImageFont.load_default()



def fit_text(draw, text, font_path, start_size, max_width, max_lines, min_size=26):
    size = start_size
    while size >= min_size:
        font = load_font(font_path, size)
        wrapped = textwrap.fill(text, width=max(10, int(max_width / max(size * 0.58, 1))))
        lines = wrapped.split("\n")
        if len(lines) <= max_lines and all(
            draw.textbbox((0, 0), line, font=font, stroke_width=2)[2] <= max_width
            for line in lines
        ):
            return font, lines
        size -= 2
    font = load_font(font_path, min_size)
    return font, textwrap.wrap(text, width=20)[:max_lines]


def draw_centered_lines(draw, lines, font, y, fill, stroke_fill="black", stroke_width=2, gap=8):
    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font, stroke_width=stroke_width)
        width = bbox[2] - bbox[0]
        x = (WIDTH - width) // 2
        draw.text(
            (x, y),
            line,
            font=font,
            fill=fill,
            stroke_fill=stroke_fill,
            stroke_width=stroke_width,
        )
        y += (bbox[3] - bbox[1]) + gap
    return y


def draw_badge(draw, center_x, center_y, value, label, fill_color):
    radius = 138
    draw.ellipse(
        (center_x - radius, center_y - radius, center_x + radius, center_y + radius),
        fill=fill_color,
        outline=(255, 227, 92),
        width=8,
    )
    value_font = load_font("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 54)
    label_font = load_font("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 24)
    value_box = draw.textbbox((0, 0), value, font=value_font, stroke_width=3)
    value_w = value_box[2] - value_box[0]
    draw.text(
        (center_x - value_w // 2, center_y - 12),
        value,
        font=value_font,
        fill="white",
        stroke_fill="black",
        stroke_width=3,
    )
    label_box = draw.textbbox((0, 0), label, font=label_font, stroke_width=2)
    label_w = label_box[2] - label_box[0]
    draw.text(
        (center_x - label_w // 2, center_y + 48),
        label,
        font=label_font,
        fill="white",
        stroke_fill="black",
        stroke_width=2,
    )


def create_trending_poster(
    title,
    hook_subtitle,
    headline,
    hero_keyword,
    badge_left_keyword,
    badge_right_keyword,
    badge_left_value,
    badge_left_label,
    badge_right_value,
    badge_right_label,
    category_label="NEWS",
    points=None,
):
    output_dir = os.path.join(os.getcwd(), "output")
    os.makedirs(output_dir, exist_ok=True)

    base_img = fetch_background_image(hero_keyword)
    blurred_bg = base_img.filter(ImageFilter.GaussianBlur(radius=10)).convert("RGBA")
    dark_overlay = Image.new("RGBA", (WIDTH, HEIGHT), (8, 10, 16, 135))
    canvas = Image.alpha_composite(blurred_bg, dark_overlay)

    hero = base_img.resize((760, 620)).convert("RGBA")
    hero_mask = Image.new("L", hero.size, 0)
    ImageDraw.Draw(hero_mask).rounded_rectangle((0, 0, hero.size[0], hero.size[1]), radius=36, fill=255)
    hero.putalpha(hero_mask)
    canvas.alpha_composite(hero, (160, 74))

    draw = ImageDraw.Draw(canvas)
    draw.rounded_rectangle((150, 64, 930, 704), radius=40, outline=(255, 230, 120), width=6)

    draw_badge(draw, 165, 210, badge_left_value, badge_left_label, (220, 80, 115))
    draw_badge(draw, 915, 210, badge_right_value, badge_right_label, (104, 94, 235))

    pill_font = load_font("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 34)
    pill_w = 210
    pill_x0 = (WIDTH - pill_w) // 2
    pill_y0 = 720
    draw.rounded_rectangle((pill_x0, pill_y0, pill_x0 + pill_w, pill_y0 + 58), radius=29, fill=(255, 227, 92))
    pill_box = draw.textbbox((0, 0), category_label.upper(), font=pill_font)
    pill_text_w = pill_box[2] - pill_box[0]
    draw.text((WIDTH // 2 - pill_text_w // 2, pill_y0 + 10), category_label.upper(), font=pill_font, fill="black")

    draw.rounded_rectangle((90, 805, 990, 1280), radius=36, fill=(15, 15, 19, 220))

    title_font, title_lines = fit_text(
        draw,
        title.upper(),
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        72,
        820,
        2,
        min_size=42,
    )
    y = 845
    y = draw_centered_lines(draw, title_lines, title_font, y, fill="white", gap=2)

    if hook_subtitle:
        sub_font, sub_lines = fit_text(
            draw,
            hook_subtitle.upper(),
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            34,
            760,
            2,
            min_size=24,
        )
        y += 10
        y = draw_centered_lines(draw, sub_lines, sub_font, y, fill="#FFE45C", gap=4)

    headline_font, headline_lines = fit_text(
        draw,
        headline.upper(),
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        58,
        820,
        4,
        min_size=32,
    )
    y += 14
    y = draw_centered_lines(draw, headline_lines, headline_font, y, fill="#FFE45C", gap=2)

    points = points or []
    if points:
        bullet_font = load_font("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 28)
        bullet_y = max(y + 16, 1130)
        for point in points[:2]:
            bullet_text = f"\u2022 {point.upper()}"
            bullet_lines = textwrap.wrap(bullet_text, width=40)[:2]
            for line in bullet_lines:
                bbox = draw.textbbox((0, 0), line, font=bullet_font, stroke_width=2)
                line_w = bbox[2] - bbox[0]
                x = (WIDTH - line_w) // 2
                draw.text(
                    (x, bullet_y),
                    line,
                    font=bullet_font,
                    fill="white",
                    stroke_fill="black",
                    stroke_width=2,
                )
                bullet_y += 34
            bullet_y += 8

    output_path = os.path.join(output_dir, "facebook_post.jpg")
    canvas.convert("RGB").save(output_path, quality=95)
    print(f"✅ Image created: {output_path}")
    return output_path


def create_facebook_image(title, points, image_keyword, hook_subtitle=None):
    return create_trending_poster(
        title=title,
        hook_subtitle=hook_subtitle,
        headline=title,
        hero_keyword=image_keyword,
        badge_left_keyword=image_keyword,
        badge_right_keyword=image_keyword,
        badge_left_value="500M",
        badge_left_label="12 HOURS",
        badge_right_value="475M",
        badge_right_label="24 HOURS",
        category_label="NEWS",
        points=points,
    )
