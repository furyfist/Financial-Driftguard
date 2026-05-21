"""
TrustHandler — deterministic model trust scoring for agent-to-agent consumption.

No LLM involved. Pure DB read + decision matrix. Must be fast and reliable
because external AI agents depend on this response before making credit decisions.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

logger = logging.getLogger(__name__)

# ── Valid recommendation values ────────────────────────────────────────────────
PROCEED              = "proceed"
PROCEED_WITH_CAUTION = "proceed_with_caution"
ESCALATE             = "escalate"
HALT                 = "halt"

# Regimes classified as macro-driven — drift in these regimes does NOT indicate model decay
_MACRO_REGIMES = frozenset({"rate_shock", "credit_stress", "recession"})

# Severities that count as "elevated" drift
_ELEVATED   = frozenset({"medium", "high", "critical"})
_HIGH       = frozenset({"high", "critical"})
_NEGLIGIBLE = frozenset({"none", "low"})

# How long until the next check is recommended per recommendation level
_NEXT_CHECK_HOURS: dict[str, int] = {
    HALT:                 1,
    ESCALATE:             6,
    PROCEED_WITH_CAUTION: 12,
    PROCEED:              24,
}


@dataclass
class TrustScore:
    model_id: str
    trustworthy: bool            # binary go/no-go for external agents
    confidence: float            # 0.0–1.0
    regime: str                  # macro regime at time of scoring
    drift_severity: str          # current drift severity
    recommendation: str          # proceed | proceed_with_caution | escalate | halt
    reason: str                  # one-sentence human/machine-readable explanation
    last_checked: datetime       # timestamp of the latest drift run consulted
    next_check_recommended: datetime


class TrustHandler:
    """
    Scores whether a model is currently trustworthy enough to use in automated decisions.

    Consumes the latest DriftRun and MacroCache from SQLite — zero LLM calls.
    """

    def score(self, model_id: str, context: str = "") -> TrustScore:
        """
        Return a TrustScore for model_id.

        context is an optional hint from the calling agent about intended use
        (e.g. "credit decisioning for $50K loans"). It is used only to enrich
        the reason string — it never changes the recommendation.
        """
        drift = _latest_drift(model_id)
        macro = _latest_macro()

        severity = (drift.get("overall_severity") or "none").lower() if drift else "none"
        regime   = ((drift.get("regime") if drift else None) or macro.get("regime") or "unknown").lower()
        checked_at = _parse_dt(drift.get("checked_at")) if drift else datetime.now(timezone.utc)

        recommendation, trustworthy, confidence = _apply_matrix(severity, regime)
        reason = _build_reason(recommendation, severity, regime, context)
        next_check = checked_at + timedelta(hours=_NEXT_CHECK_HOURS[recommendation])

        return TrustScore(
            model_id=model_id,
            trustworthy=trustworthy,
            confidence=confidence,
            regime=regime,
            drift_severity=severity,
            recommendation=recommendation,
            reason=reason,
            last_checked=checked_at,
            next_check_recommended=next_check,
        )


# ── Decision matrix ────────────────────────────────────────────────────────────

def _apply_matrix(severity: str, regime: str) -> tuple[str, bool, float]:
    """
    Core decision matrix. Returns (recommendation, trustworthy, confidence).

    Priority order (first match wins):
    1. black_swan → halt, regardless of severity
    2. negligible drift → proceed, regardless of regime
    3. macro regime + any drift → proceed_with_caution (drift is regime-driven)
    4. stable + elevated drift → escalate (model decay)
    5. stable + negligible drift → proceed
    6. unknown regime → proceed_with_caution (not enough info)
    """
    if regime == "black_swan":
        return HALT, False, 1.0

    if severity in _NEGLIGIBLE:
        return PROCEED, True, 0.95

    # Drift is elevated from here on
    if regime in _MACRO_REGIMES:
        # High drift is macro-driven — model is correctly reflecting uncertainty
        # Credit_stress with critical drift still warrants extra caution
        confidence = 0.75 if severity == "critical" else 0.85
        return PROCEED_WITH_CAUTION, True, confidence

    if regime == "stable":
        if severity in _HIGH:
            # No macro explanation → model decay → do not use
            return ESCALATE, False, 0.90
        # Medium drift in stable regime — borderline, watch closely
        return PROCEED_WITH_CAUTION, True, 0.80

    # unknown regime — insufficient data
    return PROCEED_WITH_CAUTION, True, 0.50


# ── Reason builder ─────────────────────────────────────────────────────────────

def _build_reason(
    recommendation: str,
    severity: str,
    regime: str,
    context: str,
) -> str:
    use_hint = f" for {context}" if context else ""

    if recommendation == HALT:
        return (
            f"Black swan macro regime detected — all automated model usage{use_hint} "
            "must be paused immediately pending human review."
        )
    if recommendation == ESCALATE:
        return (
            f"{severity.capitalize()} drift detected in a stable macro regime — "
            f"this indicates model decay, not market movement. "
            f"Do not use{use_hint} until the model is retrained and re-validated."
        )
    if recommendation == PROCEED_WITH_CAUTION:
        if regime in _MACRO_REGIMES:
            return (
                f"Elevated drift ({severity}) is consistent with the {regime} macro regime "
                f"and does not indicate model decay. Proceed{use_hint} with heightened monitoring."
            )
        if regime == "unknown":
            return (
                f"Macro regime is unclassified — trust score is provisional. "
                f"Proceed{use_hint} with caution and re-check after regime data is refreshed."
            )
        return (
            f"Moderate drift ({severity}) detected. Model is within acceptable bounds "
            f"but warrants close monitoring{use_hint}."
        )
    # PROCEED
    return (
        f"No material drift detected in a {regime} regime. "
        f"Model is trustworthy for use{use_hint}."
    )


# ── DB helpers ─────────────────────────────────────────────────────────────────

def _latest_drift(model_id: str) -> dict | None:
    try:
        from sqlmodel import Session, select, desc
        from driftguard.store.database import DriftRun, engine

        with Session(engine) as session:
            run = session.exec(
                select(DriftRun)
                .where(DriftRun.model_id == model_id)
                .order_by(desc(DriftRun.checked_at))
                .limit(1)
            ).first()
        if not run:
            return None
        return {
            "overall_severity": run.overall_severity,
            "drift_score": run.drift_score,
            "regime": run.regime,
            "regime_confidence": run.regime_confidence,
            "checked_at": run.checked_at.isoformat(),
        }
    except Exception as exc:
        logger.warning("_latest_drift query failed for %s: %s", model_id, exc)
        return None


def _latest_macro() -> dict:
    try:
        from sqlmodel import Session, select, desc
        from driftguard.store.database import MacroCache, engine

        with Session(engine) as session:
            m = session.exec(
                select(MacroCache).order_by(desc(MacroCache.fetched_at)).limit(1)
            ).first()
        if not m:
            return {}
        return {"regime": m.regime, "regime_confidence": m.regime_confidence}
    except Exception as exc:
        logger.warning("_latest_macro query failed: %s", exc)
        return {}


def _parse_dt(value: str | None) -> datetime:
    if not value:
        return datetime.now(timezone.utc)
    try:
        dt = datetime.fromisoformat(value)
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except ValueError:
        return datetime.now(timezone.utc)
