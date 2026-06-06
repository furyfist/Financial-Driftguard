"""Approval queue routes — CRUD + Slack/Telegram webhook handlers."""

import hashlib
import hmac
import json
import logging
import os
from datetime import datetime, timezone

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlmodel import Session, select

from driftguard.api.auth import verify_api_key
from driftguard.store.database import ApprovalQueue, get_session

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/approvals", tags=["approvals"])
webhook_router = APIRouter(prefix="/webhooks", tags=["webhooks"])


# ── CRUD ─────────────────────────────────────────────────────────────────────

@router.get("")
def list_approvals(
    status: str | None = None,
    model_id: str | None = None,
    session: Session = Depends(get_session),
    _: str = Depends(verify_api_key),
):
    stmt = select(ApprovalQueue).order_by(ApprovalQueue.created_at.desc())
    if status:
        stmt = stmt.where(ApprovalQueue.status == status)
    if model_id:
        stmt = stmt.where(ApprovalQueue.model_id == model_id)
    rows = session.exec(stmt).all()
    return [_serialize(r) for r in rows]


@router.get("/{approval_id}")
def get_approval(
    approval_id: int,
    session: Session = Depends(get_session),
    _: str = Depends(verify_api_key),
):
    row = session.get(ApprovalQueue, approval_id)
    if not row:
        raise HTTPException(status_code=404, detail="Approval not found")
    return _serialize(row)


@router.post("/{approval_id}/approve")
def approve_action(
    approval_id: int,
    session: Session = Depends(get_session),
    _: str = Depends(verify_api_key),
):
    row = session.get(ApprovalQueue, approval_id)
    if not row:
        raise HTTPException(status_code=404, detail="Approval not found")
    row.status = "approved"
    row.responded_at = datetime.now(timezone.utc)
    row.responded_by = "dashboard"
    session.add(row)
    session.commit()
    session.refresh(row)
    return _serialize(row)


@router.post("/{approval_id}/reject")
def reject_action(
    approval_id: int,
    session: Session = Depends(get_session),
    _: str = Depends(verify_api_key),
):
    row = session.get(ApprovalQueue, approval_id)
    if not row:
        raise HTTPException(status_code=404, detail="Approval not found")
    row.status = "rejected"
    row.responded_at = datetime.now(timezone.utc)
    row.responded_by = "dashboard"
    session.add(row)
    session.commit()
    session.refresh(row)
    return _serialize(row)


# ── Slack interactive webhook ─────────────────────────────────────────────────

@webhook_router.post("/slack/interact")
async def slack_interact(request: Request, session: Session = Depends(get_session)):
    """Receive Slack interactive button payload and update ApprovalQueue."""
    body_bytes = await request.body()

    signing_secret = os.getenv("SLACK_SIGNING_SECRET", "")
    if signing_secret:
        ts = request.headers.get("x-slack-request-timestamp", "")
        sig_header = request.headers.get("x-slack-signature", "")
        base = f"v0:{ts}:{body_bytes.decode()}"
        expected = "v0=" + hmac.new(
            signing_secret.encode(), base.encode(), hashlib.sha256
        ).hexdigest()
        if not hmac.compare_digest(expected, sig_header):
            raise HTTPException(status_code=403, detail="Invalid Slack signature")

    from urllib.parse import parse_qs
    parsed = parse_qs(body_bytes.decode())
    payload_raw = parsed.get("payload", ["{}"])[0]
    payload = json.loads(payload_raw)

    actions = payload.get("actions", [])
    response_url = payload.get("response_url", "")

    for action in actions:
        action_id = action.get("action_id", "")
        approval_id_str = action.get("value", "")
        try:
            approval_id = int(approval_id_str)
        except (ValueError, TypeError):
            continue

        row = session.get(ApprovalQueue, approval_id)
        if not row:
            continue

        user = payload.get("user", {}).get("name", "slack_user")
        if action_id == "approve_action":
            row.status = "approved"
        elif action_id == "reject_action":
            row.status = "rejected"
        else:
            continue

        row.responded_at = datetime.now(timezone.utc)
        row.responded_by = user
        session.add(row)
        session.commit()

        if response_url:
            _update_slack_message(response_url, row)

    return {"ok": True}


def _update_slack_message(response_url: str, row: ApprovalQueue) -> None:
    """Update the original Slack message with the decision result."""
    emoji = "✅" if row.status == "approved" else "❌"
    text = f"{emoji} *{row.status.upper()}* by {row.responded_by} — {row.action} for {row.model_id}"
    try:
        with httpx.Client(timeout=5.0) as client:
            client.post(response_url, json={"text": text, "replace_original": True})
    except Exception as exc:
        logger.warning("Slack message update failed: %s", exc)


# ── Telegram webhook ──────────────────────────────────────────────────────────

@webhook_router.post("/telegram")
async def telegram_interact(request: Request, session: Session = Depends(get_session)):
    """Receive Telegram callback query and update ApprovalQueue."""
    payload = await request.json()
    callback = payload.get("callback_query", {})
    data = callback.get("data", "")
    callback_query_id = callback.get("id", "")
    user = callback.get("from", {}).get("username", "telegram_user")

    if "_" not in data:
        return {"ok": True}

    parts = data.rsplit("_", 1)
    if len(parts) != 2:
        return {"ok": True}

    action_type, approval_id_str = parts
    try:
        approval_id = int(approval_id_str)
    except ValueError:
        return {"ok": True}

    row = session.get(ApprovalQueue, approval_id)
    if row:
        row.status = "approved" if action_type == "approve" else "rejected"
        row.responded_at = datetime.now(timezone.utc)
        row.responded_by = user
        session.add(row)
        session.commit()

    _answer_telegram_callback(callback_query_id)
    return {"ok": True}


def _answer_telegram_callback(callback_query_id: str) -> None:
    """Answer Telegram callback to remove the loading spinner."""
    token = os.getenv("TELEGRAM_BOT_TOKEN", "")
    if not token or not callback_query_id:
        return
    try:
        with httpx.Client(timeout=5.0) as client:
            client.post(
                f"https://api.telegram.org/bot{token}/answerCallbackQuery",
                json={"callback_query_id": callback_query_id},
            )
    except Exception as exc:
        logger.warning("Telegram answerCallbackQuery failed: %s", exc)


def _serialize(row: ApprovalQueue) -> dict:
    return {
        "id": row.id,
        "model_id": row.model_id,
        "action": row.action,
        "recommendation": row.recommendation,
        "regime": row.regime,
        "confidence": row.confidence,
        "status": row.status,
        "responded_by": row.responded_by,
        "responded_at": row.responded_at.isoformat() if row.responded_at else None,
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }
