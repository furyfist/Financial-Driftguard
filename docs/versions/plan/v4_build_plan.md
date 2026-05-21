# FinSight AI — V4 Build Plan

**Document type:** Engineering build plan  
**Project:** `finsight-ai`  
**Current version:** `v0.3.0` (hackathon submission, May 2026)  
**Target version:** `v0.4.0`  
**Built on top of:** V3 — governance agent, trust API, PDF reports, 3 demo scenarios  
**Date:** May 2026  

---

## 1. What V4 Is About

V3 proved the thesis: same drift, different regime, opposite action. V4 makes it **demo-ready, user-ready, and production-closer** in three parallel tracks:

- **Track A — Visual Polish:** Make the backend work visible. The system is powerful but looks like a dev tool. V4 makes it look like a product.
- **Track B — User Features:** Five features that shift FinSight from "a tool you query" to "a system that reports to you."
- **Track C — Production Foundations:** Tech debt from V1–V3 that blocks deployment, plus migration to Google ADK 2.0.

---

## 2. What Changed Since V3

### External Updates (as of May 21, 2026)

**Google ADK 2.0** — Released at Google I/O '26 (May 19, 2026). Code-first framework for multi-agent systems. Unified graph-based engine, collaborative workflows, one-command deploy to Google Cloud. Available in Python, Go, Java, TypeScript. Model-agnostic — works with Gemini, Claude, Llama. This replaces our custom `BaseLLMProvider` abstraction for the Gemini submission path.

**Phoenix v15.11.1** — Our current version. Latest release adds:
- Span attribute filtering via Python/TypeScript client and CLI
- CLI span notes (`px span add-note`)
- Claude Opus 4.7 in the Playground
- Azure managed identity for PostgreSQL
- Experiment `trace_id` in evaluator functions
- Secrets management UI

**Phoenix MCP Server** — Full tool coverage confirmed:
- Prompts: `list-prompts`, `get-prompt`, `upsert-prompt` + 7 more
- Projects: `list-projects`, `get-project`
- Traces: `list-traces`, `get-trace`
- Spans: `get-spans`, `get-span-annotations`
- Sessions: `list-sessions`, `get-session`
- Datasets: `list-datasets`, `get-dataset`, `get-dataset-examples`, `add-dataset-examples`
- Experiments: `list-experiments-for-dataset`, `get-experiment-by-id`

**arize-phoenix-client 2.4.0+** — Span attribute filtering, experiment trace ID access.

**arize-phoenix-evals** — Released May 5, 2026. Supports Python 3.10–3.14, adapters for OpenAI, LiteLLM, LangChain.

---

## 3. Architecture Evolution (V3 → V4)

```
V3 Architecture:
  Groq/Gemini ← custom BaseLLMProvider abstraction
  Phoenix ← phoenix.otel.register()
  MCP ← thin Python wrappers in phoenix_tools.py
  Dashboard ← functional but raw

V4 Architecture:
  Google ADK 2.0 ← replaces custom LLM abstraction for agent orchestration
  │  └── Groq adapter (dev) / Gemini native (submission)
  │  └── Multi-agent: GovernanceAgent + AnalystAgent + ReportAgent
  Phoenix v15.11+ ← span attribute filtering, experiment trace_id
  │  └── phoenix-client 2.4.0+ for typed queries
  MCP ← same tools, better utilisation (span annotations, session tracking)
  Dashboard ← visual polish layer on top of existing components
  Notifications ← Slack/Email with regime context (new)
  Scheduled Jobs ← weekly digest (new)
```

---

## 4. Track A — Visual Polish

All visual work amplifies the backend. No visual exists for its own sake.

---

### A1. Animated HALT Overlay on Black Swan Detection

**What:** When regime flips to `black_swan`, a full-screen overlay fires for 2 seconds — dark background, red pulse animation, the word **HALT** in large type, then the dashboard updates underneath.

**Why:** This is the single most powerful demo moment. A judge sees the screen go red before reading anything and immediately understands the product.

**Where it lives:** `dashboard/src/components/HaltOverlay.tsx`

**Trigger:** `ModelDetail.tsx` watches the latest drift run. If `regime === "black_swan"` AND this is a new run (not already displayed), fire the overlay. Overlay auto-dismisses after 2 seconds via `setTimeout`.

**Design:**
- Background: `rgba(0, 0, 0, 0.92)` — near-black
- Text: `HALT` in Bricolage Grotesque, 120px, `#C0200F` (existing critical colour)
- Subtext: "Black swan regime detected. All automated decisions frozen." in 18px, white, `DM Mono`
- Red ring pulse animation: `@keyframes halt-pulse` — 0.8s ease-in-out infinite, border 4px solid `#C0200F`
- After 2s: overlay fades out over 300ms, dashboard is updated underneath

**Effort:** 3 hours

---

### A2. Drift Score Chart with Regime Colour Bands

**What:** Replace the single-point `LineChart` on ModelDetail with a full 13-run chart showing regime-coloured data points and vertical shaded bands per regime period.

**Why:** One glance tells the entire product thesis — three regimes, three severity levels, three opposite actions. No text needed.

**Where it lives:** `dashboard/src/components/DriftChart.tsx` (new), imported into `ModelDetail.tsx`

**Design:**
- X-axis: timestamps of all drift runs
- Y-axis: drift score (0–0.10)
- Data points: circles coloured by regime — `#1A6B3C` (stable), `#B45309` (credit_stress), `#C0200F` (black_swan)
- `ReferenceArea` components from Recharts: vertical shaded bands behind the chart showing regime periods
  - Stable = green tint `rgba(26, 107, 60, 0.08)`
  - Credit stress = amber tint `rgba(180, 83, 9, 0.08)`
  - Black swan = red tint `rgba(192, 32, 15, 0.08)`
- Horizontal `ReferenceLine` at PSI threshold `0.10` (dashed, grey)
- `Tooltip` on hover: regime badge, severity, top drifted feature, recommendation snippet
- `DM Mono` for all numbers in the chart

**Data source:** `GET /drift/{model_id}/history?limit=50` — already returns everything needed

**Effort:** 4 hours

---

### A3. Demo Scenario Control Panel

**What:** A dashboard component that replaces terminal commands for demos. Three scenario cards, each with a "Run" button. Clicking fires the API and the dashboard updates live.

**Why:** Judges can drive the demo themselves. No terminals. Cause and effect, visually.

**Where it lives:** `dashboard/src/components/DemoPanel.tsx`, shown only when URL has `?demo=true` query param

**Design:**
- Three cards in a horizontal row:
  - **Rate Hike Q4 2018** — amber left border, `credit_stress` badge, "Expected: monitor, don't retrain"
  - **COVID Crash March 2020** — red left border, `black_swan` badge, "Expected: HALT"
  - **Normal Model Decay** — green left border, `stable` badge, "Expected: investigate, retrain"
- Each card has a "Run Scenario" button
- On click: fires `POST /drift/{model_id}/run` with the scenario's macro payload
- Loading spinner while running
- After completion: dashboard auto-refreshes, chart adds a new point, regime badge updates
- Right side: a live log panel showing the terminal-style output in `DM Mono` (scrollable, dark background)

**API support needed:** New endpoint `POST /demo/scenarios/{scenario_name}` that wraps the scenario scripts. Returns the drift result directly so the frontend can update without polling.

**Effort:** 4 hours (frontend) + 2 hours (backend endpoint)

---

### A4. Agent Chat Structured Response Cards

**What:** Upgrade `AgentChat.tsx` from plain text bubbles to structured cards with visual hierarchy.

**Why:** Makes the chat look like a real financial product, not a dev tool.

**Where it lives:** `dashboard/src/components/AgentResponseCard.tsx` (new)

**Design per response card:**
- Top row: `RegimeBadge` (existing) + severity pill + confidence progress bar
- Main body: recommendation text in bold, 16px
- Impact box: grey background, estimated loss range and FNR increase
- Source chips: small pills at the bottom linking to trace IDs
- Typing animation: three pulsing dots while Groq is streaming

**Suggestion chips when chat is empty:**
- "Is my lending model safe right now?"
- "What happened in March 2020?"
- "Should I retrain?"
- Clicking a chip sends that query to `/agent/ask`

**Effort:** 3 hours

---

### A5. PDF Cover Page

**What:** Add a one-page cover to the SR 11-7 report before Section 1.

**Where it lives:** `finsight/reports/generator.py` — insert cover page before existing sections

**Design (in reportlab):**
- Top: "FinSight AI" in 36pt bold
- Subtitle: "MODEL GOVERNANCE REPORT" in 14pt, caps, grey
- Coloured status box: current regime badge (red/amber/green background with white text)
- Model name, reporting period, generated timestamp
- One-line executive summary: auto-generated from the latest agent recommendation
- Bottom: "CONFIDENTIAL" watermark diagonally across the page in 10% opacity grey

**Effort:** 2 hours

---

## 5. Track B — User Features

Five features that shift FinSight from a tool you query to a system that reports to you.

---

### B1. Slack / Email Alerts with Regime Context

**What:** When drift crosses a severity threshold, fire a Slack message and/or email that includes regime context, recommended action, and business impact estimate.

**Current state:** V2 built a `BaseNotifier` interface with Discord, Slack (partial), and Telegram (partial) adapters. Webhook config endpoint exists. BUT the payloads only contain severity and PSI — no regime, no recommendation, no impact.

**V4 scope:**
- Enrich the existing `SlackNotifier` payload with: regime, confidence, recommended action, top 3 drifted features, estimated dollar impact
- Add `EmailNotifier` adapter using SMTP (stdlib `smtplib` — no new dependencies)
- Wire the notification trigger into the agent's decision chain: after the agent produces a recommendation, if severity is `high` or `critical`, fire the notification with the full context
- Test the Slack adapter end-to-end against a real Slack webhook URL

**Payload format (Slack Block Kit):**
```json
{
  "blocks": [
    {"type": "header", "text": "🛑 FinSight AI — lending_club_v1"},
    {"type": "section", "text": "Regime: black_swan (confidence: 1.00)\nSeverity: CRITICAL | Drift: 0.0754"},
    {"type": "section", "text": "Recommendation: HALT automated decisions\nEst. impact: $3.2M–$4.8M exposure"},
    {"type": "actions", "elements": [{"type": "button", "text": "Open Dashboard", "url": "http://..."}]}
  ]
}
```

**New files:**
- `finsight/notifications/enricher.py` — takes `AgentResponse` + `ImpactEstimate` → enriched notification payload
- `driftguard/adapters/email_notifier.py` — SMTP email adapter

**Modified files:**
- `driftguard/adapters/slack_notifier.py` — replace simple payload with enriched Block Kit format
- `finsight/agent/brain.py` — after producing recommendation, call enricher → fire notification

**Env vars:**
```
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/...
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=...
SMTP_PASSWORD=...
ALERT_EMAIL_TO=risk-officer@example.com
```

**Effort:** 2 days

---

### B2. Natural Language Drift Query

**What:** Users ask questions about their drift history in plain English. The agent translates the question into a structured query against Phoenix traces + DriftGuard DB and returns a formatted answer.

**Examples:**
- "Show me all drift runs where regime was black_swan"
- "Which features have drifted consistently across all regimes?"
- "Compare last quarter vs this quarter — what changed?"
- "When was the last time this model was fully healthy?"

**How it works:**
- New tool in `finsight/agent/tools/query_tools.py` — `query_drift_history(filters)`
- Filters: `regime`, `severity`, `date_range`, `feature_name`, `model_id`
- Agent receives the user question, calls the tool with the right filters, formats the response
- Uses existing `/drift/{model_id}/history` endpoint with new query parameters added

**New API query params on `/drift/{model_id}/history`:**
- `regime=black_swan` — filter by regime
- `severity=critical` — filter by severity
- `feature=int_rate` — filter by top drifted feature
- `since=2026-01-01` / `until=2026-05-21` — date range

**Frontend:** Already handled — questions go through `/agent/ask`, agent has the new tool. No new UI needed beyond the existing `AgentChat`.

**Effort:** 3 days

---

### B3. Explainable Drift — "Why Did This Feature Drift?"

**What:** When a feature drifts at `high` or `critical` severity, the agent generates a one-paragraph explanation using macro context, historical patterns, and the feature's domain role.

**Output example:**
> "int_rate drifted (PSI 0.10) because new loan originations are pricing in the Fed's forward guidance. VIX is elevated at 25 and the yield curve is nearly flat (0.21). This is consistent with the Q4 2018 hiking cycle — macro-driven drift, not a data quality issue. Retraining on this data would lock in rate-cycle patterns that reverse post-stabilisation."

**How it works:**
- New tool in `finsight/agent/tools/drift_tools.py` — `explain_feature_drift(feature_name, drift_result, regime, macro)`
- Calls the LLM with a structured prompt containing:
  - Feature name and its role in the model (from a feature metadata lookup)
  - Current PSI/KS/JS scores
  - Current regime and macro values
  - Historical pattern from `historical_patterns.py` (if available)
- Agent calls this tool automatically when producing recommendations for `high`/`critical` severity

**New files:**
- `finsight/impact/feature_metadata.py` — static lookup: `{"int_rate": "Loan interest rate — directly affected by Fed policy", "dti": "Debt-to-income ratio — sensitive to employment and income trends", ...}` for all 17 Lending Club features

**Frontend:** `ActionCard.tsx` gets an expandable "Why did this drift?" section that shows the explanation text when clicked.

**Effort:** 2 days

---

### B4. Scheduled Governance Review — Weekly Digest

**What:** Every Monday at 8am, auto-generate a one-page weekly digest for every registered model. Delivered by email or Slack.

**Digest contents:**
- Model name and current status (traffic light: green/amber/red)
- Regime this week vs last week
- Drift score trend (up/down/stable arrow)
- Any agent decisions made during the week
- Forecast for next 7 days (from the existing forecaster)
- One-line summary: "lending_club_v1 is healthy. No action required." or "lending_club_v1 needs attention — drift increasing in stable regime."

**How it works:**
- New scheduled job in `driftguard/scheduler/jobs.py` — `_run_weekly_digest()`
- Runs every Monday 08:00 UTC via APScheduler
- Calls `ReportGenerator` with `format="digest"` flag (new) — produces a short text summary instead of the full 7-section PDF
- Fires the enriched notification via Slack/email (reuses B1 infrastructure)

**New files:**
- `finsight/reports/digest.py` — `DigestGenerator.generate(model_id, period="7d") → DigestReport`
- `DigestReport` dataclass: `status_light`, `regime_current`, `regime_previous`, `drift_trend`, `agent_decisions_count`, `forecast_summary`, `one_liner`

**Effort:** 1 day

---

### B5. Model Version Registry

**What:** Every model has versions. Each version has its own drift history, baseline, and agent decision log. When you retrain, you create a new version — old history stays intact.

**Why this matters long-term:** Without version tracking, drift history is meaningless after the first retrain. All runs before and after the retrain get mixed together.

**Schema changes:**
- New table: `ModelVersion` — `id`, `model_id`, `version_label`, `description`, `baseline_blob`, `baseline_rows`, `created_at`, `promoted_at`, `demoted_at`, `is_active`
- `DriftRun` gets a new column: `model_version_id` (foreign key to `ModelVersion`)
- `AgentDecisionLog` gets a new column: `model_version_id`

**API changes:**
- `POST /models/{id}/versions` — create a new version (with baseline)
- `GET /models/{id}/versions` — list all versions
- `POST /models/{id}/versions/{v}/promote` — set as active champion
- `GET /drift/{id}/history` — add `version` query param to filter by version

**Dashboard changes:**
- `ModelDetail.tsx` — version selector dropdown above the drift chart
- Switching versions filters the chart and all data below it
- Version badges next to model name: `v1 (active)`, `v2 (challenger)`

**Migration concern:** Existing drift runs get assigned `version_id=1` (auto-created "v1" for each existing model). No data loss.

**Effort:** 4 days

---

## 6. Track C — Production Foundations

---

### C1. Google ADK 2.0 Migration

**What:** Replace the custom `BaseLLMProvider` abstraction with Google ADK 2.0's agent framework for the submission path.

**Why:** ADK 2.0 is the sponsor's production framework (released May 19, 2026). Using it shows deep integration with Google Cloud. It also gives us multi-agent orchestration for free.

**Migration plan:**
- Keep `finsight/llm/` for dev (Groq stays as-is)
- Add `finsight/adk/` for the ADK 2.0 agent definition
- ADK agent wraps our existing `GovernanceAgent` logic as an `LlmAgent`
- MCP tools are registered as ADK `Tool` definitions
- Config switch: `AGENT_FRAMEWORK=native` (current) or `AGENT_FRAMEWORK=adk` (new)

**Multi-agent split with ADK 2.0:**
```python
from google.adk.agents import LlmAgent

governance_agent = LlmAgent(
    name="governance_agent",
    model="gemini-2.5-pro",
    instruction="You are the FinSight AI governance orchestrator...",
    tools=[drift_check, get_macro, list_traces, get_trust_score],
    sub_agents=[analyst_agent, report_agent],
)

analyst_agent = LlmAgent(
    name="analyst_agent",
    model="gemini-2.0-flash",
    instruction="You explain drift causes using macro context...",
    tools=[explain_feature_drift, get_historical_patterns],
)

report_agent = LlmAgent(
    name="report_agent",
    model="gemini-2.0-flash",
    instruction="You generate SR 11-7 compliant report sections...",
    tools=[generate_section, format_pdf],
)
```

**New files:**
- `finsight/adk/__init__.py`
- `finsight/adk/agents.py` — ADK agent definitions
- `finsight/adk/tools.py` — ADK tool wrappers around existing tools
- `finsight/adk/config.py` — ADK configuration and model selection

**Env vars:**
```
AGENT_FRAMEWORK=adk          # or "native"
GOOGLE_GENAI_API_KEY=...
```

**Effort:** 3 days

---

### C2. API Authentication

**What:** Static API key in `.env` with `X-API-Key` header validation on all routes.

**Current state:** Any client on the network can call every endpoint. Single biggest blocker for deployment.

**Implementation:**
- New middleware in `driftguard/api/middleware/auth.py`
- Reads `API_KEY` from `.env`
- If set, validates `X-API-Key` header on every request
- If not set (local dev), all requests pass through
- Exempt: `GET /health` (always open)

**Effort:** 4 hours

---

### C3. Phoenix Trace ID Linkage

**What:** Store the OTEL span ID alongside the `DriftRun` DB record so the audit trail references real Phoenix trace UUIDs.

**Current state:** Agent decision sources show `run_id: 6` not OTEL span UUIDs.

**Implementation:**
- After each traced drift run completes, extract the span context's `trace_id` from the active span
- Store it in a new `trace_id` column on the `DriftRun` table
- Report generator and agent source references use the real trace ID
- Trust API response includes `phoenix_trace_id` field

**Effort:** 4 hours

---

### C4. Section 7 Prose Count Fix

**What:** Pass the actual run count to the Section 7 LLM prompt instead of letting it infer from the 5-run capped context.

**Current bug:** Section 7 says "5 drift checks" but the audit trail lists 13.

**Fix:** Add `total_run_count: int` to the Section 7 prompt template: "There were {total_run_count} drift checks in this period."

**Effort:** 30 minutes

---

### C5. V2 Technical Debt Cleanup

Items carried over from V2 that are now worth fixing:

| Item | What | Effort |
|---|---|---|
| `drifted_features` dedup | Count unique features, not detector hits. Feature in PSI+KS+JS counts 3x currently | 2h |
| Webhook config persistence | `WebhookConfig` table in SQLite, loaded on startup | 4h |
| Scheduler health endpoint | `GET /health/scheduler` returns job states, last run, failures | 4h |
| Async macro fetch on startup | Background thread, don't block lifespan | 2h |
| `.env.example` validation | Warn on missing keys at startup instead of silent failure | 1h |
| Minimum row validation | `DataSnapshot.from_dataframe()` raises if < 100 rows | 1h |

**Total effort:** 2 days

---

### C6. Docker Compose Full Stack

**What:** Single `docker compose up` starts everything: backend, frontend, Phoenix, Phoenix MCP server.

**Current state:** Phoenix is in compose. Backend and frontend require manual terminal commands.

**Services:**
```yaml
services:
  phoenix:
    image: arizephoenix/phoenix:latest
    ports: ["6006:6006", "4317:4317"]

  phoenix-mcp:
    image: node:20-slim
    command: npx -y @arizeai/phoenix-mcp@latest --baseUrl http://phoenix:6006
    depends_on: [phoenix]

  backend:
    build: .
    command: uvicorn driftguard.api.main:app --host 0.0.0.0 --port 8000
    ports: ["8000:8000"]
    env_file: .env
    depends_on: [phoenix]
    volumes:
      - ./driftguard.db:/app/driftguard.db

  dashboard:
    build: ./dashboard
    ports: ["5173:5173"]
    depends_on: [backend]
```

**New files:**
- `Dockerfile` (backend)
- `dashboard/Dockerfile` (frontend)
- Updated `docker-compose.yml`

**Effort:** 1 day

---

## 7. Checkpoint Map

| Checkpoint | Items | What's True When Done | Priority |
|---|---|---|---|
| **CP1: Visual Core** | A1, A2 | HALT overlay fires on black_swan. Drift chart shows 13 points with regime bands. | MUST DO |
| **CP2: Demo Ready** | A3, A4, A5 | Judges click scenario buttons. Agent chat has structured cards. PDF has cover page. | SHOULD DO |
| **CP3: Notifications** | B1, B4 | Slack fires on critical drift with regime context. Weekly digest runs on schedule. | SHOULD DO |
| **CP4: Intelligence** | B2, B3 | Users query drift history in English. Agent explains WHY a feature drifted. | SHOULD DO |
| **CP5: Production** | C1, C2, C3, C4, C5, C6 | ADK 2.0 integrated. Auth on all routes. Docker compose full stack. Tech debt cleared. | NICE TO HAVE |
| **CP6: Registry** | B5 | Model versions tracked. Drift history per version. Version selector in dashboard. | NICE TO HAVE |

---

## 8. Build Order

```
Week 1:  CP1 (A1 + A2) + C2 (auth) + C4 (section 7 fix)
         ↓ system is visually strong and auth-ready

Week 2:  CP2 (A3 + A4 + A5) + B1 (slack/email)
         ↓ demo-ready, notifications working

Week 3:  B3 (explainable drift) + B4 (weekly digest) + C3 (trace ID linkage)
         ↓ intelligence layer complete

Week 4:  C1 (ADK 2.0 migration) + B2 (natural language query) + C5 (tech debt)
         ↓ production foundations solid

Week 5:  B5 (model version registry) + C6 (docker compose full stack)
         ↓ V4 complete
```

---

## 9. Dependency Updates

### Python

```
# Existing — pin to latest
arize-phoenix>=15.11.0          # was 8.0.0
arize-phoenix-otel>=0.16.0      # unchanged
arize-phoenix-client>=2.4.0     # was 1.0.0 — adds span attribute filtering
arize-phoenix-evals>=latest     # new — for server-side evals (if needed)

# New
google-adk>=2.0.0               # ADK 2.0 (Track C1)
google-genai>=1.0.0             # Gemini SDK for ADK

# Unchanged
groq>=0.9.0
reportlab>=4.0.0
opentelemetry-api>=1.20.0
opentelemetry-sdk>=1.20.0
```

### Node (dashboard)

```
# No new dependencies — existing React + Recharts + Axios sufficient
```

---

## 10. Risk Register

| Risk | Impact | Mitigation |
|---|---|---|
| ADK 2.0 is 2 days old — possible breaking changes | Agent might not work on final deploy | Keep `AGENT_FRAMEWORK=native` as fallback. ADK is additive, not replacement |
| Groq → Gemini prompt differences in ADK | Agent responses differ in structure | Budget 3 hours for prompt tuning after ADK integration |
| HALT overlay too dramatic for formal demo | Judges might find it gimmicky | Make it toggleable via URL param `?dramatic=true` |
| Weekly digest runs before enough data accumulates | Empty or misleading digests | Guard: only fire digest if ≥3 drift runs exist for the model |
| Model version registry migration on existing data | Existing runs lose version context | Auto-create "v1" for each model, assign all existing runs to it |
| Full Docker compose might mask startup errors | Harder to debug | Keep manual terminal mode documented as the primary dev path |

---

## 11. Success Criteria

V4 is complete when:

1. A judge can click three buttons and see three different regime responses — no terminals
2. The HALT overlay fires on COVID scenario and the room understands in 2 seconds
3. A Slack message arrives within 10 seconds of a critical drift event
4. A risk officer can ask "Why did int_rate drift?" and get a domain-specific explanation
5. The PDF report has a professional cover page and all 7 sections render correctly
6. `docker compose up` starts the entire system from zero
7. All API routes require `X-API-Key` (except `/health`)
8. The governance agent runs on Google ADK 2.0 with Gemini 2.5 Pro

---

## 12. What V5 Looks Like (Not In Scope)

- Recession classifier — dedicated binary sub-classifier (0% recall inherited from V2)
- PostgreSQL migration — required for multi-user deployment
- Multi-model monitoring — monitoring more than one model simultaneously
- PyPI packaging — `pip install finsight-ai`
- Team collaboration — shared dashboard with role-based access
- Custom evaluators — user-defined drift evaluation criteria in Phoenix
- Real-time streaming — WebSocket push for live drift score updates

---

*FinSight AI V4 Build Plan — May 2026*  
*Built on V3 (hackathon submission)*  
*Target: demo-ready product + production foundations + Google ADK 2.0*
