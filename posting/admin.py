from django.contrib import admin

from .models import Post, PostRun


class PostRunInline(admin.TabularInline):
    model = PostRun
    extra = 0


@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ("title", "workspace", "status", "scheduled_for", "updated_at")
    list_filter = ("status",)
    search_fields = ("title", "workspace__name")
    inlines = [PostRunInline]


@admin.register(PostRun)
class PostRunAdmin(admin.ModelAdmin):
    list_display = ("post", "platform", "status", "started_at", "completed_at")
    list_filter = ("platform", "status")
