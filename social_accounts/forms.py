from django import forms

from .models import SocialAccount


class SocialAccountForm(forms.ModelForm):
    class Meta:
        model = SocialAccount
        fields = (
            "platform",
            "account_name",
            "account_identifier",
            "client_id",
            "client_secret",
            "token_uri",
            "access_token",
            "refresh_token",
            "token_expires_at",
            "is_connected",
        )
        widgets = {
            "access_token": forms.Textarea(attrs={"rows": 3}),
            "refresh_token": forms.Textarea(attrs={"rows": 3}),
            "client_secret": forms.PasswordInput(render_value=True),
            "token_expires_at": forms.DateTimeInput(attrs={"type": "datetime-local"}),
        }

    def clean(self):
        cleaned_data = super().clean()
        platform = cleaned_data.get("platform")
        if platform == SocialAccount.Platform.FACEBOOK and not cleaned_data.get("account_identifier"):
            self.add_error("account_identifier", "Facebook requires the page ID in this field.")
        if platform == SocialAccount.Platform.YOUTUBE:
            for field in ("client_id", "client_secret", "refresh_token"):
                if not cleaned_data.get(field):
                    self.add_error(field, "This field is required for YouTube publishing.")
        if platform == SocialAccount.Platform.LINKEDIN and not cleaned_data.get("access_token"):
            self.add_error("access_token", "LinkedIn publishing requires an access token.")
        return cleaned_data
