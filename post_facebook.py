import requests
import os

def post_to_facebook(caption, video_path):
    page_id    = os.environ["FB_PAGE_ID"]
    page_token = os.environ["FB_PAGE_ACCESS_TOKEN"]

    print("📤 Uploading video to Facebook...")
    with open(video_path, "rb") as video_file:
        response = requests.post(
            f"https://graph.facebook.com/{page_id}/videos",
            data={
                "description":  caption,
                "access_token": page_token
            },
            files={"source": video_file}
        )

    result = response.json()
    if "id" in result:
        print(f"✅ Facebook Reel posted! ID: {result['id']}")
    else:
        print(f"❌ Facebook error: {result}")
    return result