from django.test import TestCase

from .forms import SocialAccountForm


class SocialAccountFormTests(TestCase):
    def test_youtube_requires_oauth_fields(self):
        form = SocialAccountForm(
            data={
                "platform": "youtube",
                "account_name": "My Channel",
                "account_identifier": "channel-id",
                "is_connected": "on",
            }
        )
        self.assertFalse(form.is_valid())
        self.assertIn("client_id", form.errors)
        self.assertIn("client_secret", form.errors)
        self.assertIn("refresh_token", form.errors)

    def test_facebook_requires_page_id(self):
        form = SocialAccountForm(
            data={
                "platform": "facebook",
                "account_name": "My Page",
                "access_token": "token",
                "is_connected": "on",
            }
        )
        self.assertFalse(form.is_valid())
        self.assertIn("account_identifier", form.errors)
