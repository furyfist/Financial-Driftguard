import json
import pandas as pd
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Any
from sqlmodel import Session, select, desc

from ...store.database import DriftRun, AlertRecord, ModelRecord, get_session
from ..schemas import DriftRunOut
from ...scheduler.jobs import run_drift_check, register_baseline
from ...core.snapshot import DataSnapshot

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

class RunCheckRequest(BaseModel):
    records: list[dict[str, Any]]   # list of row dicts — same format as df.to_dict("records")
    set_as_baseline: bool = False


@router.post("/{model_id}/run")
def trigger_drift_check(
    model_id: str,
    payload: RunCheckRequest,
    session: Session = Depends(get_session),
):
    model = session.exec(
        select(ModelRecord).where(ModelRecord.model_id == model_id)
    ).first()
    if not model:
        raise HTTPException(status_code=404, detail=f"Model '{model_id}' not found")

    df = pd.DataFrame(payload.records)
    snapshot = DataSnapshot.from_dataframe(df, label="live")

    if payload.set_as_baseline:
        register_baseline(model_id, snapshot)
        return {"message": f"Baseline set for '{model_id}'", "rows": len(df)}

    result = run_drift_check(model_id, snapshot)
    if result is None:
        raise HTTPException(
            status_code=400,
            detail="No baseline registered. POST with set_as_baseline=true first."
        )

    return {
        "model_id": model_id,
        "overall_severity": result.overall_severity.value,
        "drift_score": result.drift_score,
        "regime": result.regime,
        "notes": result.notes,
        "drifted_features": [
            {"feature": f.feature_name, "detector": f.detector, "score": f.score}
            for f in result.drifted_features
        ],
    }