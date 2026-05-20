"""Tests for the Phoenix tracing layer — verifies spans, attributes, and graceful degradation."""

from unittest.mock import MagicMock, patch

import pytest
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

# ── One in-memory tracer shared across all tests in this module ───────────────

_EXPORTER = InMemorySpanExporter()
_PROVIDER = TracerProvider()
_PROVIDER.add_span_processor(SimpleSpanProcessor(_EXPORTER))
trace.set_tracer_provider(_PROVIDER)


@pytest.fixture(autouse=True)
def clear_spans():
    _EXPORTER.clear()
    yield
    _EXPORTER.clear()


def _finished(name: str):
    """Return finished spans matching the given span name."""
    return [s for s in _EXPORTER.get_finished_spans() if s.name == name]


# ── traced_drift_check ────────────────────────────────────────────────────────

def test_traced_drift_check_creates_span():
    from finsight.tracing.decorators import traced_drift_check
    from driftguard.core.drift_result import DriftSeverity

    mock_self = MagicMock()
    mock_self.model_id = "lending_club_v1"
    mock_self.detectors = [MagicMock(), MagicMock(), MagicMock()]

    mock_result = MagicMock()
    mock_result.overall_severity = DriftSeverity.LOW
    mock_result.feature_results = [MagicMock(), MagicMock()]
    mock_result.regime = "stable"

    def fake_check(self, baseline, current, macro=None):
        return mock_result

    traced = traced_drift_check(fake_check)
    result = traced(mock_self, None, None)

    assert result is mock_result
    spans = _finished("drift_check")
    assert len(spans) == 1
    attrs = spans[0].attributes
    assert attrs["model.id"] == "lending_club_v1"
    assert attrs["drift.detector_count"] == 3
    assert attrs["drift.severity"] == "low"
    assert attrs["drift.feature_results_count"] == 2
    assert attrs["regime.class"] == "stable"
    assert attrs["openinference.span.kind"] == "CHAIN"


def test_traced_drift_check_no_regime_attribute_when_regime_is_none():
    from finsight.tracing.decorators import traced_drift_check
    from driftguard.core.drift_result import DriftSeverity

    mock_self = MagicMock()
    mock_self.model_id = "model_x"
    mock_self.detectors = []

    mock_result = MagicMock()
    mock_result.overall_severity = DriftSeverity.NONE
    mock_result.feature_results = []
    mock_result.regime = None

    traced = traced_drift_check(lambda self, b, c, macro=None: mock_result)
    traced(mock_self, None, None)

    spans = _finished("drift_check")
    assert "regime.class" not in spans[0].attributes


def test_traced_drift_check_records_error_on_exception():
    from finsight.tracing.decorators import traced_drift_check

    mock_self = MagicMock()
    mock_self.model_id = "bad_model"
    mock_self.detectors = []

    def exploding_check(self, b, c, macro=None):
        raise RuntimeError("compute failed")

    traced = traced_drift_check(exploding_check)
    with pytest.raises(RuntimeError, match="compute failed"):
        traced(mock_self, None, None)

    spans = _finished("drift_check")
    assert len(spans) == 1
    from opentelemetry.trace import StatusCode
    assert spans[0].status.status_code == StatusCode.ERROR


# ── traced_regime_tag ─────────────────────────────────────────────────────────

def test_traced_regime_tag_creates_span():
    from finsight.tracing.decorators import traced_regime_tag
    from driftguard.regime.tagger import Regime

    mock_self = MagicMock()
    mock_assessment = MagicMock()
    mock_assessment.regime = Regime.CREDIT_STRESS
    mock_assessment.confidence = 0.82
    mock_assessment.signals_fired = ["vix_stress", "credit_spread_stress"]

    def fake_tag(self, drift_result, macro):
        return mock_assessment

    traced = traced_regime_tag(fake_tag)
    result = traced(mock_self, MagicMock(), MagicMock())

    assert result is mock_assessment
    spans = _finished("regime_tag")
    assert len(spans) == 1
    attrs = spans[0].attributes
    assert attrs["regime.class"] == "credit_stress"
    assert attrs["regime.confidence"] == pytest.approx(0.82)
    assert "vix_stress" in attrs["regime.signals_fired"]
    assert attrs["openinference.span.kind"] == "CHAIN"


# ── traced_detector ───────────────────────────────────────────────────────────

def test_traced_detector_creates_span():
    from finsight.tracing.decorators import traced_detector
    from driftguard.core.drift_result import DriftSeverity

    mock_self = MagicMock()
    mock_self.name = "psi"

    mock_result = MagicMock()
    mock_result.score = 0.18
    mock_result.severity = DriftSeverity.MEDIUM
    mock_result.threshold = 0.2

    def fake_detect(self, feature_name, baseline, current):
        return mock_result

    traced = traced_detector(fake_detect)
    result = traced(mock_self, "int_rate", None, None)

    assert result is mock_result
    spans = _finished("detector_run")
    assert len(spans) == 1
    attrs = spans[0].attributes
    assert attrs["drift.detector_name"] == "psi"
    assert attrs["drift.feature_name"] == "int_rate"
    assert attrs["drift.score"] == pytest.approx(0.18)
    assert attrs["drift.severity"] == "medium"
    assert attrs["drift.threshold"] == pytest.approx(0.2)
    assert attrs["openinference.span.kind"] == "CHAIN"


# ── traced_macro_fetch ────────────────────────────────────────────────────────

def test_traced_macro_fetch_creates_span_with_signals():
    from finsight.tracing.decorators import traced_macro_fetch
    from datetime import date

    mock_self = MagicMock()
    mock_snapshot = MagicMock()
    mock_snapshot.vix = 28.5
    mock_snapshot.credit_spread = 1.8
    mock_snapshot.fed_funds_rate = 5.33
    mock_snapshot.yield_curve = -0.4
    mock_snapshot.unemployment_rate = 3.9

    def fake_fetch(self, as_of=None):
        return mock_snapshot

    traced = traced_macro_fetch(fake_fetch)
    result = traced(mock_self, date.today())

    assert result is mock_snapshot
    spans = _finished("macro_fetch")
    assert len(spans) == 1
    attrs = spans[0].attributes
    assert attrs["macro.vix"] == pytest.approx(28.5)
    assert attrs["macro.credit_spread"] == pytest.approx(1.8)
    assert attrs["macro.fed_funds_rate"] == pytest.approx(5.33)
    assert attrs["macro.yield_curve"] == pytest.approx(-0.4)
    assert attrs["macro.unemployment_rate"] == pytest.approx(3.9)
    assert attrs["openinference.span.kind"] == "TOOL"


def test_traced_macro_fetch_skips_none_signals():
    from finsight.tracing.decorators import traced_macro_fetch

    mock_self = MagicMock()
    mock_snapshot = MagicMock()
    mock_snapshot.vix = 18.0
    mock_snapshot.credit_spread = None   # unavailable
    mock_snapshot.fed_funds_rate = None
    mock_snapshot.yield_curve = None
    mock_snapshot.unemployment_rate = None

    traced = traced_macro_fetch(lambda self, as_of=None: mock_snapshot)
    traced(mock_self)

    spans = _finished("macro_fetch")
    attrs = spans[0].attributes
    assert attrs["macro.vix"] == pytest.approx(18.0)
    assert "macro.credit_spread" not in attrs
    assert "macro.fed_funds_rate" not in attrs


# ── init_tracing graceful degradation ─────────────────────────────────────────

def test_init_tracing_returns_false_when_phoenix_unreachable():
    from finsight import tracing
    import finsight.tracing.setup as setup_mod

    # Reset the initialized flag so init_tracing actually runs
    original_flag = setup_mod._TRACING_INITIALIZED
    setup_mod._TRACING_INITIALIZED = False

    try:
        with patch.dict("sys.modules", {"phoenix": None, "phoenix.otel": None}):
            result = tracing.init_tracing("test-project")
        assert result is False
    finally:
        setup_mod._TRACING_INITIALIZED = original_flag
