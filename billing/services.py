from datetime import datetime, timezone as dt_timezone

from django.utils import timezone
from django.conf import settings

from .models import SubscriptionPlan, UsageRecord, WorkspaceSubscription


def ensure_default_plans():
    plans = [
        {
            "code": SubscriptionPlan.Code.FREE,
            "name": "Free",
            "razorpay_plan_id": settings.RAZORPAY_PLAN_IDS.get("free", ""),
            "monthly_price": 0,
            "monthly_post_limit": 5,
            "supports_all_platforms": False,
        },
        {
            "code": SubscriptionPlan.Code.BASIC,
            "name": "Basic",
            "razorpay_plan_id": settings.RAZORPAY_PLAN_IDS.get("basic", ""),
            "monthly_price": 499,
            "monthly_post_limit": 30,
            "supports_all_platforms": False,
        },
        {
            "code": SubscriptionPlan.Code.PRO,
            "name": "Pro",
            "razorpay_plan_id": settings.RAZORPAY_PLAN_IDS.get("pro", ""),
            "monthly_price": 999,
            "monthly_post_limit": 999999,
            "supports_all_platforms": True,
        },
    ]
    for plan in plans:
        SubscriptionPlan.objects.update_or_create(code=plan["code"], defaults=plan)


def get_or_create_usage_record(workspace):
    now = timezone.localtime()
    return UsageRecord.objects.get_or_create(
        workspace=workspace,
        year=now.year,
        month=now.month,
        defaults={"posts_used": 0, "ai_generations_used": 0},
    )[0]


def assign_free_plan(workspace):
    ensure_default_plans()
    free_plan = SubscriptionPlan.objects.get(code=SubscriptionPlan.Code.FREE)
    WorkspaceSubscription.objects.get_or_create(workspace=workspace, defaults={"plan": free_plan})


def set_workspace_plan(workspace, plan_code):
    ensure_default_plans()
    plan = SubscriptionPlan.objects.get(code=plan_code)
    subscription, _ = WorkspaceSubscription.objects.get_or_create(
        workspace=workspace,
        defaults={"plan": plan},
    )
    subscription.plan = plan
    subscription.status = "active"
    subscription.save(update_fields=["plan", "status", "updated_at"])
    return subscription


def sync_subscription_from_razorpay(workspace_subscription, razorpay_data):
    workspace_subscription.razorpay_subscription_id = razorpay_data.get("id", workspace_subscription.razorpay_subscription_id)
    workspace_subscription.razorpay_customer_id = razorpay_data.get("customer_id", workspace_subscription.razorpay_customer_id)
    workspace_subscription.status = razorpay_data.get("status", workspace_subscription.status)
    workspace_subscription.metadata = razorpay_data
    if razorpay_data.get("current_start"):
        workspace_subscription.active_from = datetime.fromtimestamp(
            razorpay_data["current_start"],
            tz=dt_timezone.utc,
        )
    if razorpay_data.get("current_end"):
        workspace_subscription.active_until = datetime.fromtimestamp(
            razorpay_data["current_end"],
            tz=dt_timezone.utc,
        )
    workspace_subscription.save()
    return workspace_subscription


def can_create_post(workspace):
    usage = get_or_create_usage_record(workspace)
    subscription = getattr(workspace, "subscription", None)
    if subscription is None:
        assign_free_plan(workspace)
        subscription = workspace.subscription
    return usage.posts_used < subscription.plan.monthly_post_limit


def increment_posts_used(workspace, count=1):
    usage = get_or_create_usage_record(workspace)
    usage.posts_used += count
    usage.save(update_fields=["posts_used", "updated_at"])
    return usage


def increment_ai_generations(workspace, count=1):
    usage = get_or_create_usage_record(workspace)
    usage.ai_generations_used += count
    usage.save(update_fields=["ai_generations_used", "updated_at"])
    return usage
