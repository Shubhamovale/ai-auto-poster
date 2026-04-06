from django.urls import path

from .views import profile_view, signup_view, verify_signup_otp_view

urlpatterns = [
    path("signup/", signup_view, name="signup"),
    path("signup/verify/", verify_signup_otp_view, name="verify_signup_otp"),
    path("profile/", profile_view, name="profile"),
]
