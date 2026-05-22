from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select, desc
from pydantic import BaseModel as PydanticBase

from ...scheduler.jobs import register_notifier
from ...notifications.discord import DiscordNotifier
from ...notifications.slack import SlackNotifier
from ...store.database import AlertRecord, WebhookConfigRecord, engine, get_session
from ..schemas import AlertOut, AckRequest

router = APIRouter(prefix="/alerts", tags=["alerts"])

class WebhookConfig(PydanticBase):
    platform:           str          # "discord" or "slack"
    webhook_url:        str
    model_id:           str | None = None
    severity_threshold: str = "high"

@router.get("/", response_model=list[AlertOut])
def list_alerts(
    unacknowledged_only: bool = False,
    session: Session = Depends(get_session),
):
    query = select(AlertRecord).order_by(desc(AlertRecord.created_at))
    if unacknowledged_only:
        query = query.where(AlertRecord.acknowledged == False)
    return session.exec(query).all()


@router.get("/{model_id}", response_model=list[AlertOut])
def alerts_for_model(model_id: str, session: Session = Depends(get_session)):
    return session.exec(
        select(AlertRecord)
        .where(AlertRecord.model_id == model_id)
        .order_by(desc(AlertRecord.created_at))
    ).all()


@router.post("/acknowledge")
def acknowledge_alert(payload: AckRequest, session: Session = Depends(get_session)):
    alert = session.get(AlertRecord, payload.alert_id)
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    alert.acknowledged = True
    session.add(alert)
    session.commit()
    return {"acknowledged": payload.alert_id}

@router.post("/webhooks/configure")
def configure_webhook(payload: WebhookConfig):
    """
    Register a webhook notifier at runtime.
    Persists for the lifetime of the server process.
    """
    if payload.platform == "discord":
        notifier = DiscordNotifier(
            webhook_url=payload.webhook_url,
            severity_threshold=payload.severity_threshold,
        )
    elif payload.platform == "slack":
        notifier = SlackNotifier(
            webhook_url=payload.webhook_url,
            severity_threshold=payload.severity_threshold,
        )
    else:
        from fastapi import HTTPException
        raise HTTPException(
            status_code=400,
            detail=f"Unknown platform '{payload.platform}'. Use 'discord' or 'slack'."
        )

    register_notifier(notifier, model_id=payload.model_id)
    with Session(engine) as s:
        s.add(WebhookConfigRecord(
            platform=payload.platform,
            webhook_url=payload.webhook_url,
            model_id=payload.model_id,
            severity_threshold=payload.severity_threshold,
        ))
        s.commit()
    return {
        "configured": payload.platform,
        "model_id":   payload.model_id or "all models",
        "threshold":  payload.severity_threshold,
    }