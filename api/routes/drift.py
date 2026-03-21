import json
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select, desc

from ...store.database import DriftRun, AlertRecord, ModelRecord, get_session
from ..schemas import DriftRunOut

router = APIRouter(prefix="/drift", tags=["drift"])


@router.get("/{model_id}/history", response_model=list[DriftRunOut])
def get_drift_history(
    model_id: str,
    limit: int = 50,
    session: Session = Depends(get_session),
):
    model = session.exec(
        select(ModelRecord).where(ModelRecord.model_id == model_id)
    ).first()
    if not model:
        raise HTTPException(status_code=404, detail=f"Model '{model_id}' not found")

    runs = session.exec(
        select(DriftRun)
        .where(DriftRun.model_id == model_id)
        .order_by(desc(DriftRun.checked_at))
        .limit(limit)
    ).all()
    return runs


@router.get("/{model_id}/latest", response_model=DriftRunOut)
def get_latest_drift(model_id: str, session: Session = Depends(get_session)):
    run = session.exec(
        select(DriftRun)
        .where(DriftRun.model_id == model_id)
        .order_by(desc(DriftRun.checked_at))
        .limit(1)
    ).first()
    if not run:
        raise HTTPException(status_code=404, detail="No drift runs found")
    return run


@router.get("/{model_id}/features/{run_id}")
def get_feature_results(
    model_id: str,
    run_id: int,
    session: Session = Depends(get_session),
):
    run = session.get(DriftRun, run_id)
    if not run or run.model_id != model_id:
        raise HTTPException(status_code=404, detail="Run not found")
    return json.loads(run.feature_results_json)