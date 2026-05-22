"""Agent routes — POST /agent/ask, POST /agent/analyze, POST /agent/report, GET /agent/log."""

import json
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlmodel import Session, select, desc

from ...store.database import AgentDecisionLog, ModelRecord, get_session
from ..schemas import (
    AgentAskRequest,
    AgentAnalyzeRequest,
    AgentResponseOut,
    AgentLogOut,
    ReportRequest,
    ReportOut,
)

router = APIRouter(prefix="/agent", tags=["agent"])
logger = logging.getLogger(__name__)


# ── Routes ────────────────────────────────────────────────────────────────────

@router.post("/analyze", response_model=AgentResponseOut)
def analyze(
    request: AgentAnalyzeRequest,
    session: Session = Depends(get_session),
):
    """
    Autonomous drift governance analysis.
    The agent calls its tools (macro, drift, Phoenix traces) and returns a
    structured recommendation with an action, confidence, and reasoning.
    """
    model = session.exec(
        select(ModelRecord).where(ModelRecord.model_id == request.model_id)
    ).first()
    if not model:
        raise HTTPException(
            status_code=404, detail=f"Model '{request.model_id}' not found"
        )

    result = _run_agent(lambda agent: agent.analyze(model_id=request.model_id))
    _persist(session, result, query=f"analyze:{request.model_id}")

    return AgentResponseOut(
        recommendation=result.recommendation,
        action=result.action,
        confidence=result.confidence,
        reasoning=result.reasoning,
        sources=result.sources,
        model_id=result.model_id,
        regime=result.regime,
    )


@router.post("/ask", response_model=AgentResponseOut)
def ask(
    request: AgentAskRequest,
    session: Session = Depends(get_session),
):
    """
    Conversational governance query — the risk officer chat interface.
    Accepts free-text questions; the agent calls tools as needed before answering.
    """
    result = _run_agent(
        lambda agent: agent.ask(query=request.query, model_id=request.model_id)
    )
    _persist(session, result, query=request.query)

    return AgentResponseOut(
        recommendation=result.recommendation,
        action=result.action,
        confidence=result.confidence,
        reasoning=result.reasoning,
        sources=result.sources,
        model_id=result.model_id,
        regime=result.regime,
    )


@router.post("/report", response_class=FileResponse)
def generate_report(
    request: ReportRequest,
    session: Session = Depends(get_session),
):
    """
    Generate an SR 11-7 compliant PDF report for a model over a date range.
    Returns the PDF as a file download.
    date_range format: "YYYY-MM-DD/YYYY-MM-DD" (empty string → last 30 days).
    """
    model = session.exec(
        select(ModelRecord).where(ModelRecord.model_id == request.model_id)
    ).first()
    if not model:
        raise HTTPException(status_code=404, detail=f"Model '{request.model_id}' not found")

    date_range = request.date_range or _default_date_range()

    try:
        from finsight.reports import ReportGenerator
        gen = ReportGenerator()
        report = gen.build(model_id=request.model_id, date_range=date_range)
        pdf_path = gen.to_pdf(report)
    except ImportError as exc:
        logger.error("finsight.reports not available: %s", exc)
        raise HTTPException(
            status_code=503,
            detail="Report generation requires: pip install reportlab>=4.0.0",
        )
    except Exception as exc:
        logger.error("Report generation failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=503, detail=f"Report generation failed: {exc}")

    return FileResponse(
        path=str(pdf_path),
        media_type="application/pdf",
        filename=pdf_path.name,
    )


@router.get("/log", response_model=list[AgentLogOut])
def get_agent_log(
    limit: int = 20,
    model_id: str | None = None,
    session: Session = Depends(get_session),
):
    """Return recent agent decisions for audit trail and dashboard display."""
    query = select(AgentDecisionLog).order_by(desc(AgentDecisionLog.created_at))
    if model_id:
        query = query.where(AgentDecisionLog.model_id == model_id)
    records = session.exec(query.limit(limit)).all()
    return records


# ── Helpers ───────────────────────────────────────────────────────────────────

def _run_agent(fn):
    """
    Instantiate the agent and call fn(agent). Returns AgentResponse.
    Returns HTTP 503 if finsight is not installed or the LLM is unavailable.
    """
    try:
        from finsight.agent import DriftGuardAgent
        agent = DriftGuardAgent()
        return fn(agent)
    except ImportError as exc:
        logger.error("finsight package not installed: %s", exc)
        raise HTTPException(
            status_code=503,
            detail="FinSight AI is not installed. Run: pip install -e '.[llm,tracing,agent]'",
        )
    except Exception as exc:
        logger.error("Agent call failed: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=503,
            detail=f"Agent unavailable: {exc}",
        )


def _default_date_range() -> str:
    from datetime import timedelta
    end   = datetime.now(timezone.utc)
    start = end - timedelta(days=365)  # cover seeded runs stored months ago
    return f"{start.strftime('%Y-%m-%d')}/{end.strftime('%Y-%m-%d')}"


def _persist(session: Session, result, query: str) -> None:
    """Write the agent decision to the audit log. Never raises — audit failure must not block response."""
    try:
        log = AgentDecisionLog(
            model_id=result.model_id,
            query=query,
            recommendation=result.recommendation,
            action=result.action,
            confidence=result.confidence,
            regime_context=result.regime or "",
            trace_ids_referenced=json.dumps(result.sources),
        )
        session.add(log)
        session.commit()
    except Exception as exc:
        logger.warning("Failed to persist agent decision log: %s", exc)
