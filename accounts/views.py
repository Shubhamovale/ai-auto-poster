from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from .forms import ProfileForm, SignUpForm


def signup_view(request):
    if request.method == "POST":
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.email = form.cleaned_data["email"]
            user.save()
            profile = user.profile
            profile.company_name = form.cleaned_data.get("company_name", "")
            profile.save()
            login(request, user)
            messages.success(request, "Your account is ready. Let's set up your workspace.")
            return redirect("dashboard:home")
    else:
        form = SignUpForm()
    return render(request, "accounts/signup.html", {"form": form})


@login_required
def profile_view(request):
    profile = request.user.profile
    if request.method == "POST":
        form = ProfileForm(request.POST)
        if form.is_valid():
            profile.company_name = form.cleaned_data["company_name"]
            profile.phone_number = form.cleaned_data["phone_number"]
            profile.timezone = form.cleaned_data["timezone"] or profile.timezone
            profile.onboarding_completed = True
            profile.save()
            messages.success(request, "Profile updated.")
            return redirect("dashboard:home")
    else:
        form = ProfileForm(
            initial={
                "company_name": profile.company_name,
                "phone_number": profile.phone_number,
                "timezone": profile.timezone,
            }
        )
    return render(request, "accounts/profile.html", {"form": form})
