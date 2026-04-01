import requests


LINKEDIN_API_BASE = "https://api.linkedin.com/v2"


def post_to_linkedin(caption, access_token, author_urn):
    if not access_token:
        raise ValueError("LinkedIn access token is missing.")
    if not author_urn:
        raise ValueError("LinkedIn author URN is missing.")

    response = requests.post(
        f"{LINKEDIN_API_BASE}/ugcPosts",
        json={
            "author": author_urn,
            "lifecycleState": "PUBLISHED",
            "specificContent": {
                "com.linkedin.ugc.ShareContent": {
                    "shareCommentary": {
                        "text": caption or "",
                    },
                    "shareMediaCategory": "NONE",
                }
            },
            "visibility": {
                "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC",
            },
        },
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
            "X-Restli-Protocol-Version": "2.0.0",
        },
        timeout=30,
    )
    response.raise_for_status()
    payload = response.json() if response.content else {}
    payload["ugc_post_id"] = response.headers.get("x-restli-id", "")
    return payload
