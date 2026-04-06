from django import forms

from .models import Workspace


class WorkspaceForm(forms.ModelForm):
    class Meta:
        model = Workspace
        fields = ("name", "website_url", "brand_voice", "timezone")
        widgets = {
            "name": forms.TextInput(attrs={"placeholder": "Shubham Shorts, My Creator Page, Fitness Reels..."}),
            "website_url": forms.URLInput(attrs={"placeholder": "Optional website or profile link"}),
            "brand_voice": forms.Textarea(
                attrs={
                    "rows": 4,
                    "placeholder": "Optional tone, niche, or style. Example: energetic, funny, informative.",
                }
            ),
        }
        help_texts = {
            "website_url": "Optional.",
            "brand_voice": "Optional. You can add this later.",
        }
        labels = {
            "name": "Space name",
            "website_url": "Website or profile link",
            "brand_voice": "Tone or content style",
        }
