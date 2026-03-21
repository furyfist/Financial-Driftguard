import numpy as np
from .base import BaseDetector


class PSIDetector(BaseDetector):
    """
    Population Stability Index.
    Industry standard for credit model monitoring.

    PSI < 0.10  → no significant drift
    PSI 0.10–0.25 → moderate drift, investigate
    PSI > 0.25  → significant drift, action required
    """

    name = "psi"
    THRESHOLD_LOW = 0.10
    THRESHOLD_MEDIUM = 0.20
    THRESHOLD_HIGH = 0.25

    def __init__(self, n_bins: int = 10, epsilon: float = 1e-6):
        self.n_bins = n_bins
        self.epsilon = epsilon  # prevents log(0)

    def compute(
        self,
        baseline: np.ndarray,
        current: np.ndarray,
    ) -> tuple[float, dict]:
        # Bin edges defined on baseline — this is intentional.
        # Current data is bucketed using *baseline* boundaries.
        bin_edges = np.percentile(baseline, np.linspace(0, 100, self.n_bins + 1))
        bin_edges = np.unique(bin_edges)  # handle duplicates in low-variance features

        baseline_counts, _ = np.histogram(baseline, bins=bin_edges)
        current_counts, _ = np.histogram(current, bins=bin_edges)

        # Convert to proportions, guard against empty bins
        baseline_pct = (baseline_counts / len(baseline)) + self.epsilon
        current_pct = (current_counts / len(current)) + self.epsilon

        psi_per_bin = (current_pct - baseline_pct) * np.log(current_pct / baseline_pct)
        psi_total = float(np.sum(psi_per_bin))

        return psi_total, {
            "n_bins": len(bin_edges) - 1,
            "psi_per_bin": psi_per_bin.tolist(),
            "baseline_size": len(baseline),
            "current_size": len(current),
        }