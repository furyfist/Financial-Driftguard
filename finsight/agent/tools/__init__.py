"""Agent tool implementations — thin wrappers around Phoenix, DriftGuard, macro, and trust APIs."""

from .phoenix_tools import PHOENIX_TOOLS, call_phoenix_tool
from .drift_tools import DRIFT_TOOLS, call_drift_tool
from .macro_tools import MACRO_TOOLS, call_macro_tool
from .experiment_tools import EXPERIMENT_TOOLS, call_experiment_tool
from .trust_tools import TRUST_TOOLS, call_trust_tool

ALL_TOOLS = PHOENIX_TOOLS + DRIFT_TOOLS + MACRO_TOOLS + EXPERIMENT_TOOLS + TRUST_TOOLS

__all__ = [
    "PHOENIX_TOOLS", "call_phoenix_tool",
    "DRIFT_TOOLS", "call_drift_tool",
    "MACRO_TOOLS", "call_macro_tool",
    "EXPERIMENT_TOOLS", "call_experiment_tool",
    "TRUST_TOOLS", "call_trust_tool",
    "ALL_TOOLS",
]
