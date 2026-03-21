from datetime import datetime, timezone
from typing import Optional
import numpy as np

from .snapshot import DataSnapshot
from .drift_result import DriftResult, DriftSeverity
from ..detectors.base import BaseDetector
from ..detectors.psi import PSIDetector
from ..detectors.ks_test import KSDetector
from ..detectors.js_divergence import JSDivergenceDetector


_DEFAULT_DETECTORS: list[BaseDetector] = [
    PSIDetector(),
    KSDetector(),
    JSDivergenceDetector(),
]


class Monitor:
    """
    Main entry point for DriftGuard.

    Usage:
        monitor = Monitor(model_id="lending_club_v1")
        result = monitor.check(baseline_snap, current_snap)
    """

    def __init__(
        self,
        model_id: str,
        detectors: Optional[list[BaseDetector]] = None,
        features: Optional[list[str]] = None,   # None = check all shared features
    ):
        self.model_id = model_id
        self.detectors = detectors or _DEFAULT_DETECTORS
        self.features = features

    def check(
        self,
        baseline: DataSnapshot,
        current: DataSnapshot,
    ) -> DriftResult:
        features_to_check = self._resolve_features(baseline, current)
        feature_results = []

        for feat in features_to_check:
            base_arr = baseline.get(feat)
            curr_arr = current.get(feat)

            for detector in self.detectors:
                result = detector.detect(feat, base_arr, curr_arr)
                feature_results.append(result)

        overall = self._aggregate_severity(feature_results)

        return DriftResult(
            model_id=self.model_id,
            checked_at=datetime.now(timezone.utc),
            feature_results=feature_results,
            overall_severity=overall,
        )

    def _resolve_features(
        self, baseline: DataSnapshot, current: DataSnapshot
    ) -> list[str]:
        shared = set(baseline.feature_names()) & set(current.feature_names())
        if self.features:
            missing = set(self.features) - shared
            if missing:
                raise ValueError(f"Features not found in both snapshots: {missing}")
            return self.features
        return sorted(shared)

    def _aggregate_severity(self, results) -> DriftSeverity:
        if not results:
            return DriftSeverity.NONE
        order = list(DriftSeverity)
        worst = max(results, key=lambda r: order.index(r.severity))
        return worst.severity