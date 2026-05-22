from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class ModelCreate(BaseModel):
    model_id: str
    description: str = ""


class ModelOut(BaseModel):
    model_id: str
    description: str
    created_at: datetime


class ModelVersionCreate(BaseModel):
    version_label: str
    description: str = ""


class ModelVersionOut(BaseModel):
    id: int
    model_id: str
    version_label: str
    description: str
    baseline_rows: Optional[int]
    created_at: datetime
    promoted_at: Optional[datetime]
    demoted_at: Optional[datetime]
    is_active: bool


class DriftRunOut(BaseModel):
    id: int
    model_id: str
    checked_at: datetime
    overall_severity: str
    drift_score: float
    regime: Optional[str]
    notes: str
    phoenix_trace_id: Optional[str] = None
    model_version_id: Optional[int] = None


class AlertOut(BaseModel):
    id: int
    model_id: str
    severity: str
    message: str
    acknowledged: bool
    created_at: datetime


class AckRequest(BaseModel):
    alert_id: int


# ── Agent schemas ─────────────────────────────────────────────────────────────

class AgentAskRequest(BaseModel):
    query: str
    model_id: Optional[str] = None


class AgentAnalyzeRequest(BaseModel):
    model_id: str


class AgentResponseOut(BaseModel):
    recommendation: str
    action: str
    confidence: float
    reasoning: str
    sources: list[str] = []
    model_id: Optional[str] = None


class AgentLogOut(BaseModel):
    id: int
    model_id: Optional[str]
    query: str
    action: str
    confidence: float
    regime_context: str
    created_at: datetime


class DriftForecastOut(BaseModel):
    probability: float
    expected_regime: str
    trigger_signals: list[str]
    horizon_days: int
    explanation: str


class TrustScoreOut(BaseModel):
    model_id: str
    trustworthy: bool
    confidence: float
    regime: str
    drift_severity: str
    recommendation: str   # proceed | proceed_with_caution | escalate | halt
    reason: str
    last_checked: datetime
    next_check_recommended: datetime


class ReportRequest(BaseModel):
    model_id: str
    date_range: str = ""   # "YYYY-MM-DD/YYYY-MM-DD"; empty → last 30 days


class ReportOut(BaseModel):
    model_id: str
    date_range: str
    generated_at: datetime
    filename: str
    download_path: str


class ChallengerResultOut(BaseModel):
    model_id: str
    status: str
    champion_run_id: Optional[int] = None
    challenger_run_id: Optional[int] = None
    champion_drift_score: Optional[float] = None
    challenger_drift_score: Optional[float] = None
    champion_severity: Optional[str] = None
    challenger_severity: Optional[str] = None
    winner: str = "inconclusive"
    drift_score_delta: Optional[float] = None
    drifted_features: list[str] = []
    recommendation: str = ""
    triggered_at: datetime