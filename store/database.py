from datetime import datetime, timezone
from typing import Optional
from sqlmodel import Field, Session, SQLModel, create_engine, select


class ModelRecord(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    model_id: str = Field(index=True, unique=True)
    description: str = ""
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class DriftRun(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    model_id: str = Field(index=True, foreign_key="modelrecord.model_id")
    checked_at: datetime
    overall_severity: str
    drift_score: float
    regime: Optional[str] = None
    notes: str = ""
    feature_results_json: str = "{}"  # serialised JSON blob


class AlertRecord(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    model_id: str = Field(index=True)
    drift_run_id: int = Field(foreign_key="driftrun.id")
    severity: str
    message: str
    acknowledged: bool = False
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


sqlite_url = "sqlite:///./driftguard.db"
engine = create_engine(sqlite_url, echo=False)


def create_db():
    SQLModel.metadata.create_all(engine)


def get_session():
    with Session(engine) as session:
        yield session