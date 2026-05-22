"""Natural language drift history query tool for the governance agent."""

import logging
from datetime import datetime
from typing import Any

from sqlmodel import Session, select, desc

from driftguard.store.database import DriftRun, engine

logger = logging.getLogger(__name__)


def query_drift_history(
    model_id: str,
    regime: str | None = None,
    severity: str | None = None,
    feature: str | None = None,
    since: str | None = None,
    until: str | None = None,
    limit: int = 20,
) -> list[dict] | dict:
    """
    Query drift run history for a model with optional filters.

    Args:
        model_id: The model to query (required).
        regime: Filter by regime string (e.g. "stable", "rate_shock").
        severity: Filter by overall_severity (e.g. "high", "critical").
        feature: Case-insensitive substring match against feature_results_json.
        since: ISO date string "YYYY-MM-DD" — inclusive lower bound on checked_at.
        until: ISO date string "YYYY-MM-DD" — inclusive upper bound on checked_at.
        limit: Maximum number of results to return (default 20).
    """
    try:
        with Session(engine) as session:
            q = (
                select(DriftRun)
                .where(DriftRun.model_id == model_id)
            )
            if regime is not None:
                q = q.where(DriftRun.regime == regime)
            if severity is not None:
                q = q.where(DriftRun.overall_severity == severity)
            if feature is not None:
                q = q.where(DriftRun.feature_results_json.contains(feature))
            if since is not None:
                q = q.where(DriftRun.checked_at >= datetime.fromisoformat(since))
            if until is not None:
                q = q.where(DriftRun.checked_at <= datetime.fromisoformat(until))

            q = q.order_by(desc(DriftRun.checked_at)).limit(limit)
            runs = session.exec(q).all()

            return [
                {
                    "run_id": r.id,
                    "checked_at": str(r.checked_at),
                    "overall_severity": r.overall_severity,
                    "drift_score": r.drift_score,
                    "regime": r.regime,
                    "notes": r.notes,
                }
                for r in runs
            ]
    except Exception as exc:
        logger.warning("query_drift_history failed for %s: %s", model_id, exc)
        return {"error": str(exc)}


# ── OpenAI-compatible tool schema ─────────────────────────────────────────────

QUERY_TOOLS: list[dict] = [
    {
        "type": "function",
        "function": {
            "name": "query_drift_history",
            "description": (
                "Query drift run history for a model with optional filters. "
                "Supports filtering by regime, severity, feature name, and date range. "
                "Use this to answer natural language questions like 'show me all high-severity "
                "runs during rate_shock' or 'when did int_rate last drift?'"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "model_id": {
                        "type": "string",
                        "description": "The model ID to query history for.",
                    },
                    "regime": {
                        "type": "string",
                        "description": "Filter by regime (e.g. 'stable', 'rate_shock', 'credit_stress').",
                    },
                    "severity": {
                        "type": "string",
                        "description": "Filter by overall_severity (e.g. 'none', 'low', 'medium', 'high', 'critical').",
                    },
                    "feature": {
                        "type": "string",
                        "description": "Substring to match against feature names in the run's feature_results_json.",
                    },
                    "since": {
                        "type": "string",
                        "description": "ISO date string 'YYYY-MM-DD' — include runs on or after this date.",
                    },
                    "until": {
                        "type": "string",
                        "description": "ISO date string 'YYYY-MM-DD' — include runs on or before this date.",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of results to return. Defaults to 20.",
                    },
                },
                "required": ["model_id"],
            },
        },
    },
]


# ── Agent-facing dispatch ──────────────────────────────────────────────────────

_DISPATCH: dict[str, Any] = {
    "query_drift_history": query_drift_history,
}


def call_query_tool(name: str, arguments: dict) -> Any:
    """Dispatch a query tool call from the agent LLM."""
    fn = _DISPATCH.get(name)
    if fn is None:
        raise ValueError(f"Unknown query tool: {name!r}. Valid: {list(_DISPATCH)}")
    return fn(**arguments)
