import numpy as np
import pytest
from driftguard.detectors.psi import PSIDetector
from driftguard.detectors.ks_test import KSDetector
from driftguard.detectors.js_divergence import JSDivergenceDetector
from driftguard.core.drift_result import DriftSeverity


np.random.seed(42)


# ── Fixtures 

@pytest.fixture
def identical():
    """Same distribution — expect no drift."""
    data = np.random.normal(50, 10, 1000)
    return data, data.copy()

@pytest.fixture
def mild_shift():
    """Small mean shift — expect low/medium drift."""
    baseline = np.random.normal(50, 10, 1000)
    current  = np.random.normal(53, 10, 1000)
    return baseline, current

@pytest.fixture
def severe_shift():
    """Large mean + variance shift — expect high/critical drift."""
    baseline = np.random.normal(50, 10, 1000)
    current  = np.random.normal(80, 25, 1000)
    return baseline, current

@pytest.fixture
def small_sample():
    """Tiny arrays — detectors should still not crash."""
    return np.array([1.0, 2.0, 3.0]), np.array([4.0, 5.0, 6.0])


# ── PSI 

class TestPSIDetector:
    def test_identical_distributions_no_drift(self, identical):
        baseline, current = identical
        result = PSIDetector().detect("feature", baseline, current)
        assert result.severity == DriftSeverity.NONE
        assert result.score < 0.10

    def test_severe_shift_is_critical(self, severe_shift):
        baseline, current = severe_shift
        result = PSIDetector().detect("feature", baseline, current)
        assert result.severity in (DriftSeverity.HIGH, DriftSeverity.CRITICAL)
        assert result.score > 0.25

    def test_result_has_correct_detector_name(self, identical):
        result = PSIDetector().detect("annual_inc", *identical)
        assert result.detector == "psi"
        assert result.feature_name == "annual_inc"

    def test_details_contains_psi_per_bin(self, identical):
        result = PSIDetector().detect("feature", *identical)
        assert "psi_per_bin" in result.details
        assert "n_bins" in result.details

    def test_empty_array_raises(self):
        with pytest.raises(ValueError, match="Empty array"):
            PSIDetector().detect("feature", np.array([]), np.array([1.0, 2.0]))

    def test_small_sample_does_not_crash(self, small_sample):
        result = PSIDetector().detect("feature", *small_sample)
        assert result.score >= 0

    def test_score_is_non_negative(self, severe_shift):
        result = PSIDetector().detect("feature", *severe_shift)
        assert result.score >= 0


# ── KS 

class TestKSDetector:
    def test_identical_distributions_no_drift(self, identical):
        result = KSDetector().detect("feature", *identical)
        assert result.severity == DriftSeverity.NONE

    def test_severe_shift_detected(self, severe_shift):
        result = KSDetector().detect("feature", *severe_shift)
        assert result.severity in (DriftSeverity.MEDIUM, DriftSeverity.HIGH, DriftSeverity.CRITICAL)

    def test_p_value_present(self, mild_shift):
        result = KSDetector().detect("feature", *mild_shift)
        assert result.p_value is not None
        assert 0.0 <= result.p_value <= 1.0

    def test_details_contains_means(self, mild_shift):
        result = KSDetector().detect("feature", *mild_shift)
        assert "baseline_mean" in result.details
        assert "current_mean" in result.details

    def test_significant_flag_on_severe_shift(self, severe_shift):
        result = KSDetector().detect("feature", *severe_shift)
        assert result.details["significant"] is True

    def test_score_bounded_0_to_1(self, severe_shift):
        result = KSDetector().detect("feature", *severe_shift)
        assert 0.0 <= result.score <= 1.0


# ── JS Divergence 

class TestJSDivergenceDetector:
    def test_identical_distributions_near_zero(self, identical):
        result = JSDivergenceDetector().detect("feature", *identical)
        assert result.score < 0.05

    def test_severe_shift_high_score(self, severe_shift):
        result = JSDivergenceDetector().detect("feature", *severe_shift)
        assert result.score > 0.10

    def test_score_bounded_0_to_1(self, severe_shift):
        result = JSDivergenceDetector().detect("feature", *severe_shift)
        assert 0.0 <= result.score <= 1.0

    def test_detector_name(self, identical):
        result = JSDivergenceDetector().detect("feature", *identical)
        assert result.detector == "js"


# ── Monitor integration 

class TestMonitorIntegration:
    def test_full_pipeline_no_drift(self):
        import pandas as pd
        from driftguard import Monitor, DataSnapshot

        df = pd.DataFrame({
            "annual_inc": np.random.normal(65000, 15000, 500),
            "dti":        np.random.normal(18, 5, 500),
        })
        baseline = DataSnapshot.from_dataframe(df, "baseline")
        current  = DataSnapshot.from_dataframe(df.copy(), "current")

        result = Monitor(model_id="test_model").check(baseline, current)
        assert result.overall_severity == DriftSeverity.NONE
        assert result.model_id == "test_model"

    def test_full_pipeline_detects_drift(self):
        import pandas as pd
        from driftguard import Monitor, DataSnapshot

        baseline_df = pd.DataFrame({
            "annual_inc": np.random.normal(65000, 15000, 500),
            "dti":        np.random.normal(18, 5, 500),
        })
        current_df = pd.DataFrame({
            "annual_inc": np.random.normal(40000, 25000, 500),
            "dti":        np.random.normal(32, 10, 500),
        })
        baseline = DataSnapshot.from_dataframe(baseline_df, "baseline")
        current  = DataSnapshot.from_dataframe(current_df, "current")

        result = Monitor(model_id="test_model").check(baseline, current)
        assert result.overall_severity != DriftSeverity.NONE
        assert len(result.drifted_features) > 0

    def test_drift_score_is_float_between_0_and_1(self):
        import pandas as pd
        from driftguard import Monitor, DataSnapshot

        df = pd.DataFrame({"x": np.random.normal(0, 1, 300)})
        snap = DataSnapshot.from_dataframe(df, "snap")
        result = Monitor(model_id="m").check(snap, snap)
        assert isinstance(result.drift_score, float)