from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


class DriftSeverity(str, Enum):
    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class FeatureDriftResult:
    feature_name: str
    detector: str          # "psi", "ks", "js"
    score: float
    threshold: float
    severity: DriftSeverity
    p_value: Optional[float] = None   # where the test produces one
    details: dict = field(default_factory=dict)

    @property
    def is_drifted(self) -> bool:
        return self.severity != DriftSeverity.NONE


@dataclass
class DriftResult:
    model_id: str
    checked_at: datetime
    feature_results: list[FeatureDriftResult]
    overall_severity: DriftSeverity
    regime: Optional[str] = None      # filled in by RegimeTagger later
    notes: str = ""

    @property
    def drifted_features(self) -> list[FeatureDriftResult]:
        return [f for f in self.feature_results if f.is_drifted]

    @property
    def unique_drifted_features(self) -> list[FeatureDriftResult]:
        """One entry per feature name — keeps the highest-score entry per feature."""
        best: dict[str, FeatureDriftResult] = {}
        for f in self.drifted_features:
            if f.feature_name not in best or f.score > best[f.feature_name].score:
                best[f.feature_name] = f
        return list(best.values())

    @property
    def drift_score(self) -> float:
        """Normalised 0-1 score across all features."""
        if not self.feature_results:
            return 0.0
        return round(
            sum(f.score for f in self.feature_results) / len(self.feature_results), 4
        )