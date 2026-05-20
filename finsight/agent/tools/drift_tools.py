"""DriftGuard DB wrappers exposed as OpenAI-compatible tool definitions for the agent."""

import json
import logging
from typing import Any

from sqlmodel import Session, select, desc

from driftguard.store.database import DriftRun, ModelRecord, engine

logger = logging.getLogger(__name__)


# ── Tool functions ─────────────────────────────────────────────────────────────

def list_models() -> list[dict]:
    """Return all registered models with their baseline status."""
    try:
        with Session(engine) as session:
            records = session.exec(select(ModelRecord)).all()
            return [
                {
                    "model_id": r.model_id,
                    "description": r.description,
                    "has_baseline": r.baseline_data is not None,
                    "baseline_set_at": str(r.baseline_set_at) if r.baseline_set_at else None,
                    "baseline_row_count": r.baseline_row_count,
                }
                for r in records
            ]
    except Exception as exc:
        logger.warning("list_models failed: %s", exc)
        return []


def get_latest_drift(model_id: str) -> dict | None:
    """Return the most recent drift check result for a model."""
    try:
        with Session(engine) as session:
            run = session.exec(
                select(DriftRun)
                .where(DriftRun.model_id == model_id)
                .order_by(desc(DriftRun.checked_at))
                .limit(1)
            ).first()
            if not run:
                return None
            return {
                "run_id": run.id,
                "model_id": run.model_id,
                "checked_at": str(run.checked_at),
                "overall_severity": run.overall_severity,
                "drift_score": run.drift_score,
                "regime": run.regime,
                "regime_confidence": run.regime_confidence,
                "notes": run.notes,
            }
    except Exception as exc:
        logger.warning("get_latest_drift failed for %s: %s", model_id, exc)
        return None


def get_model_history(model_id: str, limit: int = 10) -> list[dict]:
    """Return recent drift history for a model — useful for spotting trends."""
    try:
        with Session(engine) as session:
            runs = session.exec(
                select(DriftRun)
                .where(DriftRun.model_id == model_id)
                .order_by(desc(DriftRun.checked_at))
                .limit(limit)
            ).all()
            return [
                {
                    "run_id": r.id,
                    "checked_at": str(r.checked_at),
                    "overall_severity": r.overall_severity,
                    "drift_score": r.drift_score,
                    "regime": r.regime,
                }
                for r in runs
            ]
    except Exception as exc:
        logger.warning("get_model_history failed for %s: %s", model_id, exc)
        return []


def get_feature_breakdown(model_id: str, run_id: int) -> list[dict]:
    """Return per-detector, per-feature drift scores for a specific run."""
    try:
        with Session(engine) as session:
            run = session.get(DriftRun, run_id)
            if not run or run.model_id != model_id:
                return []
            return json.loads(run.feature_results_json)
    except Exception as exc:
        logger.warning("get_feature_breakdown failed for %s run %s: %s", model_id, run_id, exc)
        return []


# ── OpenAI-compatible tool schema ─────────────────────────────────────────────

DRIFT_TOOLS: list[dict] = [
    {
        "type": "function",
        "function": {
            "name": "list_models",
            "description": "List all financial ML models registered in DriftGuard with their baseline status.",
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
            "name": "get_latest_drift",
            "description": (
                "Get the most recent drift check result for a specific model. "
                "Returns overall_severity, drift_score, regime, and the agent recommendation notes."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "model_id": {
                        "type": "string",
                        "description": "The model ID to retrieve the latest drift result for.",
                    },
                },
                "required": ["model_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_model_history",
            "description": (
                "Get the drift history for a model over recent runs. "
                "Use this to identify trends — is drift getting worse, stable, or improving?"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "model_id": {
                        "type": "string",
                        "description": "The model ID to retrieve drift history for.",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Number of recent runs to return. Defaults to 10.",
                    },
                },
                "required": ["model_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_feature_breakdown",
            "description": (
                "Get per-feature, per-detector drift scores for a specific run. "
                "Use this to identify which features are driving drift and whether "
                "multiple detectors (PSI, KS, JS) agree."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "model_id": {
                        "type": "string",
                        "description": "The model ID.",
                    },
                    "run_id": {
                        "type": "integer",
                        "description": "The run ID from get_latest_drift or get_model_history.",
                    },
                },
                "required": ["model_id", "run_id"],
            },
        },
    },
]


# ── Agent-facing dispatch ──────────────────────────────────────────────────────

_DISPATCH: dict[str, Any] = {
    "list_models": list_models,
    "get_latest_drift": get_latest_drift,
    "get_model_history": get_model_history,
    "get_feature_breakdown": get_feature_breakdown,
}


def call_drift_tool(name: str, arguments: dict) -> Any:
    """Dispatch a tool call from the agent LLM to the correct DriftGuard function."""
    fn = _DISPATCH.get(name)
    if fn is None:
        raise ValueError(f"Unknown drift tool: {name!r}. Valid: {list(_DISPATCH)}")
    return fn(**arguments)
