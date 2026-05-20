"""Tests for the proactive drift forecaster (Step 6)."""

from datetime import date
from unittest.mock import MagicMock

import pytest

from finsight.forecast import DriftForecast, DriftForecaster, forecast_from_macro_rows
from finsight.forecast.event_calendar import days_to_next_fomc, FOMC_DATES


# ── Helpers ───────────────────────────────────────────────────────────────────

def _row(vix=None, credit_spread=None, yield_curve=None):
    row = MagicMock()
    row.vix           = vix
    row.credit_spread = credit_spread
    row.yield_curve   = yield_curve
    return row


# ── Stable / no-signal cases ─────────────────────────────────────────────────

def test_stable_macro_low_probability():
    rows = [_row(vix=14.0, credit_spread=0.8, yield_curve=0.5) for _ in range(10)]
    result = forecast_from_macro_rows(rows)
    assert result.probability < 0.20
    assert result.expected_regime == "stable"
    assert result.trigger_signals == []


def test_empty_rows_unknown_regime():
    result = forecast_from_macro_rows([])
    assert result.probability == 0.0
    assert result.expected_regime == "unknown"
    assert result.trigger_signals == []


def test_rows_with_no_macro_data_gives_low_probability():
    rows = [_row() for _ in range(5)]  # all None fields
    result = forecast_from_macro_rows(rows)
    assert result.probability == 0.0


# ── VIX momentum ─────────────────────────────────────────────────────────────

def test_vix_2sigma_spike_elevates_probability():
    """
    Spike from baseline 14 → 28 must fire the 2σ signal.
    Needs ~50 stable rows so the spike rows don't pull up historical mean/std enough
    to keep z below 2.0.
    """
    baseline = [_row(vix=14.0) for _ in range(50)]
    spike    = [_row(vix=28.0) for _ in range(5)]
    result   = forecast_from_macro_rows(baseline + spike)
    assert result.probability >= 0.35
    assert "vix_momentum_2sigma" in result.trigger_signals


def test_vix_1sigma_spike_moderate():
    """Moderate VIX rise → 1σ signal, lower contribution than 2σ."""
    baseline = [_row(vix=14.0) for _ in range(20)]
    spike    = [_row(vix=22.0) for _ in range(5)]
    result   = forecast_from_macro_rows(baseline + spike)
    assert 0.10 <= result.probability < 0.40
    assert "vix_momentum_1sigma" in result.trigger_signals


def test_vix_crisis_produces_black_swan_regime():
    rows   = [_row(vix=50.0) for _ in range(5)]
    result = forecast_from_macro_rows(rows)
    assert result.expected_regime == "black_swan"
    assert "vix_crisis" in result.trigger_signals
    assert result.probability >= 0.50


def test_vix_crisis_dominates_other_signals():
    """Even with stable credit/yield, VIX crisis → black_swan."""
    rows   = [_row(vix=55.0, credit_spread=0.5, yield_curve=0.5) for _ in range(5)]
    result = forecast_from_macro_rows(rows)
    assert result.expected_regime == "black_swan"


# ── Yield curve ───────────────────────────────────────────────────────────────

def test_inverted_yield_curve_fires_signal():
    rows   = [_row(vix=16.0, yield_curve=-0.15, credit_spread=0.9) for _ in range(5)]
    result = forecast_from_macro_rows(rows)
    assert "yield_curve_inverted" in result.trigger_signals
    assert result.probability >= 0.25


def test_inverted_yield_curve_predicts_rate_shock():
    rows   = [_row(vix=16.0, yield_curve=-0.20) for _ in range(5)]
    result = forecast_from_macro_rows(rows)
    assert result.expected_regime == "rate_shock"


def test_flattening_yield_curve_moderate_signal():
    rows   = [_row(vix=16.0, yield_curve=0.10) for _ in range(5)]
    result = forecast_from_macro_rows(rows)
    assert "yield_curve_flattening" in result.trigger_signals


# ── Credit spread ─────────────────────────────────────────────────────────────

def test_wide_credit_spread_triggers_credit_stress():
    rows   = [_row(vix=20.0, credit_spread=2.8, yield_curve=0.3) for _ in range(5)]
    result = forecast_from_macro_rows(rows)
    assert "credit_spread_wide" in result.trigger_signals
    assert result.expected_regime == "credit_stress"
    assert result.probability >= 0.25


def test_elevated_credit_spread_moderate_signal():
    rows   = [_row(vix=18.0, credit_spread=1.8, yield_curve=0.4) for _ in range(5)]
    result = forecast_from_macro_rows(rows)
    assert "credit_spread_elevated" in result.trigger_signals


# ── Regime classification ─────────────────────────────────────────────────────

def test_inverted_curve_plus_wide_spread_predicts_recession():
    rows   = [_row(vix=25.0, credit_spread=3.0, yield_curve=-0.2) for _ in range(5)]
    result = forecast_from_macro_rows(rows)
    assert result.expected_regime == "recession"


# ── Horizon selection ─────────────────────────────────────────────────────────

def test_high_probability_uses_7d_horizon():
    """Probability ≥ 0.40 → 7-day horizon (more urgent)."""
    rows   = [_row(vix=50.0, credit_spread=4.0, yield_curve=-0.5) for _ in range(5)]
    result = forecast_from_macro_rows(rows)
    assert result.horizon_days == 7


def test_low_probability_uses_14d_horizon():
    rows   = [_row(vix=13.0, credit_spread=0.7, yield_curve=0.5) for _ in range(10)]
    result = forecast_from_macro_rows(rows)
    assert result.horizon_days == 14


# ── Combined / edge cases ─────────────────────────────────────────────────────

def test_probability_capped_at_1():
    rows   = [_row(vix=55.0, credit_spread=4.0, yield_curve=-0.5) for _ in range(10)]
    result = forecast_from_macro_rows(rows)
    assert result.probability <= 1.0


def test_probability_is_rounded_to_3dp():
    rows   = [_row(vix=14.0) for _ in range(10)]
    result = forecast_from_macro_rows(rows)
    assert result.probability == round(result.probability, 3)


# ── Explanation string ────────────────────────────────────────────────────────

def test_explanation_contains_percentage():
    rows   = [_row(vix=28.0, credit_spread=2.0, yield_curve=0.1) for _ in range(10)]
    result = forecast_from_macro_rows(rows)
    assert "%" in result.explanation


def test_stable_explanation_mentions_stable():
    rows   = [_row(vix=13.0) for _ in range(10)]
    result = forecast_from_macro_rows(rows)
    assert "stable" in result.explanation.lower()


def test_explanation_contains_expected_regime():
    rows   = [_row(vix=28.0, credit_spread=2.8, yield_curve=0.2) for _ in range(5)]
    result = forecast_from_macro_rows(rows)
    assert result.expected_regime in result.explanation


# ── DriftForecast dataclass ───────────────────────────────────────────────────

def test_forecast_dataclass_fields():
    rows   = [_row(vix=25.0, credit_spread=1.8, yield_curve=0.1) for _ in range(5)]
    result = forecast_from_macro_rows(rows)
    assert isinstance(result, DriftForecast)
    assert 0.0 <= result.probability <= 1.0
    assert isinstance(result.trigger_signals, list)
    assert isinstance(result.explanation, str)
    assert result.horizon_days in (7, 14)


# ── DriftForecaster class wrapper ─────────────────────────────────────────────

def test_forecaster_wrapper_matches_function():
    rows       = [_row(vix=25.0, credit_spread=2.0, yield_curve=-0.1) for _ in range(5)]
    forecaster = DriftForecaster()
    r_cls      = forecaster.forecast(rows)
    r_fn       = forecast_from_macro_rows(rows)
    assert r_cls.probability      == r_fn.probability
    assert r_cls.expected_regime  == r_fn.expected_regime
    assert r_cls.trigger_signals  == r_fn.trigger_signals


# ── Event calendar ────────────────────────────────────────────────────────────

def test_days_to_next_fomc_positive_for_past_date():
    """A date well before the first FOMC entry should return a positive count."""
    days = days_to_next_fomc(as_of=date(2025, 1, 1))
    assert days is not None
    assert days >= 0


def test_days_to_next_fomc_zero_on_meeting_day():
    """On a meeting day itself, days_to_next_fomc should return 0."""
    meeting = FOMC_DATES[0]
    days = days_to_next_fomc(as_of=meeting)
    assert days == 0


def test_days_to_next_fomc_none_after_last_date():
    days = days_to_next_fomc(as_of=date(2030, 1, 1))
    assert days is None


def test_fomc_dates_are_sorted():
    assert FOMC_DATES == sorted(FOMC_DATES)
