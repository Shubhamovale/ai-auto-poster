import requests
import os


def post_to_facebook(caption, video_path):
    page_id    = os.environ["FB_PAGE_ID"]
    page_token = os.environ["FB_PAGE_ACCESS_TOKEN"]

    print("📤 Posting to Facebook as photo post...")
    
    # Use thumbnail instead of video for now
    thumb_path = video_path.replace(".mp4", "_thumb.jpg")
    
    # Extract first frame as thumbnail
    import subprocess
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-ss",
            "00:00:01",
            "-i",
            video_path,
            "-frames:v",
            "1",
            "-update",
            "1",
            thumb_path,
        ],
        check=True,
    )

    with open(thumb_path, "rb") as img_file:
        response = requests.post(
            f"https://graph.facebook.com/{page_id}/photos",
            data={
                "caption": caption,
                "access_token": page_token
            },
            files={"source": img_file}
        )

    result = response.json()
    if "id" in result:
        print(f"✅ Facebook photo posted! ID: {result['id']}")
    else:
        print(f"❌ Facebook error: {result}")
        error = result.get("error", {})
        if error.get("code") == 190 and error.get("error_subcode") == 463:
            print(
                "🔐 Facebook access token expired. Generate a fresh Page access token "
                "and update the GitHub secret FB_PAGE_ACCESS_TOKEN."
            )
    return result
