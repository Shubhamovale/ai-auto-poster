from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import include, path

from dashboard.views import LandingPageView


urlpatterns = [
    path("", LandingPageView.as_view(), name="landing"),
    path("admin/", admin.site.urls),
    path("accounts/login/", auth_views.LoginView.as_view(template_name="auth/login.html"), name="login"),
    path("accounts/logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("accounts/", include("accounts.urls")),
    path("app/", include("dashboard.urls")),
]
