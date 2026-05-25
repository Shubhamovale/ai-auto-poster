import traceback
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

from create_image import create_trending_poster
from generate_content import generate_post_content
from post_facebook import post_to_facebook


def main():
    print("🚀 Starting AI Auto Poster...")

    print("📝 Generating content with Gemini...")
    content = generate_post_content()
    print(f"✅ Content generated: {content['title']}")

    print("🖼️ Creating Facebook image...")
    image_path = create_trending_poster(
        content["title"],
        content.get("hook_subtitle"),
        content.get("headline", content["title"]),
        content.get("hero_keyword", content["image_keyword"]),
        content.get("badge_left_keyword", content["image_keyword"]),
        content.get("badge_right_keyword", content["image_keyword"]),
        content.get("badge_left_value", "500M"),
        content.get("badge_left_label", "12 HOURS"),
        content.get("badge_right_value", "475M"),
        content.get("badge_right_label", "24 HOURS"),
        content.get("category_label", "NEWS"),
        content.get("points"),
    )
    print(f"✅ Image created: {image_path}")

    print("📤 Posting to Facebook...")
    post_to_facebook(content["caption"], image_path)
    print("🎉 All done!")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"❌ Error: {e}")
        traceback.print_exc()
        raise
