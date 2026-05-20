"""Business impact estimator — converts PSI score + macro regime into dollar exposure."""

from __future__ import annotations

from dataclasses import dataclass

from .historical_patterns import REGIME_CONTEXT

BASE_DEFAULT_RATE = 0.04   # 4% baseline consumer/commercial default rate
_HIGH_RANGE_FACTOR = 1.5   # uncertainty band: high = low * 1.5

# PSI threshold bands → base FNR (false negative rate) increase fraction.
# Calibrated so that PSI=0.18, credit_stress, $200M → $1.2M–$1.8M.
_PSI_BANDS: list[tuple[float, float, float]] = [
    (0.00, 0.10, 0.00),         # negligible drift — no material impact
    (0.10, 0.20, 0.10),         # moderate: +10% FNR
    (0.20, 0.25, 0.20),         # high: +20% FNR
    (0.25, float("inf"), 0.35), # critical: +35% FNR
]

# Regime multipliers applied on top of the PSI-derived base FNR increase.
_REGIME_MULTIPLIERS: dict[str, float] = {
    "stable":        1.0,
    "rate_shock":    1.2,
    "credit_stress": 1.5,
    "recession":     2.0,
    "black_swan":    4.0,
    "unknown":       1.3,
}


@dataclass
class ImpactEstimate:
    low_usd: float
    high_usd: float
    fnr_increase_pct: float  # estimated FNR increase in percentage points
    regime: str
    psi_score: float
    portfolio_size: float
    summary: str             # human-readable one-liner for the LLM prompt


def estimate_impact(
    psi_score: float,
    regime: str,
    portfolio_size: float = 200_000_000,
) -> ImpactEstimate:
    """
    Translate a PSI drift score + macro regime into estimated dollar exposure.

    Calibration check: PSI=0.18, credit_stress, $200M → $1.2M–$1.8M.
    """
    base_fnr    = _base_fnr_increase(psi_score)
    multiplier  = _REGIME_MULTIPLIERS.get(regime, 1.3)
    adjusted    = base_fnr * multiplier

    low_usd  = portfolio_size * BASE_DEFAULT_RATE * adjusted
    high_usd = low_usd * _HIGH_RANGE_FACTOR
    fnr_pct  = adjusted * 100.0

    context_note = REGIME_CONTEXT.get(regime, "")

    if low_usd < 1.0:
        summary = (
            f"No material financial impact estimated "
            f"(PSI={psi_score:.3f}, {regime} regime)."
        )
    else:
        summary = (
            f"Estimated exposure: ${low_usd / 1e6:.1f}M–${high_usd / 1e6:.1f}M "
            f"(FNR +{fnr_pct:.0f}%, PSI={psi_score:.3f}, {regime} regime). "
            f"{context_note}"
        ).strip()

    return ImpactEstimate(
        low_usd=low_usd,
        high_usd=high_usd,
        fnr_increase_pct=fnr_pct,
        regime=regime,
        psi_score=psi_score,
        portfolio_size=portfolio_size,
        summary=summary,
    )


def _base_fnr_increase(psi: float) -> float:
    for lo, hi, fnr in _PSI_BANDS:
        if lo <= psi < hi:
            return fnr
    return _PSI_BANDS[-1][2]


class ImpactEstimator:
    """Thin wrapper — stateless class for dependency injection in tests."""

    def estimate(
        self,
        psi_score: float,
        regime: str,
        portfolio_size: float = 200_000_000,
    ) -> ImpactEstimate:
        return estimate_impact(psi_score, regime, portfolio_size)
