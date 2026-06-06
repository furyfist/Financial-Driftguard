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

# ADK agent spans
ADK_AGENT_NAME = "adk.agent_name"
ADK_TOOL_NAME = "adk.tool_name"
ADK_TOOL_INPUT = "adk.tool_input"
ADK_TOOL_OUTPUT = "adk.tool_output"
ADK_AGENT_ACTION = "adk.recommended_action"
ADK_AGENT_CONFIDENCE = "adk.confidence"
ADK_REQUIRES_APPROVAL = "adk.requires_approval"
ADK_APPROVAL_ID = "adk.approval_id"
ADK_SELF_EVAL_ACCURACY = "adk.self_eval_accuracy"
ADK_CONFIDENCE_ADJUSTED = "adk.confidence_adjusted"
