"""Proactive drift forecaster — predicts elevated drift probability from macro signals."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from statistics import mean, stdev

from .event_calendar import days_to_next_fomc

# ── Thresholds ─────────────────────────────────────────────────────────────────

_VIX_STRESS          = 25.0   # VIX above this is elevated
_VIX_CRISIS          = 40.0   # VIX above this is crisis territory
_CREDIT_SPREAD_ELEV  = 1.5    # BAA-AAA spread (%) — elevated
_CREDIT_SPREAD_WIDE  = 2.5    # BAA-AAA spread (%) — wide / stress
_YIELD_CURVE_FLAT    = 0.20   # 10Y-2Y spread approaching flat
_FOMC_WINDOW_DAYS    = 7      # boost if FOMC announcement within this many days
_FOMC_BOOST          = 0.15   # probability boost when FOMC is imminent


# ── Output dataclass ───────────────────────────────────────────────────────────

@dataclass
class DriftForecast:
    probability: float           # 0.0–1.0
    expected_regime: str         # predicted upcoming regime
    trigger_signals: list[str]   # which signals fired
    horizon_days: int            # forecast horizon (7 or 14)
    explanation: str             # human-readable summary


# ── Core forecast function ─────────────────────────────────────────────────────

def forecast_from_macro_rows(
    rows: list,             # list of MacroCache ORM rows (duck-typed)
    horizon_days: int = 14,
    as_of: date | None = None,
) -> DriftForecast:
    """
    Compute drift forecast from a sequence of MacroCache rows.

    Uses rule-based signal detection — no additional ML model required.
    Calibration: 5 stable rows → probability < 0.20; VIX spike to 50 → probability > 0.50.
    """
    if not rows:
        return DriftForecast(
            probability=0.0,
            expected_regime="unknown",
            trigger_signals=[],
            horizon_days=horizon_days,
            explanation="Insufficient macro history for forecast.",
        )

    signals: list[str] = []
    contributions: list[float] = []

    # ── Signal 1: VIX momentum ────────────────────────────────────────────────
    vix_vals = [r.vix for r in rows if r.vix is not None]
    if vix_vals:
        latest_vix = vix_vals[-1]
        if latest_vix > _VIX_CRISIS:
            signals.append("vix_crisis")
            contributions.append(0.55)
        elif len(vix_vals) >= 5:
            recent_avg = mean(vix_vals[-5:])
            hist_avg   = mean(vix_vals)
            hist_std   = stdev(vix_vals) if len(vix_vals) > 1 else 5.0
            z_score    = (recent_avg - hist_avg) / max(hist_std, 1e-6)
            if z_score > 2.0:
                signals.append("vix_momentum_2sigma")
                contributions.append(0.40)
            elif z_score > 1.0:
                signals.append("vix_momentum_1sigma")
                contributions.append(0.20)
        else:
            # Not enough history — use absolute level only
            if latest_vix > _VIX_STRESS:
                signals.append("vix_elevated")
                contributions.append(0.15)

    # ── Signal 2: yield curve ─────────────────────────────────────────────────
    yield_vals = [r.yield_curve for r in rows if r.yield_curve is not None]
    if yield_vals:
        latest_yc = yield_vals[-1]
        if latest_yc < 0:
            signals.append("yield_curve_inverted")
            contributions.append(0.30)
        elif latest_yc < _YIELD_CURVE_FLAT:
            signals.append("yield_curve_flattening")
            contributions.append(0.12)

    # ── Signal 3: credit spread ───────────────────────────────────────────────
    spread_vals = [r.credit_spread for r in rows if r.credit_spread is not None]
    if spread_vals:
        latest_spread = spread_vals[-1]
        if latest_spread > _CREDIT_SPREAD_WIDE:
            signals.append("credit_spread_wide")
            contributions.append(0.30)
        elif latest_spread > _CREDIT_SPREAD_ELEV:
            signals.append("credit_spread_elevated")
            contributions.append(0.15)

    # ── Signal 4: FOMC proximity boost ───────────────────────────────────────
    # Only boost if there's already some macro stress — don't fire on FOMC alone
    if contributions:
        days_to_fomc = days_to_next_fomc(as_of)
        if days_to_fomc is not None and days_to_fomc <= _FOMC_WINDOW_DAYS:
            signals.append(f"fomc_in_{days_to_fomc}d")
            contributions.append(_FOMC_BOOST)

    probability     = round(min(1.0, sum(contributions)), 3)
    expected_regime = _predict_regime(signals)
    actual_horizon  = 7 if probability >= 0.40 else horizon_days

    return DriftForecast(
        probability=probability,
        expected_regime=expected_regime,
        trigger_signals=signals,
        horizon_days=actual_horizon,
        explanation=_build_explanation(probability, expected_regime, signals, actual_horizon),
    )


# ── Helpers ────────────────────────────────────────────────────────────────────

def _predict_regime(signals: list[str]) -> str:
    if "vix_crisis" in signals:
        return "black_swan"
    if "yield_curve_inverted" in signals and (
        "credit_spread_wide" in signals or "credit_spread_elevated" in signals
    ):
        return "recession"
    if "credit_spread_wide" in signals or "credit_spread_elevated" in signals:
        return "credit_stress"
    if "yield_curve_inverted" in signals or "yield_curve_flattening" in signals:
        return "rate_shock"
    if any(s.startswith("vix_momentum") for s in signals):
        return "credit_stress"
    return "stable"


_SIGNAL_LABELS: dict[str, str] = {
    "vix_crisis":             "VIX in crisis territory",
    "vix_momentum_2sigma":    "VIX rising sharply (>2σ above recent mean)",
    "vix_momentum_1sigma":    "VIX elevated (>1σ above recent mean)",
    "vix_elevated":           "VIX above stress threshold",
    "yield_curve_inverted":   "yield curve inverted",
    "yield_curve_flattening": "yield curve flattening",
    "credit_spread_wide":     "credit spreads wide",
    "credit_spread_elevated": "credit spreads elevated",
}


def _build_explanation(
    probability: float,
    regime: str,
    signals: list[str],
    horizon_days: int,
) -> str:
    if not signals:
        return f"All macro signals stable — low drift probability over next {horizon_days} days."

    readable = [_SIGNAL_LABELS.get(s, s) for s in signals if not s.startswith("fomc_in_")]
    fomc_sigs = [s for s in signals if s.startswith("fomc_in_")]
    if fomc_sigs:
        readable.append("FOMC meeting imminent")

    signal_str = " and ".join(readable[:3])
    pct        = int(probability * 100)
    return (
        f"{pct}% probability of elevated drift in next {horizon_days} days. "
        f"Signals: {signal_str}. Expected regime: {regime}."
    )


# ── Class wrapper ──────────────────────────────────────────────────────────────

class DriftForecaster:
    """Thin stateless wrapper — provides `forecast_from_db()` convenience method."""

    def forecast(
        self,
        rows: list,
        horizon_days: int = 14,
        as_of: date | None = None,
    ) -> DriftForecast:
        return forecast_from_macro_rows(rows, horizon_days, as_of)

    def forecast_from_db(self, limit: int = 30, horizon_days: int = 14) -> DriftForecast:
        """Read recent MacroCache rows from the SQLite DB and compute forecast."""
        from sqlmodel import Session, select, asc
        from driftguard.store.database import engine, MacroCache

        with Session(engine) as session:
            rows = session.exec(
                select(MacroCache)
                .order_by(asc(MacroCache.fetched_at))
                .limit(limit)
            ).all()
        return forecast_from_macro_rows(rows, horizon_days)
