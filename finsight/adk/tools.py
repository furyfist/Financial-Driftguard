"""ADK FunctionTool wrappers around existing FinSight tool dispatch functions."""

import logging

from finsight.agent.tools.drift_tools import call_drift_tool
from finsight.agent.tools.macro_tools import call_macro_tool
from finsight.agent.tools.phoenix_tools import call_phoenix_tool
from finsight.agent.tools.trust_tools import call_trust_tool

logger = logging.getLogger(__name__)


def adk_get_latest_drift(model_id: str) -> dict:
    """Return the latest drift run result for a model, including per-feature scores."""
    return call_drift_tool("get_latest_drift", {"model_id": model_id})


def adk_get_model_history(model_id: str, limit: int = 10) -> dict:
    """Return the last N drift runs for a model as a time-series summary."""
    return call_drift_tool("get_model_history", {"model_id": model_id, "limit": limit})


def adk_explain_feature_drift(model_id: str, feature_name: str) -> dict:
    """Explain why a specific feature is drifting based on its distribution shift."""
    return call_drift_tool("explain_feature_drift", {"model_id": model_id, "feature_name": feature_name})


def adk_get_current_macro(model_id: str = "") -> dict:
    """Fetch current macro signals: VIX, credit spread, fed funds rate, yield curve."""
    return call_macro_tool("get_current_macro", {"model_id": model_id})


def adk_list_traces(model_id: str = "", limit: int = 20) -> dict:
    """List recent Phoenix traces for drift analysis runs."""
    return call_phoenix_tool("list_recent_drift_traces", {"model_id": model_id, "limit": limit})


def adk_get_trust_score(model_id: str) -> dict:
    """Return the current trust score and trust components for a model."""
    return call_trust_tool("check_model_trust", {"model_id": model_id})


def adk_evaluate_past_recommendations(model_id: str, window_days: int = 30) -> dict:
    """Evaluate accuracy of past agent recommendations via LLM-as-Judge using Phoenix traces."""
    try:
        from finsight.agent.tools.self_eval_tools import evaluate_past_recommendations
        return evaluate_past_recommendations(model_id=model_id, window_days=window_days)
    except Exception as exc:
        logger.warning("self-eval unavailable: %s", exc)
        return {"error": str(exc), "accuracies": {}, "adjustments": []}


try:
    from google.adk.tools import FunctionTool

    ADK_GOVERNANCE_TOOLS = [
        FunctionTool(func=adk_get_latest_drift),
        FunctionTool(func=adk_get_model_history),
        FunctionTool(func=adk_explain_feature_drift),
        FunctionTool(func=adk_get_current_macro),
        FunctionTool(func=adk_list_traces),
        FunctionTool(func=adk_get_trust_score),
        FunctionTool(func=adk_evaluate_past_recommendations),
    ]

    ADK_ANALYST_TOOLS = [
        FunctionTool(func=adk_get_latest_drift),
        FunctionTool(func=adk_explain_feature_drift),
        FunctionTool(func=adk_get_current_macro),
    ]

    ADK_REPORT_TOOLS = [
        FunctionTool(func=adk_get_latest_drift),
        FunctionTool(func=adk_get_trust_score),
    ]

except ImportError:
    logger.warning(
        "google-adk not installed — ADK tool lists will be empty. "
        "Install google-adk>=2.0.0 to enable ADK multi-agent mode."
    )
    ADK_GOVERNANCE_TOOLS = []
    ADK_ANALYST_TOOLS = []
    ADK_REPORT_TOOLS = []
