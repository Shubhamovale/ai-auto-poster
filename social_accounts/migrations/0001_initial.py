from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("workspaces", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="SocialAccount",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("platform", models.CharField(choices=[("facebook", "Facebook"), ("instagram", "Instagram"), ("youtube", "YouTube")], max_length=20)),
                ("account_name", models.CharField(max_length=255)),
                ("account_identifier", models.CharField(blank=True, max_length=255)),
                ("access_token", models.TextField(blank=True)),
                ("refresh_token", models.TextField(blank=True)),
                ("token_expires_at", models.DateTimeField(blank=True, null=True)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("is_connected", models.BooleanField(default=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("workspace", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="social_accounts", to="workspaces.workspace")),
            ],
            options={
                "unique_together": {("workspace", "platform", "account_identifier")},
            },
        ),
    ]
