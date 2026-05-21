from datetime import datetime, timezone
from typing import Optional
from sqlmodel import Field, Session, SQLModel, create_engine, select
import io


class ModelRecord(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    model_id: str = Field(index=True, unique=True)
    description: str = ""
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    baseline_data: Optional[bytes] = Field(default=None)   # parquet blob
    baseline_set_at: Optional[datetime] = Field(default=None)
    baseline_row_count: Optional[int] = Field(default=None)


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


sqlite_url = "sqlite:///./driftguard.db"
engine = create_engine(sqlite_url, echo=False)


def create_db():
    SQLModel.metadata.create_all(engine)


def get_session():
    with Session(engine) as session:
        yield session


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