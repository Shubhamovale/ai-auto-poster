from django.contrib import admin

from .models import Workspace, WorkspaceMembership


class WorkspaceMembershipInline(admin.TabularInline):
    model = WorkspaceMembership
    extra = 0


@admin.register(Workspace)
class WorkspaceAdmin(admin.ModelAdmin):
    list_display = ("name", "owner", "timezone", "is_active", "created_at")
    search_fields = ("name", "owner__username", "owner__email")
    prepopulated_fields = {"slug": ("name",)}
    inlines = [WorkspaceMembershipInline]


@admin.register(WorkspaceMembership)
class WorkspaceMembershipAdmin(admin.ModelAdmin):
    list_display = ("workspace", "user", "role", "created_at")
    search_fields = ("workspace__name", "user__username", "user__email")
