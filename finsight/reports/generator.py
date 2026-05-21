"""SR 11-7 compliant PDF report generator — pulls data from DB, calls LLM for prose, renders PDF."""

from __future__ import annotations

import json
import logging
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from finsight.llm import get_llm
from finsight.reports.templates.sr_11_7 import SR117Report, SR117Section
from finsight.reports._prompt import REPORT_WRITER_PROMPT

logger = logging.getLogger(__name__)

_OUTPUT_DIR = Path(__file__).parent / "output"


class ReportGenerator:
    """
    Builds an SR 11-7 compliant governance report for a given model and date range.

    Usage:
        gen = ReportGenerator()
        report = gen.build(model_id="lending_club_v1", date_range="2024-01-01/2024-03-31")
        pdf_path = gen.to_pdf(report)
    """

    def __init__(self) -> None:
        self._llm = get_llm(role="fast")

    def build(self, model_id: str, date_range: str) -> SR117Report:
        """Collect raw data from DB then generate all 7 sections via LLM."""
        start, end = _parse_date_range(date_range)
        raw = _collect_data(model_id, start, end)
        sections = _generate_sections(raw, self._llm)
        return SR117Report(
            model_id=model_id,
            date_range=date_range,
            generated_at=datetime.now(timezone.utc),
            model_identification=sections["model_identification"],
            performance_summary=sections["performance_summary"],
            regime_context=sections["regime_context"],
            drift_analysis=sections["drift_analysis"],
            agent_recommendations=sections["agent_recommendations"],
            risk_assessment=sections["risk_assessment"],
            audit_trail=sections["audit_trail"],
        )

    def to_pdf(self, report: SR117Report) -> Path:
        """Render the SR117Report to a PDF file and return its path."""
        try:
            from reportlab.lib import colors
            from reportlab.lib.pagesizes import letter
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.lib.units import inch
            from reportlab.platypus import (
                SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable,
            )
        except ImportError as exc:
            raise RuntimeError(
                "reportlab is required for PDF generation. "
                "Install it with: pip install reportlab>=4.0.0"
            ) from exc

        _OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        ts = report.generated_at.strftime("%Y%m%d_%H%M%S")
        out_path = _OUTPUT_DIR / f"{report.model_id}_{ts}.pdf"

        doc = SimpleDocTemplate(
            str(out_path),
            pagesize=letter,
            leftMargin=inch,
            rightMargin=inch,
            topMargin=inch,
            bottomMargin=inch,
        )

        styles = getSampleStyleSheet()
        style_title  = ParagraphStyle("ReportTitle",  parent=styles["Title"],  fontSize=18, spaceAfter=6)
        style_meta   = ParagraphStyle("ReportMeta",   parent=styles["Normal"], fontSize=9,  textColor=colors.grey, spaceAfter=16)
        style_h1     = ParagraphStyle("SectionHead",  parent=styles["Heading1"], fontSize=12, spaceBefore=18, spaceAfter=6, textColor=colors.HexColor("#1a3a5c"))
        style_body   = ParagraphStyle("SectionBody",  parent=styles["Normal"], fontSize=10, leading=15, spaceAfter=8)
        style_bullet = ParagraphStyle("Bullet",       parent=styles["Normal"], fontSize=9,  leftIndent=12, spaceAfter=3, textColor=colors.HexColor("#444444"))

        story: list[Any] = []

        # Cover header
        story.append(Paragraph("FinSight AI — Model Governance Report", style_title))
        story.append(Paragraph(
            f"Model: <b>{report.model_id}</b> &nbsp;&nbsp;|&nbsp;&nbsp; "
            f"Period: {report.date_range} &nbsp;&nbsp;|&nbsp;&nbsp; "
            f"Generated: {report.generated_at.strftime('%Y-%m-%d %H:%M UTC')}",
            style_meta,
        ))
        story.append(Paragraph(
            "Prepared in accordance with SR 11-7 — Supervisory Guidance on Model Risk Management "
            "(Federal Reserve, April 2011).",
            style_meta,
        ))
        story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#1a3a5c")))
        story.append(Spacer(1, 0.2 * inch))

        # Seven sections
        for idx, section in enumerate(report.sections(), start=1):
            story.append(Paragraph(f"{idx}. {section.title}", style_h1))
            for para in section.prose.split("\n\n"):
                para = para.strip()
                if para:
                    story.append(Paragraph(para, style_body))
            if section.data_points:
                for point in section.data_points:
                    story.append(Paragraph(f"• {point}", style_bullet))
            story.append(Spacer(1, 0.1 * inch))

        doc.build(story)
        logger.info("Report PDF written to %s", out_path)
        return out_path


# ── Data collection ────────────────────────────────────────────────────────────

def _collect_data(model_id: str, start: datetime, end: datetime) -> dict:
    """Read drift runs, macro snapshots, and agent decisions from SQLite for the report period."""
    try:
        from sqlmodel import Session, select
        from driftguard.store.database import (
            engine, ModelRecord, DriftRun, MacroCache, AgentDecisionLog,
        )

        with Session(engine) as session:
            model = session.exec(
                select(ModelRecord).where(ModelRecord.model_id == model_id)
            ).first()

            drift_runs = session.exec(
                select(DriftRun)
                .where(DriftRun.model_id == model_id)
                .where(DriftRun.checked_at >= start)
                .where(DriftRun.checked_at <= end)
                .order_by(DriftRun.checked_at)  # type: ignore[arg-type]
            ).all()

            macro_records = session.exec(
                select(MacroCache)
                .where(MacroCache.fetched_at >= start)
                .where(MacroCache.fetched_at <= end)
                .order_by(MacroCache.fetched_at)  # type: ignore[arg-type]
            ).all()

            agent_decisions = session.exec(
                select(AgentDecisionLog)
                .where(AgentDecisionLog.model_id == model_id)
                .where(AgentDecisionLog.created_at >= start)
                .where(AgentDecisionLog.created_at <= end)
                .order_by(AgentDecisionLog.created_at)  # type: ignore[arg-type]
            ).all()

        # Deduplicate macro records — MacroCache stores one row per 6-hour fetch.
        # Keep only the most recent record per calendar date for clean report output.
        _seen_dates: set = set()
        _deduped_macro: list = []
        for m in reversed(macro_records):  # reversed = most-recent-first
            day = m.fetched_at.date()
            if day not in _seen_dates:
                _seen_dates.add(day)
                _deduped_macro.append(m)
        _deduped_macro.reverse()  # restore chronological order

        return {
            "model": {
                "model_id": model.model_id if model else model_id,
                "description": model.description if model else "",
                "created_at": str(model.created_at) if model else "unknown",
                "baseline_row_count": model.baseline_row_count if model else None,
            },
            "drift_runs": [
                {
                    "id": r.id,
                    "checked_at": str(r.checked_at),
                    "severity": r.overall_severity,
                    "drift_score": r.drift_score,
                    "regime": r.regime,
                    "regime_confidence": r.regime_confidence,
                    "feature_results": _safe_json(r.feature_results_json),
                    "phoenix_trace_id": r.phoenix_trace_id,
                }
                for r in drift_runs
            ],
            "macro_snapshots": [
                {
                    "fetched_at": str(m.fetched_at),
                    "vix": m.vix,
                    "credit_spread": m.credit_spread,
                    "fed_funds_rate": m.fed_funds_rate,
                    "yield_curve": m.yield_curve,
                    "regime": m.regime,
                    "regime_confidence": m.regime_confidence,
                }
                for m in _deduped_macro
            ],
            "agent_decisions": [
                {
                    "id": d.id,
                    "created_at": str(d.created_at),
                    "query": d.query,
                    "action": d.action,
                    "recommendation": d.recommendation,
                    "confidence": d.confidence,
                    "regime_context": d.regime_context,
                    "trace_ids": _safe_json(d.trace_ids_referenced),
                }
                for d in agent_decisions
            ],
        }

    except Exception as exc:
        logger.warning("DB data collection failed: %s — using empty dataset", exc)
        return {
            "model": {"model_id": model_id, "description": "", "created_at": "unknown", "baseline_row_count": None},
            "drift_runs": [],
            "macro_snapshots": [],
            "agent_decisions": [],
        }


# ── LLM section generation ─────────────────────────────────────────────────────

def _generate_sections(raw: dict, llm) -> dict[str, SR117Section]:
    """Single LLM call returns JSON with prose for all 7 sections.

    Only a representative slice of runs/snapshots is sent to the LLM —
    the full dataset is still used for data_points in the rendered sections.
    This keeps the prompt well within free-tier TPM limits on Groq.
    """
    # Build a compact run summary for the LLM — feature_results is a full
    # per-detector list (~1,400 tokens/run) that the LLM doesn't need for prose.
    # Replace it with the top-3 drifted feature names derived from the same data.
    def _slim_run(r: dict) -> dict:
        fr = r.get("feature_results") or {}
        if isinstance(fr, list):
            scores = {entry["feature_name"]: entry["score"] for entry in fr if isinstance(entry, dict)}
        elif isinstance(fr, dict):
            scores = {k: (v.get("score", 0) if isinstance(v, dict) else 0) for k, v in fr.items()}
        else:
            scores = {}
        top = sorted(scores, key=scores.get, reverse=True)[:3]  # type: ignore[arg-type]
        return {k: v for k, v in r.items() if k != "feature_results"} | {"top_features": top}

    llm_raw = {
        **raw,
        # 5 most-recent runs, feature_results stripped down to top-3 names
        "drift_runs":       [_slim_run(r) for r in raw["drift_runs"][-5:]],
        "macro_snapshots":  raw["macro_snapshots"][:3],
        "agent_decisions":  raw["agent_decisions"],
        # Pass total so the LLM cites the real count, not the capped slice
        "total_drift_runs": len(raw["drift_runs"]),
    }
    context = json.dumps(llm_raw, indent=2, default=str)
    messages = [
        {"role": "system", "content": REPORT_WRITER_PROMPT},
        {"role": "user", "content": f"RAW_DATA:\n{context}"},
    ]
    try:
        response = llm.complete(messages, temperature=0.3)
        return _parse_section_response(response.content, raw)
    except Exception as exc:
        logger.error("LLM section generation failed: %s — using fallback prose", exc)
        return _fallback_sections(raw)


def _parse_section_response(content: str, raw: dict) -> dict[str, SR117Section]:
    """Extract JSON section map from LLM response, falling back gracefully."""
    cleaned = re.sub(r"```(?:json)?\s*", "", content)
    cleaned = re.sub(r"```", "", cleaned).strip()
    match = re.search(r"\{.*\}", cleaned, re.DOTALL)

    if not match:
        logger.warning("LLM returned no JSON — using fallback sections")
        return _fallback_sections(raw)

    try:
        data = json.loads(match.group())
    except json.JSONDecodeError:
        return _fallback_sections(raw)

    model_id = raw["model"]["model_id"]
    runs = raw["drift_runs"]
    decisions = raw["agent_decisions"]
    agent_trace_ids = [tid for d in decisions for tid in (d.get("trace_ids") or [])]
    run_trace_ids = [r["phoenix_trace_id"] for r in runs if r.get("phoenix_trace_id")]
    # Merge and deduplicate, preserving order
    all_trace_ids = list(dict.fromkeys(agent_trace_ids + run_trace_ids))

    def _section(key: str, title: str, data_fn) -> SR117Section:
        return SR117Section(
            title=title,
            prose=data.get(key, f"No data available for {title}."),
            data_points=data_fn(),
        )

    return {
        "model_identification": _section(
            "model_identification", "Model Identification",
            lambda: [
                f"Model ID: {model_id}",
                f"Description: {raw['model']['description'] or 'N/A'}",
                f"Registered: {raw['model']['created_at']}",
                f"Baseline rows: {raw['model']['baseline_row_count'] or 'N/A'}",
            ],
        ),
        "performance_summary": _section(
            "performance_summary", "Performance Summary",
            lambda: [
                f"Drift run #{r['id']} on {r['checked_at'][:10]}: severity={r['severity']}, PSI={r['drift_score']:.4f}"
                for r in runs
            ],
        ),
        "regime_context": _section(
            "regime_context", "Regime Context",
            lambda: [
                f"{m['fetched_at'][:10]}: regime={m['regime']}, VIX={m['vix']}, spread={m['credit_spread']}"
                for m in raw["macro_snapshots"]
            ],
        ),
        "drift_analysis": _section(
            "drift_analysis", "Drift Analysis",
            lambda: _top_drifted_features(runs),
        ),
        "agent_recommendations": _section(
            "agent_recommendations", "Agent Recommendations",
            lambda: [
                f"{d['created_at'][:10]}: action={d['action']}, confidence={d['confidence']:.2f}"
                for d in decisions
            ],
        ),
        "risk_assessment": _section(
            "risk_assessment", "Risk Assessment",
            lambda: [
                f"Max drift score in period: {max((r['drift_score'] for r in runs), default=0):.4f}",
                f"Unique regimes observed: {', '.join({r['regime'] for r in runs if r['regime']})}",
                f"Total agent decisions: {len(decisions)}",
            ],
        ),
        "audit_trail": _section(
            "audit_trail", "Audit Trail",
            lambda: [f"Phoenix trace ID: {tid}" for tid in all_trace_ids]
            + [f"DB drift run ID: {r['id']} — {r['checked_at'][:10]}" for r in runs],
        ),
    }


def _fallback_sections(raw: dict) -> dict[str, SR117Section]:
    """Minimal fallback when LLM is unavailable — data points only, no prose."""
    model_id = raw["model"]["model_id"]
    runs = raw["drift_runs"]

    _titles = {
        "model_identification": "Model Identification",
        "performance_summary":  "Performance Summary",
        "regime_context":       "Regime Context",
        "drift_analysis":       "Drift Analysis",
        "agent_recommendations":"Agent Recommendations",
        "risk_assessment":      "Risk Assessment",
        "audit_trail":          "Audit Trail",
    }
    return {
        key: SR117Section(
            title=title,
            prose=f"[LLM unavailable — raw data below for {title}]",
            data_points=[
                f"Model: {model_id}",
                f"Drift runs in period: {len(runs)}",
            ],
        )
        for key, title in _titles.items()
    }


# ── Utilities ──────────────────────────────────────────────────────────────────

def _parse_date_range(date_range: str) -> tuple[datetime, datetime]:
    """Parse 'YYYY-MM-DD/YYYY-MM-DD' into (start, end) UTC datetimes.

    Date-only strings (no time component) are treated as start-of-day for
    the start bound and end-of-day for the end bound, so that all runs
    timestamped during the final calendar day are included.
    """
    from datetime import timedelta

    def _parse_one(s: str) -> datetime:
        dt = datetime.fromisoformat(s.strip())
        return dt.replace(tzinfo=timezone.utc)

    try:
        parts = date_range.split("/")
        start = _parse_one(parts[0])
        end   = _parse_one(parts[1])
        # Date-only end (time == midnight) → extend to end-of-day so today's
        # runs aren't excluded by a < 00:00:00 cutoff.
        if end.hour == 0 and end.minute == 0 and end.second == 0:
            end = end + timedelta(days=1) - timedelta(microseconds=1)
        return start, end
    except Exception:
        # Fallback: last 365 days — covers seeded runs stored months ago
        now = datetime.now(timezone.utc)
        return now - timedelta(days=365), now


def _safe_json(s: str) -> Any:
    try:
        return json.loads(s)
    except Exception:
        return {}


def _top_drifted_features(runs: list[dict], top_n: int = 5) -> list[str]:
    """Extract the worst-drifting feature names across all runs."""
    feature_scores: dict[str, float] = {}
    for run in runs:
        fr = run.get("feature_results") or {}
        if isinstance(fr, dict):
            for feat, result in fr.items():
                score = result.get("score", 0) if isinstance(result, dict) else 0
                feature_scores[feat] = max(feature_scores.get(feat, 0), score)
    sorted_feats = sorted(feature_scores.items(), key=lambda x: x[1], reverse=True)
    return [f"{feat}: max PSI {score:.4f}" for feat, score in sorted_feats[:top_n]]
