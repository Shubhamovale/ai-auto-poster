from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("social_accounts", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="socialaccount",
            name="client_id",
            field=models.CharField(blank=True, max_length=255),
        ),
        migrations.AddField(
            model_name="socialaccount",
            name="client_secret",
            field=models.CharField(blank=True, max_length=255),
        ),
        migrations.AddField(
            model_name="socialaccount",
            name="token_uri",
            field=models.URLField(blank=True, default="https://oauth2.googleapis.com/token"),
        ),
    ]
