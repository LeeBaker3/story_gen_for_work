"""Billing endpoints for authenticated Stripe Checkout, Portal, and webhooks."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from backend import auth, billing, database, entitlements, schemas
from backend.database import get_db


billing_router = APIRouter()


@billing_router.post(
    "/billing/checkout-session",
    response_model=schemas.BillingSessionResponse,
)
async def create_checkout_session(
    db: Session = Depends(get_db),
    current_user: database.User = Depends(auth.get_current_active_user),
):
    """Create a Stripe Checkout session for the authenticated user."""

    try:
        return schemas.BillingSessionResponse(
            url=billing.create_checkout_session(db, current_user)
        )
    except billing.BillingConfigurationError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    except billing.BillingRequestError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@billing_router.post(
    "/billing/portal-session",
    response_model=schemas.BillingSessionResponse,
)
async def create_portal_session(
    db: Session = Depends(get_db),
    current_user: database.User = Depends(auth.get_current_active_user),
):
    """Create a Stripe Customer Portal session for the authenticated user."""

    entitlement = entitlements.get_entitlement(db, current_user.id)
    if entitlement is None or not entitlement.stripe_customer_id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="No Stripe customer is linked to this account.",
        )

    try:
        return schemas.BillingSessionResponse(
            url=billing.create_portal_session(entitlement.stripe_customer_id)
        )
    except billing.BillingConfigurationError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    except billing.BillingRequestError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@billing_router.post(
    "/billing/stripe/webhook",
    response_model=schemas.BillingWebhookResponse,
)
async def stripe_webhook(
    request: Request,
    db: Session = Depends(get_db),
):
    """Verify and apply a Stripe webhook event without requiring auth."""

    payload = await request.body()
    signature_header = request.headers.get("stripe-signature", "")

    try:
        duplicate = billing.process_webhook_event(db, payload, signature_header)
    except billing.BillingConfigurationError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    except billing.BillingWebhookError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    return schemas.BillingWebhookResponse(received=True, duplicate=duplicate)