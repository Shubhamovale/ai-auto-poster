from django.contrib.auth.models import User
from django.core import mail
from django.test import TestCase, override_settings
from django.urls import reverse


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class SignupOTPTests(TestCase):
    def test_signup_sends_otp_and_defers_user_creation(self):
        response = self.client.post(
            reverse("signup"),
            {
                "username": "otp-user",
                "email": "otp@example.com",
                "company_name": "Acme",
                "password1": "VeryStrongPass123",
                "password2": "VeryStrongPass123",
            },
        )

        self.assertRedirects(response, reverse("verify_signup_otp"))
        self.assertFalse(User.objects.filter(username="otp-user").exists())
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("verification code", mail.outbox[0].subject.lower())
        session = self.client.session
        self.assertEqual(session["signup_otp_state"]["email"], "otp@example.com")

    def test_correct_otp_creates_user_and_logs_in(self):
        self.client.post(
            reverse("signup"),
            {
                "username": "otp-user",
                "email": "otp@example.com",
                "company_name": "Acme",
                "password1": "VeryStrongPass123",
                "password2": "VeryStrongPass123",
            },
        )
        otp = self.client.session["signup_otp_state"]["otp"]

        response = self.client.post(reverse("verify_signup_otp"), {"otp": otp})

        self.assertRedirects(response, reverse("dashboard:home"))
        user = User.objects.get(username="otp-user")
        self.assertEqual(user.email, "otp@example.com")
        self.assertEqual(user.profile.company_name, "Acme")
        self.assertEqual(int(self.client.session["_auth_user_id"]), user.id)

    def test_invalid_otp_does_not_create_user(self):
        self.client.post(
            reverse("signup"),
            {
                "username": "otp-user",
                "email": "otp@example.com",
                "company_name": "Acme",
                "password1": "VeryStrongPass123",
                "password2": "VeryStrongPass123",
            },
        )

        response = self.client.post(reverse("verify_signup_otp"), {"otp": "000000"})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "does not match")
        self.assertFalse(User.objects.filter(username="otp-user").exists())

    def test_resend_replaces_otp_and_sends_new_email(self):
        self.client.post(
            reverse("signup"),
            {
                "username": "otp-user",
                "email": "otp@example.com",
                "company_name": "Acme",
                "password1": "VeryStrongPass123",
                "password2": "VeryStrongPass123",
            },
        )
        original_otp = self.client.session["signup_otp_state"]["otp"]

        response = self.client.post(reverse("verify_signup_otp"), {"action": "resend"})

        self.assertRedirects(response, reverse("verify_signup_otp"))
        self.assertEqual(len(mail.outbox), 2)
        refreshed_otp = self.client.session["signup_otp_state"]["otp"]
        self.assertNotEqual(original_otp, refreshed_otp)

    def test_signup_rejects_duplicate_email(self):
        User.objects.create_user(
            username="existing-user",
            email="otp@example.com",
            password="VeryStrongPass123",
        )

        response = self.client.post(
            reverse("signup"),
            {
                "username": "otp-user",
                "email": "otp@example.com",
                "company_name": "Acme",
                "password1": "VeryStrongPass123",
                "password2": "VeryStrongPass123",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "An account with this email already exists.")
        self.assertFalse("signup_otp_state" in self.client.session)


class EmailLoginTests(TestCase):
    def setUp(self):
        self.password = "VeryStrongPass123"
        self.user = User.objects.create_user(
            username="shubham",
            email="shubham12@gmail.com",
            password=self.password,
        )

    def test_login_with_username_still_works(self):
        response = self.client.post(
            reverse("login"),
            {"username": "shubham", "password": self.password},
        )

        self.assertRedirects(response, reverse("dashboard:home"))
        self.assertEqual(int(self.client.session["_auth_user_id"]), self.user.id)

    def test_login_with_registered_email_works(self):
        response = self.client.post(
            reverse("login"),
            {"username": "shubham12@gmail.com", "password": self.password},
        )

        self.assertRedirects(response, reverse("dashboard:home"))
        self.assertEqual(int(self.client.session["_auth_user_id"]), self.user.id)

    @override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
    def test_password_reset_sends_email_for_registered_user(self):
        response = self.client.post(
            reverse("password_reset"),
            {"email": "shubham12@gmail.com"},
        )

        self.assertRedirects(response, reverse("password_reset_done"))
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("reset", mail.outbox[0].subject.lower())
        self.assertIn("shubham12@gmail.com", mail.outbox[0].to)

    def test_login_page_contains_forgot_password_link(self):
        response = self.client.get(reverse("login"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, reverse("password_reset"))
