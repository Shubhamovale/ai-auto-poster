from datetime import timedelta
from random import randint

from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core.mail import send_mail
from django.shortcuts import redirect, render
from django.utils import timezone

from .forms import EmailOTPForm, ProfileForm, SignUpForm
from workspaces.services import ensure_default_workspace


SIGNUP_OTP_SESSION_KEY = "signup_otp_state"
SIGNUP_OTP_TTL_MINUTES = 10


def _generate_otp():
    return f"{randint(0, 999999):06d}"


def _send_signup_otp(email, otp):
    send_mail(
        subject="Your AI Auto Poster verification code",
        message=(
            "Use this verification code to finish creating your account: "
            f"{otp}\n\nThis code will expire in {SIGNUP_OTP_TTL_MINUTES} minutes."
        ),
        from_email=None,
        recipient_list=[email],
        fail_silently=False,
    )


def signup_view(request):
    if request.method == "POST":
        form = SignUpForm(request.POST)
        if form.is_valid():
            otp = _generate_otp()
            request.session[SIGNUP_OTP_SESSION_KEY] = {
                "username": form.cleaned_data["username"],
                "email": form.cleaned_data["email"],
                "company_name": form.cleaned_data.get("company_name", ""),
                "password": form.cleaned_data["password1"],
                "otp": otp,
                "expires_at": (timezone.now() + timedelta(minutes=SIGNUP_OTP_TTL_MINUTES)).isoformat(),
            }
            _send_signup_otp(form.cleaned_data["email"], otp)
            messages.success(request, "We sent a 6-digit verification code to your email.")
            return redirect("verify_signup_otp")
    else:
        form = SignUpForm()
    return render(request, "accounts/signup.html", {"form": form})


def verify_signup_otp_view(request):
    signup_state = request.session.get(SIGNUP_OTP_SESSION_KEY)
    if not signup_state:
        messages.error(request, "Your signup session expired. Please create your account again.")
        return redirect("signup")

    if request.method == "POST" and request.POST.get("action") == "resend":
        otp = _generate_otp()
        signup_state["otp"] = otp
        signup_state["expires_at"] = (timezone.now() + timedelta(minutes=SIGNUP_OTP_TTL_MINUTES)).isoformat()
        request.session[SIGNUP_OTP_SESSION_KEY] = signup_state
        _send_signup_otp(signup_state["email"], otp)
        messages.success(request, "A fresh verification code has been sent.")
        return redirect("verify_signup_otp")

    form = EmailOTPForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        expires_at = timezone.datetime.fromisoformat(signup_state["expires_at"])
        if timezone.is_naive(expires_at):
            expires_at = timezone.make_aware(expires_at, timezone.get_current_timezone())
        if timezone.now() > expires_at:
            form.add_error("otp", "This verification code expired. Please request a new one.")
        elif form.cleaned_data["otp"] != signup_state["otp"]:
            form.add_error("otp", "That code does not match. Please try again.")
        elif User.objects.filter(username=signup_state["username"]).exists():
            messages.error(request, "That username is no longer available. Please sign up again.")
            request.session.pop(SIGNUP_OTP_SESSION_KEY, None)
            return redirect("signup")
        elif User.objects.filter(email__iexact=signup_state["email"]).exists():
            messages.error(request, "That email is already registered. Please log in instead.")
            request.session.pop(SIGNUP_OTP_SESSION_KEY, None)
            return redirect("login")
        else:
            user = User.objects.create_user(
                username=signup_state["username"],
                email=signup_state["email"],
                password=signup_state["password"],
            )
            profile = user.profile
            profile.company_name = signup_state.get("company_name", "")
            profile.save(update_fields=["company_name"])
            ensure_default_workspace(user)
            login(request, user)
            request.session.pop(SIGNUP_OTP_SESSION_KEY, None)
            messages.success(request, "Your account is verified. Your content space is ready.")
            return redirect("dashboard:home")

    return render(
        request,
        "accounts/verify_signup_otp.html",
        {"form": form, "pending_email": signup_state["email"], "otp_valid_minutes": SIGNUP_OTP_TTL_MINUTES},
    )


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
