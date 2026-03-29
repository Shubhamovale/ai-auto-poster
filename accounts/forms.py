from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User


class SignUpForm(UserCreationForm):
    email = forms.EmailField(required=True)
    company_name = forms.CharField(required=False, max_length=255)

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username", "email", "company_name")


class ProfileForm(forms.Form):
    company_name = forms.CharField(required=False, max_length=255)
    phone_number = forms.CharField(required=False, max_length=32)
    timezone = forms.CharField(required=False, max_length=64)
