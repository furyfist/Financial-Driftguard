"""FinSight AI governance agent — orchestrates tool calls and produces regime-aware recommendations."""

import json
import logging
import re
from dataclasses import dataclass, field

from finsight.llm import get_llm, LLMResponse
from finsight.agent.prompts.orchestrator import ORCHESTRATOR_PROMPT, RESPONSE_SCHEMA_INSTRUCTIONS
from finsight.agent.tools.phoenix_tools import PHOENIX_TOOLS, call_phoenix_tool
from finsight.agent.tools.drift_tools import DRIFT_TOOLS, call_drift_tool
from finsight.agent.tools.macro_tools import MACRO_TOOLS, call_macro_tool
from finsight.agent.tools.experiment_tools import EXPERIMENT_TOOLS, call_experiment_tool
from finsight.agent.tools.trust_tools import TRUST_TOOLS, call_trust_tool

logger = logging.getLogger(__name__)

# Every LLM call uses low temperature — governance decisions must be deterministic
_TEMPERATURE = 0.2
MAX_TOOL_ITERATIONS = 8

ALL_TOOLS = PHOENIX_TOOLS + DRIFT_TOOLS + MACRO_TOOLS + EXPERIMENT_TOOLS + TRUST_TOOLS

_PHOENIX_NAMES    = {t["function"]["name"] for t in PHOENIX_TOOLS}
_DRIFT_NAMES      = {t["function"]["name"] for t in DRIFT_TOOLS}
_MACRO_NAMES      = {t["function"]["name"] for t in MACRO_TOOLS}
_EXPERIMENT_NAMES = {t["function"]["name"] for t in EXPERIMENT_TOOLS}
_TRUST_NAMES      = {t["function"]["name"] for t in TRUST_TOOLS}

VALID_ACTIONS = frozenset({
    "monitor", "investigate", "retrain", "freeze", "champion_challenger", "escalate",
})


@dataclass
class AgentResponse:
    recommendation: str
    action: str
    confidence: float
    reasoning: str
    sources: list[str] = field(default_factory=list)
    model_id: str | None = None
    regime: str | None = None


class DriftGuardAgent:
    """
    Regime-aware governance agent.

    Usage:
        agent = DriftGuardAgent()
        result = agent.analyze(model_id="lending_club_v1")
        # result.action → "monitor" | "investigate" | "retrain" | "freeze" | ...
    """

    def __init__(self) -> None:
        self._llm = get_llm(role="reasoning")

    # ── Public API ─────────────────────────────────────────────────────────────

    def analyze(self, model_id: str) -> AgentResponse:
        """
        Autonomous drift analysis for a model.
        Calls tools in sequence per the orchestrator prompt's reasoning process,
        then returns a structured recommendation.
        """
        impact_hint = _get_impact_hint(model_id)
        content = (
            f"Perform a complete drift governance analysis for model '{model_id}'. "
            "Follow the reasoning process: call get_current_macro first to establish "
            "the regime, then get_latest_drift for the severity and score, then "
            "get_feature_breakdown if severity is medium or above. "
            "Return your structured JSON recommendation."
        )
        if impact_hint:
            content += f"\n\nBUSINESS IMPACT PRE-CALCULATION: {impact_hint}"

        messages = [
            {"role": "system", "content": _system_prompt()},
            {"role": "user", "content": content},
        ]
        response = self._run_tool_loop(messages)
        result = _parse_response(response.content)
        result.model_id = model_id
        return result

    def ask(
        self,
        query: str,
        model_id: str | None = None,
        memory=None,  # ConversationMemory | None
    ) -> AgentResponse:
        """
        Conversational interface for the risk officer chat endpoint.
        Optionally uses ConversationMemory for multi-turn context.
        """
        system = _system_prompt()

        if memory is not None:
            memory.add_user(query)
            messages = memory.get_messages(system)
        else:
            messages = [
                {"role": "system", "content": system},
                {"role": "user", "content": query},
            ]

        if model_id:
            messages[-1] = dict(messages[-1])  # don't mutate the memory's list
            messages[-1]["content"] = f"[Model: {model_id}]\n{messages[-1]['content']}"

        response = self._run_tool_loop(messages)
        result = _parse_response(response.content)
        result.model_id = model_id

        if memory is not None:
            memory.add_assistant(response.content)

        return result

    # ── Core loop ──────────────────────────────────────────────────────────────

    def _run_tool_loop(self, messages: list[dict]) -> LLMResponse:
        """
        Agentic tool-calling loop.
        Runs until the LLM stops calling tools or MAX_TOOL_ITERATIONS is hit.
        """
        for iteration in range(MAX_TOOL_ITERATIONS):
            response = self._llm.complete(
                messages, tools=ALL_TOOLS, temperature=_TEMPERATURE
            )

            if not response.tool_calls:
                return response

            # Append assistant turn with the tool calls it requested
            messages = messages + [
                {
                    "role": "assistant",
                    "content": response.content or "",
                    "tool_calls": [
                        {
                            "id": f"call_{iteration}_{i}",
                            "type": "function",
                            "function": {
                                "name": tc.name,
                                "arguments": json.dumps(tc.arguments),
                            },
                        }
                        for i, tc in enumerate(response.tool_calls)
                    ],
                }
            ]

            # Execute each tool and append its result
            for i, tc in enumerate(response.tool_calls):
                tool_id = f"call_{iteration}_{i}"
                try:
                    result = _dispatch_tool_call(tc.name, tc.arguments)
                    logger.debug("Tool %s(%s) → %s", tc.name, tc.arguments, str(result)[:120])
                except Exception as exc:
                    result = {"error": str(exc)}
                    logger.warning("Tool %s failed: %s", tc.name, exc)

                messages = messages + [
                    {
                        "role": "tool",
                        "tool_call_id": tool_id,
                        "content": json.dumps(result, default=str),
                    }
                ]

        # Iteration cap hit — force a conclusion with the data gathered so far
        logger.warning("Max tool iterations (%d) reached — forcing conclusion", MAX_TOOL_ITERATIONS)
        messages = messages + [
            {
                "role": "user",
                "content": (
                    "You have gathered sufficient data. "
                    "Now provide your final JSON recommendation."
                ),
            }
        ]
        return self._llm.complete(messages, temperature=_TEMPERATURE)


# ── Module-level helpers ───────────────────────────────────────────────────────

def _system_prompt() -> str:
    return ORCHESTRATOR_PROMPT + "\n\n" + RESPONSE_SCHEMA_INSTRUCTIONS


def _dispatch_tool_call(name: str, arguments: dict) -> object:
    """Route a tool call by name to the correct handler across all tool sets."""
    if name in _PHOENIX_NAMES:
        return call_phoenix_tool(name, arguments)
    if name in _DRIFT_NAMES:
        return call_drift_tool(name, arguments)
    if name in _MACRO_NAMES:
        return call_macro_tool(name, arguments)
    if name in _EXPERIMENT_NAMES:
        return call_experiment_tool(name, arguments)
    if name in _TRUST_NAMES:
        return call_trust_tool(name, arguments)
    logger.warning("Unknown tool called: %r", name)
    return {"error": f"Unknown tool: {name!r}"}


def _get_impact_hint(model_id: str) -> str:
    """
    Pre-compute a business impact estimate from the latest drift run + current macro.
    Returns a one-line summary string to inject into the analyze() prompt, or "" on failure.
    Failures are silently swallowed — impact hint is best-effort.
    """
    try:
        from finsight.impact import estimate_impact
        from finsight.agent.tools.drift_tools import get_latest_drift
        from finsight.agent.tools.macro_tools import get_current_macro

        drift = get_latest_drift(model_id)
        macro = get_current_macro()

        psi    = drift.get("drift_score") if drift else None
        regime = (macro.get("regime") if macro else None) or "unknown"

        if psi is None:
            return ""

        return estimate_impact(psi_score=float(psi), regime=str(regime)).summary
    except Exception:
        return ""


def _parse_response(content: str) -> AgentResponse:
    """
    Extract and validate the JSON recommendation from LLM output.
    Handles markdown code fences. Falls back to action=escalate on any parse failure.
    """
    # Strip markdown code fences if present
    cleaned = re.sub(r"```(?:json)?\s*", "", content)
    cleaned = re.sub(r"```", "", cleaned).strip()

    match = re.search(r"\{.*\}", cleaned, re.DOTALL)
    if not match:
        logger.error("No JSON found in agent response: %.300s", content)
        return AgentResponse(
            recommendation="Agent produced an unparseable response — escalating for human review.",
            action="escalate",
            confidence=0.0,
            reasoning=content,
        )

    try:
        data = json.loads(match.group())
    except json.JSONDecodeError as exc:
        logger.error("JSON decode failed (%s): %.300s", exc, match.group())
        return AgentResponse(
            recommendation="Agent produced malformed JSON — escalating for human review.",
            action="escalate",
            confidence=0.0,
            reasoning=content,
        )

    action = data.get("action", "escalate")
    if action not in VALID_ACTIONS:
        logger.warning("Unknown action %r from agent — defaulting to escalate", action)
        action = "escalate"

    return AgentResponse(
        recommendation=data.get("recommendation", ""),
        action=action,
        confidence=float(data.get("confidence", 0.5)),
        reasoning=data.get("reasoning", ""),
        sources=data.get("sources", []),
    )
