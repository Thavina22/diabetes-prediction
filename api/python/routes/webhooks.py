"""Clerk -> Neon user-sync webhook (Task 3.1).

Verifies the Svix signature that Clerk attaches to every webhook delivery,
then upserts or deletes the local `users` row.
"""

import logging

from fastapi import APIRouter, HTTPException, Request

from config import get_settings
from db.repositories.users import delete_user_by_clerk_id, sync_user_from_clerk

logger = logging.getLogger(__name__)
router = APIRouter()


def _verify(payload: bytes, headers) -> dict:
    """Verify the Svix signature and return the decoded event."""
    settings = get_settings()
    if not settings.CLERK_WEBHOOK_SECRET:
        raise HTTPException(status_code=503, detail="Webhook secret not configured")

    try:
        from svix.webhooks import Webhook, WebhookVerificationError
    except ImportError as exc:  # pragma: no cover - dependency guard
        raise HTTPException(status_code=500, detail="svix library not installed") from exc

    wh = Webhook(settings.CLERK_WEBHOOK_SECRET)
    try:
        return wh.verify(
            payload,
            {
                "svix-id": headers.get("svix-id"),
                "svix-timestamp": headers.get("svix-timestamp"),
                "svix-signature": headers.get("svix-signature"),
            },
        )
    except WebhookVerificationError as exc:
        raise HTTPException(status_code=400, detail="Invalid webhook signature") from exc


@router.post("/webhooks/clerk")
async def clerk_webhook(request: Request):
    payload = await request.body()
    event = _verify(payload, request.headers)

    event_type = event.get("type", "")
    data = event.get("data", {}) or {}

    primary_email = None
    emails = data.get("email_addresses") or []
    primary_id = data.get("primary_email_address_id")
    for entry in emails:
        if entry.get("id") == primary_id:
            primary_email = entry.get("email_address")
            break
    if primary_email is None and emails:
        primary_email = emails[0].get("email_address")

    full_name = " ".join(
        part for part in [data.get("first_name"), data.get("last_name")] if part
    ) or None

    if event_type in ("user.created", "user.updated"):
        user_id = await sync_user_from_clerk(
            clerk_id=data.get("id", ""),
            email=primary_email,
            full_name=full_name,
            avatar_url=data.get("image_url"),
        )
        return {"status": "synced" if user_id else "ignored", "clerk_id": data.get("id")}

    if event_type == "user.deleted":
        await delete_user_by_clerk_id(data.get("id", ""))
        return {"status": "deleted", "clerk_id": data.get("id")}

    logger.info("Unhandled Clerk webhook event: %s", event_type)
    return {"status": "ignored", "type": event_type}
