"""ADK FunctionTool wrappers around existing FinSight tool dispatch functions."""

import logging

from finsight.agent.tools.drift_tools import call_drift_tool
from finsight.agent.tools.macro_tools import call_macro_tool
from finsight.agent.tools.phoenix_tools import call_phoenix_tool
from finsight.agent.tools.trust_tools import call_trust_tool

logger = logging.getLogger(__name__)


def _make_adk_tool(name: str, description: str, call_fn, schema_params: dict):
    """Build a google.adk FunctionTool wrapping call_fn(**kwargs)."""
    from google.adk.tools import FunctionTool

    def _wrapper(**kwargs):
        return call_fn(**kwargs)

    _wrapper.__name__ = name
    _wrapper.__doc__ = description
    return FunctionTool(func=_wrapper)


try:
    def adk_get_latest_drift(**kwargs):
        return call_drift_tool("get_latest_drift", kwargs)

    def adk_get_model_history(**kwargs):
        return call_drift_tool("get_model_history", kwargs)

    def adk_explain_feature_drift(**kwargs):
        return call_drift_tool("explain_feature_drift", kwargs)

    def adk_get_current_macro(**kwargs):
        return call_macro_tool("get_current_macro", kwargs)

    def adk_list_traces(**kwargs):
        return call_phoenix_tool("list_recent_drift_traces", kwargs)

    def adk_get_trust_score(**kwargs):
        return call_trust_tool("check_model_trust", kwargs)

    from google.adk.tools import FunctionTool

    ADK_GOVERNANCE_TOOLS = [
        FunctionTool(func=adk_get_latest_drift),
        FunctionTool(func=adk_get_model_history),
        FunctionTool(func=adk_explain_feature_drift),
        FunctionTool(func=adk_get_current_macro),
        FunctionTool(func=adk_list_traces),
        FunctionTool(func=adk_get_trust_score),
    ]

    ADK_ANALYST_TOOLS = [
        FunctionTool(func=adk_get_latest_drift),
        FunctionTool(func=adk_explain_feature_drift),
    ]

except ImportError:
    logger.warning(
        "google-adk is not installed — ADK_GOVERNANCE_TOOLS and ADK_ANALYST_TOOLS "
        "will be empty. Install google-adk to enable ADK multi-agent mode."
    )
    ADK_GOVERNANCE_TOOLS = []
    ADK_ANALYST_TOOLS = []
