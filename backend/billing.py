"""Stripe billing helpers for checkout, portal, and webhook sync."""

from __future__ import annotations

import hashlib
import hmac
import json
import time
from datetime import datetime, timezone
from typing import Any, Optional

import requests
from sqlalchemy.orm import Session

from backend import entitlements, schemas
from backend.database import AccountEntitlement, ProcessedStripeEvent, User
from backend.settings import get_settings


class BillingConfigurationError(RuntimeError):
    """Raised when required billing configuration is missing."""


class BillingRequestError(RuntimeError):
    """Raised when Stripe rejects a checkout or portal request."""


class BillingWebhookError(RuntimeError):
    """Raised when a webhook cannot be verified or applied."""


def _utc_now() -> datetime:
    """Return a timezone-aware UTC timestamp."""

    return datetime.now(timezone.utc)


def _coerce_datetime(value: Optional[datetime]) -> Optional[datetime]:
    """Treat naive datetimes as UTC for SQLite compatibility."""

    if value is None:
        return None
    if value.tzinfo is None or value.tzinfo.utcoffset(value) is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _timestamp_to_datetime(value: Any) -> Optional[datetime]:
    """Convert a Stripe unix timestamp into an aware UTC datetime."""

    if value in (None, ""):
        return None
    return datetime.fromtimestamp(int(value), tz=timezone.utc)


def _require_api_settings() -> Any:
    """Return billing settings or raise when Stripe API config is incomplete."""

    settings = get_settings()
    required = {
        "STRIPE_SECRET_KEY": settings.stripe_secret_key,
        "STRIPE_MONTHLY_PRICE_ID": settings.stripe_monthly_price_id,
        "STRIPE_CHECKOUT_SUCCESS_URL": settings.stripe_checkout_success_url,
        "STRIPE_CHECKOUT_CANCEL_URL": settings.stripe_checkout_cancel_url,
        "STRIPE_CUSTOMER_PORTAL_RETURN_URL": (
            settings.stripe_customer_portal_return_url
        ),
    }
    missing = [name for name, value in required.items() if not value]
    if missing:
        raise BillingConfigurationError(
            "Missing Stripe billing configuration: " + ", ".join(missing)
        )
    return settings


def _require_webhook_settings() -> Any:
    """Return billing settings or raise when webhook config is incomplete."""

    settings = get_settings()
    if not settings.stripe_webhook_secret:
        raise BillingConfigurationError(
            "Missing Stripe billing configuration: STRIPE_WEBHOOK_SECRET"
        )
    return settings


def _stripe_post(path: str, form_data: list[tuple[str, str]]) -> dict[str, Any]:
    """Send a form-encoded request to Stripe's API and return the JSON body."""

    settings = _require_api_settings()
    response = requests.post(
        f"https://api.stripe.com/v1{path}",
        auth=(settings.stripe_secret_key, ""),
        data=form_data,
        timeout=15,
    )
    payload = response.json()
    if response.status_code >= 400:
        error_detail = payload.get("error", {}).get("message") or "Stripe request failed."
        raise BillingRequestError(error_detail)
    return payload


def create_checkout_session(db: Session, user: User) -> str:
    """Create a Stripe Checkout session for the single monthly beta plan."""

    settings = _require_api_settings()
    if not user.email:
        raise BillingRequestError("An account email is required before starting checkout.")

    entitlement = entitlements.provision_trial_entitlement(db, user.id)
    form_data = [
        ("mode", "subscription"),
        ("success_url", settings.stripe_checkout_success_url),
        ("cancel_url", settings.stripe_checkout_cancel_url),
        ("client_reference_id", str(user.id)),
        ("metadata[user_id]", str(user.id)),
        ("metadata[user_email]", str(user.email)),
        ("metadata[username]", str(user.username)),
        ("subscription_data[metadata][user_id]", str(user.id)),
        ("subscription_data[metadata][user_email]", str(user.email)),
        ("line_items[0][price]", settings.stripe_monthly_price_id),
        ("line_items[0][quantity]", "1"),
    ]
    if entitlement.stripe_customer_id:
        form_data.append(("customer", entitlement.stripe_customer_id))
    else:
        form_data.append(("customer_email", str(user.email)))

    payload = _stripe_post("/checkout/sessions", form_data)
    url = payload.get("url")
    if not url:
        raise BillingRequestError("Stripe Checkout did not return a redirect URL.")
    return str(url)


def create_portal_session(customer_id: str) -> str:
    """Create a Stripe Customer Portal session for an existing customer."""

    settings = _require_api_settings()
    payload = _stripe_post(
        "/billing_portal/sessions",
        [
            ("customer", customer_id),
            ("return_url", settings.stripe_customer_portal_return_url),
        ],
    )
    url = payload.get("url")
    if not url:
        raise BillingRequestError("Stripe billing portal did not return a redirect URL.")
    return str(url)


def _parse_signature_header(signature_header: str) -> tuple[int, list[str]]:
    """Parse Stripe's signature header into a timestamp and v1 signatures."""

    timestamp: Optional[int] = None
    signatures: list[str] = []
    for part in (signature_header or "").split(","):
        key, _, value = part.partition("=")
        if key == "t" and value:
            timestamp = int(value)
        elif key == "v1" and value:
            signatures.append(value)
    if timestamp is None or not signatures:
        raise BillingWebhookError("Invalid Stripe signature header.")
    return timestamp, signatures


def verify_webhook_signature(payload: bytes, signature_header: str) -> dict[str, Any]:
    """Verify a Stripe webhook payload signature and decode the JSON event."""

    settings = _require_webhook_settings()
    timestamp, signatures = _parse_signature_header(signature_header)
    if abs(int(time.time()) - timestamp) > 300:
        raise BillingWebhookError("Stripe webhook signature has expired.")

    signed_payload = f"{timestamp}.{payload.decode('utf-8')}".encode("utf-8")
    expected_signature = hmac.new(
        settings.stripe_webhook_secret.encode("utf-8"),
        signed_payload,
        hashlib.sha256,
    ).hexdigest()
    if not any(hmac.compare_digest(expected_signature, value) for value in signatures):
        raise BillingWebhookError("Invalid Stripe webhook signature.")

    try:
        return json.loads(payload.decode("utf-8"))
    except json.JSONDecodeError as exc:
        raise BillingWebhookError("Stripe webhook payload was not valid JSON.") from exc


def _metadata_user_id(payload: dict[str, Any]) -> Optional[int]:
    """Extract a user id from common Stripe metadata locations."""

    metadata = payload.get("metadata") or {}
    user_id = metadata.get("user_id") or payload.get("client_reference_id")
    if user_id is None:
        subscription_details = payload.get("subscription_details") or {}
        user_id = (subscription_details.get("metadata") or {}).get("user_id")
    if user_id is None:
        parent = payload.get("parent") or {}
        subscription_details = parent.get("subscription_details") or {}
        user_id = (subscription_details.get("metadata") or {}).get("user_id")
    if user_id in (None, ""):
        return None
    return int(user_id)


def _resolve_entitlement(
    db: Session,
    *,
    customer_id: Optional[str],
    subscription_id: Optional[str],
    fallback_user_id: Optional[int],
) -> Optional[AccountEntitlement]:
    """Locate the entitlement Stripe billing events should mutate."""

    entitlement: Optional[AccountEntitlement] = None
    if subscription_id:
        entitlement = (
            db.query(AccountEntitlement)
            .filter(AccountEntitlement.stripe_subscription_id == subscription_id)
            .first()
        )
    if entitlement is None and customer_id:
        entitlement = (
            db.query(AccountEntitlement)
            .filter(AccountEntitlement.stripe_customer_id == customer_id)
            .first()
        )
    if entitlement is None and fallback_user_id is not None:
        entitlement = entitlements.provision_trial_entitlement(db, fallback_user_id)
    return entitlement


def _invoice_period(invoice: dict[str, Any]) -> tuple[Optional[datetime], Optional[datetime]]:
    """Extract the current invoice period bounds from a Stripe invoice payload."""

    period_start = _timestamp_to_datetime(invoice.get("period_start"))
    period_end = _timestamp_to_datetime(invoice.get("period_end"))
    if period_start is not None and period_end is not None:
        return period_start, period_end

    lines = ((invoice.get("lines") or {}).get("data") or [])
    if lines:
        line_period = (lines[0].get("period") or {})
        period_start = _timestamp_to_datetime(line_period.get("start"))
        period_end = _timestamp_to_datetime(line_period.get("end"))
    return period_start, period_end


def _subscription_period(subscription: dict[str, Any]) -> tuple[Optional[datetime], Optional[datetime]]:
    """Extract current billing period bounds from a Stripe subscription payload."""

    return (
        _timestamp_to_datetime(subscription.get("current_period_start")),
        _timestamp_to_datetime(subscription.get("current_period_end")),
    )


def _apply_checkout_session_completed(db: Session, payload: dict[str, Any]) -> None:
    """Bind Stripe customer and subscription ids after successful checkout."""

    entitlement = _resolve_entitlement(
        db,
        customer_id=payload.get("customer"),
        subscription_id=payload.get("subscription"),
        fallback_user_id=_metadata_user_id(payload),
    )
    if entitlement is None:
        raise BillingWebhookError("Could not resolve entitlement for checkout session.")

    entitlement.stripe_customer_id = payload.get("customer")
    entitlement.stripe_subscription_id = payload.get("subscription")
    db.add(entitlement)


def _apply_invoice_paid(db: Session, payload: dict[str, Any]) -> None:
    """Promote the entitlement into the current paid billing period."""

    settings = get_settings()
    entitlement = _resolve_entitlement(
        db,
        customer_id=payload.get("customer"),
        subscription_id=payload.get("subscription"),
        fallback_user_id=_metadata_user_id(payload),
    )
    if entitlement is None:
        raise BillingWebhookError("Could not resolve entitlement for paid invoice.")

    period_start, period_end = _invoice_period(payload)
    entitlement.stripe_customer_id = payload.get("customer") or entitlement.stripe_customer_id
    entitlement.stripe_subscription_id = (
        payload.get("subscription") or entitlement.stripe_subscription_id
    )
    entitlement.access_state = schemas.EntitlementAccessState.PAID_ACTIVE.value
    entitlement.story_credits_total = settings.stripe_monthly_story_credits
    entitlement.image_credits_total = settings.stripe_monthly_image_credits
    entitlement.current_period_started_at = period_start
    entitlement.renews_at = period_end
    entitlement.cancel_at_period_end = False
    db.add(entitlement)


def _apply_invoice_payment_failed(db: Session, payload: dict[str, Any]) -> None:
    """Move a paid entitlement into grace after a failed invoice."""

    entitlement = _resolve_entitlement(
        db,
        customer_id=payload.get("customer"),
        subscription_id=payload.get("subscription"),
        fallback_user_id=_metadata_user_id(payload),
    )
    if entitlement is None:
        raise BillingWebhookError(
            "Could not resolve entitlement for failed invoice."
        )

    entitlement.access_state = schemas.EntitlementAccessState.GRACE.value
    db.add(entitlement)


def _subscription_access_state(status: Optional[str]) -> str:
    """Map a Stripe subscription status into the local entitlement state."""

    if status in {"active", "trialing"}:
        return schemas.EntitlementAccessState.PAID_ACTIVE.value
    if status in {"past_due", "unpaid", "incomplete"}:
        return schemas.EntitlementAccessState.GRACE.value
    return schemas.EntitlementAccessState.SUSPENDED.value


def _apply_subscription_updated(db: Session, payload: dict[str, Any]) -> None:
    """Sync subscription state, renewal timing, and cancellation flags."""

    entitlement = _resolve_entitlement(
        db,
        customer_id=payload.get("customer"),
        subscription_id=payload.get("id"),
        fallback_user_id=_metadata_user_id(payload),
    )
    if entitlement is None:
        raise BillingWebhookError("Could not resolve entitlement for subscription update.")

    period_start, period_end = _subscription_period(payload)
    entitlement.stripe_customer_id = payload.get("customer") or entitlement.stripe_customer_id
    entitlement.stripe_subscription_id = payload.get("id") or entitlement.stripe_subscription_id
    entitlement.current_period_started_at = period_start or entitlement.current_period_started_at
    entitlement.renews_at = period_end or entitlement.renews_at
    entitlement.cancel_at_period_end = bool(payload.get("cancel_at_period_end"))
    entitlement.access_state = _subscription_access_state(payload.get("status"))
    db.add(entitlement)


def _apply_subscription_deleted(db: Session, payload: dict[str, Any]) -> None:
    """Remove active paid access after a subscription cancellation/deletion."""

    entitlement = _resolve_entitlement(
        db,
        customer_id=payload.get("customer"),
        subscription_id=payload.get("id"),
        fallback_user_id=_metadata_user_id(payload),
    )
    if entitlement is None:
        raise BillingWebhookError(
            "Could not resolve entitlement for subscription deletion."
        )

    period_start, period_end = _subscription_period(payload)
    entitlement.current_period_started_at = period_start or entitlement.current_period_started_at
    entitlement.renews_at = period_end or entitlement.renews_at
    entitlement.cancel_at_period_end = False
    entitlement.access_state = schemas.EntitlementAccessState.SUSPENDED.value
    db.add(entitlement)


def process_webhook_event(
    db: Session,
    payload: bytes,
    signature_header: str,
) -> bool:
    """Verify, apply, and idempotently record a Stripe webhook event."""

    event = verify_webhook_signature(payload, signature_header)
    event_id = str(event.get("id") or "")
    if not event_id:
        raise BillingWebhookError("Stripe webhook payload missing event id.")

    existing = (
        db.query(ProcessedStripeEvent)
        .filter(ProcessedStripeEvent.event_id == event_id)
        .first()
    )
    if existing is not None:
        return True

    event_type = str(event.get("type") or "")
    event_payload = (event.get("data") or {}).get("object") or {}

    try:
        if event_type == "checkout.session.completed":
            _apply_checkout_session_completed(db, event_payload)
        elif event_type == "invoice.paid":
            _apply_invoice_paid(db, event_payload)
        elif event_type == "invoice.payment_failed":
            _apply_invoice_payment_failed(db, event_payload)
        elif event_type == "customer.subscription.updated":
            _apply_subscription_updated(db, event_payload)
        elif event_type == "customer.subscription.deleted":
            _apply_subscription_deleted(db, event_payload)

        db.add(
            ProcessedStripeEvent(
                event_id=event_id,
                event_type=event_type or "unknown",
            )
        )
        db.commit()
    except Exception:
        db.rollback()
        raise

    return False