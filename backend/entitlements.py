"""Small entitlement and quota helpers for billable AI generation entrypoints."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Dict, Optional

from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.database import AccountEntitlement, UsageLedgerEntry
from backend.settings import get_settings

from . import schemas


def _utc_now() -> datetime:
    """Return a timezone-aware UTC timestamp."""

    return datetime.now(timezone.utc)


def _coerce_datetime_to_utc(value: Optional[datetime]) -> Optional[datetime]:
    """Treat SQLite naive datetimes as UTC for safe entitlement comparisons."""

    if value is None:
        return None
    if value.tzinfo is None or value.tzinfo.utcoffset(value) is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def get_entitlement(
    db: Session,
    user_id: int,
) -> Optional[AccountEntitlement]:
    """Return the persisted entitlement row for a user, if present."""

    return (
        db.query(AccountEntitlement)
        .filter(AccountEntitlement.user_id == user_id)
        .first()
    )


def provision_trial_entitlement(
    db: Session,
    user_id: int,
) -> AccountEntitlement:
    """Create a default bounded-trial entitlement when one does not exist."""

    existing = get_entitlement(db, user_id)
    if existing is not None:
        return existing

    settings = get_settings()
    now = _utc_now()
    entitlement = AccountEntitlement(
        user_id=user_id,
        access_state=schemas.EntitlementAccessState.TRIAL.value,
        story_credits_total=settings.trial_story_credits,
        image_credits_total=settings.trial_image_credits,
        trial_started_at=now,
        trial_expires_at=now + timedelta(days=settings.trial_access_days),
    )
    db.add(entitlement)
    db.flush()
    return entitlement


def _sum_credits_by_status(
    db: Session,
    entitlement_id: int,
    credit_bucket: schemas.CreditBucket,
) -> Dict[str, int]:
    """Summarize ledger credits by status for a single entitlement bucket."""

    rows = (
        db.query(
            UsageLedgerEntry.status,
            func.coalesce(func.sum(UsageLedgerEntry.credits), 0),
        )
        .filter(
            UsageLedgerEntry.entitlement_id == entitlement_id,
            UsageLedgerEntry.credit_bucket == credit_bucket.value,
        )
        .group_by(UsageLedgerEntry.status)
        .all()
    )
    totals = {"reserved": 0, "consumed": 0, "released": 0}
    for entry_status, credits in rows:
        totals[str(entry_status)] = int(credits or 0)
    return totals


def _build_balance(
    total: int,
    status_totals: Dict[str, int],
) -> schemas.EntitlementBalance:
    """Translate ledger totals into a public balance summary."""

    reserved = int(status_totals.get("reserved", 0))
    consumed = int(status_totals.get("consumed", 0))
    remaining = max(0, int(total) - reserved - consumed)
    return schemas.EntitlementBalance(
        total=int(total),
        reserved=reserved,
        consumed=consumed,
        remaining=remaining,
    )


def resolve_effective_state(
    db: Session,
    user_id: int,
    *,
    provision_if_missing: bool = False,
) -> schemas.EntitlementStatus:
    """Resolve the current entitlement state and remaining balances."""

    entitlement = get_entitlement(db, user_id)
    if entitlement is None and provision_if_missing:
        entitlement = provision_trial_entitlement(db, user_id)
        db.commit()
        db.refresh(entitlement)

    if entitlement is None:
        empty = schemas.EntitlementBalance()
        return schemas.EntitlementStatus(
            access_state=schemas.EntitlementAccessState.SUSPENDED,
            active_entitlement=False,
            story_credits=empty,
            image_credits=empty,
        )

    story_balance = _build_balance(
        entitlement.story_credits_total,
        _sum_credits_by_status(db, entitlement.id, schemas.CreditBucket.STORY),
    )
    image_balance = _build_balance(
        entitlement.image_credits_total,
        _sum_credits_by_status(db, entitlement.id, schemas.CreditBucket.IMAGE),
    )

    now = _utc_now()
    effective_state = schemas.EntitlementAccessState(entitlement.access_state)
    trial_expires_at = _coerce_datetime_to_utc(entitlement.trial_expires_at)
    renews_at = _coerce_datetime_to_utc(entitlement.renews_at)
    trial_expired = bool(
        trial_expires_at and trial_expires_at <= now
    )
    renewal_elapsed = bool(
        renews_at and renews_at <= now
    )

    if effective_state == schemas.EntitlementAccessState.SUSPENDED:
        can_generate_stories = False
        can_generate_images = False
    else:
        if effective_state == schemas.EntitlementAccessState.TRIAL and trial_expired:
            effective_state = schemas.EntitlementAccessState.GRACE
        elif (
            effective_state == schemas.EntitlementAccessState.PAID_ACTIVE
            and renewal_elapsed
            and story_balance.remaining <= 0
            and image_balance.remaining <= 0
        ):
            effective_state = schemas.EntitlementAccessState.GRACE

        generating_enabled = effective_state in {
            schemas.EntitlementAccessState.TRIAL,
            schemas.EntitlementAccessState.PAID_ACTIVE,
        }
        can_generate_stories = generating_enabled and story_balance.remaining > 0
        can_generate_images = generating_enabled and image_balance.remaining > 0

        if not can_generate_stories and not can_generate_images:
            effective_state = schemas.EntitlementAccessState.GRACE

    return schemas.EntitlementStatus(
        access_state=effective_state,
        active_entitlement=True,
        renews_at=renews_at,
        trial_expires_at=trial_expires_at,
        can_generate_stories=can_generate_stories,
        can_generate_images=can_generate_images,
        story_credits=story_balance,
        image_credits=image_balance,
    )


def _quota_error_detail(
    resolved: schemas.EntitlementStatus,
    action_type: schemas.BillableAction,
    credit_bucket: schemas.CreditBucket,
) -> Dict[str, object]:
    """Build a structured quota error payload for future frontend handling."""

    balance = (
        resolved.story_credits
        if credit_bucket == schemas.CreditBucket.STORY
        else resolved.image_credits
    )
    return {
        "code": "quota_exhausted",
        "message": "Generation is not available for this action.",
        "access_state": resolved.access_state.value,
        "action_type": action_type.value,
        "credit_bucket": credit_bucket.value,
        "remaining": balance.remaining,
        "can_generate_stories": resolved.can_generate_stories,
        "can_generate_images": resolved.can_generate_images,
    }


def reserve_credits(
    db: Session,
    user_id: int,
    action_type: schemas.BillableAction,
    credit_bucket: schemas.CreditBucket,
    *,
    credits: int = 1,
) -> UsageLedgerEntry:
    """Reserve credits before a provider call starts or raise a quota error."""

    entitlement = provision_trial_entitlement(db, user_id)
    resolved = resolve_effective_state(db, user_id)
    is_allowed = (
        resolved.can_generate_stories
        if credit_bucket == schemas.CreditBucket.STORY
        else resolved.can_generate_images
    )
    balance = (
        resolved.story_credits
        if credit_bucket == schemas.CreditBucket.STORY
        else resolved.image_credits
    )
    if not is_allowed or balance.remaining < credits:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail=_quota_error_detail(resolved, action_type, credit_bucket),
        )

    reservation = UsageLedgerEntry(
        user_id=user_id,
        entitlement_id=entitlement.id,
        action_type=action_type.value,
        credit_bucket=credit_bucket.value,
        credits=credits,
        status="reserved",
    )
    db.add(reservation)
    db.commit()
    db.refresh(reservation)
    return reservation


def consume_credits(
    db: Session,
    reservation_id: int,
) -> Optional[UsageLedgerEntry]:
    """Finalize a prior reservation as consumed after spend has started."""

    reservation = (
        db.query(UsageLedgerEntry)
        .filter(UsageLedgerEntry.id == reservation_id)
        .first()
    )
    if reservation is None:
        return None
    if reservation.status != "reserved":
        return reservation

    reservation.status = "consumed"
    reservation.finalized_at = _utc_now()
    reservation.release_reason = None
    db.add(reservation)
    db.commit()
    db.refresh(reservation)
    return reservation


def release_credits(
    db: Session,
    reservation_id: int,
    *,
    reason: str,
) -> Optional[UsageLedgerEntry]:
    """Release a reservation when the request exits before provider spend."""

    reservation = (
        db.query(UsageLedgerEntry)
        .filter(UsageLedgerEntry.id == reservation_id)
        .first()
    )
    if reservation is None:
        return None
    if reservation.status != "reserved":
        return reservation

    reservation.status = "released"
    reservation.finalized_at = _utc_now()
    reservation.release_reason = reason
    db.add(reservation)
    db.commit()
    db.refresh(reservation)
    return reservation