"""Tests for champion-challenger automation (Step 7)."""

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from finsight.challenger import ChallengerResult, ChallengerRunner
from finsight.challenger.runner import (
    TRIGGER_REGIMES,
    TRIGGER_SEVERITIES,
    STABLE_SEVERITIES,
    _determine_winner,
    _extract_drifted_features,
    _build_recommendation,
)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _drift_run(
    run_id: int = 1,
    model_id: str = "lending_club_v1",
    regime: str = "stable",
    severity: str = "high",
    drift_score: float = 0.35,
    feature_results_json: str = "[]",
) -> MagicMock:
    r = MagicMock()
    r.id                   = run_id
    r.model_id             = model_id
    r.regime               = regime
    r.overall_severity     = severity
    r.drift_score          = drift_score
    r.feature_results_json = feature_results_json
    return r


# ── Trigger guard tests ───────────────────────────────────────────────────────

@patch("finsight.challenger.runner._load_latest_run")
def test_wrong_regime_not_stable_returns_wrong_regime(mock_load):
    """credit_stress or black_swan → must NOT trigger, drift is macro-driven."""
    for regime in ("credit_stress", "black_swan", "rate_shock", "recession", "unknown"):
        mock_load.return_value = _drift_run(regime=regime, severity="high")
        result = ChallengerRunner().run("lending_club_v1")
        assert result.status == "wrong_regime", f"Expected wrong_regime for {regime!r}"
        assert result.winner == "inconclusive"


@patch("finsight.challenger.runner._load_latest_run")
def test_stable_regime_passes_regime_guard(mock_load):
    """stable regime + high severity must proceed past the regime guard."""
    mock_load.return_value = _drift_run(regime="stable", severity="high")
    # The runner will try to load a challenger next; we don't mock it so it'll
    # hit DB or return no_baseline — either way, status is NOT wrong_regime.
    with patch("finsight.challenger.runner._load_last_stable_run", return_value=None):
        result = ChallengerRunner().run("lending_club_v1")
    assert result.status != "wrong_regime"


@patch("finsight.challenger.runner._load_latest_run")
def test_wrong_severity_low_returns_wrong_severity(mock_load):
    """Severity 'low' or 'none' with stable regime → no comparison needed."""
    for sev in ("none", "low"):
        mock_load.return_value = _drift_run(regime="stable", severity=sev)
        result = ChallengerRunner().run("lending_club_v1")
        assert result.status == "wrong_severity", f"Expected wrong_severity for {sev!r}"


@patch("finsight.challenger.runner._load_latest_run")
def test_high_and_critical_severity_pass_guard(mock_load):
    """High and critical drift must pass the severity guard."""
    for sev in ("high", "critical"):
        mock_load.return_value = _drift_run(regime="stable", severity=sev)
        with patch("finsight.challenger.runner._load_last_stable_run", return_value=None):
            result = ChallengerRunner().run("lending_club_v1")
        assert result.status != "wrong_severity", f"Expected to pass guard for {sev!r}"


# ── No data cases ─────────────────────────────────────────────────────────────

@patch("finsight.challenger.runner._load_latest_run", return_value=None)
def test_no_drift_runs_returns_insufficient_data(_mock):
    result = ChallengerRunner().run("lending_club_v1")
    assert result.status == "insufficient_data"


@patch("finsight.challenger.runner._load_latest_run")
@patch("finsight.challenger.runner._load_last_stable_run", return_value=None)
def test_no_challenger_baseline_returns_no_baseline(mock_stable, mock_latest):
    mock_latest.return_value = _drift_run(regime="stable", severity="high")
    result = ChallengerRunner().run("lending_club_v1")
    assert result.status == "no_baseline"
    assert result.winner == "no_baseline"


# ── Comparison logic ──────────────────────────────────────────────────────────

@patch("finsight.challenger.runner._load_latest_run")
@patch("finsight.challenger.runner._load_last_stable_run")
def test_high_delta_picks_challenger_better(mock_stable, mock_latest):
    """Champion score 0.55 vs challenger 0.10 — Δ=0.45 → challenger_better."""
    mock_latest.return_value  = _drift_run(run_id=10, regime="stable", severity="high", drift_score=0.55)
    mock_stable.return_value  = _drift_run(run_id=3,  regime="stable", severity="low",  drift_score=0.10)
    result = ChallengerRunner().run("lending_club_v1")
    assert result.status == "completed"
    assert result.winner == "challenger_better"
    assert result.drift_score_delta == pytest.approx(0.45, abs=1e-4)


@patch("finsight.challenger.runner._load_latest_run")
@patch("finsight.challenger.runner._load_last_stable_run")
def test_similar_scores_inconclusive(mock_stable, mock_latest):
    """Champion 0.22 vs challenger 0.21 — Δ=0.01 (< noise threshold) → inconclusive."""
    mock_latest.return_value = _drift_run(run_id=10, regime="stable", severity="high", drift_score=0.22)
    mock_stable.return_value = _drift_run(run_id=3,  regime="stable", severity="low",  drift_score=0.21)
    result = ChallengerRunner().run("lending_club_v1")
    assert result.status == "completed"
    assert result.winner == "inconclusive"


@patch("finsight.challenger.runner._load_latest_run")
@patch("finsight.challenger.runner._load_last_stable_run")
def test_champion_better_than_challenger(mock_stable, mock_latest):
    """Champion outperforms challenger (rare) → champion_better."""
    mock_latest.return_value = _drift_run(run_id=10, regime="stable", severity="high", drift_score=0.05)
    mock_stable.return_value = _drift_run(run_id=3,  regime="stable", severity="low",  drift_score=0.20)
    result = ChallengerRunner().run("lending_club_v1")
    assert result.status == "completed"
    assert result.winner == "champion_better"


@patch("finsight.challenger.runner._load_latest_run")
@patch("finsight.challenger.runner._load_last_stable_run")
def test_result_populates_scores(mock_stable, mock_latest):
    """Completed result must carry both drift scores."""
    mock_latest.return_value = _drift_run(run_id=10, regime="stable", severity="critical", drift_score=0.62)
    mock_stable.return_value = _drift_run(run_id=3,  regime="stable", severity="none",    drift_score=0.08)
    result = ChallengerRunner().run("lending_club_v1")
    assert result.champion_drift_score   == pytest.approx(0.62)
    assert result.challenger_drift_score == pytest.approx(0.08)
    assert result.champion_run_id        == 10
    assert result.challenger_run_id      == 3


# ── Feature extraction ────────────────────────────────────────────────────────

def test_extract_drifted_features_parses_json():
    import json
    features = json.dumps([
        {"feature_name": "int_rate",      "severity": "high"},
        {"feature_name": "dti",           "severity": "medium"},
        {"feature_name": "annual_inc",    "severity": "low"},   # excluded
        {"feature_name": "credit_score",  "severity": "critical"},
    ])
    result = _extract_drifted_features(features)
    assert "int_rate"     in result
    assert "dti"          in result
    assert "credit_score" in result
    assert "annual_inc"   not in result


def test_extract_drifted_features_handles_bad_json():
    result = _extract_drifted_features("{broken")
    assert result == []


# ── _determine_winner thresholds ──────────────────────────────────────────────

def test_winner_challenger_at_significant_delta():
    assert _determine_winner(0.11) == "challenger_better"   # strictly above 0.10 threshold
    assert _determine_winner(0.50) == "challenger_better"


def test_winner_inconclusive_in_noise_band():
    assert _determine_winner(0.00) == "inconclusive"
    assert _determine_winner(0.01) == "inconclusive"


def test_winner_champion_when_negative_delta():
    assert _determine_winner(-0.05) == "champion_better"


# ── Recommendation string ─────────────────────────────────────────────────────

def test_recommendation_mentions_scores():
    rec = _build_recommendation("challenger_better", 0.55, 0.10, 0.45, [])
    assert "0.55" in rec or "0.550" in rec
    assert "0.10" in rec or "0.100" in rec


def test_recommendation_mentions_features():
    rec = _build_recommendation("challenger_better", 0.55, 0.10, 0.45, ["int_rate", "dti"])
    assert "int_rate" in rec


# ── Constants ─────────────────────────────────────────────────────────────────

def test_trigger_regimes_contains_only_stable():
    assert TRIGGER_REGIMES == {"stable"}


def test_trigger_severities():
    assert "high"     in TRIGGER_SEVERITIES
    assert "critical" in TRIGGER_SEVERITIES
    assert "low"      not in TRIGGER_SEVERITIES
    assert "none"     not in TRIGGER_SEVERITIES


def test_stable_severities():
    assert "none" in STABLE_SEVERITIES
    assert "low"  in STABLE_SEVERITIES
    assert "high" not in STABLE_SEVERITIES
