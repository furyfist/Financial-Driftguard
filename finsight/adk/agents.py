"""ADK LlmAgent definitions for FinSight AI multi-agent governance."""

import json
import logging
import re
from typing import Any

logger = logging.getLogger(__name__)

_ANALYST_INSTRUCTION = """\
You are the FinSight AI Analyst. Your job is to explain drift causes.
For any feature flagged at medium severity or above, call explain_feature_drift.
Call get_current_macro to provide regime context for each feature's drift.
Return a JSON object with keys: feature_analysis (list of {feature, cause, severity}),
regime_context (dict), and summary (string).
Respond ONLY with valid JSON. No markdown fences.
"""

_REPORT_INSTRUCTION = """\
You are the FinSight AI Report Writer. You generate SR 11-7 compliant prose.
You receive a JSON summary of drift analysis and must format it into a concise
governance narrative. Be factual, cite drift scores and regime directly.
Return a JSON object with keys: executive_summary (string), technical_detail (string),
recommended_action (string).
Respond ONLY with valid JSON. No markdown fences.
"""


def build_agents():
    """Build and return (governance_agent, analyst_agent, report_agent)."""
    from google.adk.agents import LlmAgent
    from finsight.adk.tools import ADK_GOVERNANCE_TOOLS, ADK_ANALYST_TOOLS, ADK_REPORT_TOOLS
    from finsight.adk.config import ADK_GOVERNANCE_MODEL, ADK_ANALYST_MODEL
    from finsight.agent.prompts.orchestrator import ORCHESTRATOR_PROMPT, RESPONSE_SCHEMA_INSTRUCTIONS

    analyst_agent = LlmAgent(
        name="analyst_agent",
        model=ADK_ANALYST_MODEL,
        instruction=_ANALYST_INSTRUCTION,
        tools=ADK_ANALYST_TOOLS,
    )

    report_agent = LlmAgent(
        name="report_agent",
        model=ADK_ANALYST_MODEL,
        instruction=_REPORT_INSTRUCTION,
        tools=ADK_REPORT_TOOLS,
    )

    governance_agent = LlmAgent(
        name="governance_agent",
        model=ADK_GOVERNANCE_MODEL,
        instruction=ORCHESTRATOR_PROMPT + "\n\n" + RESPONSE_SCHEMA_INSTRUCTIONS,
        tools=ADK_GOVERNANCE_TOOLS,
        sub_agents=[analyst_agent, report_agent],
    )

    return governance_agent, analyst_agent, report_agent


def _parse_agent_output(raw: Any) -> dict:
    """Extract JSON dict from ADK runner output regardless of wrapping."""
    text = raw.text if hasattr(raw, "text") else str(raw)
    text = text.strip()
    fence_match = re.search(r"```(?:json)?\s*([\s\S]+?)\s*```", text)
    if fence_match:
        text = fence_match.group(1).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {
            "recommendation": text,
            "action": "monitor",
            "confidence": 0.5,
            "reasoning": "ADK output could not be parsed as JSON",
            "sources": [],
        }


def run_adk_analysis(model_id: str, query: str) -> dict:
    """Run the GovernanceAgent for a model query. Returns AgentResponse-compatible dict."""
    try:
        governance_agent, _, _ = build_agents()
    except ImportError as exc:
        logger.warning("google-adk not installed: %s", exc)
        return {
            "recommendation": "ADK not available — install google-adk>=2.0.0",
            "action": "monitor",
            "confidence": 0.0,
            "reasoning": str(exc),
            "sources": [],
        }

    try:
        from google.adk.runners import InMemoryRunner
        runner = InMemoryRunner(agent=governance_agent)
        prompt = f"model_id: {model_id}\n\n{query}"
        result = runner.run(prompt)
        parsed = _parse_agent_output(result)
        parsed.setdefault("model_id", model_id)
        parsed.setdefault("framework", "adk")
        return parsed
    except Exception as exc:
        logger.warning("run_adk_analysis failed: %s", exc)
        return {
            "recommendation": f"ADK analysis failed: {exc}",
            "action": "escalate",
            "confidence": 0.0,
            "reasoning": str(exc),
            "sources": [],
            "model_id": model_id,
            "framework": "adk",
        }
