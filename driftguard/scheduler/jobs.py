import json
import logging
from datetime import datetime, timezone

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from sqlmodel import Session, select

from ..store.database import engine, DriftRun, AlertRecord, ModelRecord
from ..core.monitor import Monitor
from ..core.snapshot import DataSnapshot

logger = logging.getLogger(__name__)

scheduler = BackgroundScheduler()

# In-memory baseline store — keyed by model_id
# Real usage: load from file/DB. For v1 this is fine.
_baselines: dict[str, DataSnapshot] = {}


def register_baseline(model_id: str, snapshot: DataSnapshot):
    """Call this once when you register a model to set its baseline."""
    _baselines[model_id] = snapshot
    logger.info(f"Baseline registered for model '{model_id}'")


def run_drift_check(model_id: str, current: DataSnapshot):
    """
    Run a full drift check for one model and persist results.
    Called by the scheduler or manually via API later.
    """
    if model_id not in _baselines:
        logger.warning(f"No baseline registered for '{model_id}' — skipping")
        return None

    baseline = _baselines[model_id]
    monitor = Monitor(model_id=model_id)
    result = monitor.check(baseline, current)

    # Serialise feature results to JSON for storage
    feature_json = json.dumps([
        {
            "feature_name": f.feature_name,
            "detector": f.detector,
            "score": f.score,
            "severity": f.severity.value,
            "p_value": f.p_value,
        }
        for f in result.feature_results
    ])

    with Session(engine) as session:
        run = DriftRun(
            model_id=model_id,
            checked_at=result.checked_at,
            overall_severity=result.overall_severity.value,
            drift_score=result.drift_score,
            regime=result.regime,
            notes=result.notes,
            feature_results_json=feature_json,
        )
        session.add(run)
        session.commit()
        session.refresh(run)

        # Create alert if severity is high or critical
        if result.overall_severity.value in ("high", "critical"):
            alert = AlertRecord(
                model_id=model_id,
                drift_run_id=run.id,
                severity=result.overall_severity.value,
                message=(
                    f"Drift score {result.drift_score:.3f} on model '{model_id}'. "
                    f"Regime: {result.regime or 'unknown'}. {result.notes[:120]}"
                ),
            )
            session.add(alert)
            session.commit()

    logger.info(
        f"Drift check complete — {model_id} | "
        f"severity={result.overall_severity.value} | score={result.drift_score}"
    )
    return result


def start_scheduler(interval_minutes: int = 30):
    if scheduler.running:
        return
    scheduler.start()
    logger.info(f"Scheduler started — checks every {interval_minutes} min")


def stop_scheduler():
    if scheduler.running:
        scheduler.shutdown()