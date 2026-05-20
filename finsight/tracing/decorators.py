"""Tracing decorators — wrap DriftGuard methods without touching their source files."""

import functools
import logging

from opentelemetry import trace
from opentelemetry.trace import StatusCode

from .attributes import (
    OTEL_SPAN_KIND,
    SPAN_KIND_CHAIN,
    SPAN_KIND_TOOL,
    MODEL_ID,
    DRIFT_SCORE,
    DRIFT_SEVERITY,
    DRIFT_FEATURE,
    DRIFT_THRESHOLD,
    DRIFT_DETECTOR_COUNT,
    DRIFT_FEATURE_RESULTS_COUNT,
    DETECTOR_NAME,
    REGIME_CLASS,
    REGIME_CONFIDENCE,
    REGIME_SIGNALS,
    MACRO_VIX,
    MACRO_SPREAD,
    MACRO_FED_FUNDS,
    MACRO_YIELD_CURVE,
    MACRO_UNEMPLOYMENT,
)

logger = logging.getLogger(__name__)

_TRACER_NAME = "finsight.driftguard"


def traced_drift_check(func):
    """Traces Monitor.check() — CHAIN span with model_id, severity, regime, feature count."""
    @functools.wraps(func)
    def wrapper(self, baseline, current, macro=None):
        tracer = trace.get_tracer(_TRACER_NAME)
        with tracer.start_as_current_span("drift_check") as span:
            span.set_attribute(OTEL_SPAN_KIND, SPAN_KIND_CHAIN)
            span.set_attribute(MODEL_ID, self.model_id)
            span.set_attribute(DRIFT_DETECTOR_COUNT, len(self.detectors))
            try:
                result = func(self, baseline, current, macro)
                span.set_attribute(DRIFT_SEVERITY, result.overall_severity.value)
                span.set_attribute(DRIFT_FEATURE_RESULTS_COUNT, len(result.feature_results))
                if result.regime:
                    span.set_attribute(REGIME_CLASS, result.regime)
                return result
            except Exception as e:
                span.record_exception(e)
                span.set_status(StatusCode.ERROR, str(e))
                raise
    return wrapper


def traced_regime_tag(func):
    """Traces RegimeTagger.tag() — CHAIN span with regime class, confidence, signals fired."""
    @functools.wraps(func)
    def wrapper(self, drift_result, macro):
        tracer = trace.get_tracer(_TRACER_NAME)
        with tracer.start_as_current_span("regime_tag") as span:
            span.set_attribute(OTEL_SPAN_KIND, SPAN_KIND_CHAIN)
            try:
                assessment = func(self, drift_result, macro)
                span.set_attribute(REGIME_CLASS, assessment.regime.value)
                span.set_attribute(REGIME_CONFIDENCE, assessment.confidence)
                span.set_attribute(REGIME_SIGNALS, str(assessment.signals_fired))
                return assessment
            except Exception as e:
                span.record_exception(e)
                span.set_status(StatusCode.ERROR, str(e))
                raise
    return wrapper


def traced_detector(func):
    """Traces BaseDetector.detect() — CHAIN span with detector name, feature, score, severity."""
    @functools.wraps(func)
    def wrapper(self, feature_name, baseline, current):
        tracer = trace.get_tracer(_TRACER_NAME)
        with tracer.start_as_current_span("detector_run") as span:
            span.set_attribute(OTEL_SPAN_KIND, SPAN_KIND_CHAIN)
            span.set_attribute(DETECTOR_NAME, self.name)
            span.set_attribute(DRIFT_FEATURE, feature_name)
            try:
                result = func(self, feature_name, baseline, current)
                span.set_attribute(DRIFT_SCORE, result.score)
                span.set_attribute(DRIFT_SEVERITY, result.severity.value)
                span.set_attribute(DRIFT_THRESHOLD, result.threshold)
                return result
            except Exception as e:
                span.record_exception(e)
                span.set_status(StatusCode.ERROR, str(e))
                raise
    return wrapper


def traced_macro_fetch(func):
    """Traces MacroSignalFetcher.fetch() — TOOL span with live macro signal values."""
    @functools.wraps(func)
    def wrapper(self, as_of=None):
        tracer = trace.get_tracer(_TRACER_NAME)
        with tracer.start_as_current_span("macro_fetch") as span:
            span.set_attribute(OTEL_SPAN_KIND, SPAN_KIND_TOOL)
            try:
                snapshot = func(self, as_of)
                if snapshot.vix is not None:
                    span.set_attribute(MACRO_VIX, snapshot.vix)
                if snapshot.credit_spread is not None:
                    span.set_attribute(MACRO_SPREAD, snapshot.credit_spread)
                if snapshot.fed_funds_rate is not None:
                    span.set_attribute(MACRO_FED_FUNDS, snapshot.fed_funds_rate)
                if snapshot.yield_curve is not None:
                    span.set_attribute(MACRO_YIELD_CURVE, snapshot.yield_curve)
                if snapshot.unemployment_rate is not None:
                    span.set_attribute(MACRO_UNEMPLOYMENT, snapshot.unemployment_rate)
                return snapshot
            except Exception as e:
                span.record_exception(e)
                span.set_status(StatusCode.ERROR, str(e))
                raise
    return wrapper
