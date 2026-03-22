import traceback

from create_video import create_reel_video
from generate_content import generate_post_content
from post_facebook import post_to_facebook
from post_youtube import post_to_youtube


def main():
    print("🚀 Starting AI Auto Poster...")

    print("📝 Generating content with Gemini...")
    content = generate_post_content()
    print(f"✅ Content generated: {content['title']}")

    print("🎬 Creating video...")
    video_path, prompt_path, metadata_path = create_reel_video(
        content["title"],
        content["points"],
        content["image_keyword"],
        content.get("video_prompt"),
        content.get("hook_subtitle"),
        content.get("voiceover_script"),
        content.get("video_keywords"),
    )
    print(f"✅ Video created: {video_path}")
    print(f"📝 Prompt saved: {prompt_path}")
    print(f"🗂️ Metadata saved: {metadata_path}")

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
