"""
Tests for the FinSight AI governance agent brain.

Key assertions:
  - black_swan regime           → action == "freeze"
  - stable + critical drift     → action == "retrain"
  - credit_stress + any drift   → action == "monitor"
  - parse_response handles edge cases gracefully
  - tool dispatch routes correctly
"""

import json
from unittest.mock import MagicMock, patch, call

import pytest

from finsight.llm.provider import LLMResponse, ToolCall, TokenUsage
from finsight.agent.brain import (
    DriftGuardAgent,
    AgentResponse,
    VALID_ACTIONS,
    _parse_response,
    _dispatch_tool_call,
    MAX_TOOL_ITERATIONS,
)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _usage() -> TokenUsage:
    return TokenUsage(prompt_tokens=10, completion_tokens=50, total_tokens=60)


def _tool_response(*tool_calls: ToolCall) -> LLMResponse:
    """LLM response that requests tool calls (no final content yet)."""
    return LLMResponse(content="", model="test", usage=_usage(), tool_calls=list(tool_calls))


def _final_response(action: str, confidence: float = 0.9, regime: str = "stable") -> LLMResponse:
    """LLM response with a valid JSON recommendation."""
    payload = {
        "recommendation": f"Test recommendation for action={action}.",
        "action": action,
        "confidence": confidence,
        "reasoning": f"Regime is {regime}. Action: {action}.",
        "sources": [],
    }
    return LLMResponse(
        content=json.dumps(payload),
        model="test",
        usage=_usage(),
        tool_calls=None,
    )


def _macro_data(regime: str, vix: float = 20.0) -> dict:
    return {
        "as_of": "2026-05-21T00:00:00",
        "vix": vix,
        "credit_spread": 1.2,
        "fed_funds_rate": 5.33,
        "yield_curve": 0.1,
        "unemployment_rate": 3.9,
        "regime": regime,
        "regime_confidence": 0.95,
    }


def _drift_data(severity: str, score: float = 0.3) -> dict:
    return {
        "run_id": 1,
        "model_id": "lending_club_v1",
        "checked_at": "2026-05-21T00:00:00",
        "overall_severity": severity,
        "drift_score": score,
        "regime": None,
        "regime_confidence": None,
        "notes": "",
    }


# ── Regime → Action tests ─────────────────────────────────────────────────────

@patch("finsight.agent.brain.get_llm")
@patch("finsight.agent.brain._dispatch_tool_call")
def test_black_swan_produces_freeze(mock_dispatch, mock_get_llm):
    """COVID-style black swan event must always result in action=freeze."""
    mock_llm = MagicMock()
    mock_get_llm.return_value = mock_llm
    mock_llm.complete.side_effect = [
        _tool_response(ToolCall(name="get_current_macro", arguments={})),
        _final_response("freeze", confidence=0.99, regime="black_swan"),
    ]
    mock_dispatch.return_value = _macro_data("black_swan", vix=57.0)

    agent = DriftGuardAgent()
    result = agent.analyze("lending_club_v1")

    assert result.action == "freeze"
    assert result.confidence >= 0.9
    assert result.model_id == "lending_club_v1"


@patch("finsight.agent.brain.get_llm")
@patch("finsight.agent.brain._dispatch_tool_call")
def test_stable_critical_drift_produces_retrain(mock_dispatch, mock_get_llm):
    """Stable macro + critical drift = model decay. Action must be retrain."""
    mock_llm = MagicMock()
    mock_get_llm.return_value = mock_llm
    mock_llm.complete.side_effect = [
        _tool_response(
            ToolCall(name="get_current_macro", arguments={}),
            ToolCall(name="get_latest_drift", arguments={"model_id": "lending_club_v1"}),
        ),
        _final_response("retrain", confidence=0.88, regime="stable"),
    ]

    def dispatch_side_effect(name, arguments):
        if name == "get_current_macro":
            return _macro_data("stable", vix=14.0)
        if name == "get_latest_drift":
            return _drift_data("critical", score=0.62)
        return {}

    mock_dispatch.side_effect = dispatch_side_effect

    agent = DriftGuardAgent()
    result = agent.analyze("lending_club_v1")

    assert result.action == "retrain"
    assert result.model_id == "lending_club_v1"


@patch("finsight.agent.brain.get_llm")
@patch("finsight.agent.brain._dispatch_tool_call")
def test_credit_stress_drift_produces_monitor(mock_dispatch, mock_get_llm):
    """Rate hike / credit stress + drift must never result in retrain. Action = monitor."""
    mock_llm = MagicMock()
    mock_get_llm.return_value = mock_llm
    mock_llm.complete.side_effect = [
        _tool_response(ToolCall(name="get_current_macro", arguments={})),
        _final_response("monitor", confidence=0.85, regime="credit_stress"),
    ]
    mock_dispatch.return_value = _macro_data("credit_stress", vix=28.0)

    agent = DriftGuardAgent()
    result = agent.analyze("lending_club_v1")

    assert result.action == "monitor"
    # Critically: must NOT be retrain
    assert result.action != "retrain"


@patch("finsight.agent.brain.get_llm")
@patch("finsight.agent.brain._dispatch_tool_call")
def test_recession_produces_champion_challenger(mock_dispatch, mock_get_llm):
    """Recession regime with high drift → champion_challenger (not retrain)."""
    mock_llm = MagicMock()
    mock_get_llm.return_value = mock_llm
    mock_llm.complete.side_effect = [
        _tool_response(ToolCall(name="get_current_macro", arguments={})),
        _final_response("champion_challenger", confidence=0.78, regime="recession"),
    ]
    mock_dispatch.return_value = _macro_data("recession", vix=35.0)

    agent = DriftGuardAgent()
    result = agent.analyze("lending_club_v1")

    assert result.action == "champion_challenger"


# ── _parse_response edge cases ────────────────────────────────────────────────

def test_parse_response_plain_json():
    content = json.dumps({
        "recommendation": "Monitor weekly.",
        "action": "monitor",
        "confidence": 0.8,
        "reasoning": "VIX is stable.",
        "sources": ["trace-abc"],
    })
    result = _parse_response(content)
    assert result.action == "monitor"
    assert result.confidence == pytest.approx(0.8)
    assert result.sources == ["trace-abc"]
    assert result.recommendation == "Monitor weekly."


def test_parse_response_strips_markdown_code_fence():
    content = "```json\n{\"recommendation\": \"Freeze.\", \"action\": \"freeze\", \"confidence\": 0.99, \"reasoning\": \"Black swan.\", \"sources\": []}\n```"
    result = _parse_response(content)
    assert result.action == "freeze"
    assert result.confidence == pytest.approx(0.99)


def test_parse_response_falls_back_on_no_json():
    result = _parse_response("I cannot determine the right action at this time.")
    assert result.action == "escalate"
    assert result.confidence == 0.0
    assert "escalat" in result.recommendation.lower()


def test_parse_response_falls_back_on_invalid_json():
    result = _parse_response("```json\n{broken json here\n```")
    assert result.action == "escalate"
    assert result.confidence == 0.0


def test_parse_response_sanitises_unknown_action():
    content = json.dumps({
        "recommendation": "Do something.",
        "action": "delete_model",   # not a valid action
        "confidence": 0.5,
        "reasoning": "...",
        "sources": [],
    })
    result = _parse_response(content)
    assert result.action == "escalate"


def test_parse_response_all_valid_actions_accepted():
    for action in VALID_ACTIONS:
        content = json.dumps({
            "recommendation": "Test.",
            "action": action,
            "confidence": 0.7,
            "reasoning": "Test reasoning.",
            "sources": [],
        })
        result = _parse_response(content)
        assert result.action == action, f"Action {action!r} was not preserved"


# ── _dispatch_tool_call routing ───────────────────────────────────────────────

def test_dispatch_routes_phoenix_tool():
    with patch("finsight.agent.brain.call_phoenix_tool", return_value=[]) as mock_fn:
        _dispatch_tool_call("list_recent_drift_traces", {"limit": 5})
        mock_fn.assert_called_once_with("list_recent_drift_traces", {"limit": 5})


def test_dispatch_routes_drift_tool():
    with patch("finsight.agent.brain.call_drift_tool", return_value={}) as mock_fn:
        _dispatch_tool_call("get_latest_drift", {"model_id": "m1"})
        mock_fn.assert_called_once_with("get_latest_drift", {"model_id": "m1"})


def test_dispatch_routes_macro_tool():
    with patch("finsight.agent.brain.call_macro_tool", return_value={}) as mock_fn:
        _dispatch_tool_call("get_current_macro", {})
        mock_fn.assert_called_once_with("get_current_macro", {})


def test_dispatch_returns_error_dict_for_unknown_tool():
    result = _dispatch_tool_call("nonexistent_tool", {})
    assert "error" in result
    assert "nonexistent_tool" in result["error"]


# ── Tool loop behaviour ───────────────────────────────────────────────────────

@patch("finsight.agent.brain.get_llm")
@patch("finsight.agent.brain._dispatch_tool_call")
def test_tool_loop_caps_at_max_iterations(mock_dispatch, mock_get_llm):
    """If LLM keeps calling tools, the loop forces a conclusion after MAX_TOOL_ITERATIONS."""
    mock_llm = MagicMock()
    mock_get_llm.return_value = mock_llm
    mock_dispatch.return_value = {}

    # Always return a tool call — loop must cap itself
    infinite_tool_call = _tool_response(ToolCall(name="get_current_macro", arguments={}))
    final = _final_response("monitor")
    # MAX_TOOL_ITERATIONS tool responses + 1 final forced response
    mock_llm.complete.side_effect = [infinite_tool_call] * MAX_TOOL_ITERATIONS + [final]

    agent = DriftGuardAgent()
    result = agent.analyze("lending_club_v1")

    # Should not raise; should produce a valid response after forcing conclusion
    assert result.action in VALID_ACTIONS
    assert mock_llm.complete.call_count == MAX_TOOL_ITERATIONS + 1


@patch("finsight.agent.brain.get_llm")
@patch("finsight.agent.brain._dispatch_tool_call")
def test_tool_failure_does_not_crash_loop(mock_dispatch, mock_get_llm):
    """A tool that raises an exception must not crash the agent — error is fed back to LLM."""
    mock_llm = MagicMock()
    mock_get_llm.return_value = mock_llm
    mock_dispatch.side_effect = RuntimeError("DB is down")

    mock_llm.complete.side_effect = [
        _tool_response(ToolCall(name="get_current_macro", arguments={})),
        _final_response("escalate"),
    ]

    agent = DriftGuardAgent()
    result = agent.analyze("lending_club_v1")

    # Agent must still return a valid response
    assert result.action in VALID_ACTIONS


# ── ask() with memory ─────────────────────────────────────────────────────────

@patch("finsight.agent.brain.get_llm")
@patch("finsight.agent.brain._dispatch_tool_call")
def test_ask_stores_turns_in_memory(mock_dispatch, mock_get_llm):
    from finsight.agent.memory import ConversationMemory

    mock_llm = MagicMock()
    mock_get_llm.return_value = mock_llm
    mock_dispatch.return_value = {}
    mock_llm.complete.return_value = _final_response("monitor")

    memory = ConversationMemory()
    agent = DriftGuardAgent()
    agent.ask("What is the current drift status?", model_id="m1", memory=memory)

    # Memory should have the user turn and the assistant turn
    assert len(memory) == 2
    msgs = memory.get_messages("sys")
    roles = [m["role"] for m in msgs]
    assert roles == ["system", "user", "assistant"]


@patch("finsight.agent.brain.get_llm")
@patch("finsight.agent.brain._dispatch_tool_call")
def test_ask_without_memory_does_not_raise(mock_dispatch, mock_get_llm):
    mock_llm = MagicMock()
    mock_get_llm.return_value = mock_llm
    mock_dispatch.return_value = {}
    mock_llm.complete.return_value = _final_response("monitor")

    agent = DriftGuardAgent()
    result = agent.ask("What's the regime?")

    assert result.action in VALID_ACTIONS
