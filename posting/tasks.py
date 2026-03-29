from celery import shared_task
from django.utils import timezone

from .models import Post
from .services import publish_post


@shared_task
def publish_single_post_task(post_id):
    post = Post.objects.get(pk=post_id)
    return publish_post(post)


@shared_task
def publish_due_posts_task():
    due_posts = Post.objects.filter(
        status=Post.Status.SCHEDULED,
        scheduled_for__lte=timezone.now(),
    ).order_by("scheduled_for")
    processed = []
    for post in due_posts:
        publish_post(post)
        processed.append(post.id)
    return processed
