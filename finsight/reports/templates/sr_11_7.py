"""SR 11-7 report structure — Fed model risk management guidance format."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class SR117Section:
    title: str
    prose: str                         # LLM-generated regulatory prose
    data_points: list[str] = field(default_factory=list)   # raw facts cited


@dataclass
class SR117Report:
    """Seven-section SR 11-7 compliant model risk report."""
    model_id: str
    date_range: str
    generated_at: datetime

    # Section 1 — Model Identification
    model_identification: SR117Section
    # Section 2 — Performance Summary
    performance_summary: SR117Section
    # Section 3 — Regime Context
    regime_context: SR117Section
    # Section 4 — Drift Analysis
    drift_analysis: SR117Section
    # Section 5 — Agent Recommendations
    agent_recommendations: SR117Section
    # Section 6 — Risk Assessment
    risk_assessment: SR117Section
    # Section 7 — Audit Trail
    audit_trail: SR117Section

    def sections(self) -> list[SR117Section]:
        return [
            self.model_identification,
            self.performance_summary,
            self.regime_context,
            self.drift_analysis,
            self.agent_recommendations,
            self.risk_assessment,
            self.audit_trail,
        ]
