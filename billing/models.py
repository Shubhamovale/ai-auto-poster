from django.db import models
from django.utils import timezone

from workspaces.models import Workspace


class SubscriptionPlan(models.Model):
    class Code(models.TextChoices):
        FREE = "free", "Free"
        BASIC = "basic", "Basic"
        PRO = "pro", "Pro"

    code = models.CharField(max_length=16, choices=Code.choices, unique=True)
    name = models.CharField(max_length=64)
    razorpay_plan_id = models.CharField(max_length=255, blank=True)
    monthly_price = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    monthly_post_limit = models.PositiveIntegerField(default=5)
    supports_all_platforms = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name


class WorkspaceSubscription(models.Model):
    workspace = models.OneToOneField(Workspace, on_delete=models.CASCADE, related_name="subscription")
    plan = models.ForeignKey(SubscriptionPlan, on_delete=models.PROTECT)
    razorpay_subscription_id = models.CharField(max_length=255, blank=True)
    razorpay_customer_id = models.CharField(max_length=255, blank=True)
    razorpay_payment_id = models.CharField(max_length=255, blank=True)
    active_from = models.DateTimeField(default=timezone.now)
    active_until = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=32, default="active")
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.workspace.name} - {self.plan.name}"


class UsageRecord(models.Model):
    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE, related_name="usage_records")
    year = models.PositiveIntegerField()
    month = models.PositiveIntegerField()
    posts_used = models.PositiveIntegerField(default=0)
    ai_generations_used = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("workspace", "year", "month")

    def __str__(self):
        return f"{self.workspace.name} - {self.month}/{self.year}"
