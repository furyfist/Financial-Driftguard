"""Notification payload enricher — converts AgentResponse + drift data → NotificationPayload."""

from __future__ import annotations

import logging
import re
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

# Maps agent action values to notification severity levels.
_ACTION_SEVERITY: dict[str, str] = {
    "halt":                "critical",
    "freeze":              "critical",
    "escalate":            "critical",
    "retrain":             "high",
    "investigate":         "high",
    "champion_challenger": "high",
    "proceed_with_caution":"medium",
    "monitor":             "medium",
    "proceed":             "low",
}

# Pattern to extract feature names and PSI scores from the notes string.
# Matches: "int_rate (PSI=0.12)" or "int_rate (PSI: 0.12)"
_FEATURE_PATTERN = re.compile(r"(\w+)\s+\(PSI[=:]\s*([0-9.]+)\)", re.IGNORECASE)


def build_enriched_payload(agent_response, model_id: str, drift_result=None):
    """
    Build a NotificationPayload from an AgentResponse and optional drift result dict.

    Args:
        agent_response: AgentResponse dataclass from finsight.agent.brain.
        model_id:       The model being monitored.
        drift_result:   Optional dict with keys drift_score, regime, regime_confidence,
                        notes (as returned by get_latest_drift).  If None, read from DB.

    Returns:
        NotificationPayload — never raises; returns a minimal payload on any failure.
    """
    try:
        from driftguard.notifications.base import NotificationPayload

        if drift_result is None:
            try:
                from finsight.agent.tools.drift_tools import get_latest_drift
                drift_result = get_latest_drift(model_id)
            except Exception as exc:
                logger.warning("build_enriched_payload: get_latest_drift failed: %s", exc)
                drift_result = {}

        drift_result = drift_result or {}

        action   = (getattr(agent_response, "action", None) or "").lower()
        severity = _ACTION_SEVERITY.get(action, "low")

        regime = (
            getattr(agent_response, "regime", None)
            or drift_result.get("regime")
            or "unknown"
        )

        regime_confidence = float(drift_result.get("regime_confidence") or 0.0)
        drift_score       = float(drift_result.get("drift_score") or 0.0)

        recommendation = (getattr(agent_response, "recommendation", "") or "")[:300]

        top_features = _parse_features_from_notes(
            drift_result.get("notes") or "", severity
        )

        return NotificationPayload(
            model_id=model_id,
            overall_severity=severity,
            drift_score=drift_score,
            regime=regime,
            regime_confidence=regime_confidence,
            recommendation=recommendation,
            top_features=top_features,
            checked_at=datetime.now(timezone.utc).isoformat(),
        )

    except Exception as exc:
        logger.warning("build_enriched_payload failed: %s — returning minimal payload", exc)
        return _minimal_payload(model_id)


def _parse_features_from_notes(notes: str, severity: str) -> list[dict]:
    """Best-effort extraction of feature/PSI pairs from a drift notes string."""
    features: list[dict] = []
    for match in _FEATURE_PATTERN.finditer(notes):
        features.append({
            "feature":  match.group(1),
            "score":    float(match.group(2)),
            "severity": severity,
        })
        if len(features) >= 5:
            break
    return features


def _minimal_payload(model_id: str):
    """Return a safe fallback NotificationPayload when enrichment fails."""
    try:
        from driftguard.notifications.base import NotificationPayload
        return NotificationPayload(
            model_id=model_id,
            overall_severity="high",
            drift_score=0.0,
            regime="unknown",
            regime_confidence=0.0,
            recommendation="",
            top_features=[],
            checked_at=datetime.now(timezone.utc).isoformat(),
        )
    except Exception:
        # Absolute last resort — return a plain object so callers don't crash.
        class _Stub:
            pass
        p = _Stub()
        p.model_id          = model_id
        p.overall_severity  = "high"
        p.drift_score       = 0.0
        p.regime            = "unknown"
        p.regime_confidence = 0.0
        p.recommendation    = ""
        p.top_features      = []
        p.checked_at        = datetime.now(timezone.utc).isoformat()
        return p
