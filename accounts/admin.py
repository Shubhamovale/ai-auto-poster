from django.contrib import admin

from .models import UserProfile


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "company_name", "timezone", "onboarding_completed")
    search_fields = ("user__username", "user__email", "company_name")
