import hashlib
import hmac

import requests
from django.conf import settings


RAZORPAY_API_BASE = "https://api.razorpay.com/v1"


def razorpay_enabled():
    return bool(settings.RAZORPAY_KEY_ID and settings.RAZORPAY_KEY_SECRET)


def create_subscription(*, plan_id, customer_notify, total_count, notes):
    response = requests.post(
        f"{RAZORPAY_API_BASE}/subscriptions",
        auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET),
        json={
            "plan_id": plan_id,
            "customer_notify": customer_notify,
            "total_count": total_count,
            "quantity": 1,
            "notes": notes,
        },
        timeout=20,
    )
    response.raise_for_status()
    return response.json()


def fetch_subscription(subscription_id):
    response = requests.get(
        f"{RAZORPAY_API_BASE}/subscriptions/{subscription_id}",
        auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET),
        timeout=20,
    )
    response.raise_for_status()
    return response.json()


def verify_checkout_signature(*, payment_id, subscription_id, signature):
    payload = f"{payment_id}|{subscription_id}".encode("utf-8")
    generated = hmac.new(
        settings.RAZORPAY_KEY_SECRET.encode("utf-8"),
        payload,
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(generated, signature)


def verify_webhook_signature(*, body, signature):
    generated = hmac.new(
        settings.RAZORPAY_WEBHOOK_SECRET.encode("utf-8"),
        body,
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(generated, signature)
