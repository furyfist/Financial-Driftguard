"""Tests for Phoenix tool wrappers — schema validity, output shape, graceful degradation."""

import os
from unittest.mock import MagicMock, patch

import pytest

from finsight.agent.tools.phoenix_tools import (
    PHOENIX_TOOLS,
    call_phoenix_tool,
    list_traces,
    get_trace,
    get_spans,
    list_datasets,
    get_dataset_examples,
    list_experiments,
    get_experiment,
)


# ── OpenAI schema validation ──────────────────────────────────────────────────

def test_all_tools_have_required_schema_fields():
    """Every tool must conform to the OpenAI function calling schema."""
    for tool in PHOENIX_TOOLS:
        assert tool["type"] == "function", f"tool.type must be 'function': {tool}"
        fn = tool["function"]
        assert "name" in fn, f"Missing 'name' in tool: {fn}"
        assert "description" in fn, f"Missing 'description' in tool: {fn}"
        assert "parameters" in fn, f"Missing 'parameters' in tool: {fn}"
        params = fn["parameters"]
        assert params["type"] == "object", f"parameters.type must be 'object': {fn['name']}"
        assert "properties" in params, f"Missing 'properties' in tool: {fn['name']}"
        assert "required" in params, f"Missing 'required' in tool: {fn['name']}"
        assert isinstance(params["required"], list)


def test_all_seven_tools_defined():
    names = {t["function"]["name"] for t in PHOENIX_TOOLS}
    assert names == {
        "list_recent_drift_traces",
        "get_trace_details",
        "get_drift_spans",
        "list_datasets",
        "get_dataset_examples",
        "list_experiments",
        "get_experiment",
    }


def test_required_parameter_tools():
    """Tools that require parameters must list them."""
    required_map = {
        t["function"]["name"]: t["function"]["parameters"]["required"]
        for t in PHOENIX_TOOLS
    }
    assert "trace_id" in required_map["get_trace_details"]
    assert "trace_id" in required_map["get_drift_spans"]
    assert "dataset_id" in required_map["get_dataset_examples"]
    assert "dataset_id" in required_map["list_experiments"]
    assert "experiment_id" in required_map["get_experiment"]
    # Optional-only tools
    assert required_map["list_recent_drift_traces"] == []
    assert required_map["list_datasets"] == []


# ── Graceful degradation (Phoenix unreachable) ────────────────────────────────

def _patch_httpx_fail():
    """Patch httpx.Client so every request raises ConnectionError."""
    mock_client = MagicMock()
    mock_client.__enter__ = MagicMock(return_value=mock_client)
    mock_client.__exit__ = MagicMock(return_value=False)
    mock_client.get.side_effect = ConnectionError("Phoenix is down")
    return patch("finsight.agent.tools.phoenix_tools.httpx.Client", return_value=mock_client)


def test_list_traces_returns_empty_list_when_unreachable():
    with _patch_httpx_fail():
        result = list_traces()
    assert result == []


def test_get_trace_returns_none_when_unreachable():
    with _patch_httpx_fail():
        result = get_trace("abc-123")
    assert result is None


def test_get_spans_returns_empty_list_when_unreachable():
    with _patch_httpx_fail():
        result = get_spans("abc-123")
    assert result == []


def test_list_datasets_returns_empty_list_when_unreachable():
    with _patch_httpx_fail():
        result = list_datasets()
    assert result == []


def test_get_experiment_returns_none_when_unreachable():
    with _patch_httpx_fail():
        result = get_experiment("exp-999")
    assert result is None


# ── Parseable output when Phoenix responds ────────────────────────────────────

def _mock_httpx_response(data: list | dict):
    """Return a mock httpx client that returns the given data as JSON."""
    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json.return_value = {"data": data} if isinstance(data, list) else data

    mock_client = MagicMock()
    mock_client.__enter__ = MagicMock(return_value=mock_client)
    mock_client.__exit__ = MagicMock(return_value=False)
    mock_client.get.return_value = mock_resp
    return patch("finsight.agent.tools.phoenix_tools.httpx.Client", return_value=mock_client)


def test_list_traces_deduplicates_by_trace_id():
    spans = [
        {"context": {"trace_id": "tid-1"}, "name": "drift_check", "start_time": "2026-01-01T00:00:00Z", "attributes": {}},
        {"context": {"trace_id": "tid-1"}, "name": "detector_run", "start_time": "2026-01-01T00:00:01Z", "attributes": {}},
        {"context": {"trace_id": "tid-2"}, "name": "drift_check", "start_time": "2026-01-02T00:00:00Z", "attributes": {}},
    ]
    with _mock_httpx_response(spans):
        result = list_traces(limit=10)
    assert len(result) == 2
    trace_ids = {t["trace_id"] for t in result}
    assert trace_ids == {"tid-1", "tid-2"}


def test_get_trace_returns_structured_dict():
    spans = [
        {"span_id": "s1", "name": "drift_check", "attributes": {"drift.severity": "low"}},
    ]
    with _mock_httpx_response(spans):
        result = get_trace("tid-42")
    assert result is not None
    assert result["trace_id"] == "tid-42"
    assert isinstance(result["spans"], list)
    assert result["spans"][0]["name"] == "drift_check"


def test_list_datasets_returns_list():
    datasets = [{"id": "ds-1", "name": "lending_club_baseline"}]
    with _mock_httpx_response(datasets):
        result = list_datasets()
    assert len(result) == 1
    assert result[0]["id"] == "ds-1"


# ── call_phoenix_tool dispatch ────────────────────────────────────────────────

def test_call_phoenix_tool_dispatches_list_datasets():
    datasets = [{"id": "ds-1", "name": "test"}]
    with _mock_httpx_response(datasets):
        result = call_phoenix_tool("list_datasets", {})
    assert isinstance(result, list)


def test_call_phoenix_tool_raises_on_unknown_name():
    with pytest.raises(ValueError, match="Unknown Phoenix tool"):
        call_phoenix_tool("nonexistent_tool", {})


def test_call_phoenix_tool_passes_arguments():
    with _patch_httpx_fail():
        # Even when Phoenix is down, the function should be called with the right args
        result = call_phoenix_tool("get_experiment", {"experiment_id": "exp-1"})
    assert result is None  # graceful failure
