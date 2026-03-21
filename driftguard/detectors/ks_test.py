import numpy as np
from scipy import stats
from .base import BaseDetector


class KSDetector(BaseDetector):
    """
    Kolmogorov-Smirnov two-sample test.
    Catches distributional shape changes PSI can miss.
    Good for skewed financial features (income, loan_amnt).

    Score = KS statistic (max distance between CDFs), range [0, 1].
    p_value < 0.05 → distributions are significantly different.
    """

    name = "ks"
    THRESHOLD_LOW = 0.05
    THRESHOLD_MEDIUM = 0.10
    THRESHOLD_HIGH = 0.15

    def compute(
        self,
        baseline: np.ndarray,
        current: np.ndarray,
    ) -> tuple[float, dict]:
        ks_stat, p_value = stats.ks_2samp(baseline, current)

        return float(ks_stat), {
            "p_value": float(p_value),
            "significant": bool(p_value < 0.05),
            "baseline_mean": float(np.mean(baseline)),
            "current_mean": float(np.mean(current)),
            "baseline_std": float(np.std(baseline)),
            "current_std": float(np.std(current)),
        }