"""ADK stub — google-adk removed. Native Groq agent is used instead."""


def run_adk_analysis(model_id: str, query: str) -> dict:
    return {
        "recommendation": "ADK not available — using native Groq agent",
        "action": "monitor",
        "confidence": 0.0,
        "reasoning": "google-adk not installed",
        "sources": [],
        "model_id": model_id,
    }
