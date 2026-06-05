# FinSight AI — Project Status

**Document type:** Living engineering status document  
**Last updated:** June 2026  
**Current version:** `v0.4.0` (post-V4, all sessions complete)  
**Branch:** `main`

---

## What This Project Is

FinSight AI is a **regime-aware financial model governance agent**. It monitors ML models in production and distinguishes between two failure modes that every other tool conflates:

- **Market regime shift** (rate hike, recession, black swan) → drift is expected, **do not retrain**
- **Model decay** (data pipeline change, population drift) → drift is real, **retrain immediately**

Same drift signal. Opposite actions. The regime is the deciding variable. No horizontal tool (Arize AX, WhyLabs, Evidently, MLflow) makes this distinction.

The thesis is validated on a LightGBM credit default model (Lending Club, AUC 0.69) monitored through the 2017–2018 Federal Reserve hiking cycle. The system correctly classifies `int_rate` drift as macro-driven (`credit_stress`) and recommends against retraining — the operationally correct call.

---

## Version History at a Glance

| Version | Tag | Theme | Key deliverable |
|---|---|---|---|
| V1 | `v0.1.0` | Core library | PSI + KS + JS detectors, rule-based regime tagger, FastAPI, React dashboard, Lending Club demo |
| V2 | `v0.2.0` | ML regime classifier | LightGBM classifier (93.9% accuracy), baseline persistence, live macro fetch, backtesting engine, Discord notifier |
| V3 | `v0.3.0` | Governance agent | LLM abstraction, Phoenix tracing, MCP bridge, GovernanceAgent, trust API, SR 11-7 PDF report, 3 demo scenarios |
| V4 | `v0.4.0` | Production-closer | HALT overlay, drift chart, demo panel, agent chat cards, PDF cover, Slack/email alerts, explainable drift, weekly digest, ADK 2.0 scaffold, NL query, tech debt cleanup, model version registry, full Docker compose |

---

## What Is Actually Built Right Now

### Drift Detection Engine (V1 — stable, untouched since)

Three statistical detectors operating on feature distributions:

- **PSI** (`driftguard/detectors/psi.py`) — Population Stability Index, percentile-binned on baseline, epsilon-smoothed. Industry standard for credit model monitoring. Thresholds: 0.10 / 0.20 / 0.25.
- **KS test** (`driftguard/detectors/ks_test.py`) — Kolmogorov-Smirnov two-sample via scipy. Catches distributional shape changes PSI misses.
- **JS divergence** (`driftguard/detectors/js_divergence.py`) — Jensen-Shannon, bounded [0,1], symmetric. Handles non-overlapping support after regime shifts.

`Monitor.check(baseline, current, macro=None)` runs all three, aggregates severity, and optionally tags the regime. 20 passing tests, 0 regressions in 4 versions.

### Regime Classifier (V2 — 93.9% walk-forward accuracy)

Replaces the V1 rule-based tagger. LightGBM classifier trained on 30 years of NBER-labelled macro history.

- **Input:** 33 features from 5 raw macro series (VIX, BAA10Y credit spread, T10Y2Y yield curve, DFF fed funds, UNRATE unemployment)
- **Features include:** rolling VIX momentum (5d/21d/63d), credit spread velocity, yield curve inversion duration counter, composite stress index
- **Classes:** `stable`, `credit_stress`, `rate_shock`, `black_swan`, `recession`, `unknown`
- **Validation:** COVID March 2020 → `black_swan` at 1.000 confidence. 2017–2018 hiking cycle → `credit_stress`.
- **Known gap:** `recession` recall is 0% — conflated with `credit_stress` and `black_swan`. Noted for V5.

Live macro fetched every 6 hours from FRED + Yahoo Finance (VIX). Cached in `MacroCache` table. Every drift run automatically attaches the latest cached snapshot — regime tag fires without caller intervention.

### Backend API (FastAPI + SQLite)

Base routes (V1/V2):
- `GET /health` — `{"status": "ok", "version": "0.2.0"}`
- `GET /models/` + `POST /models/` + `DELETE /models/{id}`
- `POST /drift/{id}/run` — trigger drift check, optional macro override
- `GET /drift/{id}/history` — filter by `regime`, `severity`, `feature`, `since`, `until` (added V4/B2)
- `GET /drift/{id}/latest`
- `GET /drift/macro/latest` — live macro snapshot with regime
- `GET /alerts/` + `POST /alerts/acknowledge`
- `POST /alerts/webhooks/configure` — runtime webhook config (persisted to DB since V4/C5)
- `GET /health/scheduler` — APScheduler job states + next run times (added V4/C5)

Agent routes (V3):
- `POST /agent/ask` — conversational governance query
- `POST /agent/analyze` — structured drift analysis for a model
- `POST /agent/report` — generate SR 11-7 PDF, returns download link
- `GET /trust/{model_id}` — machine-readable trust score for agent-to-agent consumption
- `POST /experiments/{id}/challenger` — trigger champion-challenger comparison
- `GET /experiments/{id}/results` — retrieve comparison result
- `GET /forecast/{model_id}` — 7–14 day drift probability forecast

Demo routes (V4):
- `POST /demo/scenarios/{name}` — fire a preset scenario (`rate_hike`, `covid_crash`, `normal_decay`)

Version registry routes (V4/B5):
- `POST /models/{id}/versions` — create a new model version with baseline
- `GET /models/{id}/versions` — list all versions with badges
- `POST /models/{id}/versions/{v}/promote` — promote a version to champion
- `GET /drift/{id}/history?version={v}` — history filtered by version

Auth (V4/C2):
- `APIKeyMiddleware` in `driftguard/api/auth.py` — validates `X-API-Key` header when `API_KEY` env var is set. `GET /health` is exempt.

### Governance Agent (`finsight/agent/`)

`GovernanceAgent` (brain.py) — reasoning loop over Phoenix traces + macro context:

1. Fetch latest drift traces from Phoenix via MCP tools
2. Extract regime assessment and feature breakdown
3. Cross-reference with live macro signals
4. Apply regime-specific decision rules:
   - `black_swan` → HALT, never retrain
   - `credit_stress` / `rate_shock` → monitor, do not retrain
   - `stable` + drift → investigate model decay, retrain
   - `recession` → champion-challenger
5. Generate structured `AgentResponse` with recommendation, action, confidence, sources
6. Fire enriched Slack/email notification if severity is high/critical (V4/B1)
7. Log decision to `AgentDecisionLog` table (persisted audit trail)
8. Emit agent decision itself as a Phoenix trace (full observability of reasoning)

**LLM abstraction** (`finsight/llm/`) — `BaseLLMProvider` ABC. Groq (`llama-3.3-70b-versatile`) for dev, Gemini 2.5 Pro for submission. Swap by changing 3 env vars. Zero agent code changes.

**Google ADK 2.0 scaffold** (`finsight/adk/`) — V4/C1. `AGENT_FRAMEWORK=adk` activates multi-agent path: `governance_agent` (Gemini 2.5 Pro) with sub-agents `analyst_agent` + `report_agent` (Gemini Flash). `AGENT_FRAMEWORK=native` (default) keeps existing Groq path fully intact. ADK import errors are caught silently — native path always works without google-adk installed.

**Tools the agent can call:**
- `get_latest_drift`, `get_model_history`, `get_feature_breakdown` — DriftGuard API wrappers
- `explain_feature_drift` — LLM-generated per-feature explanation with macro context (V4/B3)
- `query_drift_history` — NL-driven filter query against drift run history (V4/B2)
- `get_current_macro`, `get_macro_history` — MacroSignalFetcher wrappers
- `list_recent_drift_traces`, `get_trace`, `get_spans` — Phoenix MCP wrappers
- `get_trust_score` — trust API wrapper

### Notifications (V4/B1)

- **Slack** — enriched Block Kit payload: regime badge, confidence, severity, recommended action, top 3 drifted features, estimated dollar impact, dashboard link button. Fires after every high/critical agent decision.
- **Email** — SMTP adapter (`smtplib` stdlib, no new deps). Same enriched payload in HTML. Configurable via `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `ALERT_EMAIL_TO`.
- **Weekly digest** (V4/B4) — `DigestGenerator` runs every Monday 08:00 UTC via APScheduler. Per-model status light (green/amber/red), regime comparison week-over-week, drift trend arrow, agent decision count, 7-day forecast summary, one-line verdict.
- Webhook configs are now persisted to `WebhookConfigRecord` SQLite table and reloaded on startup (no longer lost on server restart).

### SR 11-7 PDF Report Generator (`finsight/reports/`)

On-demand regulatory report. Seven sections matching Fed model risk management guidance:

1. Model Identification — metadata, baseline size, creation date
2. Performance Summary — drift score trend, severity distribution
3. Regime Context — macro conditions over period, deduplicated by calendar day
4. Drift Analysis — top drifted features, detector breakdown, root cause
5. Agent Recommendations — governance decisions taken, confidence
6. Risk Assessment — estimated dollar impact, regime-adjusted risk
7. Audit Trail — all drift run IDs, Phoenix trace IDs, agent decision IDs

Cover page added in V4 (A5): FinSight AI branding, regime status box, model name, reporting period, exec summary from latest agent recommendation, CONFIDENTIAL watermark.

LLM prose capped at 5 most recent runs to stay within Groq free-tier TPM limits. Audit trail (Section 7) renders all runs directly — LLM does not intermediate the factual record.

**Verified output:** 13 drift runs · `stable`, `credit_stress`, `black_swan` regimes · max drift 0.0754 · 3 unique macro dates · all 7 sections LLM-written prose.

### Business Impact Translator (`finsight/impact/`)

Maps PSI drift scores to estimated dollar exposure. Rule-based, calibrated against Lending Club historical data.

| PSI range | FNR increase | Regime multiplier |
|---|---|---|
| 0.10–0.20 | 2–5% | `stable` = 1× |
| 0.20–0.50 | 5–12% | `credit_stress` = 1.5× |
| > 0.50 | 12–25% | `black_swan` = 3× |

`explain_feature_drift` tool (V4/B3) generates a one-paragraph LLM explanation per drifted feature: feature's domain role, current PSI/KS/JS scores, macro context, historical pattern from `feature_metadata.py`, recommendation. Surfaced in `ActionCard.tsx` as an expandable "Why did this drift?" section.

### Model Version Registry (V4/B5)

`ModelVersion` SQLModel table — `version_label`, `description`, `baseline_blob`, `is_active`, `promoted_at`. Existing drift runs auto-assigned to version `v1` on migration. `DriftRun` and `AgentDecisionLog` both carry `model_version_id` FK.

Dashboard: version selector dropdown in `ModelDetail.tsx`. Switching version filters the drift chart and all data below it. Version badges show `v1 (active)` / `v2 (challenger)`.

### React Dashboard (`dashboard/`)

**Stack:** Vite + React 18 + TypeScript + Tailwind CSS v3 + Recharts + Axios + React Router

**Pages:**
- `Overview.tsx` — model health grid, alert feed, MacroPanel, ForecastAlert banner, persona selector (Engineer / Quant / Risk Officer)
- `ModelDetail.tsx` — version selector, DriftChart with regime bands, ActionCard (with Why section), ImpactBanner, DemoPanel (on `?demo=true`), HALT overlay on black swan
- `AgentView.tsx` (`/agent`) — AgentResponseCard chat with regime badge + severity + confidence + impact box + source chips + suggestion chips, one-button PDF report generation
- `ExperimentView.tsx` (`/experiments`) — champion-challenger comparison, trigger button, side-by-side metrics

**Key V4 visual components:**
- `HaltOverlay.tsx` — full-screen dark overlay, HALT in 120px red, ring pulse animation, auto-dismisses after 2s on black swan detection
- `DriftChart.tsx` — 13-point Recharts LineChart with `ReferenceArea` regime colour bands (green/amber/red tints), regime-coloured dot per point, hover tooltip with regime + severity + recommendation
- `DemoPanel.tsx` — 3 scenario cards with Run button, loading spinner, live log in DM Mono. Visible only on `?demo=true`.
- `AgentResponseCard.tsx` — structured chat card: regime badge, severity pill, confidence bar, bold recommendation, impact box, source chips, typing animation

### Demo Scenarios (`demo/scenarios/`)

Three self-contained scripts, each verified passing:

| Scenario | Macro inject | Expected regime | Expected action |
|---|---|---|---|
| `rate_hike_2017.py` | Q4 2018 peak (VIX=25, spread=1.90) | `credit_stress` | Monitor, do not retrain |
| `covid_crash.py` | March 2020 (VIX=57.1, spread=3.82, unemp=14.7) | `black_swan` | HALT, freeze all automated decisions |
| `normal_decay.py` | Stable (current live macro) | `stable` | Investigate and retrain |

`scripts/demo_full.py --auto` runs all three. **Verified runtime: 26.6s, 3/3 passing.**

Demo panel in dashboard fires the same scenarios via `POST /demo/scenarios/{name}` with no terminal needed.

### Phoenix Observability (`finsight/tracing/`)

Every drift run emits a structured OTEL trace to Phoenix (`localhost:6006`). Decorators applied at route handler level — DriftGuard's core functions are unmodified. If Phoenix is unreachable, the decorated function runs normally.

Spans emitted:
- `@traced_drift_check` — CHAIN span: model_id, drift.score, drift.severity, regime.class, regime.confidence
- `@traced_regime_tag` — CHAIN span: regime, confidence, signals_fired
- `@traced_detector` — CHAIN span per detector: detector_name, feature_name, score, threshold, severity
- `@traced_macro_fetch` — TOOL span: vix, credit_spread, fed_funds, yield_curve

`phoenix_trace_id` column on `DriftRun` stores the OTEL span ID alongside the DB record (V4/C3). Agent decision sources reference real trace UUIDs.

### Docker Compose (V4/C6)

Single `docker compose up` starts the full stack:
- `phoenix` — Arize Phoenix observability (`localhost:6006`)
- `phoenix-mcp` — Phoenix MCP server (node:20-slim, npx)
- `backend` — FastAPI (`localhost:8000`), SQLite volume-mounted
- `dashboard` — Vite React (`localhost:5173`)

---

## Verified Demo Results (May 2026)

From `DEMO_RUN_RESULTS.md`, all on Windows / Python 3.11 / Groq `llama-3.3-70b-versatile`:

| Test | Result | Key output |
|---|---|---|
| `GET /health` | PASS | `{"status":"ok","version":"0.2.0"}` |
| `GET /drift/macro/latest` | PASS | VIX=17.28, regime=stable, confidence=1.0 |
| `GET /models/lending_club_v1` | PASS | model found, created 2026-03-21 |
| Rate hike scenario | PASS | drift=0.0493, severity=HIGH, credit_stress |
| COVID crash scenario | PASS | drift=0.0754, severity=CRITICAL, black_swan, HALT |
| Normal decay scenario | PASS | drift=0.0368, severity=HIGH, stable, retrain |
| `POST /agent/ask` | PASS | confidence=0.8, action=investigate |
| `GET /trust/lending_club_v1` | PASS | trustworthy=false, recommendation=escalate |
| `demo_full.py --auto` | PASS | 3/3, 26.6s total |
| PDF report | PASS | 13 runs, 3 regimes, 7 LLM-written sections |

---

## Current State of the Codebase

### What is stable and load-bearing

- All 3 drift detectors — 20 passing tests, untouched since V1
- `Monitor.check()` — clean typed interface, lazy regime tagging
- Regime classifier — 93.9% walk-forward accuracy, COVID = black_swan at 1.000 confidence
- Baseline persistence — parquet blobs in SQLite, survives restarts
- All FastAPI routes — verified working
- Demo scenarios — 3/3 passing, 26.6s end-to-end

### What is working but not hardened

- **ADK 2.0 path** — scaffold is in place (`finsight/adk/`), `AGENT_FRAMEWORK=adk` activates it. Not end-to-end validated against live Gemini because google-adk was 2 days old at implementation. Native path (`AGENT_FRAMEWORK=native`) is the production path.
- **Phoenix trace ID linkage** — `phoenix_trace_id` column exists on `DriftRun`. Population depends on successful trace export. Traces confirmed to export after 405 fix; individual run trace IDs not manually verified.
- **Slack notifier** — Block Kit payload is built and enriched. End-to-end delivery against a live Slack workspace not verified.
- **Gemini swap** — mechanical (3 env vars), budget 2–3 hours for prompt output tuning.

### Known gaps (inherited, not fixed in V4)

| Gap | Status |
|---|---|
| Recession classifier recall = 0% | Inherited from V2. Separate binary sub-classifier needed. V5. |
| SQLite concurrency | Single-file, no connection pooling. Single-user local only. PostgreSQL = V5. |
| `version` string in `/health` shows `0.2.0` | Stale, not updated. Cosmetic. |
| Rate hike scenario named `rate_hike_2017.py` | Uses Q4 2018 peak values. Filename is misleading but the scenario works correctly. |
| Champion-challenger uses Lending Club dataset only | Not generalised to arbitrary model datasets. |
| Forecast accuracy not backtested | Rule-based heuristic. 7–14 day probability is directionally correct, not calibrated. |

---

## Tech Stack Summary

| Layer | Technology |
|---|---|
| Drift detection | PSI + KS + JS (scipy, numpy) |
| Regime classification | LightGBM (93.9% accuracy on 30-year walk-forward) |
| Macro data | FRED API + Yahoo Finance (yfinance) |
| Backend | FastAPI + SQLModel + SQLite + APScheduler |
| Agent LLM (dev) | Groq `llama-3.3-70b-versatile` |
| Agent LLM (submission) | Gemini 2.5 Pro (via google-generativeai) |
| Agent framework (submission) | Google ADK 2.0 (scaffold ready, `AGENT_FRAMEWORK=adk`) |
| Observability | Arize Phoenix v15.11.1 (OTEL traces) |
| MCP | `@arizeai/phoenix-mcp` (Node, Docker sidecar) |
| Report generation | reportlab (SR 11-7 PDF) |
| Dashboard | React 18 + Vite + Tailwind v3 + Recharts + Axios |
| Notifications | Slack Block Kit + SMTP (stdlib) |
| Containerisation | Docker Compose (4-service full stack) |
| Demo model | LightGBM credit default on Lending Club (AUC 0.69, 2.26M rows) |

---

## What V5 Looks Like

In rough priority order:

1. **Recession classifier** — dedicated binary sub-classifier (NBER-labelled, lagged unemployment + yield curve inversion duration). Fixes 0% recall inherited from V2.
2. **PostgreSQL migration** — required for multi-user or hosted deployment. SQLite is the only remaining V1 component still load-bearing in prod.
3. **ADK 2.0 end-to-end validation** — run `demo_full.py --auto` with `AGENT_FRAMEWORK=adk`. Tune prompts where output structure differs. Document the swap.
4. **PyPI packaging** — `pip install finsight-ai`. Requires `pyproject.toml` cleanup, `MANIFEST.in`, GitHub Actions release workflow.
5. **Multi-model monitoring** — current demo is single-model. Registry and dashboard already support multiple models; agent reasoning needs updating.
6. **Real-time WebSocket push** — live drift score updates without polling.
7. **Team collaboration** — shared dashboard, role-based access, shared agent decision log.

---

## How to Run From Scratch

### Option A — Docker (recommended)

```bash
git clone https://github.com/<username>/financial-driftguard
cd financial-driftguard
cp .env.example .env
# edit .env — add FRED_API_KEY, GROQ_API_KEY
docker compose up
# Backend: http://localhost:8000
# Dashboard: http://localhost:5173
# Phoenix: http://localhost:6006
```

### Option B — Manual (dev)

```powershell
# Terminal 1 — Phoenix
docker compose up phoenix

# Terminal 2 — Backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
pip install -e .
uvicorn driftguard.api.main:app --reload

# Terminal 3 — Seed demo data (run once)
python demo\lending_club.py

# Terminal 4 — Dashboard
cd dashboard
npm install
npm run dev

# Terminal 3 — Run full demo
python scripts\demo_full.py --auto
```

### Makefile shortcuts

```bash
make setup       # venv + pip + npm install
make serve       # uvicorn backend
make seed        # seed demo data
make ui          # npm run dev
make demo-auto   # all 3 scenarios
make test        # pytest 20 tests
```

---

## Doc Map

| Document | What it covers |
|---|---|
| [docs/v1_summary.md](v1_summary.md) | V1 engineering reference — detectors, regime tagger, API, Lending Club demo, all decisions |
| [docs/v2_summary.md](v2_summary.md) | V2 snapshot — ML classifier, backtesting, baseline persistence, webhook system |
| [docs/v3_summary.md](v3_summary.md) | V3 implementation — governance agent, Phoenix, MCP, trust API, report, all 8 bugs |
| [docs/v4_build_plan.md](v4_build_plan.md) | V4 spec — all tracks A/B/C, item-by-item implementation detail |
| [docs/v4_session_plan.md](v4_session_plan.md) | V4 session execution guide — 5 sessions, kickoff prompts |
| [docs/project_status.md](project_status.md) | This document — current state of everything |
| [DEMO_RUN_RESULTS.md](../DEMO_RUN_RESULTS.md) | Verified demo outputs from May 2026 run |
| [docs/archive/finsight_ai_build_plan.md](archive/finsight_ai_build_plan.md) | V3 build plan (superseded) |

---

*FinSight AI — Project Status — June 2026*  
*Built across 4 versions, May–June 2026*
