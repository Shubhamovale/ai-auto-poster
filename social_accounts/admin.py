from django.contrib import admin

from .models import SocialAccount


@admin.register(SocialAccount)
class SocialAccountAdmin(admin.ModelAdmin):
    list_display = ("workspace", "platform", "account_name", "is_connected", "updated_at")
    list_filter = ("platform", "is_connected")
    search_fields = ("workspace__name", "account_name", "account_identifier")
