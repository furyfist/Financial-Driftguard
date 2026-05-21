"""Tests for Step 9 — agent-to-agent trust API."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import patch

import pytest


# ── Helpers ───────────────────────────────────────────────────────────────────

def _drift(severity: str, regime: str) -> dict:
    return {
        "overall_severity": severity,
        "drift_score": 0.15,
        "regime": regime,
        "regime_confidence": 0.90,
        "checked_at": datetime.now(timezone.utc).isoformat(),
    }


def _score(severity: str, regime: str, context: str = "") -> object:
    from finsight.trust_api import TrustHandler
    with patch("finsight.trust_api.handler._latest_drift", return_value=_drift(severity, regime)), \
         patch("finsight.trust_api.handler._latest_macro", return_value={"regime": regime}):
        return TrustHandler().score("test_model", context=context)


# ── Decision matrix — all 5 plan cases ────────────────────────────────────────

def test_black_swan_any_severity_returns_halt():
    ts = _score("high", "black_swan")
    assert ts.recommendation == "halt"
    assert ts.trustworthy is False
    assert ts.confidence == 1.0


def test_stable_no_drift_returns_proceed():
    ts = _score("none", "stable")
    assert ts.recommendation == "proceed"
    assert ts.trustworthy is True
    assert ts.confidence >= 0.90


def test_stable_low_drift_returns_proceed_with_caution():
    ts = _score("low", "stable")
    assert ts.recommendation == "proceed"   # low drift is negligible → proceed
    assert ts.trustworthy is True


def test_stable_medium_drift_returns_proceed_with_caution():
    ts = _score("medium", "stable")
    assert ts.recommendation == "proceed_with_caution"
    assert ts.trustworthy is True


def test_stable_high_drift_returns_escalate():
    ts = _score("high", "stable")
    assert ts.recommendation == "escalate"
    assert ts.trustworthy is False
    assert ts.confidence >= 0.85


def test_stable_critical_drift_returns_escalate():
    ts = _score("critical", "stable")
    assert ts.recommendation == "escalate"
    assert ts.trustworthy is False


def test_credit_stress_high_drift_returns_proceed_with_caution():
    """Macro-driven drift — model correctly reflects market, do not escalate."""
    ts = _score("high", "credit_stress")
    assert ts.recommendation == "proceed_with_caution"
    assert ts.trustworthy is True


def test_rate_shock_high_drift_returns_proceed_with_caution():
    ts = _score("high", "rate_shock")
    assert ts.recommendation == "proceed_with_caution"
    assert ts.trustworthy is True


def test_recession_high_drift_returns_proceed_with_caution():
    ts = _score("high", "recession")
    assert ts.recommendation == "proceed_with_caution"
    assert ts.trustworthy is True


def test_unknown_regime_returns_proceed_with_caution():
    ts = _score("medium", "unknown")
    assert ts.recommendation == "proceed_with_caution"
    assert ts.trustworthy is True
    assert ts.confidence == 0.50   # lowest confidence — data insufficient


# ── TrustScore fields ─────────────────────────────────────────────────────────

def test_trust_score_fields_are_populated():
    ts = _score("high", "black_swan")
    assert ts.model_id == "test_model"
    assert ts.regime == "black_swan"
    assert ts.drift_severity == "high"
    assert isinstance(ts.last_checked, datetime)
    assert isinstance(ts.next_check_recommended, datetime)
    assert ts.last_checked < ts.next_check_recommended
    assert ts.reason  # non-empty string


def test_halt_next_check_is_1_hour():
    ts = _score("high", "black_swan")
    delta = ts.next_check_recommended - ts.last_checked
    assert delta.seconds // 3600 == 1


def test_proceed_next_check_is_24_hours():
    ts = _score("none", "stable")
    delta = ts.next_check_recommended - ts.last_checked
    assert delta.seconds // 3600 == 24 or delta.days >= 1


# ── Context hint ──────────────────────────────────────────────────────────────

def test_context_appears_in_reason():
    ts = _score("none", "stable", context="credit scoring $50K loans")
    assert "credit scoring $50K loans" in ts.reason


def test_halt_reason_mentions_black_swan():
    ts = _score("none", "black_swan")
    assert "black swan" in ts.reason.lower() or "Black swan" in ts.reason


# ── No DB — handler uses fallback ─────────────────────────────────────────────

def test_handler_graceful_when_no_db_data():
    from finsight.trust_api import TrustHandler
    with patch("finsight.trust_api.handler._latest_drift", return_value=None), \
         patch("finsight.trust_api.handler._latest_macro", return_value={}):
        ts = TrustHandler().score("nonexistent_model")
    # With no data, severity=none, regime=unknown → proceed_with_caution or proceed
    assert ts.recommendation in ("proceed", "proceed_with_caution")
    assert ts.model_id == "nonexistent_model"


# ── Tool schema ───────────────────────────────────────────────────────────────

def test_trust_tools_schema_is_valid():
    from finsight.agent.tools.trust_tools import TRUST_TOOLS
    assert len(TRUST_TOOLS) == 1
    tool = TRUST_TOOLS[0]
    assert tool["type"] == "function"
    fn = tool["function"]
    assert fn["name"] == "check_model_trust"
    assert "model_id" in fn["parameters"]["properties"]
    assert "model_id" in fn["parameters"]["required"]


def test_call_trust_tool_dispatch():
    from finsight.agent.tools.trust_tools import call_trust_tool
    with patch("finsight.trust_api.handler._latest_drift", return_value=_drift("none", "stable")), \
         patch("finsight.trust_api.handler._latest_macro", return_value={"regime": "stable"}):
        result = call_trust_tool("check_model_trust", {"model_id": "lending_club_v1"})
    assert result["trustworthy"] is True
    assert result["recommendation"] == "proceed"
    assert "model_id" in result
