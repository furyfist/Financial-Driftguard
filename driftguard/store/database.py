from datetime import datetime, timezone
from typing import Optional
from sqlmodel import Field, Session, SQLModel, create_engine, select
import io
import logging

_log = logging.getLogger(__name__)


class ModelRecord(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    model_id: str = Field(index=True, unique=True)
    description: str = ""
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    baseline_data: Optional[bytes] = Field(default=None)   # parquet blob
    baseline_set_at: Optional[datetime] = Field(default=None)
    baseline_row_count: Optional[int] = Field(default=None)


class ModelVersion(SQLModel, table=True):
    """Tracks discrete versions of a model — each retrain creates a new version."""
    id: Optional[int] = Field(default=None, primary_key=True)
    model_id: str = Field(index=True, foreign_key="modelrecord.model_id")
    version_label: str                           # e.g. "v1", "v2"
    description: str = ""
    baseline_blob: Optional[bytes] = Field(default=None)
    baseline_rows: Optional[int] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    promoted_at: Optional[datetime] = None
    demoted_at: Optional[datetime] = None
    is_active: bool = False


class DriftRun(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    model_id: str = Field(index=True, foreign_key="modelrecord.model_id")
    checked_at: datetime
    overall_severity: str
    drift_score: float
    regime: Optional[str] = None
    regime_confidence: Optional[float] = None   # new in v2
    notes: str = ""
    feature_results_json: str = "{}"
    phoenix_trace_id: Optional[str] = None      # new in v4
    model_version_id: Optional[int] = Field(default=None, foreign_key="modelversion.id")


class AlertRecord(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    model_id: str = Field(index=True)
    drift_run_id: int = Field(foreign_key="driftrun.id")
    severity: str
    message: str
    acknowledged: bool = False
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class MacroCache(SQLModel, table=True):
    """Stores latest macro snapshot per fetch — used by scheduler."""
    id: Optional[int] = Field(default=None, primary_key=True)
    fetched_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    vix: Optional[float] = None
    credit_spread: Optional[float] = None
    fed_funds_rate: Optional[float] = None
    yield_curve: Optional[float] = None
    unemployment_rate: Optional[float] = None
    regime: Optional[str] = None
    regime_confidence: Optional[float] = None


class WebhookConfigRecord(SQLModel, table=True):
    """Persisted webhook notifier configuration — restored on startup."""
    id: Optional[int] = Field(default=None, primary_key=True)
    platform: str                            # "slack" | "discord"
    webhook_url: str
    model_id: Optional[str] = None
    severity_threshold: str = "high"
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class AgentDecisionLog(SQLModel, table=True):
    """Audit log — every agent recommendation persisted for governance traceability."""
    id: Optional[int] = Field(default=None, primary_key=True)
    model_id: Optional[str] = Field(default=None, index=True)
    query: str
    recommendation: str
    action: str = Field(index=True)   # monitor | investigate | retrain | freeze | ...
    confidence: float
    regime_context: str = ""          # regime at time of decision
    trace_ids_referenced: str = "[]"  # JSON array of Phoenix trace IDs cited
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    model_version_id: Optional[int] = Field(default=None, foreign_key="modelversion.id")


sqlite_url = "sqlite:///./driftguard.db"
engine = create_engine(sqlite_url, echo=False)


def create_db():
    SQLModel.metadata.create_all(engine)


def get_session():
    with Session(engine) as session:
        yield session


def migrate_model_versions() -> None:
    """Auto-create 'v1' for each model that has no version yet and assign existing runs to it."""
    try:
        with Session(engine) as session:
            models = session.exec(select(ModelRecord)).all()
            for m in models:
                existing = session.exec(
                    select(ModelVersion).where(ModelVersion.model_id == m.model_id)
                ).first()
                if existing:
                    continue
                v1 = ModelVersion(
                    model_id=m.model_id,
                    version_label="v1",
                    description="Initial version (auto-created on migration)",
                    is_active=True,
                    promoted_at=datetime.now(timezone.utc),
                )
                session.add(v1)
                session.flush()
                unversioned_runs = session.exec(
                    select(DriftRun).where(
                        DriftRun.model_id == m.model_id,
                        DriftRun.model_version_id == None,  # noqa: E711
                    )
                ).all()
                for run in unversioned_runs:
                    run.model_version_id = v1.id
                    session.add(run)
                unversioned_decisions = session.exec(
                    select(AgentDecisionLog).where(
                        AgentDecisionLog.model_id == m.model_id,
                        AgentDecisionLog.model_version_id == None,  # noqa: E711
                    )
                ).all()
                for d in unversioned_decisions:
                    d.model_version_id = v1.id
                    session.add(d)
            session.commit()
    except Exception as exc:
        _log.warning("migrate_model_versions: %s", exc)


def snapshot_to_bytes(snapshot) -> bytes:
    """Serialise a DataSnapshot to parquet bytes for storage."""
    import pandas as pd
    import numpy as np
    rows = {
        feat: snapshot.get(feat)
        for feat in snapshot.feature_names()
    }
    df  = pd.DataFrame(rows)
    buf = io.BytesIO()
    df.to_parquet(buf, index=False)
    return buf.getvalue()


def bytes_to_snapshot(data: bytes, label: str = "baseline"):
    """Deserialise parquet bytes back to a DataSnapshot."""
    import pandas as pd
    from ..core.snapshot import DataSnapshot
    buf = io.BytesIO(data)
    df  = pd.read_parquet(buf)
    return DataSnapshot.from_dataframe(df, label=label)