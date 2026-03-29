import os

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload


def post_to_youtube(
    title,
    description,
    tags,
    video_path,
    *,
    client_id=None,
    client_secret=None,
    refresh_token=None,
    token_uri=None,
):
    creds = Credentials(
        token=None,
        refresh_token=refresh_token or os.environ["YOUTUBE_REFRESH_TOKEN"],
        client_id=client_id or os.environ["YOUTUBE_CLIENT_ID"],
        client_secret=client_secret or os.environ["YOUTUBE_CLIENT_SECRET"],
        token_uri=token_uri or "https://oauth2.googleapis.com/token",
    )

    youtube = build("youtube", "v3", credentials=creds)
    print("Uploading to YouTube Shorts...")

    request = youtube.videos().insert(
        part="snippet,status",
        body={
            "snippet": {
                "title":       title + " #Shorts",
                "description": description,
                "tags":        tags + ["Shorts", "AI", "Tech"],
                "categoryId":  "28"
            },
            "status": {
                "privacyStatus":           "public",
                "selfDeclaredMadeForKids": False
            }
        },
        media_body=MediaFileUpload(
            video_path,
            mimetype="video/mp4",
            chunksize=-1,
            resumable=True
        )
    )

    response = request.execute()
    print(f"YouTube Short posted. ID: {response['id']}")
    return response
