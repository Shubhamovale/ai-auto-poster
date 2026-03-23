import traceback

from create_video import create_reel_video
<<<<<<< HEAD
from archive_media import archive_run
from post_facebook import post_to_facebook
from post_youtube import post_to_youtube
import os
import traceback
=======
from generate_content import generate_post_content
from post_facebook import post_to_facebook
from post_youtube import post_to_youtube

>>>>>>> production


def require_env_vars():
    required = [
        "GEMINI_API_KEY",
        "UNSPLASH_ACCESS_KEY",
        "FB_PAGE_ID",
        "FB_PAGE_ACCESS_TOKEN",
        "YOUTUBE_CLIENT_ID",
        "YOUTUBE_CLIENT_SECRET",
        "YOUTUBE_REFRESH_TOKEN",
    ]
    missing = [name for name in required if not os.environ.get(name)]
    if missing:
        missing_str = ", ".join(missing)
        raise RuntimeError(f"Missing required environment variables: {missing_str}")


def main():
    print("🚀 Starting AI Auto Poster...")
    require_env_vars()

    print("📝 Generating content with Gemini...")
    content = generate_post_content()
    print(f"✅ Content generated: {content['title']}")

    print("🎬 Creating video...")
    video_path, prompt_path, metadata_path = create_reel_video(
        content["title"],
        content["points"],
        content["image_keyword"],
<<<<<<< HEAD
        content.get("video_prompt")
=======
        content.get("video_prompt"),
        content.get("hook_subtitle"),
        content.get("voiceover_script"),
        content.get("video_keywords"),
        content.get("subtitle_lines"),
>>>>>>> production
    )
    print(f"✅ Video created: {video_path}")
    print(f"📝 Prompt saved: {prompt_path}")
    print(f"🗂️ Metadata saved: {metadata_path}")

    archive_result = archive_run(video_path, prompt_path, metadata_path)
    if archive_result.get("video"):
        print(f"☁️ Archived video URL: {archive_result['video'].get('secure_url')}")

    print("📤 Posting to Facebook...")
    post_to_facebook(content["caption"], video_path)

    print("📤 Posting to YouTube...")
    post_to_youtube(
        content["youtube_title"],
        content["youtube_description"],
        content["youtube_tags"],
        video_path,
    )
    print("🎉 All done!")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"❌ Error: {e}")
        traceback.print_exc()
        raise
