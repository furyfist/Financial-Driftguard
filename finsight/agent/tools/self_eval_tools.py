"""Self-improvement loop tools — agent evaluates its own past recommendations via LLM-as-Judge."""

import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)

CORRECT_ACTION_MAP = {
    "stable": {"none": "monitor", "low": "monitor", "medium": "investigate", "high": "retrain", "critical": "retrain"},
    "rate_shock": {"none": "monitor", "low": "monitor", "medium": "monitor", "high": "monitor", "critical": "monitor"},
    "credit_stress": {"none": "monitor", "low": "monitor", "medium": "monitor", "high": "monitor", "critical": "monitor"},
    "recession": {"none": "monitor", "low": "monitor", "medium": "investigate", "high": "champion_challenger", "critical": "champion_challenger"},
    "black_swan": {"none": "freeze", "low": "freeze", "medium": "freeze", "high": "freeze", "critical": "freeze"},
    "unknown": {"none": "monitor", "low": "monitor", "medium": "escalate", "high": "escalate", "critical": "escalate"},
}


@dataclass
class ConfidenceAdjustment:
    regime: str
    historical_accuracy: float
    direction: str        # "increase" | "decrease" | "none"
    magnitude: float      # 0.0 to 0.2 delta
    rationale: str


@dataclass
class SelfEvalResult:
    model_id: str
    window_days: int
    traces_evaluated: int
    accuracies: dict[str, float] = field(default_factory=dict)
    adjustments: list[ConfidenceAdjustment] = field(default_factory=list)
    overall_accuracy: float = 0.0


def _fetch_traces(model_id: str, limit: int = 30) -> list[dict]:
    """Pull recent agent decision traces from Phoenix."""
    try:
        from finsight.agent.tools.phoenix_tools import list_traces
        traces = list_traces(limit=limit)
        if model_id:
            traces = [t for t in traces if model_id in str(t.get("attributes", {}))]
        return traces
    except Exception as exc:
        logger.warning("Phoenix trace fetch failed: %s", exc)
        return []


def _fetch_agent_decisions(model_id: str, window_days: int) -> list[dict]:
    """Pull agent decision log from the database for the window period."""
    try:
        from datetime import datetime, timezone, timedelta
        from sqlmodel import Session, select
        from driftguard.store.database import engine, AgentDecisionLog
        cutoff = datetime.now(timezone.utc) - timedelta(days=window_days)
        with Session(engine) as session:
            stmt = select(AgentDecisionLog).where(
                AgentDecisionLog.model_id == model_id,
                AgentDecisionLog.created_at >= cutoff,
            ).order_by(AgentDecisionLog.created_at.desc()).limit(50)
            rows = session.exec(stmt).all()
        return [
            {
                "id": r.id,
                "action": r.action,
                "confidence": r.confidence,
                "regime_context": r.regime_context,
                "created_at": str(r.created_at),
            }
            for r in rows
        ]
    except Exception as exc:
        logger.warning("AgentDecisionLog fetch failed: %s", exc)
        return []


def _llm_judge_decision(decision: dict) -> bool:
    """Use LLM-as-Judge to assess whether the decision was correct for its regime."""
    try:
        from finsight.llm import get_llm
        regime = decision.get("regime_context", "unknown").lower()
        action = decision.get("action", "monitor")
        judge_prompt = (
            f"A financial ML governance agent classified the market regime as '{regime}' "
            f"and recommended action: '{action}'.\n\n"
            "Given these governance rules:\n"
            "- stable + high drift → retrain\n"
            "- rate_shock or credit_stress (any drift) → monitor only, NEVER retrain\n"
            "- black_swan (any drift) → freeze automated decisions\n"
            "- recession + high drift → champion_challenger\n"
            "- unknown + high drift → escalate\n\n"
            "Was the recommended action correct for this regime? "
            "Answer with exactly one word: 'correct' or 'incorrect'."
        )
        llm = get_llm(role="fast")
        resp = llm.complete([{"role": "user", "content": judge_prompt}], temperature=0.0)
        answer = (resp.content or "").strip().lower()
        return answer.startswith("correct")
    except Exception as exc:
        logger.warning("LLM judge failed for decision %s: %s", decision.get("id"), exc)
        regime = decision.get("regime_context", "unknown").lower()
        action = decision.get("action", "monitor")
        expected = CORRECT_ACTION_MAP.get(regime, CORRECT_ACTION_MAP["unknown"])
        for severity_expected in expected.values():
            if action == severity_expected:
                return True
        return False


def evaluate_past_recommendations(model_id: str, window_days: int = 30) -> dict:
    """
    Evaluate accuracy of past agent recommendations.
    Returns per-regime accuracy dict and confidence adjustment suggestions.
    """
    decisions = _fetch_agent_decisions(model_id, window_days)
    if not decisions:
        return {
            "model_id": model_id,
            "window_days": window_days,
            "traces_evaluated": 0,
            "accuracies": {},
            "adjustments": [],
            "overall_accuracy": 0.0,
        }

    regime_correct: dict[str, list[bool]] = {}
    for decision in decisions:
        regime = (decision.get("regime_context") or "unknown").lower()
        correct = _llm_judge_decision(decision)
        regime_correct.setdefault(regime, []).append(correct)

    accuracies = {
        regime: sum(results) / len(results)
        for regime, results in regime_correct.items()
    }
    all_results = [r for results in regime_correct.values() for r in results]
    overall = sum(all_results) / len(all_results) if all_results else 0.0

    adjustments = []
    for regime, acc in accuracies.items():
        adj = get_confidence_adjustment(regime, acc)
        if adj.direction != "none":
            adjustments.append({
                "regime": adj.regime,
                "historical_accuracy": adj.historical_accuracy,
                "direction": adj.direction,
                "magnitude": adj.magnitude,
                "rationale": adj.rationale,
            })

    return {
        "model_id": model_id,
        "window_days": window_days,
        "traces_evaluated": len(decisions),
        "accuracies": accuracies,
        "adjustments": adjustments,
        "overall_accuracy": overall,
    }


def get_confidence_adjustment(regime: str, historical_accuracy: float) -> ConfidenceAdjustment:
    """
    Return a confidence adjustment based on the agent's historical accuracy for a regime.
    black_swan >= 0.95 → increase (HALT decisions are reliable)
    credit_stress < 0.80 → decrease (be more conservative)
    all others → no adjustment unless very low accuracy
    """
    regime = regime.lower()

    if regime == "black_swan" and historical_accuracy >= 0.95:
        return ConfidenceAdjustment(
            regime=regime,
            historical_accuracy=historical_accuracy,
            direction="increase",
            magnitude=0.05,
            rationale=f"Black swan HALT recommendations were correct {historical_accuracy:.0%} of the time over the evaluation window — increasing confidence.",
        )

    if regime in ("credit_stress", "rate_shock") and historical_accuracy < 0.80:
        return ConfidenceAdjustment(
            regime=regime,
            historical_accuracy=historical_accuracy,
            direction="decrease",
            magnitude=0.10,
            rationale=f"Agent accuracy for {regime} was only {historical_accuracy:.0%} — reducing confidence and recommending more conservative action.",
        )

    if historical_accuracy < 0.60:
        return ConfidenceAdjustment(
            regime=regime,
            historical_accuracy=historical_accuracy,
            direction="decrease",
            magnitude=0.15,
            rationale=f"Agent accuracy for {regime} was {historical_accuracy:.0%} — well below acceptable threshold, significant confidence reduction.",
        )

    return ConfidenceAdjustment(
        regime=regime,
        historical_accuracy=historical_accuracy,
        direction="none",
        magnitude=0.0,
        rationale=f"Accuracy for {regime} at {historical_accuracy:.0%} is within acceptable range — no adjustment.",
    )
