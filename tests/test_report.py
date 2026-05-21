"""Tests for Step 8 — SR 11-7 regulatory report generation."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch


# ── SR117 dataclass ───────────────────────────────────────────────────────────

def test_sr117_report_sections_order():
    from finsight.reports.templates.sr_11_7 import SR117Report, SR117Section

    def _sec(title: str) -> SR117Section:
        return SR117Section(title=title, prose="prose", data_points=["dp"])

    report = SR117Report(
        model_id="test_model",
        date_range="2024-01-01/2024-03-31",
        generated_at=datetime.now(timezone.utc),
        model_identification=_sec("Model Identification"),
        performance_summary=_sec("Performance Summary"),
        regime_context=_sec("Regime Context"),
        drift_analysis=_sec("Drift Analysis"),
        agent_recommendations=_sec("Agent Recommendations"),
        risk_assessment=_sec("Risk Assessment"),
        audit_trail=_sec("Audit Trail"),
    )

    sections = report.sections()
    assert len(sections) == 7
    assert sections[0].title == "Model Identification"
    assert sections[6].title == "Audit Trail"


# ── Date range parsing ────────────────────────────────────────────────────────

def test_parse_date_range_valid():
    from finsight.reports.generator import _parse_date_range

    start, end = _parse_date_range("2024-01-01/2024-03-31")
    assert start.year == 2024 and start.month == 1 and start.day == 1
    assert end.year == 2024 and end.month == 3 and end.day == 31
    assert start.tzinfo is not None


def test_parse_date_range_fallback_on_bad_input():
    from finsight.reports.generator import _parse_date_range

    start, end = _parse_date_range("not-a-date")
    # Should fall back to last 30 days
    assert (end - start).days == 30


# ── Section generation ────────────────────────────────────────────────────────

_SAMPLE_RAW = {
    "model": {
        "model_id": "lending_club_v1",
        "description": "LightGBM credit default model",
        "created_at": "2024-01-01T00:00:00",
        "baseline_row_count": 5000,
    },
    "drift_runs": [
        {
            "id": 1,
            "checked_at": "2024-02-15T10:00:00",
            "severity": "high",
            "drift_score": 0.22,
            "regime": "credit_stress",
            "regime_confidence": 0.87,
            "feature_results": {"int_rate": {"score": 0.22, "severity": "high"}},
        }
    ],
    "macro_snapshots": [
        {
            "fetched_at": "2024-02-15T10:00:00",
            "vix": 28.4,
            "credit_spread": 2.1,
            "fed_funds_rate": 5.25,
            "yield_curve": -0.4,
            "regime": "credit_stress",
            "regime_confidence": 0.87,
        }
    ],
    "agent_decisions": [
        {
            "id": 1,
            "created_at": "2024-02-15T10:01:00",
            "query": "analyze:lending_club_v1",
            "action": "monitor",
            "recommendation": "Macro-driven drift. Do not retrain.",
            "confidence": 0.91,
            "regime_context": "credit_stress",
            "trace_ids": ["trace-abc-123"],
        }
    ],
}


def test_generate_sections_with_mock_llm():
    from finsight.reports.generator import _generate_sections

    mock_llm = MagicMock()
    mock_response = MagicMock()
    mock_response.content = json.dumps({
        "model_identification": "The model lending_club_v1 is a LightGBM credit default model.",
        "performance_summary":  "One drift run was recorded on 2024-02-15 with high severity.",
        "regime_context":       "The macroeconomic regime was credit_stress with VIX at 28.4.",
        "drift_analysis":       "Feature int_rate showed the highest drift with PSI 0.2200.",
        "agent_recommendations":"The governance agent recommended monitoring without retraining.",
        "risk_assessment":      "Risk is elevated due to macro regime, not model decay.",
        "audit_trail":          "All drift runs and agent decisions are documented below.",
    })
    mock_llm.complete.return_value = mock_response

    sections = _generate_sections(_SAMPLE_RAW, mock_llm)

    assert set(sections.keys()) == {
        "model_identification", "performance_summary", "regime_context",
        "drift_analysis", "agent_recommendations", "risk_assessment", "audit_trail",
    }
    assert "lending_club_v1" in sections["model_identification"].prose
    assert sections["drift_analysis"].data_points  # feature data points populated
    assert "trace-abc-123" in sections["audit_trail"].data_points[-2]  # trace ID cited


def test_generate_sections_fallback_on_bad_llm_response():
    from finsight.reports.generator import _generate_sections

    mock_llm = MagicMock()
    mock_response = MagicMock()
    mock_response.content = "this is not json"
    mock_llm.complete.return_value = mock_response

    sections = _generate_sections(_SAMPLE_RAW, mock_llm)

    # Fallback sections must still cover all 7 keys
    assert len(sections) == 7
    for sec in sections.values():
        assert sec.title
        assert sec.prose


# ── Full build (mocked DB + LLM) ──────────────────────────────────────────────

def test_report_generator_build():
    from finsight.reports.generator import ReportGenerator

    with patch("finsight.reports.generator._collect_data", return_value=_SAMPLE_RAW), \
         patch("finsight.reports.generator.get_llm") as mock_get_llm:

        mock_llm = MagicMock()
        mock_response = MagicMock()
        mock_response.content = json.dumps({
            k: f"Prose for {k}." for k in [
                "model_identification", "performance_summary", "regime_context",
                "drift_analysis", "agent_recommendations", "risk_assessment", "audit_trail",
            ]
        })
        mock_llm.complete.return_value = mock_response
        mock_get_llm.return_value = mock_llm

        gen = ReportGenerator()
        report = gen.build("lending_club_v1", "2024-01-01/2024-03-31")

    assert report.model_id == "lending_club_v1"
    assert report.date_range == "2024-01-01/2024-03-31"
    assert len(report.sections()) == 7
    assert report.generated_at.tzinfo is not None


# ── PDF rendering ─────────────────────────────────────────────────────────────

def test_to_pdf_produces_file(tmp_path):
    """Verify PDF renders without errors and produces a non-empty file."""
    pytest = __import__("pytest")
    reportlab = pytest.importorskip("reportlab", reason="reportlab not installed")

    from finsight.reports.templates.sr_11_7 import SR117Report, SR117Section
    from finsight.reports.generator import ReportGenerator

    def _sec(title: str) -> SR117Section:
        return SR117Section(title=title, prose="Sample prose paragraph.", data_points=["data point one"])

    report = SR117Report(
        model_id="test_model",
        date_range="2024-01-01/2024-03-31",
        generated_at=datetime.now(timezone.utc),
        model_identification=_sec("Model Identification"),
        performance_summary=_sec("Performance Summary"),
        regime_context=_sec("Regime Context"),
        drift_analysis=_sec("Drift Analysis"),
        agent_recommendations=_sec("Agent Recommendations"),
        risk_assessment=_sec("Risk Assessment"),
        audit_trail=_sec("Audit Trail"),
    )

    with patch("finsight.reports.generator._OUTPUT_DIR", tmp_path):
        gen = ReportGenerator.__new__(ReportGenerator)  # skip __init__ to avoid LLM init
        pdf_path = gen.to_pdf(report)

    assert pdf_path.exists()
    assert pdf_path.stat().st_size > 1024   # at least 1 KB — real PDF
    assert pdf_path.suffix == ".pdf"
