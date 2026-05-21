"""Trust API tool — lets the governance agent and external MCP clients check model trustworthiness."""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


# ── Tool function ──────────────────────────────────────────────────────────────

def check_model_trust(model_id: str, context: str = "") -> dict:
    """
    Score whether a model is currently trustworthy for automated use.
    Returns a TrustScore dict. Never raises — returns an error key on failure.
    """
    try:
        from finsight.trust_api import TrustHandler
        ts = TrustHandler().score(model_id=model_id, context=context)
        return {
            "model_id": ts.model_id,
            "trustworthy": ts.trustworthy,
            "confidence": ts.confidence,
            "regime": ts.regime,
            "drift_severity": ts.drift_severity,
            "recommendation": ts.recommendation,
            "reason": ts.reason,
            "last_checked": ts.last_checked.isoformat(),
            "next_check_recommended": ts.next_check_recommended.isoformat(),
        }
    except Exception as exc:
        logger.error("check_model_trust failed for %s: %s", model_id, exc)
        return {"error": str(exc), "model_id": model_id}


# ── OpenAI-compatible tool schema ──────────────────────────────────────────────

TRUST_TOOLS: list[dict] = [
    {
        "type": "function",
        "function": {
            "name": "check_model_trust",
            "description": (
                "Check whether a financial ML model is currently trustworthy for automated use. "
                "Returns a trust score with recommendation: proceed, proceed_with_caution, "
                "escalate, or halt. Always call this before using a model for consequential decisions."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "model_id": {
                        "type": "string",
                        "description": "The model ID to evaluate trustworthiness for.",
                    },
                    "context": {
                        "type": "string",
                        "description": (
                            "Optional: describe what you intend to do with this model "
                            "(e.g. 'credit scoring for $50K personal loans'). "
                            "Used to tailor the reason string."
                        ),
                    },
                },
                "required": ["model_id"],
            },
        },
    },
]

_DISPATCH: dict[str, Any] = {
    "check_model_trust": check_model_trust,
}


def call_trust_tool(name: str, arguments: dict) -> Any:
    fn = _DISPATCH.get(name)
    if fn is None:
        raise ValueError(f"Unknown trust tool: {name!r}. Valid: {list(_DISPATCH)}")
    return fn(**arguments)
