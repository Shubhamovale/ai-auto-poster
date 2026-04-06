from django.contrib.auth.models import User
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from unittest.mock import MagicMock, patch

from billing.services import assign_free_plan, ensure_default_plans
from billing.models import SubscriptionPlan
from posting.models import Post
from social_accounts.models import SocialAccount
from workspaces.models import Workspace
import hashlib
import hmac
import json


class DashboardSmokeTests(TestCase):
    def setUp(self):
        ensure_default_plans()
        self.user = User.objects.create_user(
            username="dashboard-user",
            email="dash@example.com",
            password="strong-pass-123",
        )
        self.workspace = Workspace.objects.create(owner=self.user, name="Workspace One")
        assign_free_plan(self.workspace)
        self.post = Post.objects.create(
            workspace=self.workspace,
            title="Test Post",
            caption="Caption",
            platforms=["facebook"],
            status=Post.Status.DRAFT,
        )
        self.client = Client()
        self.client.login(username="dashboard-user", password="strong-pass-123")

    def test_dashboard_home_renders(self):
        response = self.client.get(reverse("dashboard:home"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Workspace One")

    def test_dashboard_home_auto_creates_default_workspace(self):
        user = User.objects.create_user(
            username="creator-user",
            email="creator@example.com",
            password="strong-pass-123",
        )
        client = Client()
        client.login(username="creator-user", password="strong-pass-123")

        response = client.get(reverse("dashboard:home"))

        self.assertEqual(response.status_code, 200)
        workspace = Workspace.objects.get(owner=user)
        self.assertEqual(workspace.name, "creator-user's space")
        self.assertContains(response, "creator-user&#x27;s space")

    def test_edit_post_renders(self):
        response = self.client.get(reverse("dashboard:edit_post", args=[self.post.id]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Edit post")

    def test_connect_account_page_prefers_oauth_cards(self):
        response = self.client.get(reverse("dashboard:connect_account"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Connect Facebook")
        self.assertContains(response, "Connect YouTube")
        self.assertContains(response, "Advanced setup")
        self.assertNotContains(response, "Account identifier:")

    def test_connect_account_advanced_setup_shows_manual_form(self):
        response = self.client.get(f"{reverse('dashboard:connect_account')}?advanced=1")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Advanced setup")
        self.assertContains(response, "Account identifier:")

    def test_publish_now_redirects(self):
        response = self.client.post(reverse("dashboard:publish_now", args=[self.post.id]))
        self.assertEqual(response.status_code, 302)

    @override_settings(
        YOUTUBE_OAUTH_CLIENT_ID="client-id",
        YOUTUBE_OAUTH_CLIENT_SECRET="client-secret",
    )
    @patch("dashboard.views.Flow.from_client_config")
    def test_start_youtube_oauth_redirects_to_google(self, mock_flow_factory):
        fake_flow = MagicMock()
        fake_flow.authorization_url.return_value = ("https://accounts.google.com/o/oauth2/auth?x=1", "state-123")
        mock_flow_factory.return_value = fake_flow

        response = self.client.get(reverse("dashboard:start_youtube_oauth"))

        self.assertEqual(response.status_code, 302)
        self.assertIn("accounts.google.com", response["Location"])
        session = self.client.session
        self.assertEqual(session["youtube_oauth_state"], "state-123")
        self.assertEqual(session["youtube_oauth_workspace_id"], self.workspace.id)

    @override_settings(
        YOUTUBE_OAUTH_CLIENT_ID="client-id",
        YOUTUBE_OAUTH_CLIENT_SECRET="client-secret",
    )
    @patch("dashboard.views.build")
    @patch("dashboard.views.Flow.from_client_config")
    def test_youtube_oauth_callback_saves_connected_account(self, mock_flow_factory, mock_build):
        session = self.client.session
        session["youtube_oauth_state"] = "state-123"
        session["youtube_oauth_workspace_id"] = self.workspace.id
        session.save()

        fake_credentials = MagicMock()
        fake_credentials.token = "access-token"
        fake_credentials.refresh_token = "refresh-token"
        fake_credentials.token_uri = "https://oauth2.googleapis.com/token"
        fake_credentials.expiry = None
        fake_credentials.scopes = ["scope-a"]

        fake_flow = MagicMock()
        fake_flow.credentials = fake_credentials
        mock_flow_factory.return_value = fake_flow

        youtube = MagicMock()
        youtube.channels.return_value.list.return_value.execute.return_value = {
            "items": [{"id": "channel-1", "snippet": {"title": "My Channel"}}]
        }
        mock_build.return_value = youtube

        response = self.client.get(
            reverse("dashboard:youtube_oauth_callback"),
            {"state": "state-123", "code": "code-abc"},
        )

        self.assertEqual(response.status_code, 302)
        account = SocialAccount.objects.get(workspace=self.workspace, platform=SocialAccount.Platform.YOUTUBE)
        self.assertEqual(account.account_identifier, "channel-1")
        self.assertEqual(account.account_name, "My Channel")
        self.assertTrue(account.is_connected)

    @override_settings(
        FACEBOOK_OAUTH_APP_ID="fb-app-id",
        FACEBOOK_OAUTH_APP_SECRET="fb-app-secret",
    )
    def test_start_facebook_oauth_redirects_to_meta(self):
        response = self.client.get(reverse("dashboard:start_facebook_oauth"))

        self.assertEqual(response.status_code, 302)
        self.assertIn("facebook.com", response["Location"])
        session = self.client.session
        self.assertEqual(session["facebook_oauth_workspace_id"], self.workspace.id)
        self.assertTrue(session["facebook_oauth_state"])

    @override_settings(
        FACEBOOK_OAUTH_APP_ID="fb-app-id",
        FACEBOOK_OAUTH_APP_SECRET="fb-app-secret",
    )
    @patch("dashboard.views.requests.get")
    def test_facebook_oauth_callback_saves_single_page(self, mock_get):
        session = self.client.session
        session["facebook_oauth_state"] = "fb-state"
        session["facebook_oauth_workspace_id"] = self.workspace.id
        session.save()

        token_response = MagicMock()
        token_response.json.return_value = {"access_token": "user-token"}
        token_response.raise_for_status.return_value = None

        pages_response = MagicMock()
        pages_response.json.return_value = {
            "data": [{"id": "page-1", "name": "My Page", "access_token": "page-token", "tasks": ["CREATE_CONTENT"]}]
        }
        pages_response.raise_for_status.return_value = None
        mock_get.side_effect = [token_response, pages_response]

        response = self.client.get(
            reverse("dashboard:facebook_oauth_callback"),
            {"state": "fb-state", "code": "fb-code"},
        )

        self.assertEqual(response.status_code, 302)
        account = SocialAccount.objects.get(workspace=self.workspace, platform=SocialAccount.Platform.FACEBOOK)
        self.assertEqual(account.account_identifier, "page-1")
        self.assertEqual(account.access_token, "page-token")
        self.assertTrue(account.is_connected)

    @override_settings(
        FACEBOOK_OAUTH_APP_ID="fb-app-id",
        FACEBOOK_OAUTH_APP_SECRET="fb-app-secret",
    )
    @patch("dashboard.views.requests.get")
    def test_facebook_oauth_callback_prompts_for_page_selection(self, mock_get):
        session = self.client.session
        session["facebook_oauth_state"] = "fb-state"
        session["facebook_oauth_workspace_id"] = self.workspace.id
        session.save()

        token_response = MagicMock()
        token_response.json.return_value = {"access_token": "user-token"}
        token_response.raise_for_status.return_value = None

        pages_response = MagicMock()
        pages_response.json.return_value = {
            "data": [
                {"id": "page-1", "name": "Page One", "access_token": "page-token-1", "tasks": ["CREATE_CONTENT"]},
                {"id": "page-2", "name": "Page Two", "access_token": "page-token-2", "tasks": ["CREATE_CONTENT"]},
            ]
        }
        pages_response.raise_for_status.return_value = None
        mock_get.side_effect = [token_response, pages_response]

        response = self.client.get(
            reverse("dashboard:facebook_oauth_callback"),
            {"state": "fb-state", "code": "fb-code"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Choose a Facebook Page")
        session = self.client.session
        self.assertEqual(len(session["facebook_page_options"]), 2)

    def test_select_facebook_page_saves_choice(self):
        session = self.client.session
        session["facebook_page_options"] = [
            {"id": "page-1", "name": "Page One", "access_token": "page-token-1", "tasks": ["CREATE_CONTENT"]},
            {"id": "page-2", "name": "Page Two", "access_token": "page-token-2", "tasks": ["CREATE_CONTENT"]},
        ]
        session["facebook_user_access_token"] = "user-token"
        session.save()

        response = self.client.post(reverse("dashboard:select_facebook_page"), {"page_id": "page-2"})

        self.assertEqual(response.status_code, 302)
        account = SocialAccount.objects.get(workspace=self.workspace, platform=SocialAccount.Platform.FACEBOOK)
        self.assertEqual(account.account_identifier, "page-2")
        self.assertEqual(account.access_token, "page-token-2")

    @override_settings(
        RAZORPAY_KEY_ID="rzp_test_key",
        RAZORPAY_KEY_SECRET="rzp_test_secret",
    )
    @patch("dashboard.views.razorpay_create_subscription")
    def test_subscribe_plan_renders_checkout(self, mock_create_subscription):
        plan = SubscriptionPlan.objects.get(code=SubscriptionPlan.Code.BASIC)
        plan.razorpay_plan_id = "plan_basic"
        plan.save(update_fields=["razorpay_plan_id"])
        mock_create_subscription.return_value = {"id": "sub_123", "status": "created"}

        response = self.client.get(reverse("dashboard:subscribe_plan", args=[plan.code]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Razorpay Checkout")
        self.workspace.subscription.refresh_from_db()
        self.assertEqual(self.workspace.subscription.razorpay_subscription_id, "sub_123")

    @override_settings(
        RAZORPAY_KEY_SECRET="rzp_test_secret",
    )
    @patch("dashboard.views.razorpay_fetch_subscription")
    @patch("dashboard.views.verify_checkout_signature")
    def test_razorpay_verify_updates_subscription(self, mock_verify_signature, mock_fetch_subscription):
        mock_verify_signature.return_value = True
        self.workspace.subscription.razorpay_subscription_id = "sub_123"
        self.workspace.subscription.save(update_fields=["razorpay_subscription_id"])
        mock_fetch_subscription.return_value = {
            "id": "sub_123",
            "status": "active",
            "customer_id": "cust_123",
            "current_start": 1710000000,
            "current_end": 1712592000,
        }

        response = self.client.post(
            reverse("dashboard:razorpay_verify"),
            {
                "razorpay_payment_id": "pay_123",
                "razorpay_subscription_id": "sub_123",
                "razorpay_signature": "sig_123",
            },
        )

        self.assertEqual(response.status_code, 302)
        self.workspace.subscription.refresh_from_db()
        self.assertEqual(self.workspace.subscription.status, "active")
        self.assertEqual(self.workspace.subscription.razorpay_payment_id, "pay_123")

    @override_settings(
        RAZORPAY_WEBHOOK_SECRET="webhook_secret",
    )
    def test_razorpay_webhook_updates_subscription(self):
        self.workspace.subscription.razorpay_subscription_id = "sub_123"
        self.workspace.subscription.save(update_fields=["razorpay_subscription_id"])
        payload = {
            "event": "subscription.activated",
            "payload": {
                "subscription": {
                    "entity": {
                        "id": "sub_123",
                        "status": "active",
                        "customer_id": "cust_123",
                        "current_start": 1710000000,
                        "current_end": 1712592000,
                        "notes": {"workspace_id": str(self.workspace.id)},
                    }
                },
                "payment": {"entity": {"id": "pay_123"}},
            },
        }
        body = json.dumps(payload).encode("utf-8")
        signature = hmac.new(b"webhook_secret", body, hashlib.sha256).hexdigest()

        response = self.client.post(
            reverse("dashboard:razorpay_webhook"),
            data=body,
            content_type="application/json",
            headers={"X-Razorpay-Signature": signature},
        )

        self.assertEqual(response.status_code, 200)
        self.workspace.subscription.refresh_from_db()
        self.assertEqual(self.workspace.subscription.status, "active")
        self.assertEqual(self.workspace.subscription.razorpay_payment_id, "pay_123")
