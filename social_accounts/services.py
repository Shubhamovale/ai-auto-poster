from social_accounts.models import SocialAccount


def get_connected_account(workspace, platform):
    return (
        workspace.social_accounts.filter(platform=platform, is_connected=True)
        .order_by("-updated_at")
        .first()
    )
