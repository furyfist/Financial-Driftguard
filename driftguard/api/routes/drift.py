import json
from contextlib import nullcontext
import pandas as pd
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Any
from sqlmodel import Session, select, desc

try:
    from opentelemetry import trace as _otel_trace
    _tracer = _otel_trace.get_tracer("finsight.api")
except ImportError:
    _tracer = None


def _drift_span(name: str):
    """Return an OTel span context manager; falls back to nullcontext if OTel is not installed."""
    if _tracer is None:
        return nullcontext()
    return _tracer.start_as_current_span(name)


def _current_trace_id() -> str | None:
    """Extract the active OTel trace ID as a 32-char hex string, or None."""
    try:
        from opentelemetry import trace as _otel
        ctx = _otel.get_current_span().get_span_context()
        if ctx.is_valid:
            return format(ctx.trace_id, "032x")
    except Exception:
        pass
    return None

from ...store.database import DriftRun, AlertRecord, ModelRecord, ModelVersion, get_session
from ..schemas import DriftRunOut, DriftForecastOut
from ...scheduler.jobs import run_drift_check, register_baseline
from ...core.snapshot import DataSnapshot
from ...store.database import MacroCache as MacroCacheModel
from ...regime.macro_signals import MacroSnapshot as _MacroSnapshot


router = APIRouter(prefix="/drift", tags=["drift"])


@router.get("/feature-meta")
def get_feature_meta():
    """Return static domain descriptions for all known features (no LLM call)."""
    try:
        from finsight.impact.feature_metadata import FEATURE_METADATA
        return FEATURE_METADATA
    except ImportError:
        return {}


@router.get("/macro/latest")
def get_latest_macro_snapshot(session: Session = Depends(get_session)):
    """Returns the most recently cached macro snapshot and regime."""
    latest = session.exec(
        select(MacroCacheModel)
        .order_by(MacroCacheModel.fetched_at.desc())
        .limit(1)
    ).first()

    if not latest:
        return {"status": "no macro data yet — check FRED_API_KEY in .env"}

    return {
        "fetched_at":        latest.fetched_at,
        "vix":               latest.vix,
        "credit_spread":     latest.credit_spread,
        "fed_funds_rate":    latest.fed_funds_rate,
        "yield_curve":       latest.yield_curve,
        "unemployment_rate": latest.unemployment_rate,
        "regime":            latest.regime,
        "regime_confidence": latest.regime_confidence,
    }
    
@router.get("/forecast/{model_id}", response_model=DriftForecastOut)
def get_drift_forecast(
    model_id: str,
    session: Session = Depends(get_session),
):
    """
    Proactive drift forecast for a model based on recent macro signal history.
    Returns probability 0–1 that elevated drift will occur in the next 7–14 days.
    """
    model = session.exec(
        select(ModelRecord).where(ModelRecord.model_id == model_id)
    ).first()
    if not model:
        raise HTTPException(status_code=404, detail=f"Model '{model_id}' not found")

    try:
        from finsight.forecast import DriftForecaster
        forecast = DriftForecaster().forecast_from_db()
        return DriftForecastOut(
            probability=forecast.probability,
            expected_regime=forecast.expected_regime,
            trigger_signals=forecast.trigger_signals,
            horizon_days=forecast.horizon_days,
            explanation=forecast.explanation,
        )
    except ImportError:
        raise HTTPException(
            status_code=503,
            detail="FinSight not installed — run: pip install -e '.[llm,tracing,agent]'",
        )


@router.get("/{model_id}/history", response_model=list[DriftRunOut])
def get_drift_history(
    model_id: str,
    limit: int = 50,
    regime: str | None = None,
    severity: str | None = None,
    feature: str | None = None,
    since: str | None = None,
    until: str | None = None,
    version: str | None = None,
    session: Session = Depends(get_session),
):
    from datetime import datetime as _dt
    model = session.exec(
        select(ModelRecord).where(ModelRecord.model_id == model_id)
    ).first()
    if not model:
        raise HTTPException(status_code=404, detail=f"Model '{model_id}' not found")

    q = select(DriftRun).where(DriftRun.model_id == model_id)
    if regime is not None:
        q = q.where(DriftRun.regime == regime)
    if severity is not None:
        q = q.where(DriftRun.overall_severity == severity)
    if feature is not None:
        q = q.where(DriftRun.feature_results_json.contains(feature))
    if since is not None:
        q = q.where(DriftRun.checked_at >= _dt.fromisoformat(since))
    if until is not None:
        q = q.where(DriftRun.checked_at <= _dt.fromisoformat(until))
    if version is not None:
        ver_record = session.exec(
            select(ModelVersion).where(
                ModelVersion.model_id == model_id,
                ModelVersion.version_label == version,
            )
        ).first()
        if ver_record:
            q = q.where(DriftRun.model_version_id == ver_record.id)
        else:
            return []

    runs = session.exec(q.order_by(desc(DriftRun.checked_at)).limit(limit)).all()
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

class MacroOverride(BaseModel):
    vix:              float | None = None
    credit_spread:    float | None = None
    fed_funds_rate:   float | None = None
    yield_curve:      float | None = None
    unemployment_rate: float | None = None


class RunCheckRequest(BaseModel):
    records: list[dict[str, Any]]   # list of row dicts — same format as df.to_dict("records")
    set_as_baseline: bool = False
    macro: MacroOverride | None = None


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

    macro_override: _MacroSnapshot | None = None
    if payload.macro is not None:
        from datetime import date as _date
        macro_override = _MacroSnapshot(
            as_of=_date.today(),
            vix=payload.macro.vix,
            credit_spread=payload.macro.credit_spread,
            fed_funds_rate=payload.macro.fed_funds_rate,
            yield_curve=payload.macro.yield_curve,
            unemployment_rate=payload.macro.unemployment_rate,
        )

    with _drift_span("api.drift_run") as span:
        if span is not None:
            span.set_attribute("model.id", model_id)
        result = run_drift_check(model_id, snapshot, macro=macro_override)
        if result is None:
            raise HTTPException(
                status_code=400,
                detail="No baseline registered. POST with set_as_baseline=true first."
            )
        if span is not None:
            span.set_attribute("drift.severity", result.overall_severity.value)
            if result.regime:
                span.set_attribute("regime.class", result.regime)
        # Capture the active span's trace ID and store it on the DriftRun that was
        # just written by run_drift_check (most recent row for this model).
        trace_id = _current_trace_id()
        if trace_id:
            latest_run = session.exec(
                select(DriftRun)
                .where(DriftRun.model_id == model_id)
                .order_by(desc(DriftRun.checked_at))
                .limit(1)
            ).first()
            if latest_run:
                latest_run.phoenix_trace_id = trace_id
                session.add(latest_run)
                session.commit()

    return {
        "model_id": model_id,
        "overall_severity": result.overall_severity.value,
        "drift_score": result.drift_score,
        "regime": result.regime,
        "notes": result.notes,
        "drifted_features": [
            {"feature": f.feature_name, "detector": f.detector, "score": f.score}
            for f in result.unique_drifted_features
        ],
    }

