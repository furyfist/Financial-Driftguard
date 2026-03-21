import numpy as np
from scipy.spatial.distance import jensenshannon
from .base import BaseDetector


class JSDivergenceDetector(BaseDetector):
    """
    Jensen-Shannon Divergence — symmetric, bounded [0, 1].
    Better than KL divergence for comparing distributions with
    non-overlapping support (common after regime shifts).

    Score = JS distance (square root of JS divergence).
    """

    name = "js"
    THRESHOLD_LOW = 0.05
    THRESHOLD_MEDIUM = 0.10
    THRESHOLD_HIGH = 0.20

    def __init__(self, n_bins: int = 50):
        self.n_bins = n_bins

    def compute(
        self,
        baseline: np.ndarray,
        current: np.ndarray,
    ) -> tuple[float, dict]:
        # Shared bin edges across both arrays for fair comparison
        combined_min = min(baseline.min(), current.min())
        combined_max = max(baseline.max(), current.max())
        bin_edges = np.linspace(combined_min, combined_max, self.n_bins + 1)

        baseline_hist, _ = np.histogram(baseline, bins=bin_edges, density=True)
        current_hist, _ = np.histogram(current, bins=bin_edges, density=True)

        # jensenshannon returns the *distance* (sqrt of divergence), range [0, 1]
        js_dist = float(jensenshannon(baseline_hist + 1e-9, current_hist + 1e-9))

        return js_dist, {
            "n_bins": self.n_bins,
            "baseline_size": len(baseline),
            "current_size": len(current),
        }