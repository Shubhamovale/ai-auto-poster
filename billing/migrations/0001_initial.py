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
            name="SubscriptionPlan",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("code", models.CharField(choices=[("free", "Free"), ("basic", "Basic"), ("pro", "Pro")], max_length=16, unique=True)),
                ("name", models.CharField(max_length=64)),
                ("monthly_price", models.DecimalField(decimal_places=2, default=0, max_digits=8)),
                ("monthly_post_limit", models.PositiveIntegerField(default=5)),
                ("supports_all_platforms", models.BooleanField(default=False)),
                ("is_active", models.BooleanField(default=True)),
            ],
        ),
        migrations.CreateModel(
            name="UsageRecord",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("year", models.PositiveIntegerField()),
                ("month", models.PositiveIntegerField()),
                ("posts_used", models.PositiveIntegerField(default=0)),
                ("ai_generations_used", models.PositiveIntegerField(default=0)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("workspace", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="usage_records", to="workspaces.workspace")),
            ],
            options={
                "unique_together": {("workspace", "year", "month")},
            },
        ),
        migrations.CreateModel(
            name="WorkspaceSubscription",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("razorpay_subscription_id", models.CharField(blank=True, max_length=255)),
                ("active_from", models.DateTimeField(default=django.utils.timezone.now)),
                ("active_until", models.DateTimeField(blank=True, null=True)),
                ("status", models.CharField(default="active", max_length=32)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("plan", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to="billing.subscriptionplan")),
                ("workspace", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="subscription", to="workspaces.workspace")),
            ],
        ),
    ]
