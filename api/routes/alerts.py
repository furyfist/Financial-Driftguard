from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select, desc

from ...store.database import AlertRecord, get_session
from ..schemas import AlertOut, AckRequest

router = APIRouter(prefix="/alerts", tags=["alerts"])


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