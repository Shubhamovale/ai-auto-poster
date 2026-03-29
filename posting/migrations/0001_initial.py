from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("workspaces", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="Post",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("title", models.CharField(max_length=255)),
                ("caption", models.TextField(blank=True)),
                ("content_payload", models.JSONField(blank=True, default=dict)),
                ("video_path", models.CharField(blank=True, max_length=512)),
                ("scheduled_for", models.DateTimeField(default=django.utils.timezone.now)),
                ("status", models.CharField(choices=[("draft", "Draft"), ("scheduled", "Scheduled"), ("processing", "Processing"), ("posted", "Posted"), ("failed", "Failed")], default="draft", max_length=16)),
                ("platforms", models.JSONField(blank=True, default=list)),
                ("error_message", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("workspace", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="posts", to="workspaces.workspace")),
            ],
        ),
        migrations.CreateModel(
            name="PostRun",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("platform", models.CharField(max_length=32)),
                ("status", models.CharField(default="pending", max_length=16)),
                ("response_payload", models.JSONField(blank=True, default=dict)),
                ("error_message", models.TextField(blank=True)),
                ("started_at", models.DateTimeField(auto_now_add=True)),
                ("completed_at", models.DateTimeField(blank=True, null=True)),
                ("post", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="runs", to="posting.post")),
            ],
        ),
    ]
