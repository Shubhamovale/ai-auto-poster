from generate_content import generate_post_content
import traceback

def main():
    print("🚀 Starting AI Auto Poster...")
    print("📝 Listing available Gemini models...")
    result = generate_post_content()
    print("✅ Done listing models!")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"❌ Error: {e}")
        traceback.print_exc()
        raise
