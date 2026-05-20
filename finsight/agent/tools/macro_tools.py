"""MacroCache DB wrappers exposed as OpenAI-compatible tool definitions for the agent."""

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlmodel import Session, select

from driftguard.store.database import MacroCache, engine

logger = logging.getLogger(__name__)


# ── Tool functions ─────────────────────────────────────────────────────────────

def get_current_macro() -> dict | None:
    """Return the most recently cached macro snapshot and regime classification."""
    try:
        with Session(engine) as session:
            latest = session.exec(
                select(MacroCache)
                .order_by(MacroCache.fetched_at.desc())
                .limit(1)
            ).first()
            if not latest:
                return None
            return {
                "as_of": str(latest.fetched_at),
                "vix": latest.vix,
                "credit_spread": latest.credit_spread,
                "fed_funds_rate": latest.fed_funds_rate,
                "yield_curve": latest.yield_curve,
                "unemployment_rate": latest.unemployment_rate,
                "regime": latest.regime,
                "regime_confidence": latest.regime_confidence,
            }
    except Exception as exc:
        logger.warning("get_current_macro failed: %s", exc)
        return None


def get_macro_history(days: int = 30) -> list[dict]:
    """Return macro snapshots over recent days — useful for spotting regime transitions."""
    try:
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        with Session(engine) as session:
            records = session.exec(
                select(MacroCache)
                .where(MacroCache.fetched_at >= cutoff)
                .order_by(MacroCache.fetched_at.desc())
            ).all()
            return [
                {
                    "as_of": str(r.fetched_at),
                    "vix": r.vix,
                    "credit_spread": r.credit_spread,
                    "yield_curve": r.yield_curve,
                    "regime": r.regime,
                    "regime_confidence": r.regime_confidence,
                }
                for r in records
            ]
    except Exception as exc:
        logger.warning("get_macro_history failed: %s", exc)
        return []


# ── OpenAI-compatible tool schema ─────────────────────────────────────────────

MACRO_TOOLS: list[dict] = [
    {
        "type": "function",
        "function": {
            "name": "get_current_macro",
            "description": (
                "Get the most recent macro snapshot: VIX, credit spreads, fed funds rate, "
                "yield curve, and the current market regime classification with confidence. "
                "Always call this before making a recommendation — regime determines the action."
            ),
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
            "name": "get_macro_history",
            "description": (
                "Get macro snapshots over the past N days to identify regime transitions. "
                "Use this to determine if we're entering or exiting a stress period."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "days": {
                        "type": "integer",
                        "description": "Number of past days to include. Defaults to 30.",
                    },
                },
                "required": [],
            },
        },
    },
]


# ── Agent-facing dispatch ──────────────────────────────────────────────────────

_DISPATCH: dict[str, Any] = {
    "get_current_macro": get_current_macro,
    "get_macro_history": get_macro_history,
}


def call_macro_tool(name: str, arguments: dict) -> Any:
    """Dispatch a tool call from the agent LLM to the correct macro function."""
    fn = _DISPATCH.get(name)
    if fn is None:
        raise ValueError(f"Unknown macro tool: {name!r}. Valid: {list(_DISPATCH)}")
    return fn(**arguments)
