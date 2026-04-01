from django import forms

from .models import Post


class PostForm(forms.ModelForm):
    platforms = forms.MultipleChoiceField(
        choices=[
            ("facebook", "Facebook"),
            ("instagram", "Instagram"),
            ("linkedin", "LinkedIn"),
            ("youtube", "YouTube"),
        ],
        widget=forms.CheckboxSelectMultiple,
    )

    class Meta:
        model = Post
        fields = ("title", "caption", "scheduled_for", "platforms")
        widgets = {
            "caption": forms.Textarea(attrs={"rows": 4}),
            "scheduled_for": forms.DateTimeInput(attrs={"type": "datetime-local"}),
        }
