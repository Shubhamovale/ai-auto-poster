from django.contrib import admin

from .models import SubscriptionPlan, UsageRecord, WorkspaceSubscription


@admin.register(SubscriptionPlan)
class SubscriptionPlanAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "monthly_price", "monthly_post_limit", "supports_all_platforms", "is_active")
    list_filter = ("supports_all_platforms", "is_active")


@admin.register(WorkspaceSubscription)
class WorkspaceSubscriptionAdmin(admin.ModelAdmin):
    list_display = ("workspace", "plan", "status", "active_from", "active_until")
    list_filter = ("status", "plan")


@admin.register(UsageRecord)
class UsageRecordAdmin(admin.ModelAdmin):
    list_display = ("workspace", "year", "month", "posts_used", "ai_generations_used")
