import traceback
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

from create_story_short import create_story_short
from generate_story_content import generate_story_content
from post_youtube import post_to_youtube


def main():
    print("🚀 Starting story short pipeline...")

    print("📝 Generating story content...")
    content = generate_story_content()
    print(f"✅ Story topic: {content['title']}")

    print("🎬 Creating story short...")
    video_path, metadata_path, script_path, outline_path = create_story_short(content)
    print(f"✅ Story short created: {video_path}")
    print(f"🗂️ Metadata saved: {metadata_path}")
    print(f"📝 Script saved: {script_path}")
    print(f"📄 Outline saved: {outline_path}")

    print("📤 Uploading story short to YouTube...")
    post_to_youtube(
        content["title"],
        content["youtube_description"],
        content["youtube_tags"],
        video_path,
    )
    print("🎉 Story short done!")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"❌ Error: {e}")
        traceback.print_exc()
        raise
