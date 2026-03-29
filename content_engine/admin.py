from django.contrib import admin

from .models import ContentIdea, ContentTemplate


@admin.register(ContentTemplate)
class ContentTemplateAdmin(admin.ModelAdmin):
    list_display = ("name", "workspace", "is_default", "updated_at")
    list_filter = ("is_default",)


@admin.register(ContentIdea)
class ContentIdeaAdmin(admin.ModelAdmin):
    list_display = ("topic", "workspace", "status", "created_at")
    list_filter = ("status",)
