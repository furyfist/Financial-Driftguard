"""Phoenix REST API wrappers exposed as OpenAI-compatible tool definitions for the agent."""

import logging
import os
from typing import Any

logger = logging.getLogger(__name__)


def _base_url() -> str:
    return os.getenv("PHOENIX_MCP_BASE_URL", "http://localhost:6006").rstrip("/")


def _auth_headers() -> dict:
    api_key = os.getenv("PHOENIX_API_KEY", "") or os.getenv("PHOENIX_MCP_API_KEY", "")
    return {"api_key": api_key} if api_key else {}


def _get(path: str, params: dict | None = None) -> Any:
    """GET against the Phoenix REST API. Returns parsed JSON or None on any failure."""
    try:
        import httpx
        with httpx.Client(timeout=10.0, headers=_auth_headers()) as client:
            resp = client.get(f"{_base_url()}{path}", params=params or {})
            resp.raise_for_status()
            return resp.json()
    except Exception as exc:
        logger.warning("Phoenix API unavailable at %s%s: %s", _base_url(), path, exc)
        return None


# ── Tool functions ─────────────────────────────────────────────────────────────

def list_traces(project_name: str = "finsight-ai", limit: int = 20) -> list[dict]:
    """Return the most recent drift run traces, each as a summary dict keyed by trace_id."""
    result = _get(
        "/v1/spans",
        params={"project_name": project_name, "limit": limit * 5},  # over-fetch to de-dup
    )
    if result is None:
        return []
    seen: dict[str, dict] = {}
    for span in result.get("data", []):
        tid = span.get("context", {}).get("trace_id")
        if tid and tid not in seen:
            seen[tid] = {
                "trace_id": tid,
                "root_span_name": span.get("name"),
                "start_time": span.get("start_time"),
                "attributes": span.get("attributes", {}),
            }
        if len(seen) >= limit:
            break
    return list(seen.values())


def get_trace(trace_id: str) -> dict | None:
    """Return the full span tree for a specific drift run trace."""
    result = _get("/v1/spans", params={"trace_id": trace_id})
    if result is None:
        return None
    return {"trace_id": trace_id, "spans": result.get("data", [])}


def get_spans(trace_id: str) -> list[dict]:
    """Return per-detector, per-feature span details for a specific drift trace."""
    result = _get("/v1/spans", params={"trace_id": trace_id})
    if result is None:
        return []
    return result.get("data", [])


def list_datasets() -> list[dict]:
    """Return benchmark datasets registered in Phoenix (e.g., Lending Club baseline)."""
    result = _get("/v1/datasets")
    if result is None:
        return []
    return result.get("data", [])


def get_dataset_examples(dataset_id: str, limit: int = 50) -> list[dict]:
    """Return example rows from a Phoenix dataset."""
    result = _get(f"/v1/datasets/{dataset_id}/examples", params={"limit": limit})
    if result is None:
        return []
    return result.get("data", [])


def list_experiments(dataset_id: str) -> list[dict]:
    """Return experiments run against a Phoenix dataset (champion-challenger results)."""
    result = _get(f"/v1/datasets/{dataset_id}/experiments")
    if result is None:
        return []
    return result.get("data", [])


def get_experiment(experiment_id: str) -> dict | None:
    """Return detailed experiment results including per-example evaluator scores."""
    return _get(f"/v1/experiments/{experiment_id}")


# ── OpenAI-compatible tool schema ─────────────────────────────────────────────

PHOENIX_TOOLS: list[dict] = [
    {
        "type": "function",
        "function": {
            "name": "list_recent_drift_traces",
            "description": (
                "Get the most recent drift monitoring traces from Phoenix. "
                "Each trace represents one complete drift check run for a model."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "project_name": {
                        "type": "string",
                        "description": "Phoenix project name. Defaults to 'finsight-ai'.",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of traces to return. Defaults to 20.",
                    },
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_trace_details",
            "description": (
                "Get the full span tree for a specific drift run trace, "
                "including all detector spans and the regime tag span."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "trace_id": {
                        "type": "string",
                        "description": "The trace ID returned by list_recent_drift_traces.",
                    },
                },
                "required": ["trace_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_drift_spans",
            "description": (
                "Get per-detector, per-feature spans for a drift trace. "
                "Each span contains drift.score, drift.severity, drift.feature_name, "
                "and drift.detector_name attributes."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "trace_id": {
                        "type": "string",
                        "description": "The trace ID to retrieve spans for.",
                    },
                },
                "required": ["trace_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_datasets",
            "description": "List benchmark datasets registered in Phoenix (e.g., Lending Club baseline).",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_dataset_examples",
            "description": "Get example rows from a Phoenix dataset.",
            "parameters": {
                "type": "object",
                "properties": {
                    "dataset_id": {
                        "type": "string",
                        "description": "The dataset ID returned by list_datasets.",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Max examples to return. Defaults to 50.",
                    },
                },
                "required": ["dataset_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_experiments",
            "description": (
                "List champion-challenger experiments run against a Phoenix dataset. "
                "Use this to compare current model vs baseline performance."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "dataset_id": {
                        "type": "string",
                        "description": "The dataset ID to list experiments for.",
                    },
                },
                "required": ["dataset_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_experiment",
            "description": "Get detailed results for a specific champion-challenger experiment.",
            "parameters": {
                "type": "object",
                "properties": {
                    "experiment_id": {
                        "type": "string",
                        "description": "The experiment ID returned by list_experiments.",
                    },
                },
                "required": ["experiment_id"],
            },
        },
    },
]


# ── Agent-facing dispatch ──────────────────────────────────────────────────────

_DISPATCH: dict[str, Any] = {
    "list_recent_drift_traces": list_traces,
    "get_trace_details": get_trace,
    "get_drift_spans": get_spans,
    "list_datasets": list_datasets,
    "get_dataset_examples": get_dataset_examples,
    "list_experiments": list_experiments,
    "get_experiment": get_experiment,
}


def call_phoenix_tool(name: str, arguments: dict) -> Any:
    """Dispatch a tool call from the agent LLM to the correct Phoenix function."""
    fn = _DISPATCH.get(name)
    if fn is None:
        raise ValueError(f"Unknown Phoenix tool: {name!r}. Valid: {list(_DISPATCH)}")
    return fn(**arguments)
