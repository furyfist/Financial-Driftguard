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


class DriftRunOut(BaseModel):
    id: int
    model_id: str
    checked_at: datetime
    overall_severity: str
    drift_score: float
    regime: Optional[str]
    notes: str


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