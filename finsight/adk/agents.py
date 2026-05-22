"""ADK LlmAgent definitions for FinSight AI multi-agent governance."""

import logging

logger = logging.getLogger(__name__)


def build_agents():
    """Build and return (governance_agent, analyst_agent, report_agent) ADK agents."""
    from google.adk.agents import LlmAgent
    from finsight.adk.tools import ADK_GOVERNANCE_TOOLS, ADK_ANALYST_TOOLS
    from finsight.adk.config import ADK_GOVERNANCE_MODEL, ADK_ANALYST_MODEL
    from finsight.agent.prompts.orchestrator import ORCHESTRATOR_PROMPT

    analyst_agent = LlmAgent(
        name="analyst_agent",
        model=ADK_ANALYST_MODEL,
        instruction=(
            "You explain drift causes using macro context and feature domain knowledge. "
            "Use explain_feature_drift for any feature flagged at medium severity or above."
        ),
        tools=ADK_ANALYST_TOOLS,
    )

    report_agent = LlmAgent(
        name="report_agent",
        model=ADK_ANALYST_MODEL,
        instruction=(
            "You generate SR 11-7 compliant report section prose. "
            "Be concise, cite drift scores and regime directly."
        ),
        tools=[],
    )

    governance_agent = LlmAgent(
        name="governance_agent",
        model=ADK_GOVERNANCE_MODEL,
        instruction=ORCHESTRATOR_PROMPT,
        tools=ADK_GOVERNANCE_TOOLS,
        sub_agents=[analyst_agent, report_agent],
    )

    return governance_agent, analyst_agent, report_agent


def run_adk_analysis(model_id: str, query: str) -> str:
    """Run the ADK governance agent for a given model query. Never raises."""
    try:
        governance_agent, _, _ = build_agents()
    except ImportError:
        return "ADK not available"

    try:
        from google.adk.runners import InMemoryRunner
        runner = InMemoryRunner(agent=governance_agent)
        result = runner.run(query)
        if hasattr(result, "text"):
            return result.text
        return str(result)
    except Exception as exc:
        logger.warning("run_adk_analysis failed: %s", exc)
        return str(exc)
