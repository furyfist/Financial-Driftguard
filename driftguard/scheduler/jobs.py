import json
import logging
from datetime import datetime, timezone

from apscheduler.schedulers.background import BackgroundScheduler
from sqlmodel import Session, select

from ..store.database import (
    engine, DriftRun, AlertRecord, ModelRecord,
    snapshot_to_bytes, bytes_to_snapshot
)
from ..core.monitor import Monitor
from ..core.snapshot import DataSnapshot

logger = logging.getLogger(__name__)
scheduler = BackgroundScheduler()


def register_baseline(model_id: str, snapshot: DataSnapshot):
    """
    Persist baseline to SQLite.
    Survives server restarts — loaded back on startup.
    """
    blob       = snapshot_to_bytes(snapshot)
    row_count  = len(snapshot.get(snapshot.feature_names()[0]))

    with Session(engine) as session:
        record = session.exec(
            select(ModelRecord).where(ModelRecord.model_id == model_id)
        ).first()
        if not record:
            logger.warning(f"Model '{model_id}' not found — register it first")
            return

        record.baseline_data      = blob
        record.baseline_set_at    = datetime.now(timezone.utc)
        record.baseline_row_count = row_count
        session.add(record)
        session.commit()

    logger.info(
        f"Baseline persisted for '{model_id}' — "
        f"{row_count} rows, {len(blob):,} bytes"
    )


def load_baseline(model_id: str) -> DataSnapshot | None:
    """Load baseline from SQLite. Returns None if not set."""
    with Session(engine) as session:
        record = session.exec(
            select(ModelRecord).where(ModelRecord.model_id == model_id)
        ).first()
        if not record or not record.baseline_data:
            return None
        return bytes_to_snapshot(record.baseline_data, label="baseline")


def get_latest_macro():
    """Load most recent macro snapshot from cache table."""
    from ..store.database import MacroCache
    from ..regime.macro_signals import MacroSnapshot
    from datetime import date

    with Session(engine) as session:
        latest = session.exec(
            select(MacroCache).order_by(MacroCache.fetched_at.desc()).limit(1)
        ).first()

        if not latest:
            return None

        return MacroSnapshot(
            as_of=latest.fetched_at.date(),
            vix=latest.vix,
            credit_spread=latest.credit_spread,
            fed_funds_rate=latest.fed_funds_rate,
            yield_curve=latest.yield_curve,
            unemployment_rate=latest.unemployment_rate,
        )


def run_drift_check(model_id: str, current: DataSnapshot):
    """
    Run drift check. Loads baseline from SQLite automatically.
    Attaches latest cached macro snapshot if available.
    """
    baseline = load_baseline(model_id)
    if baseline is None:
        logger.warning(f"No baseline for '{model_id}' — skipping")
        return None

    macro   = get_latest_macro()
    monitor = Monitor(model_id=model_id)
    result  = monitor.check(baseline, current, macro=macro)

    feature_json = json.dumps([
        {
            "feature_name": f.feature_name,
            "detector":     f.detector,
            "score":        f.score,
            "severity":     f.severity.value,
            "p_value":      f.p_value,
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

        if result.overall_severity.value in ("high", "critical"):
            alert = AlertRecord(
                model_id=model_id,
                drift_run_id=run.id,
                severity=result.overall_severity.value,
                message=(
                    f"Drift score {result.drift_score:.3f} on '{model_id}'. "
                    f"Regime: {result.regime or 'unknown'}. "
                    f"{result.notes[:120]}"
                ),
            )
            session.add(alert)
            session.commit()

    logger.info(
        f"Drift check — {model_id} | "
        f"severity={result.overall_severity.value} | "
        f"score={result.drift_score} | "
        f"regime={result.regime}"
    )
    return result


def restore_baselines_from_db():
    """
    Called on server startup.
    Logs persisted baselines and triggers immediate macro fetch.
    """
    from .macro_job import fetch_and_cache_macro

    with Session(engine) as session:
        records = session.exec(select(ModelRecord)).all()
        loaded  = 0
        for r in records:
            if r.baseline_data:
                logger.info(
                    f"Baseline available for '{r.model_id}' — "
                    f"{r.baseline_row_count} rows, "
                    f"set {r.baseline_set_at}"
                )
                loaded += 1
        if loaded == 0:
            logger.info("No persisted baselines found")
        else:
            logger.info(f"{loaded} model baseline(s) ready")

    # Fetch macro immediately so regime is available from first request
    logger.info("Fetching initial macro snapshot...")
    fetch_and_cache_macro()

def start_scheduler(interval_minutes: int = 30):
    if scheduler.running:
        return
    scheduler.start()
    logger.info(f"Scheduler started — drift checks every {interval_minutes} min")

def start_scheduler(interval_minutes: int = 30):
    if scheduler.running:
        return

    # Macro fetch — every 6 hours
    from .macro_job import fetch_and_cache_macro
    scheduler.add_job(
        fetch_and_cache_macro,
        trigger="interval",
        hours=6,
        id="macro_fetch",
        replace_existing=True,
    )

    scheduler.start()
    logger.info(f"Scheduler started — drift checks every {interval_minutes} min, macro every 6h")

def stop_scheduler():
    if scheduler.running:
        scheduler.shutdown()