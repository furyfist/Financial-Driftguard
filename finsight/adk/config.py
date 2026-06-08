"""ADK framework configuration — reads all ADK-related env vars in one place."""

import os
from dataclasses import dataclass, field


@dataclass
class ADKConfig:
    agent_framework: str
    google_genai_api_key: str
    reasoning_model: str
    fast_model: str

    @classmethod
    def from_env(cls) -> "ADKConfig":
        framework = os.getenv("AGENT_FRAMEWORK", "native").lower()
        if framework not in ("native", "adk"):
            framework = "native"

        api_key = os.getenv("GOOGLE_GENAI_API_KEY", "") or os.getenv("GEMINI_API_KEY", "")
        if framework == "adk" and not api_key:
            raise EnvironmentError(
                "AGENT_FRAMEWORK=adk requires GOOGLE_GENAI_API_KEY or GEMINI_API_KEY to be set"
            )

        return cls(
            agent_framework=framework,
            google_genai_api_key=api_key,
            reasoning_model=os.getenv("LLM_REASONING_MODEL", "gemini-2.5-pro"),
            fast_model=os.getenv("LLM_FAST_MODEL", "gemini-2.0-flash"),
        )

    @property
    def is_adk(self) -> bool:
        return self.agent_framework == "adk"


def get_agent_framework() -> str:
    val = os.getenv("AGENT_FRAMEWORK", "native").lower()
    return val if val in ("native", "adk") else "native"


def is_adk_enabled() -> bool:
    return get_agent_framework() == "adk"


ADK_GOVERNANCE_MODEL = os.getenv("LLM_REASONING_MODEL", "gemini-2.5-pro")
ADK_ANALYST_MODEL = os.getenv("LLM_FAST_MODEL", "gemini-2.0-flash")
