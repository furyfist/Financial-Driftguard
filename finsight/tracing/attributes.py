"""Custom OpenInference span attribute constants for the FinSight AI financial domain."""

# OpenInference span kind values (set on openinference.span.kind)
SPAN_KIND_CHAIN = "CHAIN"
SPAN_KIND_TOOL = "TOOL"
SPAN_KIND_LLM = "LLM"

# Span kind key — OpenInference standard
OTEL_SPAN_KIND = "openinference.span.kind"

# Model
MODEL_ID = "model.id"

# Drift (shared across detector + check spans)
DRIFT_SCORE = "drift.score"
DRIFT_SEVERITY = "drift.severity"
DRIFT_FEATURE = "drift.feature_name"
DRIFT_THRESHOLD = "drift.threshold"
DRIFT_DETECTOR_COUNT = "drift.detector_count"
DRIFT_FEATURE_RESULTS_COUNT = "drift.feature_results_count"

# Detector
DETECTOR_NAME = "drift.detector_name"

# Regime
REGIME_CLASS = "regime.class"
REGIME_CONFIDENCE = "regime.confidence"
REGIME_SIGNALS = "regime.signals_fired"

# Macro signals
MACRO_VIX = "macro.vix"
MACRO_SPREAD = "macro.credit_spread"
MACRO_FED_FUNDS = "macro.fed_funds_rate"
MACRO_YIELD_CURVE = "macro.yield_curve"
MACRO_UNEMPLOYMENT = "macro.unemployment_rate"
