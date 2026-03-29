from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("billing", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="subscriptionplan",
            name="razorpay_plan_id",
            field=models.CharField(blank=True, max_length=255),
        ),
        migrations.AddField(
            model_name="workspacesubscription",
            name="metadata",
            field=models.JSONField(blank=True, default=dict),
        ),
        migrations.AddField(
            model_name="workspacesubscription",
            name="razorpay_customer_id",
            field=models.CharField(blank=True, max_length=255),
        ),
        migrations.AddField(
            model_name="workspacesubscription",
            name="razorpay_payment_id",
            field=models.CharField(blank=True, max_length=255),
        ),
    ]
