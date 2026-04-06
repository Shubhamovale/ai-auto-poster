import requests
import os

GRAPH_BASE_URL = "https://graph.facebook.com/v23.0"


def exchange_for_long_lived_user_token():
    app_id = os.environ.get("FB_APP_ID")
    app_secret = os.environ.get("FB_APP_SECRET")
    short_lived_user_token = os.environ.get("FB_USER_ACCESS_TOKEN")

    if not (app_id and app_secret and short_lived_user_token):
        return short_lived_user_token

    print("🔄 Exchanging Facebook user token for a long-lived token...")
    response = requests.get(
        f"{GRAPH_BASE_URL}/oauth/access_token",
        params={
            "grant_type": "fb_exchange_token",
            "client_id": app_id,
            "client_secret": app_secret,
            "fb_exchange_token": short_lived_user_token,
        },
        timeout=30,
    )
    response.raise_for_status()
    data = response.json()
    return data.get("access_token", short_lived_user_token)


def get_page_access_token(page_id):
    explicit_page_token = os.environ.get("FB_PAGE_ACCESS_TOKEN")
    user_token = os.environ.get("FB_USER_ACCESS_TOKEN")

    if not user_token:
        return explicit_page_token

    effective_user_token = exchange_for_long_lived_user_token()
    print("🔎 Fetching Facebook page token from the configured user token...")
    response = requests.get(
        f"{GRAPH_BASE_URL}/me/accounts",
        params={"access_token": effective_user_token},
        timeout=30,
    )
    response.raise_for_status()
    data = response.json()
    pages = data.get("data", [])
    for page in pages:
        if page.get("id") == page_id and page.get("access_token"):
            return page["access_token"]

    raise RuntimeError(
        f"Could not find page {page_id} from FB_USER_ACCESS_TOKEN. "
        "Check that the user manages the page and granted the required permissions."
    )


def post_to_facebook(caption, image_path):
    page_id = os.environ["FB_PAGE_ID"]
    page_token = get_page_access_token(page_id)

    print("📤 Posting to Facebook as photo post...")

    with open(image_path, "rb") as img_file:
        response = requests.post(
            f"{GRAPH_BASE_URL}/{page_id}/photos",
            data={
                "caption": caption,
                "access_token": page_token,
            },
            files={"source": img_file},
            timeout=60,
        )

    result = response.json()
    if "id" in result:
        print(f"✅ Facebook photo posted! ID: {result['id']}")
    else:
        print(f"❌ Facebook error: {result}")
        error = result.get("error", {})
        if error.get("code") == 190 and error.get("error_subcode") == 463:
            print(
                "🔐 Facebook access token expired. Prefer storing FB_USER_ACCESS_TOKEN "
                "plus optional FB_APP_ID/FB_APP_SECRET so the workflow can derive a "
                "fresh page token automatically."
            )
        raise RuntimeError(f"Facebook post failed: {result}")
    return result
