from django.urls import path

from . import views

app_name = "dashboard"

urlpatterns = [
    path("", views.home, name="home"),
    path("posts/new/", views.create_post, name="create_post"),
    path("posts/save-generated/", views.save_generated_post, name="save_generated_post"),
    path("posts/<int:post_id>/edit/", views.edit_post, name="edit_post"),
    path("posts/<int:post_id>/publish/", views.publish_now, name="publish_now"),
    path("billing/subscribe/<str:plan_code>/", views.subscribe_plan, name="subscribe_plan"),
    path("billing/razorpay/verify/", views.razorpay_verify, name="razorpay_verify"),
    path("billing/razorpay/webhook/", views.razorpay_webhook, name="razorpay_webhook"),
    path("accounts/connect/", views.connect_account, name="connect_account"),
    path("accounts/connect/facebook/", views.start_facebook_oauth, name="start_facebook_oauth"),
    path("accounts/connect/facebook/callback/", views.facebook_oauth_callback, name="facebook_oauth_callback"),
    path("accounts/connect/facebook/select-page/", views.select_facebook_page, name="select_facebook_page"),
    path("accounts/connect/linkedin/", views.start_linkedin_oauth, name="start_linkedin_oauth"),
    path("accounts/connect/linkedin/callback/", views.linkedin_oauth_callback, name="linkedin_oauth_callback"),
    path("accounts/connect/youtube/", views.start_youtube_oauth, name="start_youtube_oauth"),
    path("accounts/connect/youtube/callback/", views.youtube_oauth_callback, name="youtube_oauth_callback"),
    path("accounts/<int:account_id>/edit/", views.edit_account, name="edit_account"),
    path("accounts/<int:account_id>/disconnect/", views.disconnect_account, name="disconnect_account"),
    path("plans/<str:plan_code>/", views.change_plan, name="change_plan"),
]
