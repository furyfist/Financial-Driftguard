"""ADK framework configuration helpers."""

import os

ADK_GOVERNANCE_MODEL = "gemini-2.5-pro"
ADK_ANALYST_MODEL = "gemini-2.0-flash"


def get_agent_framework() -> str:
    val = os.getenv("AGENT_FRAMEWORK", "native").lower()
    if val not in ("native", "adk"):
        return "native"
    return val


def is_adk_enabled() -> bool:
    return get_agent_framework() == "adk"
