# driftguard/regime/tagger.py
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
import logging

from .macro_signals import MacroSnapshot
from ..core.drift_result import DriftResult, DriftSeverity

logger = logging.getLogger(__name__)

_MODEL_PATH = Path("demo/data/regime_classifier.pkl")


class Regime(str, Enum):
    STABLE        = "stable"
    RATE_SHOCK    = "rate_shock"
    RECESSION     = "recession"
    CREDIT_STRESS = "credit_stress"
    BLACK_SWAN    = "black_swan"
    UNKNOWN       = "unknown"


@dataclass
class RegimeAssessment:
    regime: Regime
    confidence: float
    signals_fired: list[str]
    recommendation: str
    probabilities: dict = field(default_factory=dict)


class RegimeTagger:
    """
    V2: ML classifier primary, rule-based fallback.
    Backwards compatible with V1 API — tag() signature unchanged.
    """

    def __init__(self, use_classifier: bool = True):
        self._classifier = None
        if use_classifier and _MODEL_PATH.exists():
            try:
                from .classifier import RegimeClassifier
                self._classifier = RegimeClassifier.load(_MODEL_PATH)
                logger.info("RegimeTagger: using ML classifier (v2)")
            except Exception as e:
                logger.warning(f"Failed to load classifier, falling back to rules: {e}")
        else:
            logger.info("RegimeTagger: using rule-based fallback (v1)")

    def tag(
        self,
        drift_result: DriftResult,
        macro: MacroSnapshot,
    ) -> RegimeAssessment:
        if not macro.is_complete():
            return self._partial_assessment(macro)
        if self._classifier is not None:
            return self._ml_assessment(drift_result, macro)
        return self._rule_assessment(drift_result, macro)

    def _ml_assessment(
        self,
        drift_result: DriftResult,
        macro: MacroSnapshot,
    ) -> RegimeAssessment:
        regime_str, confidence, proba = self._classifier.predict(macro)
        regime = Regime(regime_str)
        return RegimeAssessment(
            regime=regime,
            confidence=confidence,
            signals_fired=[],
            recommendation=self._recommend(regime, drift_result),
            probabilities=proba,
        )

    def _rule_assessment(
        self,
        drift_result: DriftResult,
        macro: MacroSnapshot,
    ) -> RegimeAssessment:
        """V1 rule-based logic — kept as fallback when classifier unavailable."""
        _VIX_STRESS      = 25.0
        _VIX_CRISIS      = 40.0
        _SPREAD_STRESS   = 1.50
        _SPREAD_CRISIS   = 3.00
        _UNEMP_RISING    = 6.0
        _YIELD_INVERTED  = 0.0

        fired = []
        if macro.vix and macro.vix > _VIX_CRISIS:
            fired.append("vix_crisis")
        elif macro.vix and macro.vix > _VIX_STRESS:
            fired.append("vix_stress")
        if macro.credit_spread and macro.credit_spread > _SPREAD_CRISIS:
            fired.append("credit_spread_crisis")
        elif macro.credit_spread and macro.credit_spread > _SPREAD_STRESS:
            fired.append("credit_spread_stress")
        if macro.yield_curve is not None and macro.yield_curve < _YIELD_INVERTED:
            fired.append("yield_curve_inverted")
        if macro.unemployment_rate and macro.unemployment_rate > _UNEMP_RISING:
            fired.append("unemployment_elevated")
        if macro.credit_spread and macro.credit_spread > _SPREAD_STRESS:
            fired.append("credit_conditions_tightening")

        crisis = {"vix_crisis", "credit_spread_crisis"}
        if crisis.issubset(set(fired)):
            regime = Regime.BLACK_SWAN
        elif "unemployment_elevated" in fired and "yield_curve_inverted" in fired:
            regime = Regime.RECESSION
        elif "credit_conditions_tightening" in fired or "credit_spread_stress" in fired:
            if macro.vix and macro.vix > _VIX_STRESS:
                regime = Regime.RATE_SHOCK
            else:
                regime = Regime.CREDIT_STRESS
        elif "vix_stress" in fired:
            regime = Regime.CREDIT_STRESS
        else:
            regime = Regime.STABLE

        max_signals = 6
        base = min(len(fired) / max_signals, 1.0)
        if macro.vix and macro.vix > _VIX_STRESS:
            base = min(base + 0.15, 1.0)
        confidence = round(base, 2)

        return RegimeAssessment(
            regime=regime,
            confidence=confidence,
            signals_fired=fired,
            recommendation=self._recommend(regime, drift_result),
        )

    def _recommend(self, regime: Regime, drift: DriftResult) -> str:
        is_drifted = drift.overall_severity in (
            DriftSeverity.HIGH, DriftSeverity.CRITICAL
        )
        if regime == Regime.STABLE and is_drifted:
            return (
                "Drift detected in a stable macro environment — "
                "likely model decay. Investigate feature pipeline and retrain."
            )
        if regime in (Regime.RATE_SHOCK, Regime.CREDIT_STRESS) and is_drifted:
            return (
                "Drift consistent with macro regime shift. "
                "Model is correctly uncertain. Monitor closely but avoid "
                "retraining on regime data — wait for stabilisation."
            )
        if regime == Regime.RECESSION and is_drifted:
            return (
                "Recession regime detected. Credit default rates will shift "
                "structurally. Consider threshold adjustment and champion-challenger."
            )
        if regime == Regime.BLACK_SWAN:
            return (
                "Extreme market stress. Freeze automated decisions. "
                "Human review required. Do not retrain during crisis."
            )
        if not is_drifted:
            return "No significant drift. Model performing within expected bounds."
        return "Insufficient signal to distinguish regime change from model decay."

    def _partial_assessment(self, macro: MacroSnapshot) -> RegimeAssessment:
        """Handles incomplete macro snapshots — VIX only or missing fields."""
        fired  = []
        regime = Regime.UNKNOWN
        if macro.vix:
            if macro.vix > 40:
                fired.append("vix_crisis")
                regime = Regime.BLACK_SWAN
            elif macro.vix > 25:
                fired.append("vix_stress")
                regime = Regime.CREDIT_STRESS
        return RegimeAssessment(
            regime=regime,
            confidence=0.3 if fired else 0.0,
            signals_fired=fired,
            recommendation="Partial macro data — get FRED API key for full assessment.",
        )