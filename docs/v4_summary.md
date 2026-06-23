# FinSight AI — V4 Implementation Summary

**Document type:** Internal engineering milestone summary
**Version tagged:** `v0.4.0`
**Built on top of:** V3 — governance agent, Phoenix tracing, MCP bridge, trust API, SR 11-7 PDF report
**Date:** May–June 2026

---

## What V4 Was About

V3 proved the thesis. V4 made it **demo-ready, user-ready, and production-closer** across three tracks:

- **Track A — Visual Polish:** HALT overlay, regime-banded drift chart, demo scenario control panel, structured agent chat cards, PDF cover page
- **Track B — User Features:** Slack/email alerts, explainable drift, weekly digest, natural language query, model version registry
- **Track C — Production Foundations:** Google ADK 2.0 scaffold, API authentication, Phoenix trace ID linkage, V2 tech debt cleanup, full Docker Compose

---

## What Was Delivered

### Track A — Visual Polish

**HALT Overlay (`HaltOverlay.tsx`)**
Full-screen dark overlay fires for 2 seconds when regime flips to `black_swan`. HALT in 120px red (`#C0200F`), ring pulse animation, subtext "All automated decisions frozen." Auto-dismisses after 2s. Trigger: `ModelDetail.tsx` watches latest drift run — fires only on new runs.

**Drift Chart with Regime Colour Bands (`DriftChart.tsx`)**
Replaced single-point LineChart with a 13-run Recharts chart. `ReferenceArea` components shade regime periods (green/amber/red tints). Data points coloured by regime. Hover tooltip shows regime badge, severity, top drifted feature, and recommendation snippet. Horizontal `ReferenceLine` at PSI threshold 0.10.

**Demo Scenario Control Panel (`DemoPanel.tsx`)**
Three scenario cards (Rate Hike, COVID Crash, Normal Decay) with Run buttons. Fires `POST /demo/scenarios/{name}` — no terminals needed during demos. Loading spinner, live log output in DM Mono. Visible only on `?demo=true` URL param. Backend endpoint wraps the existing scenario scripts.

**Agent Chat Structured Response Cards (`AgentResponseCard.tsx`)**
Upgraded from plain text bubbles to structured cards: regime badge, severity pill, confidence progress bar, bold recommendation, impact box, source chips, typing animation. Suggestion chips when chat is empty ("Is my lending model safe right now?", "Should I retrain?").

**PDF Cover Page**
Added before Section 1 of the SR 11-7 report: FinSight AI branding, regime status box, model name, reporting period, exec summary from latest agent recommendation, CONFIDENTIAL watermark.

---

### Track B — User Features

**Slack/Email Alerts with Regime Context (B1)**
Enriched the existing `SlackNotifier` payload with regime, confidence, recommended action, top 3 drifted features, estimated dollar impact. Added `EmailNotifier` adapter (SMTP via `smtplib` — no new deps). Wired into `brain.py` — fires after every high/critical agent decision.

New file: `finsight/notifications/enricher.py` — takes `AgentResponse` + `ImpactEstimate` → enriched payload.

Env vars: `SLACK_WEBHOOK_URL`, `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `ALERT_EMAIL_TO`.

**Explainable Drift (B3)**
New tool `explain_feature_drift(feature_name, drift_result, regime, macro)` in `drift_tools.py`. Calls LLM with feature's domain role, current PSI/KS/JS scores, macro context, and historical pattern lookup. Fires automatically for high/critical severity features.

New file: `finsight/impact/feature_metadata.py` — static domain descriptions for all 17 Lending Club features (e.g. "int_rate: Loan interest rate — directly affected by Fed policy").

Frontend: expandable "Why did this drift?" section in `ActionCard.tsx`.

**Weekly Digest (B4)**
`DigestGenerator` in `finsight/reports/digest.py` runs every Monday 08:00 UTC via APScheduler. Per-model status light (green/amber/red), regime comparison week-over-week, drift trend arrow, agent decision count, 7-day forecast summary, one-line verdict. Reuses B1 notification infrastructure.

`DigestReport` dataclass: `status_light`, `regime_current`, `regime_previous`, `drift_trend`, `agent_decisions_count`, `forecast_summary`, `one_liner`.

Guard: only fires if ≥3 drift runs exist for the model.

**Natural Language Drift Query (B2)**
New tool `query_drift_history(filters)` in `finsight/agent/tools/query_tools.py`. Filters: `regime`, `severity`, `date_range`, `feature_name`, `model_id`. `/drift/{model_id}/history` gained new query params: `regime`, `severity`, `feature`, `since`, `until`. Agent translates NL questions into structured queries.

**Model Version Registry (B5)**
`ModelVersion` SQLModel table: `version_label`, `description`, `baseline_blob`, `is_active`, `promoted_at`. Existing drift runs auto-assigned to `v1` on migration. `DriftRun` and `AgentDecisionLog` carry `model_version_id` FK.

API routes: `POST /models/{id}/versions`, `GET /models/{id}/versions`, `POST /models/{id}/versions/{v}/promote`, `GET /drift/{id}/history?version={v}`.

Dashboard: version selector dropdown in `ModelDetail.tsx`. Switching version filters the drift chart and all data below it.

---

### Track C — Production Foundations

**API Authentication (C2)**
`APIKeyMiddleware` in `driftguard/api/auth.py`. Reads `API_KEY` from env. Validates `X-API-Key` header on all routes. `GET /health` is exempt. If `API_KEY` is unset, all requests pass through (local dev mode).

**Phoenix Trace ID Linkage (C3)**
`phoenix_trace_id` column added to `DriftRun`. Populated after each traced drift run from the active span context. Agent decision sources now reference real OTEL trace UUIDs rather than DB run IDs.

**Section 7 Prose Count Fix (C4)**
`total_run_count: int` passed directly to the Section 7 LLM prompt. Eliminates the "5 drift checks" prose vs "13 IDs in audit trail" inconsistency from V3.

**V2 Tech Debt Cleanup (C5)**

| Item | Fix |
|---|---|
| `drifted_features` count inflated | Deduplicated by feature name — PSI+KS+JS on same feature now counts as 1 |
| Webhook config lost on restart | New `WebhookConfigRecord` SQLModel table; loaded on startup |
| No scheduler health endpoint | `GET /health/scheduler` returns APScheduler job states and next run times |
| Macro fetch blocks startup | Promoted to background thread in lifespan; server starts immediately |
| Silent missing env var | Startup warns on missing `FRED_API_KEY` instead of failing silently |
| No minimum row validation | `DataSnapshot.from_dataframe()` raises `ValueError` if < 100 rows |

**Google ADK 2.0 Scaffold (C1)**
New `finsight/adk/` package: `agents.py`, `tools.py`, `config.py`. `AGENT_FRAMEWORK=adk` activates multi-agent path: `governance_agent` (Gemini 2.5 Pro) orchestrates `analyst_agent` + `report_agent` (Gemini Flash). `AGENT_FRAMEWORK=native` (default) keeps existing Groq path fully intact. ADK import errors caught silently — native path always works without `google-adk` installed.

**Docker Compose Full Stack (C6)**
Single `docker compose up` starts: Phoenix (`localhost:6006`), Phoenix MCP sidecar, FastAPI backend (`localhost:8000`), and React dashboard (`localhost:5173`). SQLite volume-mounted to preserve data across container restarts.

---

## Verified Demo Results

All on Windows / Python 3.11 / Groq `llama-3.3-70b-versatile`:

| Test | Result | Key output |
|---|---|---|
| `GET /health` | PASS | `{"status":"ok"}` |
| `GET /drift/macro/latest` | PASS | VIX=17.28, regime=stable, confidence=1.0 |
| Rate hike scenario | PASS | drift=0.0493, severity=HIGH, credit_stress, monitor |
| COVID crash scenario | PASS | drift=0.0754, severity=CRITICAL, black_swan, HALT |
| Normal decay scenario | PASS | drift=0.0368, severity=HIGH, stable, retrain |
| `POST /agent/ask` | PASS | confidence=0.8, action=investigate |
| `GET /trust/lending_club_v1` | PASS | trustworthy=false, recommendation=escalate |
| `demo_full.py --auto` | PASS | 3/3 scenarios, 26.6s total |
| PDF report | PASS | 13 runs, 3 regimes, 7 LLM-written sections, cover page |

---

## Known Gaps (Going into V5)

| Gap | Notes |
|---|---|
| ADK 2.0 path not end-to-end validated | Scaffold ready, `AGENT_FRAMEWORK=adk` activates it. Native path is production. |
| Slack notifier not tested against live workspace | Block Kit payload is built and enriched; delivery unverified. |
| Recession classifier recall = 0% | Inherited from V2. Binary sub-classifier planned for V5. |
| SQLite concurrency | Single-user local only. PostgreSQL migration = V5. |
| Gemini swap not smoke-tested | Mechanical (3 env vars). Budget 2–3h for prompt tuning on swap. |
| Rate hike scenario filename misleading | `rate_hike_2017.py` uses Q4 2018 peak values. Cosmetic. |

---

## How to Run (V4)

### Option A — Docker
```bash
cp .env.example .env   # add FRED_API_KEY, GROQ_API_KEY
docker compose up
# Backend: http://localhost:8000 | Dashboard: http://localhost:5173 | Phoenix: http://localhost:6006
```

### Option B — Manual
```powershell
# Terminal 1 — Phoenix
docker compose up phoenix

# Terminal 2 — Backend
venv\Scripts\activate
uvicorn driftguard.api.main:app --reload

# Terminal 3 — Seed (once)
python demo\lending_club.py

# Terminal 4 — Dashboard
cd dashboard && npm run dev

# Full demo
python scripts\demo_full.py --auto
```

---

*FinSight AI V4 — May–June 2026*
*Built on V3 (hackathon submission, v0.3.0)*
