from django.utils import timezone

from create_video import create_reel_video
from post_facebook import post_to_facebook
from post_youtube import post_to_youtube
from social_accounts.models import SocialAccount
from social_accounts.services import get_connected_account

from .models import Post, PostRun


def build_video_for_post(post: Post):
    payload = post.content_payload or {}
    video_path, prompt_path, metadata_path = create_reel_video(
        payload.get("title", post.title),
        payload.get("points", []),
        payload.get("image_keyword", payload.get("title", post.title)),
        payload.get("video_prompt"),
        payload.get("hook_subtitle"),
        payload.get("voiceover_script"),
        payload.get("video_keywords"),
        payload.get("subtitle_lines"),
    )
    post.video_path = video_path
    post.content_payload["video_prompt_path"] = prompt_path
    post.content_payload["video_metadata_path"] = metadata_path
    post.save(update_fields=["video_path", "content_payload", "updated_at"])
    return video_path


def publish_post(post: Post):
    if not post.video_path:
        build_video_for_post(post)

    post.status = Post.Status.PROCESSING
    post.error_message = ""
    post.save(update_fields=["status", "error_message", "updated_at"])

    results = {}
    for platform in post.platforms:
        run = PostRun.objects.create(post=post, platform=platform, status="processing")
        try:
            if platform == "facebook":
                social_account = get_connected_account(post.workspace, SocialAccount.Platform.FACEBOOK)
                response = post_to_facebook(
                    post.caption,
                    post.video_path,
                    page_id=getattr(social_account, "account_identifier", None),
                    page_token=getattr(social_account, "access_token", None),
                )
            elif platform == "youtube":
                payload = post.content_payload or {}
                social_account = get_connected_account(post.workspace, SocialAccount.Platform.YOUTUBE)
                response = post_to_youtube(
                    payload.get("youtube_title", post.title),
                    payload.get("youtube_description", post.caption),
                    payload.get("youtube_tags", []),
                    post.video_path,
                    client_id=getattr(social_account, "client_id", None),
                    client_secret=getattr(social_account, "client_secret", None),
                    refresh_token=getattr(social_account, "refresh_token", None),
                    token_uri=getattr(social_account, "token_uri", None),
                )
            else:
                response = {"detail": "Instagram publishing not wired yet."}
            run.status = "posted"
            run.response_payload = response
            results[platform] = response
        except Exception as exc:
            run.status = "failed"
            run.error_message = str(exc)
            post.status = Post.Status.FAILED
            post.error_message = str(exc)
            results[platform] = {"error": str(exc)}
        run.completed_at = timezone.now()
        run.save()

    if post.status != Post.Status.FAILED:
        post.status = Post.Status.POSTED
    post.save(update_fields=["status", "error_message", "updated_at"])
    return results
