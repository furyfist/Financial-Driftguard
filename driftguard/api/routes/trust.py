"""Trust route — GET /trust/{model_id} for agent-to-agent model trustworthiness queries."""

import logging

from fastapi import APIRouter, HTTPException
from sqlmodel import Session, select

from ...store.database import ModelRecord, engine
from ..schemas import TrustScoreOut

router = APIRouter(prefix="/trust", tags=["trust"])
logger = logging.getLogger(__name__)


@router.get("/{model_id}", response_model=TrustScoreOut)
def get_trust_score(model_id: str, context: str = ""):
    """
    Return a structured trust score for a financial ML model.

    Designed for agent-to-agent consumption — a credit decisioning agent calls this
    before using the model to confirm it is currently trustworthy.

    - No LLM involved: pure DB read + deterministic decision matrix.
    - Zero auth for hackathon; add API-key gating before production.
    - context: optional hint about intended use (e.g. 'credit scoring $50K loans').
    """
    # Verify the model exists — return 404 rather than a stale/meaningless score
    with Session(engine) as session:
        model = session.exec(
            select(ModelRecord).where(ModelRecord.model_id == model_id)
        ).first()
    if not model:
        raise HTTPException(status_code=404, detail=f"Model '{model_id}' not found")

    try:
        from finsight.trust_api import TrustHandler
        ts = TrustHandler().score(model_id=model_id, context=context)
    except Exception as exc:
        logger.error("TrustHandler.score failed for %s: %s", model_id, exc, exc_info=True)
        raise HTTPException(status_code=503, detail=f"Trust scoring unavailable: {exc}")

    return TrustScoreOut(
        model_id=ts.model_id,
        trustworthy=ts.trustworthy,
        confidence=ts.confidence,
        regime=ts.regime,
        drift_severity=ts.drift_severity,
        recommendation=ts.recommendation,
        reason=ts.reason,
        last_checked=ts.last_checked,
        next_check_recommended=ts.next_check_recommended,
    )
