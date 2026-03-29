from django import forms

from .models import Workspace


class WorkspaceForm(forms.ModelForm):
    class Meta:
        model = Workspace
        fields = ("name", "website_url", "brand_voice", "timezone")
        widgets = {
            "brand_voice": forms.Textarea(attrs={"rows": 4}),
        }
