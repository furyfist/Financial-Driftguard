"""LLM-as-Judge evaluation pipeline for FinSight AI governance decisions."""

import logging
import os
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)

REGIME_EVAL_TEMPLATE = """\
Given these macro signals:
VIX = {vix}
Credit Spread = {credit_spread}
Yield Curve = {yield_curve}
Fed Funds Rate = {fed_funds_rate}

The FinSight AI agent classified the market regime as: {regime}

Based on the macro signal values, was this classification correct?
Regime classification rules:
- VIX > 40 or credit spread > 400bps → black_swan
- VIX 25-40 or credit spread 200-400bps → credit_stress or rate_shock
- Yield curve inverted (negative) → recession risk
- All signals normal → stable

Answer with exactly one word: correct or incorrect.
"""

ACTION_EVAL_TEMPLATE = """\
A financial ML governance agent observed the following:
- Market regime: {regime}
- Drift severity: {drift_severity}
- Recommended action: {action}

Governance rules:
- stable + none/low drift → monitor
- stable + medium drift → investigate
- stable + high/critical drift → retrain
- rate_shock or credit_stress (any drift) → monitor (NEVER retrain)
- recession + high drift → champion_challenger
- black_swan (any drift) → freeze
- unknown + high drift → escalate

Was the recommended action correct for this regime and severity?
Answer with exactly one word: correct or incorrect.
"""


def _fetch_recent_decisions(model_id: str, limit: int = 50) -> list[dict]:
    """Pull recent agent decisions with regime context from the database."""
    try:
        from sqlmodel import Session, select
        from driftguard.store.database import engine, AgentDecisionLog
        with Session(engine) as session:
            stmt = select(AgentDecisionLog)
            if model_id:
                stmt = stmt.where(AgentDecisionLog.model_id == model_id)
            stmt = stmt.order_by(AgentDecisionLog.created_at.desc()).limit(limit)
            rows = session.exec(stmt).all()
        return [
            {
                "id": r.id,
                "action": r.action,
                "confidence": r.confidence,
                "regime": r.regime_context or "unknown",
                "created_at": str(r.created_at),
            }
            for r in rows
        ]
    except Exception as exc:
        logger.warning("decision fetch failed: %s", exc)
        return []


def _fetch_recent_drift_runs(model_id: str, limit: int = 50) -> list[dict]:
    """Pull recent drift runs with regime and severity from the database."""
    try:
        from sqlmodel import Session, select
        from driftguard.store.database import engine, DriftRun
        with Session(engine) as session:
            stmt = select(DriftRun)
            if model_id:
                stmt = stmt.where(DriftRun.model_id == model_id)
            stmt = stmt.order_by(DriftRun.checked_at.desc()).limit(limit)
            rows = session.exec(stmt).all()
        return [
            {
                "id": r.id,
                "regime": r.regime or "unknown",
                "severity": r.overall_severity,
                "drift_score": r.drift_score,
                "checked_at": str(r.checked_at),
            }
            for r in rows
        ]
    except Exception as exc:
        logger.warning("drift run fetch failed: %s", exc)
        return []


def _llm_classify(prompt: str) -> str:
    """Run the LLM judge and return 'correct' or 'incorrect'."""
    try:
        from finsight.llm import get_llm
        llm = get_llm(role="fast")
        resp = llm.complete([{"role": "user", "content": prompt}], temperature=0.0)
        answer = (resp.content or "").strip().lower()
        return "correct" if answer.startswith("correct") else "incorrect"
    except Exception as exc:
        logger.warning("LLM classify failed: %s", exc)
        return "incorrect"


def run_regime_eval(traces_df: list[dict] | None = None) -> list[dict]:
    """
    Run regime classification evaluator on recent macro cache entries.
    Returns list of {regime, vix, result} dicts.
    """
    results = []
    try:
        from sqlmodel import Session, select
        from driftguard.store.database import engine, MacroCache, DriftRun
        with Session(engine) as session:
            macro_rows = session.exec(
                select(MacroCache).order_by(MacroCache.fetched_at.desc()).limit(30)
            ).all()
        for row in macro_rows:
            if not row.regime:
                continue
            prompt = REGIME_EVAL_TEMPLATE.format(
                vix=row.vix or "N/A",
                credit_spread=row.credit_spread or "N/A",
                yield_curve=row.yield_curve or "N/A",
                fed_funds_rate=row.fed_funds_rate or "N/A",
                regime=row.regime,
            )
            verdict = _llm_classify(prompt)
            results.append({
                "eval_type": "regime_classification",
                "regime": row.regime,
                "vix": row.vix,
                "result": verdict,
                "fetched_at": str(row.fetched_at),
            })
    except Exception as exc:
        logger.warning("run_regime_eval failed: %s", exc)
    return results


def run_action_eval(model_id: str = "") -> list[dict]:
    """
    Run action appropriateness evaluator on recent agent decisions.
    Returns list of {action, regime, severity, result} dicts.
    """
    decisions = _fetch_recent_decisions(model_id, limit=30)
    drift_runs = _fetch_recent_drift_runs(model_id, limit=30)
    severity_by_id = {r["id"]: r["severity"] for r in drift_runs}

    results = []
    for d in decisions:
        severity = severity_by_id.get(d.get("id"), "medium")
        prompt = ACTION_EVAL_TEMPLATE.format(
            regime=d.get("regime", "unknown"),
            drift_severity=severity,
            action=d.get("action", "monitor"),
        )
        verdict = _llm_classify(prompt)
        results.append({
            "eval_type": "action_appropriateness",
            "action": d.get("action"),
            "regime": d.get("regime"),
            "severity": severity,
            "result": verdict,
            "decision_id": d.get("id"),
        })
    return results


def run_evals(model_id: str = "", experiment_name: str | None = None) -> dict:
    """
    Run all governance evaluations and push results to Phoenix Experiments.
    Returns combined results dict.
    """
    name = experiment_name or f"governance-eval-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M')}"
    logger.info("Running governance evals: %s", name)

    regime_results = run_regime_eval()
    action_results = run_action_eval(model_id)
    all_results = regime_results + action_results

    correct = sum(1 for r in all_results if r.get("result") == "correct")
    total = len(all_results)
    accuracy = correct / total if total > 0 else 0.0

    summary = {
        "experiment_name": name,
        "model_id": model_id,
        "total_evaluated": total,
        "correct": correct,
        "accuracy": accuracy,
        "regime_eval_count": len(regime_results),
        "action_eval_count": len(action_results),
        "results": all_results,
    }

    push_eval_results_to_phoenix(summary, name)
    return summary


def push_eval_results_to_phoenix(results: dict, experiment_name: str) -> None:
    """Push evaluation results to Phoenix Cloud Experiments tab."""
    try:
        import httpx
        base_url = os.getenv("PHOENIX_MCP_BASE_URL", "http://localhost:6006").rstrip("/")
        api_key = os.getenv("PHOENIX_API_KEY", "")
        project = os.getenv("PHOENIX_PROJECT_NAME", "finsight-ai")

        payload = {
            "name": experiment_name,
            "project_name": project,
            "metadata": {
                "model_id": results.get("model_id", ""),
                "accuracy": results.get("accuracy", 0.0),
                "total_evaluated": results.get("total_evaluated", 0),
                "correct": results.get("correct", 0),
                "run_at": datetime.now(timezone.utc).isoformat(),
            },
        }
        headers = {}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"

        with httpx.Client(timeout=15.0) as client:
            resp = client.post(
                f"{base_url}/v1/experiments",
                json=payload,
                headers=headers,
            )
            if resp.status_code < 300:
                logger.info("Eval results pushed to Phoenix: %s (acc=%.2f)", experiment_name, results.get("accuracy", 0))
            else:
                logger.warning("Phoenix experiments push returned %d: %s", resp.status_code, resp.text[:200])
    except Exception as exc:
        logger.warning("push_eval_results_to_phoenix failed: %s", exc)
