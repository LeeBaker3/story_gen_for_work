import hashlib
import hmac
import json
import time
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend import auth
from backend.database import AccountEntitlement, ProcessedStripeEvent, UsageLedgerEntry, User
from backend.settings import get_settings, reset_settings_cache


def _auth_headers_for(username: str) -> dict[str, str]:
    token = auth.create_access_token(data={"sub": username})
    return {"Authorization": f"Bearer {token}"}


def _stripe_signature(payload: bytes, secret: str) -> str:
    timestamp = int(time.time())
    signed_payload = f"{timestamp}.{payload.decode('utf-8')}".encode("utf-8")
    digest = hmac.new(
        secret.encode("utf-8"),
        signed_payload,
        hashlib.sha256,
    ).hexdigest()
    return f"t={timestamp},v1={digest}"


def _webhook_headers(payload: dict, secret: str) -> dict[str, str]:
    body = json.dumps(payload).encode("utf-8")
    return {
        "stripe-signature": _stripe_signature(body, secret),
        "content-type": "application/json",
    }


def _post_webhook(client: TestClient, payload: dict, secret: str):
    body = json.dumps(payload)
    return client.post(
        "/api/v1/billing/stripe/webhook",
        data=body,
        headers=_webhook_headers(payload, secret),
    )


def test_checkout_session_creation_returns_url_with_user_metadata(
    client: TestClient,
    db_session: Session,
    monkeypatch,
):
    monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_test_123")
    monkeypatch.setenv("STRIPE_MONTHLY_PRICE_ID", "price_monthly_beta")
    monkeypatch.setenv("STRIPE_CHECKOUT_SUCCESS_URL", "https://app.test/success")
    monkeypatch.setenv("STRIPE_CHECKOUT_CANCEL_URL", "https://app.test/cancel")
    monkeypatch.setenv("STRIPE_CUSTOMER_PORTAL_RETURN_URL", "https://app.test/account")
    reset_settings_cache()

    captured = {}

    def _fake_post(url, auth, data, timeout):
        captured["url"] = url
        captured["auth"] = auth
        captured["data"] = list(data)

        class _Response:
            status_code = 200

            @staticmethod
            def json():
                return {"url": "https://checkout.stripe.test/session_123"}

        return _Response()

    with patch("backend.billing.requests.post", side_effect=_fake_post):
        response = client.post(
            "/api/v1/billing/checkout-session",
            headers=_auth_headers_for("user@example.com"),
        )

    assert response.status_code == 200, response.text
    assert response.json()["url"] == "https://checkout.stripe.test/session_123"
    posted_data = dict(captured["data"])
    assert posted_data["metadata[user_id]"] == "2"
    assert posted_data["metadata[user_email]"] == "user@example.com"
    assert posted_data["client_reference_id"] == "2"
    assert posted_data["line_items[0][price]"] == "price_monthly_beta"


def test_portal_session_creation_returns_url_for_linked_customer(
    client: TestClient,
    db_session: Session,
    monkeypatch,
):
    monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_test_123")
    monkeypatch.setenv("STRIPE_MONTHLY_PRICE_ID", "price_monthly_beta")
    monkeypatch.setenv("STRIPE_CHECKOUT_SUCCESS_URL", "https://app.test/success")
    monkeypatch.setenv("STRIPE_CHECKOUT_CANCEL_URL", "https://app.test/cancel")
    monkeypatch.setenv("STRIPE_CUSTOMER_PORTAL_RETURN_URL", "https://app.test/account")
    reset_settings_cache()

    user = db_session.query(User).filter(User.username == "user@example.com").first()
    assert user is not None
    db_session.add(
        AccountEntitlement(
            user_id=user.id,
            access_state="trial",
            story_credits_total=3,
            image_credits_total=10,
            stripe_customer_id="cus_123",
        )
    )
    db_session.commit()

    def _fake_post(url, auth, data, timeout):
        assert dict(data)["customer"] == "cus_123"

        class _Response:
            status_code = 200

            @staticmethod
            def json():
                return {"url": "https://billing.stripe.test/portal_123"}

        return _Response()

    with patch("backend.billing.requests.post", side_effect=_fake_post):
        response = client.post(
            "/api/v1/billing/portal-session",
            headers=_auth_headers_for("user@example.com"),
        )

    assert response.status_code == 200, response.text
    assert response.json()["url"] == "https://billing.stripe.test/portal_123"


def test_invoice_paid_promotes_entitlement_and_resets_period_scoped_credits(
    client: TestClient,
    db_session: Session,
    monkeypatch,
):
    monkeypatch.setenv("STRIPE_WEBHOOK_SECRET", "whsec_test")
    monkeypatch.setenv("STRIPE_MONTHLY_STORY_CREDITS", "30")
    monkeypatch.setenv("STRIPE_MONTHLY_IMAGE_CREDITS", "100")
    reset_settings_cache()

    user = db_session.query(User).filter(User.username == "user@example.com").first()
    assert user is not None
    previous_period_start = datetime.now(timezone.utc) - timedelta(days=31)
    entitlement = AccountEntitlement(
        user_id=user.id,
        access_state="trial",
        story_credits_total=3,
        image_credits_total=10,
        stripe_customer_id="cus_paid",
        stripe_subscription_id="sub_paid",
        current_period_started_at=previous_period_start,
    )
    db_session.add(entitlement)
    db_session.commit()
    db_session.refresh(entitlement)

    db_session.add(
        UsageLedgerEntry(
            user_id=user.id,
            entitlement_id=entitlement.id,
            action_type="initial_story_generation",
            credit_bucket="story",
            credits=2,
            status="consumed",
            billing_period_start=previous_period_start,
        )
    )
    db_session.commit()

    payload = {
        "id": "evt_invoice_paid_1",
        "type": "invoice.paid",
        "data": {
            "object": {
                "id": "in_123",
                "customer": "cus_paid",
                "subscription": "sub_paid",
                "period_start": 1760000000,
                "period_end": 1762592000,
            }
        },
    }

    response = _post_webhook(client, payload, "whsec_test")
    assert response.status_code == 200, response.text

    db_session.refresh(entitlement)
    assert entitlement.access_state == "paid-active"
    assert entitlement.story_credits_total == 30
    assert entitlement.image_credits_total == 100
    assert entitlement.current_period_started_at is not None
    entitlement_response = client.get(
        "/api/v1/users/me/entitlement",
        headers=_auth_headers_for("user@example.com"),
    )
    assert entitlement_response.status_code == 200, entitlement_response.text
    body = entitlement_response.json()
    assert body["access_state"] == "paid-active"
    assert body["story_credits"]["total"] == 30
    assert body["story_credits"]["consumed"] == 0
    assert body["story_credits"]["remaining"] == 30


def test_invoice_payment_failed_moves_paid_entitlement_to_grace(
    client: TestClient,
    db_session: Session,
    monkeypatch,
):
    monkeypatch.setenv("STRIPE_WEBHOOK_SECRET", "whsec_test")
    reset_settings_cache()

    user = db_session.query(User).filter(User.username == "user@example.com").first()
    assert user is not None
    entitlement = AccountEntitlement(
        user_id=user.id,
        access_state="paid-active",
        story_credits_total=30,
        image_credits_total=100,
        stripe_customer_id="cus_fail",
        stripe_subscription_id="sub_fail",
    )
    db_session.add(entitlement)
    db_session.commit()

    payload = {
        "id": "evt_invoice_failed_1",
        "type": "invoice.payment_failed",
        "data": {
            "object": {
                "id": "in_fail",
                "customer": "cus_fail",
                "subscription": "sub_fail",
            }
        },
    }

    response = _post_webhook(client, payload, "whsec_test")
    assert response.status_code == 200, response.text
    db_session.refresh(entitlement)
    assert entitlement.access_state == "grace"


def test_duplicate_webhook_delivery_does_not_double_apply_credits(
    client: TestClient,
    db_session: Session,
    monkeypatch,
):
    monkeypatch.setenv("STRIPE_WEBHOOK_SECRET", "whsec_test")
    monkeypatch.setenv("STRIPE_MONTHLY_STORY_CREDITS", "30")
    monkeypatch.setenv("STRIPE_MONTHLY_IMAGE_CREDITS", "100")
    reset_settings_cache()

    user = db_session.query(User).filter(User.username == "user@example.com").first()
    assert user is not None
    entitlement = AccountEntitlement(
        user_id=user.id,
        access_state="grace",
        story_credits_total=0,
        image_credits_total=0,
        stripe_customer_id="cus_dup",
        stripe_subscription_id="sub_dup",
    )
    db_session.add(entitlement)
    db_session.commit()

    payload = {
        "id": "evt_invoice_paid_duplicate",
        "type": "invoice.paid",
        "data": {
            "object": {
                "id": "in_dup",
                "customer": "cus_dup",
                "subscription": "sub_dup",
                "period_start": 1760000000,
                "period_end": 1762592000,
            }
        },
    }

    first = _post_webhook(client, payload, "whsec_test")
    second = _post_webhook(client, payload, "whsec_test")

    assert first.status_code == 200, first.text
    assert second.status_code == 200, second.text
    assert second.json()["duplicate"] is True
    db_session.refresh(entitlement)
    assert entitlement.story_credits_total == 30
    assert entitlement.image_credits_total == 100
    processed = (
        db_session.query(ProcessedStripeEvent)
        .filter(ProcessedStripeEvent.event_id == "evt_invoice_paid_duplicate")
        .all()
    )
    assert len(processed) == 1