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
from ..notifications.base import BaseNotifier, NotificationPayload

logger = logging.getLogger(__name__)
scheduler = BackgroundScheduler()
_notifiers: dict[str | None, list[BaseNotifier]] = {}

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


def run_drift_check(model_id: str, current: DataSnapshot, macro=None):
    """
    Run drift check. Loads baseline from SQLite automatically.
    Uses provided macro snapshot when given; otherwise fetches latest cached macro.
    """
    baseline = load_baseline(model_id)
    if baseline is None:
        logger.warning(f"No baseline for '{model_id}' — skipping")
        return None

    if macro is None:
        macro = get_latest_macro()
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

        # Dispatch notifications
        notifiers = _get_notifiers_for_model(model_id)
        if notifiers:
            payload = _build_payload(result, model_id)
            for notifier in notifiers:
                notifier.notify(payload)

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

    # Restore persisted webhook notifiers
    try:
        from ..store.database import WebhookConfigRecord
        from ..notifications.discord import DiscordNotifier
        from ..notifications.slack import SlackNotifier
        with Session(engine) as session:
            configs = session.exec(select(WebhookConfigRecord)).all()
            for cfg in configs:
                if cfg.platform == "slack":
                    n = SlackNotifier(webhook_url=cfg.webhook_url, severity_threshold=cfg.severity_threshold)
                elif cfg.platform == "discord":
                    n = DiscordNotifier(webhook_url=cfg.webhook_url, severity_threshold=cfg.severity_threshold)
                else:
                    continue
                register_notifier(n, model_id=cfg.model_id)
        if configs:
            logger.info("%d webhook notifier(s) restored from DB", len(configs))
    except Exception as exc:
        logger.warning("Failed to restore webhook notifiers: %s", exc)

    # Fetch macro immediately so regime is available from first request
    import threading
    logger.info("Fetching initial macro snapshot in background...")
    threading.Thread(target=fetch_and_cache_macro, daemon=True, name="macro-init").start()

def start_scheduler(interval_minutes: int = 30):
    if scheduler.running:
        return
    scheduler.start()
    logger.info(f"Scheduler started — drift checks every {interval_minutes} min")

def _run_daily_forecast() -> None:
    """Compute and log daily proactive drift forecast. Best-effort — never raises."""
    try:
        from finsight.forecast import DriftForecaster
        forecast = DriftForecaster().forecast_from_db()
        if forecast.probability >= 0.50:
            logger.warning(
                "Drift forecast: %d%% probability in %dd — %s — signals: %s",
                int(forecast.probability * 100),
                forecast.horizon_days,
                forecast.expected_regime,
                ", ".join(forecast.trigger_signals) or "none",
            )
        else:
            logger.info(
                "Drift forecast: %d%% probability — signals stable",
                int(forecast.probability * 100),
            )
    except ImportError:
        pass  # finsight not installed — skip silently
    except Exception as exc:
        logger.warning("Daily forecast job failed: %s", exc)


def _run_weekly_digest() -> None:
    """
    Monday 08:00 UTC — generate a health digest for every registered model.
    Fires Slack/email notification if status_light is amber or red.
    Best-effort per model — never raises.
    """
    try:
        from finsight.reports.digest import DigestGenerator
    except ImportError:
        logger.info("_run_weekly_digest: finsight not installed — skipping")
        return

    try:
        with Session(engine) as session:
            records = session.exec(select(ModelRecord)).all()
            model_ids = [r.model_id for r in records]
    except Exception as exc:
        logger.warning("_run_weekly_digest: failed to load model IDs: %s", exc)
        return

    for model_id in model_ids:
        try:
            report = DigestGenerator().generate(model_id)
            logger.info(
                "Digest [%s] status=%s trend=%s — %s",
                model_id, report.status_light, report.drift_trend, report.one_liner,
            )

            if report.status_light in ("amber", "red"):
                severity = "critical" if report.status_light == "red" else "high"
                payload = NotificationPayload(
                    model_id=model_id,
                    overall_severity=severity,
                    drift_score=0.0,
                    regime=report.regime_current,
                    regime_confidence=0.0,
                    recommendation=report.one_liner,
                    top_features=[],
                    checked_at=report.generated_at.isoformat(),
                )
                for notifier in _get_notifiers_for_model(model_id):
                    notifier.notify(payload)

        except Exception as exc:
            logger.warning("_run_weekly_digest: error for model %s: %s", model_id, exc)


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

    # Daily proactive drift forecast
    scheduler.add_job(
        _run_daily_forecast,
        trigger="interval",
        hours=24,
        id="daily_forecast",
        replace_existing=True,
    )

    # Weekly digest — every Monday 08:00 UTC
    scheduler.add_job(
        _run_weekly_digest,
        trigger="cron",
        day_of_week="mon",
        hour=8,
        minute=0,
        id="weekly_digest",
        replace_existing=True,
    )

    scheduler.start()
    logger.info("Scheduler started — macro every 6h, forecast every 24h, digest every Monday 08:00")

def register_notifier(
    notifier: BaseNotifier,
    model_id: str | None = None,
):
    """
    Register a notifier for a specific model or all models.

    Usage:
        # notify on all models
        register_notifier(DiscordNotifier(webhook_url="..."))

        # notify only for a specific model
        register_notifier(SlackNotifier(webhook_url="..."), model_id="lending_club_v1")
    """
    key = model_id
    if key not in _notifiers:
        _notifiers[key] = []
    _notifiers[key].append(notifier)
    logger.info(
        f"Notifier registered: {notifier.name} "
        f"for {'all models' if model_id is None else model_id}"
    )


def _get_notifiers_for_model(model_id: str) -> list[BaseNotifier]:
    """Returns notifiers for a specific model + global notifiers."""
    return _notifiers.get(model_id, []) + _notifiers.get(None, [])


def _build_payload(result, model_id: str) -> NotificationPayload:
    """Build NotificationPayload from a DriftResult."""
    psi_results = [
        f for f in result.feature_results
        if f.detector == "psi" and f.severity.value != "none"
    ]
    psi_results.sort(key=lambda x: x.score, reverse=True)

    return NotificationPayload(
        model_id=model_id,
        overall_severity=result.overall_severity.value,
        drift_score=result.drift_score,
        regime=result.regime or "unknown",
        regime_confidence=0.0,
        recommendation=result.notes or "",
        top_features=[
            {
                "feature":  f.feature_name,
                "score":    f.score,
                "severity": f.severity.value,
            }
            for f in psi_results[:5]
        ],
        checked_at=result.checked_at.isoformat(),
    )


def stop_scheduler():
    if scheduler.running:
        scheduler.shutdown()