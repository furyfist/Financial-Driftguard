"""Tests for the business impact estimator (Step 5)."""

import pytest

from finsight.impact import estimate_impact, ImpactEstimate, ImpactEstimator
from finsight.impact.estimator import BASE_DEFAULT_RATE, _base_fnr_increase


# ── Calibration ───────────────────────────────────────────────────────────────

def test_demo_scenario_low():
    """Canonical check: PSI=0.18, credit_stress, $200M → low=$1.2M."""
    est = estimate_impact(psi_score=0.18, regime="credit_stress", portfolio_size=200_000_000)
    assert est.low_usd == pytest.approx(1_200_000, rel=1e-6)


def test_demo_scenario_high():
    """Canonical check: PSI=0.18, credit_stress, $200M → high=$1.8M."""
    est = estimate_impact(psi_score=0.18, regime="credit_stress", portfolio_size=200_000_000)
    assert est.high_usd == pytest.approx(1_800_000, rel=1e-6)


def test_demo_scenario_fnr_pct():
    """PSI=0.18, credit_stress → FNR increase = 15%."""
    est = estimate_impact(psi_score=0.18, regime="credit_stress", portfolio_size=200_000_000)
    assert est.fnr_increase_pct == pytest.approx(15.0, rel=1e-6)


# ── No-drift case ─────────────────────────────────────────────────────────────

def test_no_drift_zero_impact():
    est = estimate_impact(psi_score=0.05, regime="stable")
    assert est.low_usd == 0.0
    assert est.high_usd == 0.0


def test_no_drift_summary_says_no_material():
    est = estimate_impact(psi_score=0.05, regime="stable")
    assert "No material" in est.summary


# ── Regime ordering ───────────────────────────────────────────────────────────

def test_black_swan_is_4x_stable():
    """Black swan multiplier (4.0) vs stable (1.0) — dollar impact must be exactly 4×."""
    psi = 0.30
    portfolio = 100_000_000
    est_bs  = estimate_impact(psi, "black_swan",  portfolio)
    est_stb = estimate_impact(psi, "stable",      portfolio)
    assert est_bs.low_usd == pytest.approx(est_stb.low_usd * 4.0, rel=1e-6)


def test_recession_higher_than_stable():
    est_rec = estimate_impact(0.25, "recession")
    est_stb = estimate_impact(0.25, "stable")
    assert est_rec.low_usd > est_stb.low_usd


def test_credit_stress_higher_than_rate_shock():
    est_cs = estimate_impact(0.15, "credit_stress")
    est_rs = estimate_impact(0.15, "rate_shock")
    assert est_cs.low_usd > est_rs.low_usd


# ── PSI bands ─────────────────────────────────────────────────────────────────

def test_psi_bands_increase_monotonically():
    regimes = "stable"
    scores = [0.05, 0.12, 0.22, 0.30]
    impacts = [estimate_impact(s, regimes).low_usd for s in scores]
    assert impacts == sorted(impacts)


def test_psi_boundary_exactly_at_0_10_is_moderate():
    """PSI=0.10 is the first point of the moderate band."""
    assert _base_fnr_increase(0.10) == pytest.approx(0.10)


def test_psi_just_below_0_10_is_negligible():
    assert _base_fnr_increase(0.099) == pytest.approx(0.00)


# ── Summary string ────────────────────────────────────────────────────────────

def test_summary_contains_regime():
    est = estimate_impact(0.22, "rate_shock", 50_000_000)
    assert "rate_shock" in est.summary


def test_summary_contains_psi():
    est = estimate_impact(0.22, "rate_shock", 50_000_000)
    assert "PSI=" in est.summary


def test_summary_contains_dollar_range():
    est = estimate_impact(0.18, "credit_stress", 200_000_000)
    assert "$1.2M" in est.summary
    assert "$1.8M" in est.summary


def test_summary_contains_fnr():
    est = estimate_impact(0.18, "credit_stress", 200_000_000)
    assert "FNR" in est.summary


# ── ImpactEstimate dataclass ──────────────────────────────────────────────────

def test_impact_estimate_stores_inputs():
    est = estimate_impact(0.18, "credit_stress", 200_000_000)
    assert est.psi_score  == pytest.approx(0.18)
    assert est.regime     == "credit_stress"
    assert est.portfolio_size == 200_000_000


# ── ImpactEstimator class wrapper ─────────────────────────────────────────────

def test_impact_estimator_wrapper_matches_function():
    estimator = ImpactEstimator()
    result_cls = estimator.estimate(0.18, "credit_stress", 200_000_000)
    result_fn  = estimate_impact(0.18, "credit_stress", 200_000_000)
    assert result_cls.low_usd  == result_fn.low_usd
    assert result_cls.high_usd == result_fn.high_usd
    assert result_cls.summary  == result_fn.summary


# ── Unknown regime fallback ───────────────────────────────────────────────────

def test_unknown_regime_uses_conservative_multiplier():
    est_unk = estimate_impact(0.20, "unknown")
    est_stb = estimate_impact(0.20, "stable")
    # unknown (1.3×) should be above stable (1.0×)
    assert est_unk.low_usd > est_stb.low_usd


def test_unrecognised_regime_string_falls_back_gracefully():
    est = estimate_impact(0.15, "martian_crisis")
    # Should not raise; should use the 1.3 fallback
    assert est.low_usd > 0.0
