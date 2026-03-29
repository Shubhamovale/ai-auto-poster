from django.db import models

from workspaces.models import Workspace


class ContentTemplate(models.Model):
    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE, related_name="content_templates")
    name = models.CharField(max_length=255)
    prompt = models.TextField()
    is_default = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


class ContentIdea(models.Model):
    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE, related_name="content_ideas")
    topic = models.CharField(max_length=255)
    status = models.CharField(max_length=32, default="draft")
    payload = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.topic
