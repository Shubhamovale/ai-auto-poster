from django import forms
from django.contrib.auth import authenticate
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib.auth.models import User


class SignUpForm(UserCreationForm):
    email = forms.EmailField(required=True)
    company_name = forms.CharField(required=False, max_length=255)

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username", "email", "company_name")

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("An account with this email already exists.")
        return email


class EmailOrUsernameAuthenticationForm(AuthenticationForm):
    username = forms.CharField(
        label="Username or email",
        widget=forms.TextInput(
            attrs={
                "autofocus": True,
                "autocomplete": "username",
                "placeholder": "Enter username or email",
            }
        ),
    )

    def clean(self):
        username_or_email = self.cleaned_data.get("username", "").strip()
        password = self.cleaned_data.get("password")

        if username_or_email and password:
            lookup_value = username_or_email
            matched_user = User.objects.filter(email__iexact=username_or_email).only("username").first()
            if matched_user:
                lookup_value = matched_user.username

            self.user_cache = authenticate(
                self.request,
                username=lookup_value,
                password=password,
            )
            if self.user_cache is None:
                raise self.get_invalid_login_error()
            self.confirm_login_allowed(self.user_cache)

        return self.cleaned_data


class EmailOTPForm(forms.Form):
    otp = forms.CharField(
        label="Verification code",
        min_length=6,
        max_length=6,
        widget=forms.TextInput(
            attrs={
                "inputmode": "numeric",
                "autocomplete": "one-time-code",
                "placeholder": "Enter 6-digit OTP",
            }
        ),
    )

    def clean_otp(self):
        otp = self.cleaned_data["otp"].strip()
        if not otp.isdigit():
            raise forms.ValidationError("Enter the 6-digit code sent to your email.")
        return otp


class ProfileForm(forms.Form):
    company_name = forms.CharField(required=False, max_length=255)
    phone_number = forms.CharField(required=False, max_length=32)
    timezone = forms.CharField(required=False, max_length=64)
