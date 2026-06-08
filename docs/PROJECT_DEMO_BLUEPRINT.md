# FinSight AI / DriftGuard — Project Demo Blueprint

> Complete guide for recording a walkthrough video.
> Derived from actual codebase — every feature listed here has been verified.

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Architecture Summary](#2-architecture-summary)
3. [Feature Inventory](#3-feature-inventory)
4. [Demo Environment Setup](#4-demo-environment-setup)
5. [Demo Recording Plan](#5-demo-recording-plan)
6. [Optimal Demo Flow](#6-optimal-demo-flow)
7. [Demo Scenarios](#7-demo-scenarios)
8. [Feature Dependencies](#8-feature-dependencies)
9. [Demo Data Checklist](#9-demo-data-checklist)
10. [Commands Cheat Sheet](#10-commands-cheat-sheet)
11. [Troubleshooting](#11-troubleshooting)
12. [Hidden or Impressive Features](#12-hidden-or-impressive-features)

---

## 1. Project Overview

### What This Application Is

**FinSight AI** (built on the **DriftGuard** engine) is a production-grade ML model governance platform for financial services. It monitors credit and lending models for distribution drift, classifies the current macroeconomic regime using a LightGBM classifier trained on 30 years of market data, and issues regime-aware governance recommendations through a conversational AI agent.

### Primary Use Cases

- Continuous monitoring of deployed ML models for feature distribution drift
- Regime-aware action recommendations (the same drift signal can mean "retrain" or "do not retrain" depending on the macro environment)
- Human-in-the-loop approval workflows for high-risk governance actions (retrain, freeze, escalate)
- SR 11-7 compliant audit trails and PDF report generation
- Agent-to-agent trust scoring for downstream system integration

### Core Value Proposition

**The problem every ML team has:** drift detected → retrain model. This is wrong during macro stress events.

**FinSight AI's insight:** The same PSI drift score of 0.15 on `int_rate` means:
- During a Fed rate hike cycle → **do NOT retrain** (drift is macro-driven; retraining locks in temporary patterns that underperform post-cycle)
- During stable macro → **retrain** (drift is genuine model decay)

No other open-source monitoring tool makes this distinction. FinSight AI does it automatically using a 93.9%-accurate regime classifier.

### Main Personas

| Persona | Role | Primary Concern |
|---|---|---|
| **ML Engineer** | Monitors model health, receives alerts | PSI scores, feature breakdown, retrain triggers |
| **Risk Officer** | Approves governance actions, generates reports | Regime context, dollar impact, audit trail |
| **Quant / Model Validator** | Reviews SR 11-7 compliance | Accuracy metrics, champion-challenger, eval scores |
| **External Agent** | Downstream system consuming trust API | Binary trustworthy/halt signal |

---

## 2. Architecture Summary

### Frontend Stack

- **Framework:** React 18 + TypeScript + Vite
- **Styling:** Tailwind CSS
- **Routing:** React Router v6
- **State:** Local React state + REST polling
- **Build output:** Static SPA (deployed to Vercel)
- **Config:** `VITE_API_URL`, `VITE_API_KEY` via `.env`
- **Location:** `dashboard/`

### Backend Stack

- **Framework:** FastAPI (Python 3.11)
- **AI Agent:** Native tool-calling loop (GroqProvider + OpenAI-compatible tool schemas)
- **LLM Models:** `llama-3.3-70b-versatile` (reasoning), `llama-3.1-8b-instant` (fast)
- **ML:** LightGBM (regime classifier), SciPy/NumPy (PSI/KS/JS detectors)
- **Background Jobs:** APScheduler (macro refresh every 6 hours, drift checks)
- **PDF Reports:** ReportLab
- **Location:** `driftguard/` (core engine), `finsight/` (agent + AI layer)

### Database

- **Primary:** PostgreSQL via Supabase (psycopg2-binary pooler connection)
- **Dev Fallback:** SQLite (`driftguard.db`)
- **ORM:** SQLModel (SQLAlchemy + Pydantic hybrid)
- **Tables:** 8 models (ModelRecord, DriftRun, AlertRecord, MacroCache, ApprovalQueue, AgentDecisionLog, ModelVersion, WebhookConfigRecord)
- **Schema management:** Auto-created on startup via `SQLModel.metadata.create_all()`

### Infrastructure

- **Backend deploy:** Railway (Dockerfile builder, `/health` healthcheck, `$PORT` dynamic)
- **Frontend deploy:** Vercel (SPA rewrite via `vercel.json`)
- **Config files:** `railway.toml`, `dashboard/vercel.json`

### External Services

| Service | Purpose | Env Var |
|---|---|---|
| **Groq API** | LLM inference (reasoning + fast models) | `GROQ_API_KEY` |
| **Arize Phoenix Cloud** | Distributed tracing, LLM spans, eval experiments | `PHOENIX_API_KEY`, `PHOENIX_COLLECTOR_ENDPOINT` |
| **Supabase** | PostgreSQL database (pooler URL) | `DATABASE_URL` |
| **FRED API** | Macro data (fed funds rate, yield curve, unemployment) | `FRED_API_KEY` |
| **Yahoo Finance** | VIX price data (via yfinance) | none |
| **Slack** | Approval notifications + interactive button webhooks | `SLACK_WEBHOOK_URL`, `SLACK_SIGNING_SECRET` |
| **Telegram** | Approval notifications + inline keyboard callbacks | `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID` |

### High-Level System Design

```
[Frontend: React/Vite]
       |  REST + X-API-Key
       v
[FastAPI Backend]
  ├── /drift/*        — PSI/KS/JS detection engine
  ├── /agent/*        — FinSight AI governance agent (Groq LLM + 6 tool categories)
  ├── /trust/*        — Agent-to-agent binary trust score
  ├── /approvals/*    — Human-in-the-loop approval queue
  ├── /experiments/*  — Champion-challenger + LLM-as-Judge evals
  ├── /models/*       — Model registry + versioning
  └── /alerts/*       — Alert management + webhook config
       |
  ├── PostgreSQL (Supabase) — All persistence
  ├── Phoenix Cloud (Arize) — All traces + eval experiments
  ├── FRED / yfinance       — Real-time macro data
  └── Groq API              — LLM calls (agent loop + evals)

[APScheduler — Background]
  ├── Macro refresh (6 hours) — Fetches VIX + 5 FRED series, runs LightGBM regime classifier
  └── Drift jobs (per model)  — Runs drift checks, fires alerts/notifications
```

---

## 3. Feature Inventory

### Category A — Core Drift Detection Engine

| Feature | Purpose | User Value | How to Access | Prerequisites |
|---|---|---|---|---|
| **PSI Detector** | Population Stability Index per feature | Industry-standard credit model metric | Runs automatically on `POST /drift/{id}/run` | Baseline set |
| **KS Test Detector** | Kolmogorov-Smirnov two-sample test | Distribution-free drift on skewed features | Same as PSI | Baseline set |
| **JS Divergence Detector** | Jensen-Shannon divergence | Handles non-overlapping distributions post-regime shift | Same as PSI | Baseline set |
| **Per-feature breakdown** | Individual feature drift scores per detector | Pinpoints which feature is causing the alert | `GET /drift/{id}/features/{run_id}` or ModelDetail page | Drift run exists |
| **Drift history timeline** | Time-series of drift scores | Spot trend and regime transitions visually | `GET /drift/{id}/history`, ModelDetail page | Multiple drift runs |
| **Proactive forecast** | 7–14 day drift probability forecast | Early warning before severity spikes | `GET /drift/forecast/{id}` | Drift history |
| **Baseline management** | Set, persist, and restore baselines per model | Drift is always relative to approved state | `POST /drift/{id}/run` with `set_as_baseline=true` | Model registered |

### Category B — Macro Regime Intelligence

| Feature | Purpose | User Value | How to Access | Prerequisites |
|---|---|---|---|---|
| **LightGBM Regime Classifier** | Classifies macro into stable/credit_stress/recession/black_swan | 93.9% accuracy on 30 years of data | Runs automatically on macro fetch | FRED_API_KEY |
| **Macro signal panel** | Live VIX, credit spread, yield curve, fed funds rate | Single-glance market environment context | `GET /drift/macro/latest`, Overview dashboard | FRED_API_KEY |
| **6-hour macro refresh** | Auto-updates signals from FRED + Yahoo Finance | Always current without manual refresh | APScheduler background job | FRED_API_KEY |
| **Rule-based fallback** | Hardcoded thresholds when ML classifier unavailable | Graceful degradation without FRED | Automatic | None |
| **Regime badges** | Color-coded regime display in UI | Instant visual indicator (green/amber/red/black) | All pages with model cards | MacroCache populated |

### Category C — FinSight AI Governance Agent

| Feature | Purpose | User Value | How to Access | Prerequisites |
|---|---|---|---|---|
| **Autonomous drift analysis** | Agent calls all tools, applies regime rules, returns structured recommendation | Automated first-line governance decision | `POST /agent/analyze`, ModelDetail page | Model + drift data |
| **Risk officer chat** | Conversational interface for ad-hoc governance questions | "Is my lending model safe right now?" | `POST /agent/ask`, `/agent` frontend page | None (can run with no data) |
| **Multi-turn conversation** | ConversationMemory maintains context across turns | Follow-up questions without re-stating context | `/agent` frontend page | None |
| **Structured JSON output** | Agent always returns action/confidence/reasoning/sources | Machine-parseable governance decisions | All `/agent/*` endpoints | None |
| **Self-evaluation loop** | LLM-as-Judge scores its own decisions, adjusts confidence | Meta-accuracy feedback loop | Runs inside `analyze()` automatically | None |
| **SR 11-7 PDF report** | Regulatory-format audit report with model lineage, drift history, regime context | Compliance documentation for model validators | `POST /agent/report`, frontend Download button | Drift run history |
| **Agent decision log** | Full audit trail of all agent recommendations | Governance traceability | `GET /agent/log` | None |

### Category D — Human-in-the-Loop Approval Gate

| Feature | Purpose | User Value | How to Access | Prerequisites |
|---|---|---|---|---|
| **Approval queue** | Holds high-risk actions (retrain/freeze/escalate) for human sign-off | Safety net — no automated model changes without human approval | `/approvals` frontend page, `GET /approvals` API | Agent must recommend high-risk action |
| **Slack Block Kit notifications** | Posts structured approval request with Approve/Reject buttons | Risk team gets notified in their existing workflow | Triggered automatically, configured via `SLACK_WEBHOOK_URL` | `SLACK_WEBHOOK_URL` set |
| **Slack interactive webhooks** | Clicking Approve/Reject in Slack updates the queue | One-click approval without leaving Slack | `POST /webhooks/slack/interact` | `SLACK_SIGNING_SECRET` set |
| **Telegram inline keyboard** | Same approval flow via Telegram bot | Mobile-friendly approvals | Triggered automatically | `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID` set |
| **Dollar impact estimate** | Shows "$3.2M–$4.8M exposure" in approval notification | Business stakes are explicit | Part of Slack/Telegram payload | Agent confidence score |
| **Dashboard approval panel** | View + respond to pending approvals in UI | Alternative to chat notifications | `/approvals` frontend page | `API_KEY` header |

### Category E — Observability & Evals

| Feature | Purpose | User Value | How to Access | Prerequisites |
|---|---|---|---|---|
| **Phoenix distributed tracing** | OpenTelemetry spans for every drift check, regime tag, detector run | End-to-end trace per request | Arize Phoenix Cloud dashboard | `PHOENIX_COLLECTOR_ENDPOINT`, `PHOENIX_API_KEY` |
| **Trace ID in DB** | Every DriftRun stores its Phoenix trace ID | Cross-link DB record to trace | `DriftRun.phoenix_trace_id` field, drift history API | Phoenix tracing enabled |
| **LLM-as-Judge governance evals** | Evaluates whether agent made correct regime classifications and action recommendations | Measure and improve agent accuracy over time | `POST /experiments/{id}/evals`, `python scripts/run_evals.py` | Drift run + agent decision history |
| **Phoenix Experiments tab** | All eval runs visible with accuracy metrics | Historical accuracy trend for governance sign-off | `app.phoenix.arize.com` Experiments tab | Evals run at least once |

### Category F — Model Registry & Versioning

| Feature | Purpose | User Value | How to Access | Prerequisites |
|---|---|---|---|---|
| **Model registration** | Named model registry with description | Organise multiple production models | `POST /models/`, Overview page | None |
| **Model versioning** | Track discrete retraining epochs per model | Before/after comparison after retraining | `POST /models/{id}/versions`, Versions tab in UI | Model registered |
| **Version promotion** | Promote a version label to active | Controlled rollout of retrained model | `POST /models/{id}/versions/{label}/promote` | Version created |
| **Drift history by version** | Filter drift history to a specific version | Isolate post-retrain behaviour | `GET /drift/{id}/history?version=v2`, UI version filter | Multiple versions |

### Category G — Champion-Challenger

| Feature | Purpose | User Value | How to Access | Prerequisites |
|---|---|---|---|---|
| **Challenger trigger** | Compares current drift vs stable-period baseline | Quantifies how much the model has decayed | `POST /experiments/{id}/challenger`, Experiments page | Drift history with multiple runs |
| **Experiment results** | Winner (champion/challenger/inconclusive), drift delta, drifted features list | Data-driven retrain/no-retrain decision | `GET /experiments/{id}/results`, Experiments page | Challenger triggered |

### Category H — Alerts & Webhooks

| Feature | Purpose | User Value | How to Access | Prerequisites |
|---|---|---|---|---|
| **Alert feed** | Severity-flagged alerts per model | Real-time drift event stream | `GET /alerts/`, Overview page AlertFeed component | Drift run completed |
| **Alert acknowledgment** | Mark alerts as reviewed | Track which alerts have been actioned | `POST /alerts/acknowledge` | Alert exists |
| **Webhook configuration** | Register Discord or Slack webhook per model or globally | Pager-style notifications to team channels | `POST /alerts/webhooks/configure`, Settings page | Valid webhook URL |
| **Severity threshold filtering** | Only notify above configured threshold | Reduce noise — only page on HIGH/CRITICAL | `severity_threshold` on webhook config | Webhook configured |

### Category I — Trust API (Agent-to-Agent)

| Feature | Purpose | User Value | How to Access | Prerequisites |
|---|---|---|---|---|
| **Binary trust score** | Deterministic go/no-go for downstream systems | Downstream agents can gate on model trustworthiness | `GET /trust/{model_id}` | Drift run exists |
| **Structured trust response** | `trustworthy`, `confidence`, `regime`, `recommendation`, `next_check_recommended` | Richer context than a simple boolean | Same endpoint | Same |
| **No-LLM path** | Pure DB read + decision matrix, sub-50ms response | Reliable for high-frequency downstream polling | Same | Same |

---

## 4. Demo Environment Setup

### Install Dependencies

```bash
# Clone and enter project
cd financial-driftguard

# Backend — Python 3.11+
pip install -r requirements.txt

# Frontend
cd dashboard
npm install
cd ..
```

### Environment Variables

Copy and fill in `.env` at project root:

```bash
# .env — required for demo

# Database (use SQLite if no Supabase)
DATABASE_URL=postgresql+psycopg2://postgres.<project>:<password>@aws-0-region.pooler.supabase.com:5432/postgres
# For local SQLite dev: leave DATABASE_URL unset — auto-falls back to driftguard.db

# LLM
LLM_PROVIDER=groq
GROQ_API_KEY=gsk_...
LLM_REASONING_MODEL=llama-3.3-70b-versatile
LLM_FAST_MODEL=llama-3.1-8b-instant
AGENT_FRAMEWORK=native

# Macro signals
FRED_API_KEY=your_fred_api_key

# Tracing
PHOENIX_COLLECTOR_ENDPOINT=https://app.phoenix.arize.com/s/<space>/v1/traces
PHOENIX_API_KEY=eyJ0eXAi...
PHOENIX_MCP_BASE_URL=https://app.phoenix.arize.com/s/<space>
PHOENIX_PROJECT_NAME=finsight-ai

# Auth
API_KEY=finsight-dev-key

# Notifications (optional for demo)
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/...
SLACK_SIGNING_SECRET=704897e1...
TELEGRAM_BOT_TOKEN=8500327020:AAG_...
TELEGRAM_CHAT_ID=1592515397
```

### Frontend `.env`

```bash
# dashboard/.env
VITE_API_URL=http://localhost:8000
VITE_API_KEY=finsight-dev-key
```

### Verify Connections

```bash
python scripts/check_connections.py
# Expected: [ OK ] Database, Groq, Phoenix, FRED
```

### Seed Demo Data

```bash
# Step 1 — Run local LendingClub demo (trains model + sets baseline)
python demo/lending_club.py

# Step 2 — Register model + set baseline via API (requires backend running)
uvicorn driftguard.api.main:app --reload &
python demo/lending_club.py   # seed_api() runs at the bottom
```

### Start Backend

```bash
uvicorn driftguard.api.main:app --reload
# Runs on: http://localhost:8000
# Docs:    http://localhost:8000/docs
```

### Start Frontend

```bash
cd dashboard
npm run dev
# Runs on: http://localhost:5173
```

### Start Local Phoenix (optional — use cloud instead)

```bash
docker run -p 6006:6006 arizephoenix/phoenix:latest
# UI: http://localhost:6006
```

### Smoke Check

```bash
python scripts/demo_full.py --smoke
# Expected: 11/11 checks passed
```

### Localhost URLs

| Service | URL |
|---|---|
| Frontend dashboard | `http://localhost:5173` |
| Backend API | `http://localhost:8000` |
| API docs (Swagger) | `http://localhost:8000/docs` |
| Phoenix (local) | `http://localhost:6006` |
| Phoenix (cloud) | `https://app.phoenix.arize.com` |

---

## 5. Demo Recording Plan

---

### Step 1 — The Problem

**Goal:** Set up why this exists — hook the audience with the core insight.

**Screen to show:** Blank terminal or slide

**Actions:**
1. Describe the scenario: "You're monitoring a credit scoring model. PSI goes from 0.08 to 0.15 on `int_rate`. Your monitoring tool says: drift detected. What do you do?"
2. "Every standard tool says: retrain. But that answer is wrong 40% of the time."

**Narration:**
"In 2017, every Fed rate hike made lending model scores shift — because interest rates on new loans changed before the economy did. Teams that retrained their models on that data locked in rate-hike-era patterns. When rates normalized 18 months later, their models underperformed massively. The drift was real. The retrain was wrong. FinSight AI is the only monitoring tool that understands the difference."

**Expected Outcome:** Audience understands the core problem. No screen action needed.

---

### Step 2 — Connection & Environment Check

**Goal:** Show the stack is live and real.

**Screen to show:** Terminal

**Actions:**
1. Run `python scripts/check_connections.py`
2. Point to each `[ OK ]` line

**Narration:**
"Four live connections: Supabase PostgreSQL, Groq API for inference, Arize Phoenix Cloud for distributed tracing, and FRED API for real macro data — same VIX and yield curve the Fed watches."

**Expected Outcome:**
```
[ OK ] Database connected: aws-1-ap-southeast-2.pooler.supabase.com
[ OK ] Groq API responded: 'OK'
[ OK ] Phoenix reachable (HTTP 307)
[ OK ] FRED API — latest fed funds rate: 3.63%
```

---

### Step 3 — Live Macro Signals

**Goal:** Show the macro intelligence layer.

**Screen to show:** Browser — `http://localhost:5173` Overview page

**Actions:**
1. Open the dashboard
2. Point to the Macro Panel (VIX, credit spread, yield curve, fed funds rate)
3. Point to the Regime badge (e.g., "credit_stress" with amber colour)

**Narration:**
"The dashboard shows live macro signals, refreshed every 6 hours from FRED and Yahoo Finance. The regime badge — green for stable, amber for credit stress, red for recession, black for black swan — is what the LightGBM classifier has predicted right now. This classifier was trained on 30 years of data and achieves 93.9% accuracy."

**Expected Outcome:** Macro panel visible with real values, coloured regime badge.

---

### Step 4 — Model Overview

**Goal:** Show the model registry and model health cards.

**Screen to show:** Browser — Overview page model cards

**Actions:**
1. Point to the `lending_club_v1` model card showing severity badge
2. Click the card to navigate to ModelDetail page

**Narration:**
"The model registry shows all production models with their current health status. Severity badges update with every drift run. One click to drill into any model."

**Expected Outcome:** ModelDetail page loads for `lending_club_v1`.

---

### Step 5 — Scenario 1: Rate Hike Cycle (DO NOT RETRAIN)

**Goal:** Run the first demo scenario — PSI drift during a Fed rate hike cycle.

**Screen to show:** Terminal → then switch to dashboard

**Actions:**
1. In terminal: `python demo/scenarios/rate_hike_2017.py`
2. Wait for output
3. Switch to dashboard ModelDetail → Drift History timeline — new run appears
4. Point to: drift score, `credit_stress` regime, "Monitor" recommendation

**Narration:**
"We're injecting Q4 2018 macro conditions — the peak of the Fed's hiking cycle. VIX at 25, credit spread at 1.90, yield curve nearly flat at 0.21. Watch what happens to `int_rate`."

**Expected Outcome:**
```
Drift Score  : 0.0493
Severity     : HIGH
Regime       : credit_stress
Recommendation: Drift consistent with macro regime shift. Do NOT retrain.
int_rate     PSI=0.1013   low
```

**Talking points:** "The drift on `int_rate` is real. PSI is 0.10 — above the warning threshold. But the regime is `credit_stress`. The AI knows: retraining locks in rate-hike-era patterns. In 18 months when rates normalize, that retrained model will underperform. The correct action is monitor and wait."

---

### Step 6 — Scenario 2: COVID Black Swan (HALT)

**Goal:** Show the crisis response — extreme macro stress.

**Screen to show:** Terminal → Dashboard

**Actions:**
1. Run `python demo/scenarios/covid_crash.py`
2. Wait for output (should show `black_swan`, `CRITICAL`, `HALT`)
3. Switch to dashboard — check if HaltOverlay appears, or show the new run in drift history
4. Check `/approvals` page — a "freeze" approval should have been created

**Narration:**
"Now we inject March 2020 conditions. VIX 57, credit spread 3.82, unemployment 14.7. This is the most extreme stress event in 30 years of training data."

**Expected Outcome:**
```
Regime     : black_swan
Severity   : CRITICAL
Action     : HALT — freeze automated decisions, escalate to human review
```
Approval notification sent to Slack/Telegram. Approval appears in queue.

**Talking points:** "The AI doesn't guess. It knows: you cannot trust any drift metric during a black swan event. The distribution of everything changes. Retraining on COVID data produces a model that catastrophically fails post-recovery. Freeze, escalate to humans, wait for the storm to pass."

---

### Step 7 — Scenario 3: Normal Decay (RETRAIN)

**Goal:** Show the one scenario where retrain IS correct.

**Screen to show:** Terminal → Dashboard

**Actions:**
1. Run `python demo/scenarios/normal_decay.py`
2. Show output: `stable` regime, `HIGH` severity, retrain/investigate recommendation
3. Compare the three scenarios side by side in drift history timeline

**Narration:**
"Finally: the same drift signal in a stable macro environment. VIX normal, spreads tight, no regime stress. Now the drift is internal — the model has genuinely decayed. Here, retrain is the correct call."

**Expected Outcome:**
```
Regime       : stable
Severity     : HIGH
Recommendation: Investigate model decay. Trigger champion-challenger. Retrain.
```

**Talking points:** "Three scenarios. Same drift score. Three different correct answers. That's the entire value proposition of FinSight AI."

---

### Step 8 — FinSight AI Agent (Conversational Governance)

**Goal:** Show the agent answering live questions.

**Screen to show:** Browser — `http://localhost:5173/agent`

**Actions:**
1. Navigate to `/agent` page
2. Type: `"Is my lending model safe right now?"`
3. Wait for response (5–10 seconds)
4. Show the structured output: action, confidence, regime, reasoning
5. Type a follow-up: `"What would change your recommendation?"`
6. Show the second response using conversation context

**Narration:**
"The risk officer can have a natural language conversation with the governance system. The agent calls tools — checks current macro, pulls latest drift, checks feature breakdown — then applies the regime rules to produce a structured recommendation. Every response shows the action, confidence, reasoning, and data sources."

**Expected Outcome:** Structured agent response with `action`, `confidence`, `regime`, `recommendation` fields populated.

---

### Step 9 — Approval Gate (Slack + Telegram)

**Goal:** Show the human-in-the-loop workflow.

**Screen to show:** Slack or Telegram on mobile/desktop

**Actions:**
1. Show the Slack notification that arrived during Scenario 2 (COVID/freeze)
2. Point to the Block Kit message: model name, regime, action, estimated dollar impact
3. Show Approve and Reject buttons
4. Click Reject
5. Switch to `http://localhost:5173/approvals` — show queue updated to "rejected"

**Narration:**
"High-risk actions — freeze, retrain, escalate — never execute without human sign-off. The governance system fires a Slack message with the full context: model ID, regime, confidence, and dollar exposure estimate. One click to approve or reject. The decision is logged to the audit trail."

**Expected Outcome:** Slack message visible with buttons. Approvals page shows status update.

---

### Step 10 — Phoenix Traces

**Goal:** Show the observability layer — every decision is traceable.

**Screen to show:** Browser — `https://app.phoenix.arize.com`

**Actions:**
1. Open Phoenix Cloud
2. Navigate to the `finsight-ai` project
3. Click on the most recent trace
4. Expand spans: drift check → regime tag → PSI detector → KS test → JS divergence → agent tool calls
5. Show the LLM spans for the agent (input prompt, output, token count, latency)

**Narration:**
"Every drift check produces a distributed trace in Arize Phoenix. You can see the full execution: which detectors ran, which features flagged, how the regime was classified, what the LLM was asked, and what it said. For model governance, this is the audit trail you need."

**Expected Outcome:** Hierarchical span tree visible in Phoenix UI.

---

### Step 11 — LLM-as-Judge Governance Evals

**Goal:** Show the self-evaluation loop — measuring the agent's accuracy.

**Screen to show:** Terminal → Phoenix Experiments tab

**Actions:**
1. Run `python scripts/run_evals.py`
2. Show output: total evaluated, correct count, accuracy percentage
3. Open Phoenix → Experiments tab → show the eval run

**Narration:**
"FinSight AI measures its own accuracy. The LLM-as-Judge evaluator checks: given these macro signals, did the agent classify the regime correctly? Given this regime, did it recommend the right action? Results are pushed to Phoenix Experiments for trend tracking."

**Expected Outcome:**
```
Total evaluated : 6
Correct         : N
Accuracy        : X.X%
Experiment name : governance-eval-20260609-XXXX
```

---

### Step 12 — Trust API (Agent-to-Agent)

**Goal:** Show the machine-readable trust endpoint.

**Screen to show:** Terminal (curl) or Swagger UI

**Actions:**
1. Run:
   ```bash
   curl -s -H "X-API-Key: finsight-dev-key" http://localhost:8000/trust/lending_club_v1 | python -m json.tool
   ```
2. Show the JSON response

**Narration:**
"The trust API lets downstream systems — other agents, orchestrators, approval workflows — check model trustworthiness with a single GET request. No LLM involved. Pure DB read plus the decision matrix. Sub-50ms response. `trustworthy: true/false`, recommendation, and when to check again."

**Expected Outcome:**
```json
{
  "model_id": "lending_club_v1",
  "trustworthy": true,
  "confidence": 0.87,
  "regime": "credit_stress",
  "recommendation": "proceed_with_caution",
  "reason": "Drift is macro-driven; model not decaying",
  "next_check_recommended": "2026-06-09T..."
}
```

---

### Step 13 — SR 11-7 PDF Report

**Goal:** Show compliance documentation output.

**Screen to show:** Browser — ModelDetail page or Swagger UI

**Actions:**
1. In Swagger (`http://localhost:8000/docs`), find `POST /agent/report`
2. Submit with `{"model_id": "lending_club_v1"}`
3. Download and open the PDF
4. Show model lineage section, drift history table, regime context, recommendations

**Narration:**
"For model validators and regulators, the agent generates an SR 11-7 compliant PDF report: model lineage, drift history, current regime, and all governance recommendations. This is the document you hand to your model risk management team."

**Expected Outcome:** PDF downloads and opens showing formatted report.

---

### Step 14 — Closing Summary

**Goal:** Recap value proposition, show the full stack.

**Screen to show:** Dashboard Overview page

**Actions:**
1. Return to Overview page
2. Show all three scenarios reflected in drift history
3. Show macro panel, regime badge, alert feed, model cards all live

**Narration:**
"FinSight AI is the only ML governance platform that integrates macro intelligence with drift detection. It gives your team: automated regime-aware recommendations, human-in-the-loop approval gates for high-risk actions, full distributed tracing with Arize Phoenix, and regulatory-grade audit trails. The same drift signal. The right action every time."

---

## 6. Optimal Demo Flow

### Story Arc

```
HOOK          → The same drift score can mean opposite actions
PROBLEM       → Existing tools recommend retrain blindly — this is wrong
SOLUTION      → FinSight AI classifies the macro regime before recommending any action
PROOF POINT 1 → Rate hike scenario: drift detected, DO NOT retrain
PROOF POINT 2 → COVID scenario: drift detected, HALT everything
PROOF POINT 3 → Normal decay: drift detected, RETRAIN (correct)
AGENT         → Conversational risk officer interface
GOVERNANCE    → Human approval gate (Slack/Telegram)
TRUST         → Machine-readable trust API for downstream systems
OBSERVABILITY → Phoenix traces + LLM-as-Judge evals
COMPLIANCE    → SR 11-7 PDF report
CLOSE         → Regime-aware governance that no other tool provides
```

### Feature Order for Maximum Impact

1. Live connection check (credibility)
2. Macro panel — regime badge (the secret ingredient)
3. Scenario 1 — Rate hike: DON'T retrain (counterintuitive)
4. Scenario 2 — COVID: HALT (dramatic)
5. Scenario 3 — Normal decay: RETRAIN (contrasts with scenario 1)
6. Agent chat — "Is my model safe?" (interactive, impressive)
7. Approval gate — Slack/Telegram (practical governance)
8. Phoenix traces (engineering depth)
9. Trust API — curl command (external integration)
10. PDF report (compliance story)

---

## 7. Demo Scenarios

### 5-Minute Demo

Focus: Core value proposition only.

1. (1 min) Explain the problem — same drift, opposite actions
2. (1 min) Scenario 1: rate hike — show "do not retrain" output
3. (1 min) Scenario 2: COVID — show "HALT" output
4. (1 min) Scenario 3: normal decay — show "retrain" output
5. (1 min) Show dashboard Overview with regime badge and drift history

**Skip:** Agent chat, Slack/Telegram, Phoenix, PDF report, evals

---

### 10-Minute Demo

Focus: Core flow + agent + governance.

1. (1 min) Problem statement
2. (2 min) Three scenarios (run `python scripts/demo_full.py --auto` in background, show results)
3. (2 min) Dashboard walkthrough: macro panel, drift history, feature breakdown
4. (2 min) Agent chat: "Is my lending model safe right now?"
5. (1 min) Show Slack approval notification from COVID/freeze scenario
6. (1 min) Trust API curl command
7. (1 min) Close

**Skip:** Phoenix traces, PDF report, evals, experiments page

---

### 20-Minute Demo

Focus: Full product story including observability, compliance.

Steps 1–14 from the Demo Recording Plan above, at a comfortable pace.

---

### Full Feature Showcase

For technical evaluators or hackathon judges:

1. All Demo Recording Plan steps (Steps 1–14)
2. Live Phoenix trace exploration — drill into LLM spans
3. Champion-challenger: trigger via `/experiments` page
4. Model versioning: create v2, promote to active
5. Webhook config: add Discord webhook via Settings page
6. Run evals: `python scripts/run_evals.py`, show Phoenix Experiments tab
7. Swagger UI tour: show all 30+ endpoints at `localhost:8000/docs`

---

## 8. Feature Dependencies

### Features Requiring Backend Running

- All API endpoints
- All frontend pages (except static assets)
- Agent, drift, macro, approval, trust

### Features Requiring Demo Data Seeded

These require `python demo/lending_club.py` to have run first:

- Drift history charts in ModelDetail
- Feature breakdown tab
- Champion-challenger comparison
- Trust API response (needs at least one DriftRun)
- Agent full analysis (needs model + drift data in DB)
- Governance evals (needs decision history)

### Features Requiring FRED_API_KEY

- Live macro signals in dashboard
- Macro refresh job
- Regime classification from real data

Without FRED_API_KEY: macro panel shows empty/cached values; demo scenarios still work (they inject macro directly).

### Features Requiring GROQ_API_KEY

- Agent chat (`/agent` page)
- Agent analyze/report endpoints
- LLM-as-Judge evals

### Features Requiring PHOENIX_API_KEY

- Distributed tracing to Arize cloud
- Phoenix Experiments tab (eval results)
- Phoenix MCP tools in agent

Without these: agent still works, traces just don't appear in cloud UI.

### Features Requiring SLACK_WEBHOOK_URL

- Slack approval notifications
- Slack interactive webhook (approve/reject from Slack)

### Features Requiring TELEGRAM_BOT_TOKEN + TELEGRAM_CHAT_ID

- Telegram approval notifications and inline keyboard

### Features Requiring Multiple Roles / No User Roles

This app has no user accounts. All access is via `X-API-Key` header. Single API key grants full access. Set `API_KEY` env var; omit to disable auth entirely for local demo.

---

## 9. Demo Data Checklist

### Required Before Recording

- [ ] `.env` file created with all keys populated
- [ ] Backend running: `uvicorn driftguard.api.main:app --reload`
- [ ] Frontend running: `cd dashboard && npm run dev`
- [ ] `python demo/lending_club.py` executed (creates parquet files + seeds API)
- [ ] Connection check passes: `python scripts/check_connections.py` (all 4 `[ OK ]`)
- [ ] Smoke check passes: `python scripts/demo_full.py --smoke` (11/11)

### Required Records in Database

After seeding, confirm these exist:

- [ ] `ModelRecord` with `model_id="lending_club_v1"` — registered model
- [ ] `DriftRun` for `lending_club_v1` with `set_as_baseline=True` — baseline established
- [ ] `MacroCache` with at least one entry — macro fetch ran

### Required Demo Artifacts on Disk

- [ ] `demo/data/lending_club_model.pkl` — LightGBM model (generated by lending_club.py training)
- [ ] `demo/data/baseline_snapshot.parquet`
- [ ] `demo/data/live_snapshot.parquet`
- [ ] `demo/data/feature_columns.json`

### Optional (for advanced demo)

- [ ] Slack workspace with FinSight app installed and webhook configured
- [ ] Telegram bot created and chat ID confirmed
- [ ] Phoenix Cloud account with `finsight-ai` project created
- [ ] At least 3 drift runs so history chart is non-trivial

### Test Accounts

No user accounts in this system. Auth is `X-API-Key` header only.

- Demo API key: `finsight-dev-key` (or whatever is in `API_KEY` env var)
- Frontend: set `VITE_API_KEY=finsight-dev-key` in `dashboard/.env`

---

## 10. Commands Cheat Sheet

```bash
# --- SETUP ---

# Install backend
pip install -r requirements.txt

# Install frontend
cd dashboard && npm install && cd ..

# Verify env and connections
python scripts/check_connections.py

# Smoke check all env vars
python scripts/demo_full.py --smoke


# --- SEED DATA ---

# Full demo data seed (trains model + calls API — requires backend running)
python demo/lending_club.py


# --- START SERVICES ---

# Backend (from project root)
uvicorn driftguard.api.main:app --reload

# Frontend
cd dashboard && npm run dev

# Local Phoenix (optional — skip if using cloud)
docker run -p 6006:6006 arizephoenix/phoenix:latest


# --- DEMO SCENARIOS ---

# Run all three scenarios (interactive, pauses between each)
python scripts/demo_full.py

# Run all three without pausing (automated / recording mode)
python scripts/demo_full.py --auto

# Run individual scenarios
python demo/scenarios/rate_hike_2017.py
python demo/scenarios/covid_crash.py
python demo/scenarios/normal_decay.py


# --- AGENT ---

# Agent smoke test (LLM direct + tool call + full loop)
python scripts/test_agent.py


# --- EVALS ---

# Run LLM-as-Judge governance evals
python scripts/run_evals.py
python scripts/run_evals.py --model lending_club_v1


# --- API TESTING ---

# Health check
curl http://localhost:8000/health

# Get latest macro
curl -H "X-API-Key: finsight-dev-key" http://localhost:8000/drift/macro/latest

# Trust score
curl -H "X-API-Key: finsight-dev-key" http://localhost:8000/trust/lending_club_v1

# Trigger agent analysis
curl -X POST http://localhost:8000/agent/analyze \
  -H "Content-Type: application/json" \
  -H "X-API-Key: finsight-dev-key" \
  -d '{"model_id": "lending_club_v1"}'

# List approvals queue
curl -H "X-API-Key: finsight-dev-key" http://localhost:8000/approvals

# Trigger champion-challenger
curl -X POST http://localhost:8000/experiments/lending_club_v1/challenger \
  -H "X-API-Key: finsight-dev-key"

# Run evals via API
curl -X POST http://localhost:8000/experiments/lending_club_v1/evals \
  -H "X-API-Key: finsight-dev-key"


# --- URLS ---

# Frontend:   http://localhost:5173
# Backend:    http://localhost:8000
# Swagger:    http://localhost:8000/docs
# Phoenix:    http://localhost:6006  (local)  or  https://app.phoenix.arize.com
```

---

## 11. Troubleshooting

### Backend won't start — `ImportError: cannot import name 'verify_api_key'`

Fixed in codebase. If you see this on an older checkout:

```bash
git pull origin feat/governance-agent
```

### `[FAIL] Database: No module named 'psycopg2'`

```bash
pip install psycopg2-binary
```

### `[FAIL] Database: connection refused` or DNS error

Check `DATABASE_URL` in `.env`. Use the Supabase **session pooler** URL:

```
postgresql+psycopg2://postgres.<project>:<password>@aws-0-region.pooler.supabase.com:5432/postgres
```

Not the direct connection URL (direct doesn't resolve from outside Supabase's network).

### `[FAIL] Groq API` error

Verify `GROQ_API_KEY` is set. The key starts with `gsk_`. Test with:

```bash
python -c "from groq import Groq; print(Groq().chat.completions.create(model='llama-3.1-8b-instant', messages=[{'role':'user','content':'hi'}]).choices[0].message.content)"
```

### Frontend shows blank or CORS error

Check `VITE_API_URL` in `dashboard/.env` matches where backend is running. If `API_KEY` is set, ensure `VITE_API_KEY` matches.

### 401 Unauthorized from any API endpoint

Set the `X-API-Key` header to match `API_KEY` in `.env`. Or temporarily unset `API_KEY` to disable auth for local testing.

### `[FAIL] FRED API` — rate limit or invalid key

FRED API key is free at `https://fred.stlouisfed.org/docs/api/api_key.html`. Rate limit: 120 requests/60 seconds. Demo scenarios inject macro directly and don't call FRED.

### Agent returns generic answer without calling tools

Run `python scripts/test_agent.py` to verify tool calling. If `[FAIL] Tool call`, check `GROQ_API_KEY`. Model `llama-3.3-70b-versatile` is required for reliable tool use — do not substitute `llama-3.1-8b-instant` for the reasoning role.

### Slack notifications not sending

Check `SLACK_WEBHOOK_URL` is the full `https://hooks.slack.com/services/T.../B.../xxx` URL. Test with:

```bash
python -c "
import os, httpx
from dotenv import load_dotenv; load_dotenv()
r = httpx.post(os.getenv('SLACK_WEBHOOK_URL'), json={'text': 'test'})
print(r.status_code, r.text)
"
```

### Telegram not sending

Verify bot token and chat ID. The chat ID must be numeric (e.g., `1592515397`). If the bot has never received a message from that chat, it can't send to it — send the bot `/start` first.

### Phoenix traces not appearing

Verify `PHOENIX_COLLECTOR_ENDPOINT` ends in `/v1/traces`. For Arize cloud, it is `https://app.phoenix.arize.com/s/<space-slug>/v1/traces`. The `PHOENIX_API_KEY` must be a valid JWT from the Phoenix account settings.

### `demo/data/` files missing

Run `python demo/lending_club.py` from the project root. This generates all parquet and pickle files. If LightGBM is not installed:

```bash
pip install lightgbm
```

### Drift history chart empty

The chart needs at least one drift run. Run `python demo/scenarios/rate_hike_2017.py` (requires backend running and baseline set). The baseline is set by `seed_api()` inside `demo/lending_club.py`.

---

## 12. Hidden or Impressive Features

### The Three-Scenario Contrast

Running all three scenarios back to back is the single most powerful demo moment. All three use the same underlying Lending Club dataset. The only difference is the injected macro context. The regime classifier produces three different regimes → three different correct actions. This is hard to achieve and unique in the monitoring space.

### Proactive Drift Forecasting

`GET /drift/forecast/{model_id}` returns a probability of elevated drift in the next 7–14 days based on the current macro trend and historical drift patterns. This is a forward-looking signal — shown in the `ForecastAlert` UI component — that no standard monitoring tool provides.

### Business Impact Dollar Estimates in Approvals

The approval notifications automatically estimate financial exposure: "$3.2M–$4.8M" at high confidence. This turns a technical alert ("PSI=0.15") into a business decision. No configuration required — derived from agent confidence score.

### Phoenix MCP Tool Integration

The agent has access to Phoenix's REST API as tools (`list_traces`, `get_trace`, `list_experiments`). This means the agent can cross-reference its current analysis against historical traces stored in Phoenix — adding temporal reasoning over past drift events.

### Agent Self-Evaluation Loop

After producing a recommendation, the agent runs `_apply_self_eval()` — it uses the LLM-as-Judge to evaluate its own output against the governance rules and adjusts confidence accordingly. This meta-feedback loop is running on every production agent call, not just on-demand evals.

### Deterministic Trust API with Interval Scheduling

`GET /trust/{model_id}` not only returns `trustworthy: bool` but also `next_check_recommended` — a computed timestamp for when the downstream system should re-poll, based on the current risk level. Halted models: re-check in 1 hour. Proceeding models: 24 hours. This prevents both over-polling and stale trust caches in downstream agents.

### Model Version-Based Drift Filtering

The drift history API supports `?version=v2` filtering so you can isolate performance of a specific retrained model version. Combined with the version promotion flow, this gives a complete A/B view of model quality before and after retraining.

### Feature Domain Metadata Without LLM

`GET /drift/feature-meta` returns pre-computed business descriptions for every feature (what `int_rate` means in credit context, why it's a leading indicator, what a shift means). No LLM call — instant response — used to enrich the feature breakdown UI.

### HMAC Slack Signature Verification

The `/webhooks/slack/interact` endpoint implements proper `x-slack-signature` HMAC-SHA256 verification. This is production-grade Slack security — not a toy demo webhook. Only Slack can send valid approval callbacks.

### SQLite Fallback for Zero-Config Local Dev

If `DATABASE_URL` is unset, the entire backend runs on SQLite. No PostgreSQL required to demo the product. All features work identically. The startup log announces which backend is in use.

### Docker Compose Full Stack

`docker-compose.yml` brings up PostgreSQL, local Phoenix, FastAPI backend, and React dashboard in a single command for fully isolated demo environments. Not needed for local dev but useful for fully reproducible demos.

---

*Document generated from codebase analysis — all features verified against actual source code.*
*Project: `financial-driftguard` | Branch: `feat/governance-agent` | Date: 2026-06-09*
