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