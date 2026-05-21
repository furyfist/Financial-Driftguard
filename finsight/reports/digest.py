"""Weekly digest generator — produces a short health summary for a model over a rolling period."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

logger = logging.getLogger(__name__)

_SEVERITY_ORDER = ["none", "low", "medium", "high", "critical"]


@dataclass
class DigestReport:
    model_id:              str
    period_days:           int
    status_light:          str       # "green" | "amber" | "red"
    regime_current:        str
    regime_previous:       str
    drift_trend:           str       # "increasing" | "decreasing" | "stable"
    agent_decisions_count: int
    one_liner:             str
    generated_at:          datetime


class DigestGenerator:
    """Generate a weekly health digest for a registered model."""

    def generate(self, model_id: str, period_days: int = 7) -> DigestReport:
        """
        Read the last period_days of drift runs and produce a DigestReport.
        Never raises — returns a minimal fallback DigestReport on any exception.
        """
        try:
            return self._build(model_id, period_days)
        except Exception as exc:
            logger.warning("DigestGenerator.generate failed for %s: %s", model_id, exc)
            return DigestReport(
                model_id=model_id,
                period_days=period_days,
                status_light="green",
                regime_current="unknown",
                regime_previous="unknown",
                drift_trend="stable",
                agent_decisions_count=0,
                one_liner=f"{model_id} digest unavailable due to an internal error.",
                generated_at=datetime.now(timezone.utc),
            )

    # ── Internal ──────────────────────────────────────────────────────────────

    def _build(self, model_id: str, period_days: int) -> DigestReport:
        from sqlmodel import Session, select
        from driftguard.store.database import DriftRun, AgentDecisionLog, engine

        now   = datetime.now(timezone.utc)
        since = now - timedelta(days=period_days)

        with Session(engine) as session:
            runs = session.exec(
                select(DriftRun)
                .where(DriftRun.model_id == model_id)
                .where(DriftRun.checked_at >= since)
                .order_by(DriftRun.checked_at)
            ).all()

            decisions = session.exec(
                select(AgentDecisionLog)
                .where(AgentDecisionLog.model_id == model_id)
                .where(AgentDecisionLog.created_at >= since)
            ).all()

        agent_decisions_count = len(decisions)

        if len(runs) < 3:
            return DigestReport(
                model_id=model_id,
                period_days=period_days,
                status_light="green",
                regime_current=runs[-1].regime or "unknown" if runs else "unknown",
                regime_previous="unknown",
                drift_trend="stable",
                agent_decisions_count=agent_decisions_count,
                one_liner=(
                    f"{model_id} has insufficient data for digest (< 3 runs in period)."
                ),
                generated_at=now,
            )

        regime_current  = runs[-1].regime or "unknown"
        regime_previous = runs[0].regime  or "unknown"

        drift_trend = _compute_trend(runs[0].drift_score, runs[-1].drift_score)

        status_light = _compute_status_light(runs)

        one_liner = _build_one_liner(
            model_id, status_light, drift_trend, regime_current, agent_decisions_count
        )

        return DigestReport(
            model_id=model_id,
            period_days=period_days,
            status_light=status_light,
            regime_current=regime_current,
            regime_previous=regime_previous,
            drift_trend=drift_trend,
            agent_decisions_count=agent_decisions_count,
            one_liner=one_liner,
            generated_at=now,
        )


# ── Helpers ────────────────────────────────────────────────────────────────────

def _compute_trend(first_score: float, last_score: float) -> str:
    delta = last_score - first_score
    if delta > 0.005:
        return "increasing"
    if delta < -0.005:
        return "decreasing"
    return "stable"


def _compute_status_light(runs) -> str:
    """red if any critical run; amber if any high; else green."""
    severities = {r.overall_severity for r in runs if r.overall_severity}
    if "critical" in severities:
        return "red"
    if "high" in severities:
        return "amber"
    return "green"


def _build_one_liner(
    model_id: str,
    status_light: str,
    drift_trend: str,
    regime_current: str,
    decisions: int,
) -> str:
    if status_light == "green":
        return f"{model_id} is healthy. No action required."
    if drift_trend == "increasing":
        return (
            f"{model_id} needs attention — drift increasing in {regime_current} regime."
        )
    return (
        f"{model_id} has elevated risk. {decisions} agent decision(s) in period."
    )
