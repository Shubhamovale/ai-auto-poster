import secrets
import json

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import Flow
import requests
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseBadRequest, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.generic import TemplateView
from django.views.decorators.csrf import csrf_exempt

from billing.models import SubscriptionPlan
from billing.services import (
    assign_free_plan,
    can_create_post,
    get_or_create_usage_record,
    increment_ai_generations,
    increment_posts_used,
    set_workspace_plan,
    sync_subscription_from_razorpay,
)
from billing.gateway import (
    create_subscription as razorpay_create_subscription,
    fetch_subscription as razorpay_fetch_subscription,
    razorpay_enabled,
    verify_checkout_signature,
    verify_webhook_signature,
)
from content_engine.services import generate_ai_content
from posting.forms import PostForm
from posting.models import Post
from posting.services import publish_post
from posting.tasks import publish_single_post_task
from social_accounts.models import SocialAccount
from social_accounts.forms import SocialAccountForm
from workspaces.forms import WorkspaceForm
from workspaces.models import Workspace, WorkspaceMembership

YOUTUBE_SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube",
]
FACEBOOK_SCOPES = ["pages_show_list", "pages_manage_posts"]


class LandingPageView(TemplateView):
    template_name = "landing.html"


@login_required
def home(request):
    workspace = request.user.owned_workspaces.first()
    if workspace is None:
        if request.method == "POST":
            form = WorkspaceForm(request.POST)
            if form.is_valid():
                workspace = form.save(commit=False)
                workspace.owner = request.user
                workspace.save()
                WorkspaceMembership.objects.get_or_create(
                    workspace=workspace,
                    user=request.user,
                    defaults={"role": WorkspaceMembership.Role.OWNER},
                )
                assign_free_plan(workspace)
                messages.success(request, "Workspace created. You can start scheduling posts.")
                return redirect("dashboard:home")
        else:
            form = WorkspaceForm()
        return render(request, "dashboard/create_workspace.html", {"form": form})

    assign_free_plan(workspace)
    usage = get_or_create_usage_record(workspace)
    posts = workspace.posts.order_by("-created_at")[:10]
    social_accounts = workspace.social_accounts.order_by("platform")

    return render(
        request,
        "dashboard/home.html",
        {
            "workspace": workspace,
            "posts": posts,
            "social_accounts": social_accounts,
            "usage": usage,
            "subscription": workspace.subscription,
            "plans": SubscriptionPlan.objects.filter(is_active=True).order_by("monthly_price"),
        },
    )


@login_required
def create_post(request):
    workspace = get_object_or_404(Workspace, owner=request.user)
    if not can_create_post(workspace):
        messages.error(request, "Your plan limit has been reached for this month.")
        return redirect("dashboard:home")

    if request.method == "POST":
        form = PostForm(request.POST)
        if form.is_valid():
            post = form.save(commit=False)
            post.workspace = workspace
            post.status = Post.Status.SCHEDULED
            post.platforms = form.cleaned_data["platforms"]
            post.content_payload = request.session.get("draft_ai_payload", {})
            post.save()
            increment_posts_used(workspace)
            messages.success(request, "Post scheduled.")
            return redirect("dashboard:home")
    else:
        initial = {
            "scheduled_for": timezone.localtime().replace(second=0, microsecond=0),
            "platforms": ["facebook", "youtube"],
        }
        try:
            ai_payload = generate_ai_content()
            increment_ai_generations(workspace)
            initial.update(
                {
                    "title": ai_payload.get("title", ""),
                    "caption": ai_payload.get("caption", ""),
                }
            )
            request.session["draft_ai_payload"] = ai_payload
        except Exception as exc:
            request.session["draft_ai_payload"] = {}
            messages.warning(
                request,
                f"AI draft generation is unavailable right now. You can still create a manual post. Details: {exc}",
            )
        form = PostForm(initial=initial)

    return render(request, "dashboard/create_post.html", {"form": form, "workspace": workspace})


@login_required
def save_generated_post(request):
    workspace = get_object_or_404(Workspace, owner=request.user)
    ai_payload = request.session.get("draft_ai_payload")
    if not ai_payload:
        messages.error(request, "Generate a draft first.")
        return redirect("dashboard:create_post")

    post = Post.objects.create(
        workspace=workspace,
        title=ai_payload.get("title", "Untitled Post"),
        caption=ai_payload.get("caption", ""),
        content_payload=ai_payload,
        platforms=["facebook", "youtube"],
        scheduled_for=timezone.now(),
        status=Post.Status.DRAFT,
    )
    messages.success(request, "AI draft saved.")
    return redirect("dashboard:edit_post", post_id=post.id)


@login_required
def edit_post(request, post_id):
    workspace = get_object_or_404(Workspace, owner=request.user)
    post = get_object_or_404(Post, workspace=workspace, pk=post_id)
    if request.method == "POST":
        form = PostForm(request.POST, instance=post)
        if form.is_valid():
            post = form.save(commit=False)
            post.platforms = form.cleaned_data["platforms"]
            post.save()
            messages.success(request, "Post updated.")
            return redirect("dashboard:home")
    else:
        form = PostForm(instance=post, initial={"platforms": post.platforms})
    return render(
        request,
        "dashboard/edit_post.html",
        {
            "form": form,
            "post": post,
            "runs": post.runs.order_by("-started_at"),
        },
    )


@login_required
def connect_account(request):
    workspace = get_object_or_404(Workspace, owner=request.user)
    show_advanced_setup = request.method == "POST" or request.GET.get("advanced") == "1"
    if request.method == "POST":
        form = SocialAccountForm(request.POST)
        if form.is_valid():
            social_account = form.save(commit=False)
            social_account.workspace = workspace
            social_account.save()
            messages.success(request, "Social account saved.")
            return redirect("dashboard:home")
    else:
        form = SocialAccountForm()
    return render(
        request,
        "dashboard/connect_account.html",
        {
            "form": form,
            "workspace": workspace,
            "show_advanced_setup": show_advanced_setup,
        },
    )


def _youtube_client_config():
    if not settings.YOUTUBE_OAUTH_CLIENT_ID or not settings.YOUTUBE_OAUTH_CLIENT_SECRET:
        raise RuntimeError(
            "Missing YouTube OAuth client settings. Set YOUTUBE_OAUTH_CLIENT_ID and YOUTUBE_OAUTH_CLIENT_SECRET."
        )
    return {
        "web": {
            "client_id": settings.YOUTUBE_OAUTH_CLIENT_ID,
            "client_secret": settings.YOUTUBE_OAUTH_CLIENT_SECRET,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
        }
    }


def _youtube_redirect_uri(request):
    if settings.YOUTUBE_OAUTH_REDIRECT_URI:
        return settings.YOUTUBE_OAUTH_REDIRECT_URI
    return request.build_absolute_uri(reverse("dashboard:youtube_oauth_callback"))


def _facebook_redirect_uri(request):
    if settings.FACEBOOK_OAUTH_REDIRECT_URI:
        return settings.FACEBOOK_OAUTH_REDIRECT_URI
    return request.build_absolute_uri(reverse("dashboard:facebook_oauth_callback"))


@login_required
def start_youtube_oauth(request):
    workspace = get_object_or_404(Workspace, owner=request.user)
    try:
        flow = Flow.from_client_config(
            _youtube_client_config(),
            scopes=YOUTUBE_SCOPES,
            redirect_uri=_youtube_redirect_uri(request),
        )
    except RuntimeError as exc:
        messages.error(request, str(exc))
        return redirect("dashboard:home")

    authorization_url, state = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent",
    )
    request.session["youtube_oauth_state"] = state
    request.session["youtube_oauth_workspace_id"] = workspace.id
    return redirect(authorization_url)


@login_required
def start_facebook_oauth(request):
    workspace = get_object_or_404(Workspace, owner=request.user)
    if not settings.FACEBOOK_OAUTH_APP_ID or not settings.FACEBOOK_OAUTH_APP_SECRET:
        messages.error(
            request,
            "Missing Facebook OAuth settings. Set FACEBOOK_OAUTH_APP_ID and FACEBOOK_OAUTH_APP_SECRET.",
        )
        return redirect("dashboard:home")

    state = secrets.token_urlsafe(24)
    request.session["facebook_oauth_state"] = state
    request.session["facebook_oauth_workspace_id"] = workspace.id

    params = {
        "client_id": settings.FACEBOOK_OAUTH_APP_ID,
        "redirect_uri": _facebook_redirect_uri(request),
        "state": state,
        "scope": ",".join(FACEBOOK_SCOPES),
        "response_type": "code",
    }
    query = "&".join(f"{key}={requests.utils.quote(str(value), safe='')}" for key, value in params.items())
    return redirect(f"https://www.facebook.com/v22.0/dialog/oauth?{query}")


@login_required
def youtube_oauth_callback(request):
    workspace_id = request.session.get("youtube_oauth_workspace_id")
    state = request.session.get("youtube_oauth_state")
    workspace = get_object_or_404(Workspace, owner=request.user, pk=workspace_id)
    if not state:
        messages.error(request, "Missing YouTube OAuth state. Start the connection again.")
        return redirect("dashboard:home")

    flow = Flow.from_client_config(
        _youtube_client_config(),
        scopes=YOUTUBE_SCOPES,
        state=state,
        redirect_uri=_youtube_redirect_uri(request),
    )

    try:
        flow.fetch_token(authorization_response=request.build_absolute_uri())
        credentials = flow.credentials
        youtube = build("youtube", "v3", credentials=credentials)
        response = youtube.channels().list(part="snippet", mine=True).execute()
        items = response.get("items", [])
        if not items:
            raise RuntimeError("No YouTube channel was returned for this Google account.")
        channel = items[0]
        SocialAccount.objects.update_or_create(
            workspace=workspace,
            platform=SocialAccount.Platform.YOUTUBE,
            account_identifier=channel["id"],
            defaults={
                "account_name": channel["snippet"]["title"],
                "client_id": settings.YOUTUBE_OAUTH_CLIENT_ID,
                "client_secret": settings.YOUTUBE_OAUTH_CLIENT_SECRET,
                "token_uri": credentials.token_uri or "https://oauth2.googleapis.com/token",
                "access_token": credentials.token or "",
                "refresh_token": credentials.refresh_token or "",
                "token_expires_at": credentials.expiry,
                "is_connected": True,
                "metadata": {
                    "channel_title": channel["snippet"]["title"],
                    "scope": credentials.scopes,
                },
            },
        )
        messages.success(request, "YouTube channel connected successfully.")
    except Exception as exc:
        messages.error(request, f"YouTube connection failed: {exc}")
    finally:
        request.session.pop("youtube_oauth_state", None)
        request.session.pop("youtube_oauth_workspace_id", None)

    return redirect("dashboard:home")


def _store_facebook_page(workspace, page, user_access_token):
    SocialAccount.objects.update_or_create(
        workspace=workspace,
        platform=SocialAccount.Platform.FACEBOOK,
        account_identifier=page["id"],
        defaults={
            "account_name": page.get("name", "Facebook Page"),
            "access_token": page.get("access_token", ""),
            "refresh_token": "",
            "client_id": settings.FACEBOOK_OAUTH_APP_ID,
            "client_secret": settings.FACEBOOK_OAUTH_APP_SECRET,
            "metadata": {
                "page_name": page.get("name", ""),
                "page_tasks": page.get("tasks", []),
                "user_access_token": user_access_token,
            },
            "is_connected": True,
        },
    )


@login_required
def facebook_oauth_callback(request):
    workspace_id = request.session.get("facebook_oauth_workspace_id")
    expected_state = request.session.get("facebook_oauth_state")
    workspace = get_object_or_404(Workspace, owner=request.user, pk=workspace_id)

    if not expected_state:
        messages.error(request, "Missing Facebook OAuth state. Start the connection again.")
        return redirect("dashboard:home")
    if request.GET.get("state") != expected_state:
        messages.error(request, "Facebook OAuth state mismatch. Start the connection again.")
        return redirect("dashboard:home")
    if request.GET.get("error"):
        messages.error(request, f"Facebook connection failed: {request.GET.get('error_description', request.GET['error'])}")
        return redirect("dashboard:home")

    try:
        token_response = requests.get(
            "https://graph.facebook.com/v22.0/oauth/access_token",
            params={
                "client_id": settings.FACEBOOK_OAUTH_APP_ID,
                "client_secret": settings.FACEBOOK_OAUTH_APP_SECRET,
                "redirect_uri": _facebook_redirect_uri(request),
                "code": request.GET["code"],
            },
            timeout=20,
        )
        token_response.raise_for_status()
        user_access_token = token_response.json()["access_token"]

        pages_response = requests.get(
            "https://graph.facebook.com/v22.0/me/accounts",
            params={
                "access_token": user_access_token,
                "fields": "id,name,access_token,tasks",
            },
            timeout=20,
        )
        pages_response.raise_for_status()
        pages = pages_response.json().get("data", [])
        if not pages:
            raise RuntimeError("No Facebook Pages were returned for this account.")

        if len(pages) == 1:
            _store_facebook_page(workspace, pages[0], user_access_token)
            messages.success(request, "Facebook Page connected successfully.")
            return redirect("dashboard:home")

        request.session["facebook_page_options"] = pages
        request.session["facebook_user_access_token"] = user_access_token
        return render(
            request,
            "dashboard/select_facebook_page.html",
            {"workspace": workspace, "pages": pages},
        )
    except Exception as exc:
        messages.error(request, f"Facebook connection failed: {exc}")
        return redirect("dashboard:home")
    finally:
        request.session.pop("facebook_oauth_state", None)
        request.session.pop("facebook_oauth_workspace_id", None)


@login_required
def select_facebook_page(request):
    workspace = get_object_or_404(Workspace, owner=request.user)
    if request.method != "POST":
        return redirect("dashboard:home")

    pages = request.session.get("facebook_page_options", [])
    user_access_token = request.session.get("facebook_user_access_token", "")
    page_id = request.POST.get("page_id", "")
    selected_page = next((page for page in pages if page.get("id") == page_id), None)
    if not selected_page:
        messages.error(request, "Choose a valid Facebook Page.")
        return redirect("dashboard:home")

    _store_facebook_page(workspace, selected_page, user_access_token)
    request.session.pop("facebook_page_options", None)
    request.session.pop("facebook_user_access_token", None)
    messages.success(request, "Facebook Page connected successfully.")
    return redirect("dashboard:home")


@login_required
def edit_account(request, account_id):
    workspace = get_object_or_404(Workspace, owner=request.user)
    social_account = get_object_or_404(workspace.social_accounts, pk=account_id)
    if request.method == "POST":
        form = SocialAccountForm(request.POST, instance=social_account)
        if form.is_valid():
            form.save()
            messages.success(request, "Social account updated.")
            return redirect("dashboard:home")
    else:
        form = SocialAccountForm(instance=social_account)
    return render(
        request,
        "dashboard/connect_account.html",
        {"form": form, "workspace": workspace, "editing": True, "social_account": social_account},
    )


@login_required
def disconnect_account(request, account_id):
    workspace = get_object_or_404(Workspace, owner=request.user)
    social_account = get_object_or_404(workspace.social_accounts, pk=account_id)
    if request.method == "POST":
        social_account.is_connected = False
        social_account.save(update_fields=["is_connected", "updated_at"])
        messages.success(request, "Social account disconnected.")
    return redirect("dashboard:home")


@login_required
def change_plan(request, plan_code):
    workspace = get_object_or_404(Workspace, owner=request.user)
    if plan_code == SubscriptionPlan.Code.FREE:
        set_workspace_plan(workspace, plan_code)
        messages.success(request, f"Plan updated to {plan_code.title()}.")
    else:
        messages.info(request, "Use Subscribe to start a paid plan checkout.")
    return redirect("dashboard:home")


@login_required
def publish_now(request, post_id):
    workspace = get_object_or_404(Workspace, owner=request.user)
    post = get_object_or_404(Post, workspace=workspace, pk=post_id)
    if request.method != "POST":
        return redirect("dashboard:edit_post", post_id=post.id)

    try:
        post.status = Post.Status.SCHEDULED
        post.scheduled_for = timezone.now()
        post.save(update_fields=["status", "scheduled_for", "updated_at"])
        if settings.ASYNC_TASKS_ENABLED:
            publish_single_post_task.delay(post.id)
            messages.success(request, "Post queued for background publishing.")
        else:
            publish_post(post)
            messages.success(request, "Post publish job completed.")
    except Exception as exc:
        messages.error(request, f"Publishing failed: {exc}")
    return redirect("dashboard:edit_post", post_id=post.id)


@login_required
def subscribe_plan(request, plan_code):
    workspace = get_object_or_404(Workspace, owner=request.user)
    plan = get_object_or_404(SubscriptionPlan, code=plan_code, is_active=True)
    if plan.code == SubscriptionPlan.Code.FREE:
        set_workspace_plan(workspace, plan.code)
        messages.success(request, "Workspace switched to the Free plan.")
        return redirect("dashboard:home")
    if not razorpay_enabled():
        messages.error(request, "Razorpay is not configured yet.")
        return redirect("dashboard:home")
    if not plan.razorpay_plan_id:
        messages.error(request, f"No Razorpay plan id is configured for the {plan.name} plan.")
        return redirect("dashboard:home")

    subscription = workspace.subscription
    razorpay_subscription = razorpay_create_subscription(
        plan_id=plan.razorpay_plan_id,
        customer_notify=1,
        total_count=120,
        notes={
            "workspace_id": str(workspace.id),
            "workspace_slug": workspace.slug,
            "plan_code": plan.code,
            "user_email": request.user.email or request.user.username,
        },
    )
    subscription.plan = plan
    subscription.razorpay_subscription_id = razorpay_subscription["id"]
    subscription.status = razorpay_subscription.get("status", "created")
    subscription.metadata = razorpay_subscription
    subscription.save()
    return render(
        request,
        "dashboard/razorpay_checkout.html",
        {
            "workspace": workspace,
            "plan": plan,
            "subscription": subscription,
            "razorpay_key_id": settings.RAZORPAY_KEY_ID,
            "callback_url": request.build_absolute_uri(reverse("dashboard:razorpay_verify")),
        },
    )


@login_required
def razorpay_verify(request):
    if request.method != "POST":
        return HttpResponseBadRequest("Invalid request method.")

    workspace = get_object_or_404(Workspace, owner=request.user)
    subscription = workspace.subscription
    payment_id = request.POST.get("razorpay_payment_id", "")
    subscription_id = request.POST.get("razorpay_subscription_id", "")
    signature = request.POST.get("razorpay_signature", "")
    if not payment_id or not subscription_id or not signature:
        messages.error(request, "Missing Razorpay verification fields.")
        return redirect("dashboard:home")

    if not verify_checkout_signature(
        payment_id=payment_id,
        subscription_id=subscription_id,
        signature=signature,
    ):
        messages.error(request, "Razorpay signature verification failed.")
        return redirect("dashboard:home")

    razorpay_data = razorpay_fetch_subscription(subscription_id)
    subscription.razorpay_payment_id = payment_id
    sync_subscription_from_razorpay(subscription, razorpay_data)
    messages.success(request, "Subscription payment verified. Plan status updated.")
    return redirect("dashboard:home")


@csrf_exempt
def razorpay_webhook(request):
    if request.method != "POST":
        return HttpResponseBadRequest("Invalid request method.")
    if not settings.RAZORPAY_WEBHOOK_SECRET:
        return HttpResponseBadRequest("Webhook secret is not configured.")

    signature = request.headers.get("X-Razorpay-Signature", "")
    body = request.body
    if not signature or not verify_webhook_signature(body=body, signature=signature):
        return HttpResponseBadRequest("Invalid webhook signature.")

    payload = json.loads(body.decode("utf-8"))
    event = payload.get("event", "")
    subscription_entity = (
        payload.get("payload", {})
        .get("subscription", {})
        .get("entity")
    )
    if not subscription_entity:
        return JsonResponse({"status": "ignored", "reason": "no subscription payload"})

    workspace = (
        Workspace.objects.filter(id=subscription_entity.get("notes", {}).get("workspace_id"))
        .select_related("subscription")
        .first()
    )
    if not workspace or not hasattr(workspace, "subscription"):
        return JsonResponse({"status": "ignored", "reason": "workspace not found"})

    local_subscription = workspace.subscription
    sync_subscription_from_razorpay(local_subscription, subscription_entity)

    payment_entity = (
        payload.get("payload", {})
        .get("payment", {})
        .get("entity")
    )
    if payment_entity:
        local_subscription.razorpay_payment_id = payment_entity.get("id", local_subscription.razorpay_payment_id)
        local_subscription.save(update_fields=["razorpay_payment_id", "updated_at"])

    return JsonResponse({"status": "ok", "event": event})
