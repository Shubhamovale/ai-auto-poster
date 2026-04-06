from billing.services import assign_free_plan

from .models import Workspace, WorkspaceMembership


def default_workspace_name_for_user(user):
    profile = getattr(user, "profile", None)
    company_name = getattr(profile, "company_name", "").strip() if profile else ""
    if company_name:
        return company_name

    base_name = user.get_full_name().strip() or user.username.strip() or "Creator"
    return f"{base_name}'s space"


def ensure_default_workspace(user):
    workspace = user.owned_workspaces.order_by("created_at").first()
    if workspace:
        if not hasattr(workspace, "subscription"):
            assign_free_plan(workspace)
        return workspace, False

    workspace = Workspace.objects.create(
        owner=user,
        name=default_workspace_name_for_user(user),
        timezone=getattr(getattr(user, "profile", None), "timezone", "") or "Asia/Kolkata",
    )
    WorkspaceMembership.objects.get_or_create(
        workspace=workspace,
        user=user,
        defaults={"role": WorkspaceMembership.Role.OWNER},
    )
    assign_free_plan(workspace)
    return workspace, True
