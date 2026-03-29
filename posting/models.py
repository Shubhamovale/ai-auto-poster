from django.db import models
from django.utils import timezone

from workspaces.models import Workspace


class Post(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        SCHEDULED = "scheduled", "Scheduled"
        PROCESSING = "processing", "Processing"
        POSTED = "posted", "Posted"
        FAILED = "failed", "Failed"

    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE, related_name="posts")
    title = models.CharField(max_length=255)
    caption = models.TextField(blank=True)
    content_payload = models.JSONField(default=dict, blank=True)
    video_path = models.CharField(max_length=512, blank=True)
    scheduled_for = models.DateTimeField(default=timezone.now)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.DRAFT)
    platforms = models.JSONField(default=list, blank=True)
    error_message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title


class PostRun(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="runs")
    platform = models.CharField(max_length=32)
    status = models.CharField(max_length=16, default="pending")
    response_payload = models.JSONField(default=dict, blank=True)
    error_message = models.TextField(blank=True)
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.post.title} - {self.platform}"
