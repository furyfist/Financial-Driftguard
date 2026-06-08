"""Experiment routes — POST /experiments/{model_id}/challenger, GET /experiments/{model_id}/results."""

import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from ...store.database import ModelRecord, get_session
from ..schemas import ChallengerResultOut

router = APIRouter(prefix="/experiments", tags=["experiments"])
logger = logging.getLogger(__name__)


def _run_challenger(model_id: str) -> ChallengerResultOut:
    """Shared logic for trigger and results endpoints."""
    try:
        from finsight.challenger import ChallengerRunner
        result = ChallengerRunner().run(model_id)
        return ChallengerResultOut(
            model_id=result.model_id,
            status=result.status,
            champion_run_id=result.champion_run_id,
            challenger_run_id=result.challenger_run_id,
            champion_drift_score=result.champion_drift_score,
            challenger_drift_score=result.challenger_drift_score,
            champion_severity=result.champion_severity,
            challenger_severity=result.challenger_severity,
            winner=result.winner,
            drift_score_delta=result.drift_score_delta,
            drifted_features=result.drifted_features,
            recommendation=result.recommendation,
            triggered_at=result.triggered_at,
        )
    except ImportError:
        raise HTTPException(
            status_code=503,
            detail="FinSight not installed — run: pip install -e '.[llm,tracing,agent]'",
        )
    except Exception as exc:
        logger.error("Champion-challenger failed for %r: %s", model_id, exc, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Comparison failed: {exc}")


@router.post("/{model_id}/challenger", response_model=ChallengerResultOut)
def trigger_challenger(
    model_id: str,
    session: Session = Depends(get_session),
):
    """
    Trigger a champion-challenger comparison for a model.
    Returns immediately with comparison results (synchronous — no queuing needed).
    """
    model = session.exec(
        select(ModelRecord).where(ModelRecord.model_id == model_id)
    ).first()
    if not model:
        raise HTTPException(status_code=404, detail=f"Model '{model_id}' not found")
    return _run_challenger(model_id)


@router.get("/{model_id}/results", response_model=ChallengerResultOut)
def get_results(
    model_id: str,
    session: Session = Depends(get_session),
):
    """
    Return the current champion-challenger comparison for a model.
    Re-runs the comparison on each call (stateless — results reflect latest DB state).
    """
    model = session.exec(
        select(ModelRecord).where(ModelRecord.model_id == model_id)
    ).first()
    if not model:
        raise HTTPException(status_code=404, detail=f"Model '{model_id}' not found")
    return _run_challenger(model_id)


@router.post("/{model_id}/evals")
def run_governance_evals(model_id: str):
    """
    Run LLM-as-Judge governance evals for a model and push results to Phoenix.
    Evaluates recent agent decisions for regime classification and action appropriateness.
    """
    try:
        from finsight.evals.governance_eval import run_evals
        results = run_evals(model_id=model_id)
        return {
            "experiment_name": results["experiment_name"],
            "model_id": results["model_id"],
            "total_evaluated": results["total_evaluated"],
            "accuracy": results["accuracy"],
            "correct": results["correct"],
            "regime_eval_count": results["regime_eval_count"],
            "action_eval_count": results["action_eval_count"],
        }
    except ImportError:
        raise HTTPException(
            status_code=503,
            detail="FinSight not installed — run: pip install -e '.[llm,tracing,agent]'",
        )
    except Exception as exc:
        logger.error("Governance evals failed for %r: %s", model_id, exc, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Evals failed: {exc}")
