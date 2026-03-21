from abc import ABC, abstractmethod
import numpy as np
from ..core.drift_result import DriftSeverity, FeatureDriftResult


class BaseDetector(ABC):
    """
    All drift detectors implement this interface.
    Subclasses define their own score computation and thresholds.
    """

    name: str = "base"

    # Override these in subclasses to tune sensitivity
    THRESHOLD_LOW: float = 0.1
    THRESHOLD_MEDIUM: float = 0.2
    THRESHOLD_HIGH: float = 0.25

    def detect(
        self,
        feature_name: str,
        baseline: np.ndarray,
        current: np.ndarray,
    ) -> FeatureDriftResult:
        """
        Public entry point. Validates inputs, calls compute(), maps to severity.
        """
        baseline = np.asarray(baseline, dtype=float)
        current = np.asarray(current, dtype=float)

        if baseline.size == 0 or current.size == 0:
            raise ValueError(f"Empty array passed for feature '{feature_name}'")

        score, details = self.compute(baseline, current)
        severity = self._score_to_severity(score)

        return FeatureDriftResult(
            feature_name=feature_name,
            detector=self.name,
            score=round(score, 6),
            threshold=self.THRESHOLD_MEDIUM,
            severity=severity,
            p_value=details.get("p_value"),
            details=details,
        )

    @abstractmethod
    def compute(
        self,
        baseline: np.ndarray,
        current: np.ndarray,
    ) -> tuple[float, dict]:
        """
        Compute the drift score between baseline and current distributions.
        Returns: (score, details_dict)
        Score is always >= 0. Higher = more drift.
        """
        ...

    def _score_to_severity(self, score: float) -> DriftSeverity:
        if score < self.THRESHOLD_LOW:
            return DriftSeverity.NONE
        elif score < self.THRESHOLD_MEDIUM:
            return DriftSeverity.LOW
        elif score < self.THRESHOLD_HIGH:
            return DriftSeverity.MEDIUM
        elif score < self.THRESHOLD_HIGH * 2:
            return DriftSeverity.HIGH
        else:
            return DriftSeverity.CRITICAL