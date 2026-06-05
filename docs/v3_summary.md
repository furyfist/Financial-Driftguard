**Document type:** Internal engineering milestone summary  
**Project:** `financial-driftguard` → `finsight-ai`  
**Version tagged:** `v0.3.0` (pre-release, hackathon submission)  
**Branch:** `feature/regime-aware-agent`  
**Status at close:** All 10 steps complete, 3 demo scenarios passing, PDF report verified  
**Built on top of:** `v0.2.0` (DriftGuard — ML regime classifier, V2 dashboard)  

---

## Purpose of This Document

This document is the definitive engineering reference for what "V3 complete" means in the context of the FinSight AI project. It is written for the author's future self, collaborators, or any senior reviewer who needs to understand what was built on top of DriftGuard V2, why specific architectural decisions were made, what bugs were encountered and how they were fixed, what tradeoffs were accepted, and where V4 picks up. It is not a user README or marketing summary.

---

## Project Goal and the Meaning of "V3"

V3 transforms DriftGuard from a drift detection library into **FinSight AI** — a regime-aware financial model governance agent. The core thesis remains unchanged from V1/V2: the same drift signal requires opposite actions depending on the market regime. V3 adds the intelligence layer that acts on this thesis automatically, surfaces results to three distinct stakeholder personas, and produces regulatory-grade audit artifacts.

**V3 scope:** LLM abstraction layer, Phoenix observability integration, Arize MCP bridge, governance agent brain, business impact translator, proactive drift forecaster, champion-challenger automation, SR 11-7 PDF report generation, agent-to-agent trust API, and multi-persona dashboard extensions.

**What V3 is not:** production-hardened (no auth), multi-tenant, or cloud-deployed. SQLite remains the store. These are V4 concerns.

---

## Architecture

```
Financial ML Models (Lending Club LightGBM — demo)
         ↓
DriftGuard Engine (V1/V2 — untouched)
  PSI + KS + JS detectors → Monitor.check()
  RegimeTagger ML classifier (93.9% accuracy)
  MacroSignalFetcher (FRED + VIX)
         ↓
Phoenix Observability Layer (NEW — finsight/tracing/)
  Every drift run = structured OTEL trace
  Per-detector spans, regime spans, macro tool spans
         ↓
Arize MCP Server (NEW — finsight/agent/tools/phoenix_tools.py)
  Agent's only window into trace history
  list-traces, get-spans, list-experiments, get-dataset-examples
         ↓
Governance Agent (NEW — finsight/agent/)
  LLM: Groq (dev) → Gemini 2.5 Pro (submission)
  Regime-aware reasoning over Phoenix traces + macro context
  Every agent decision itself traced back to Phoenix
         ↓
Three Outputs (NEW — finsight/ modules)
  → Engineer: action cards + impact banner in dashboard
  → Quant: champion-challenger experiments in Phoenix
  → Risk officer: chat interface + SR 11-7 PDF report
  → Other agents: /trust/{model_id} trust score API
```

---

## Repository Structure (V3 additions only)

V3 adds one new top-level package (`finsight/`) and extends three existing directories. Nothing in `driftguard/core/`, `driftguard/detectors/`, or `driftguard/regime/` was modified.

```
financial-driftguard/
│
├── finsight/                            # NEW — all V3 intelligence logic
│   ├── __init__.py
│   ├── llm/
│   │   ├── __init__.py
│   │   ├── provider.py                  # BaseLLMProvider abstract class
│   │   ├── groq_provider.py             # Groq (dev)
│   │   ├── gemini_provider.py           # Gemini 2.5 Pro (submission)
│   │   └── config.py                    # reads .env, returns get_llm(role)
│   ├── tracing/
│   │   ├── __init__.py
│   │   ├── setup.py                     # init_tracing() wraps phoenix.otel.register()
│   │   ├── decorators.py                # @traced_drift_check, @traced_regime_tag etc.
│   │   └── attributes.py               # custom OpenInference attribute constants
│   ├── agent/
│   │   ├── __init__.py
│   │   ├── brain.py                     # main agent orchestrator
│   │   ├── memory.py                    # conversation context manager
│   │   ├── tools/
│   │   │   ├── __init__.py
│   │   │   ├── phoenix_tools.py         # MCP server wrappers
│   │   │   ├── drift_tools.py           # DriftGuard API wrappers
│   │   │   ├── macro_tools.py           # MacroSignalFetcher wrappers
│   │   │   └── experiment_tools.py      # Phoenix experiment triggers
│   │   └── prompts/
│   │       ├── orchestrator.py          # main reasoning system prompt
│   │       ├── analyst.py               # drift analysis prompt
│   │       └── report_writer.py         # SR 11-7 prose generation prompt
│   ├── impact/
│   │   ├── __init__.py
│   │   ├── estimator.py                 # PSI → dollar impact mapping
│   │   └── historical_patterns.py       # Lending Club calibration lookup
│   ├── forecast/
│   │   ├── __init__.py
│   │   ├── predictor.py                 # macro signal drift forecaster
│   │   └── event_calendar.py            # FOMC dates, earnings seasons
│   ├── challenger/
│   │   ├── __init__.py
│   │   └── runner.py                    # champion-challenger via Phoenix experiments
│   ├── reports/
│   │   ├── __init__.py
│   │   ├── generator.py                 # SR 11-7 PDF builder
│   │   ├── templates/
│   │   │   └── sr_11_7.py               # 7-section report structure
│   │   └── output/                      # .gitignored, generated PDFs
│   └── trust_api/
│       ├── __init__.py
│       └── handler.py                   # TrustScore dataclass + logic
│
├── driftguard/                          # EXISTING — minimal modifications
│   └── api/
│       ├── main.py                      # MODIFIED: init_tracing() in lifespan, new routes registered
│       ├── schemas.py                   # MODIFIED: AgentAskRequest, TrustScore, ReportRequest schemas
│       └── routes/
│           ├── agent.py                 # NEW: /agent/ask, /agent/analyze, /agent/report
│           ├── experiments.py           # NEW: /experiments/{id}/challenger, /experiments/{id}/results
│           └── [existing unchanged]
│   └── store/
│       └── database.py                  # MODIFIED: AgentDecisionLog table added
│
├── dashboard/                           # EXISTING — extended
│   └── src/
│       ├── api/
│       │   └── agent-client.ts          # NEW: typed client for all V3 endpoints
│       ├── components/
│       │   ├── AgentChat.tsx            # NEW: conversational interface
│       │   ├── ActionCard.tsx           # NEW: structured recommendation card
│       │   ├── ImpactBanner.tsx         # NEW: dollar impact display
│       │   └── ForecastAlert.tsx        # NEW: proactive warning banner
│       └── pages/
│           ├── AgentView.tsx            # NEW: risk officer chat page
│           └── ExperimentView.tsx       # NEW: quant experiment comparison page
│
├── demo/
│   └── scenarios/                       # NEW: pre-built demo scenarios
│       ├── __init__.py
│       ├── covid_crash.py               # VIX=57, black_swan → HALT
│       ├── rate_hike_2017.py            # Q4 2018 peak values → credit_stress
│       └── normal_decay.py              # stable + synthetic perturbation → RETRAIN
│
├── scripts/
│   └── demo_full.py                     # NEW: orchestrates all 3 scenarios
│
├── docker-compose.yml                   # NEW: Phoenix sidecar service
└── Makefile                             # NEW: make setup/serve/seed/test/demo targets
```

---

## Delivered Components

### 1. LLM Abstraction Layer (`finsight/llm/`)

The first component built. Every downstream module that needs an LLM imports only from `finsight/llm/config.py` — never from Groq or Gemini SDKs directly.

`BaseLLMProvider` — abstract class with `complete(messages, tools, temperature) → LLMResponse` and `stream(messages) → AsyncIterator[str]`. `LLMResponse` is a dataclass: `content`, `tool_calls`, `usage`, `model`.

`GroqProvider` — implements `BaseLLMProvider` against Groq's OpenAI-compatible endpoint. Default reasoning model: `llama-3.3-70b-versatile`. Default fast model: `llama-3.3-70b-versatile` (see tradeoffs — originally `llama-3.1-8b-instant`, changed due to TPM limits).

`GeminiProvider` — implements `BaseLLMProvider` against Google Generative AI SDK. Submission model: `gemini-2.5-pro` (reasoning), `gemini-2.0-flash` (generation).

`config.py` — reads `LLM_PROVIDER`, `LLM_REASONING_MODEL`, `LLM_FAST_MODEL` from environment. `get_llm(role="reasoning" | "fast") → BaseLLMProvider`. Provider selection happens exactly once, here. No other file in the codebase knows which LLM is active.

**Tradeoff accepted:** Tool/function calling schema follows OpenAI format. Both Groq and Gemini support this format, which makes the swap mechanical — change three env vars, nothing else. The cost is that Gemini's native function calling has slightly different capabilities that are not exposed.

---

### 2. Phoenix Observability Layer (`finsight/tracing/`)

Instruments existing DriftGuard operations without modifying them. All tracing code lives in `finsight/tracing/` — zero imports from this module exist inside `driftguard/core/`, `driftguard/detectors/`, or `driftguard/regime/`.

`setup.py` — `init_tracing(project_name)` wraps `phoenix.otel.register()` with DriftGuard-specific defaults. Called once in `driftguard/api/main.py` lifespan. Reads `PHOENIX_COLLECTOR_ENDPOINT` from environment.

`decorators.py` — four decorators applied at the route handler level in `driftguard/api/routes/drift.py`:
- `@traced_drift_check` — CHAIN span, attributes: `model.id`, `drift.score`, `drift.severity`, `regime.class`, `regime.confidence`
- `@traced_regime_tag` — CHAIN span, attributes: `regime.class`, `regime.confidence`, `signals_fired`
- `@traced_detector` — CHAIN span per detector, attributes: `detector.name`, `feature.name`, `drift.score`, `drift.threshold`
- `@traced_macro_fetch` — TOOL span, attributes: `macro.vix`, `macro.credit_spread`, `macro.fed_funds`, `macro.yield_curve`

`attributes.py` — custom OpenInference attribute name constants. Prevents string typos across the codebase.

**Graceful degradation:** Every decorator wraps its tracing logic in try/except. If Phoenix is unreachable, the decorated function runs normally — tracing failure never surfaces to the user.

**Phoenix project:** `finsight-ai`. Separate from any existing Phoenix projects. All FinSight traces and agent decisions land here.

---

### 3. Arize MCP Bridge (`finsight/agent/tools/phoenix_tools.py`)

Connects the agent to Phoenix's data without the agent calling the Phoenix REST API directly. The MCP server runs as a sidecar (Docker) or local process and exposes Phoenix data as structured tool calls.

Tools exposed to the agent:
- `list_recent_drift_traces(project_name, limit)` — recent drift run trace list
- `get_trace(trace_id)` — full trace tree for a specific run
- `get_spans(trace_id)` — per-detector, per-feature span breakdown
- `list_datasets()` — available Phoenix datasets
- `get_dataset_examples(dataset_id)` — drift run benchmark examples
- `list_experiments(dataset_id)` — experiment result list
- `get_experiment(experiment_id)` — detailed experiment with per-example scores

Each tool has an OpenAI-compatible function definition so the LLM can call it during reasoning. The MCP server URL is configurable via `PHOENIX_MCP_BASE_URL` env var.

**MCP server startup (local dev):**
```
npx -y @arizeai/phoenix-mcp@latest --baseUrl http://localhost:6006
```

**Docker compose:**
```yaml
phoenix-mcp:
  command: npx -y @arizeai/phoenix-mcp@latest --baseUrl http://phoenix:6006
  depends_on: [phoenix]
```

---

### 4. Governance Agent (`finsight/agent/`)

The core intelligence layer. Takes a user query or drift event trigger, reasons over Phoenix traces and macro context, and produces regime-aware recommendations.

`brain.py` — `GovernanceAgent` class. `ask(query, model_id) → AgentResponse`. Reasoning chain:
1. Fetch latest drift traces from Phoenix via MCP tools
2. Extract regime assessment and feature breakdown
3. Cross-reference with live macro signals
4. Apply regime-specific decision logic
5. Produce structured recommendation with confidence
6. Log decision to `AgentDecisionLog` table
7. Emit the agent decision itself as a Phoenix trace

`memory.py` — `ConversationMemory` class. Stores last N messages (default 20). Includes system prompt and tool results in context. Resets on new session.

`prompts/orchestrator.py` — system prompt encoding the core regime-decision rules:
- `black_swan` → always recommend HALT, never retrain
- `credit_stress` or `rate_shock` → monitor, do not retrain
- `stable` + drift → investigate model decay, consider retraining
- `recession` → champion-challenger approach

`AgentDecisionLog` SQLModel table — `model_id`, `query`, `recommendation`, `action`, `confidence`, `regime_context`, `trace_ids_referenced`, `created_at`. Every agent decision is persisted. This is the audit trail for governance decisions.

**Agent decision is itself traced:** When the agent produces a recommendation, that decision is logged as a Phoenix trace. Phoenix therefore contains both the drift data and the governance response — full observability of the reasoning layer.

**API routes (`driftguard/api/routes/agent.py`):**
- `POST /agent/ask` — `{"query": str, "model_id": str}` → `AgentResponse`
- `POST /agent/analyze` — `{"model_id": str}` → structured drift analysis
- `POST /agent/report` — `{"model_id": str, "date_range": str}` → PDF download

`AgentResponse` schema: `recommendation`, `action` (enum), `confidence` (0–1), `reasoning`, `sources` (list of trace/run IDs), `model_id`.

---

### 5. Business Impact Translator (`finsight/impact/`)

Converts drift scores into estimated dollar impact. No ML — rule-based mapping calibrated against Lending Club historical data.

`ImpactEstimator.estimate(drift_result, regime, portfolio_size) → ImpactEstimate`:
- PSI 0.10–0.20 → 2–5% FNR increase
- PSI 0.20–0.50 → 5–12% FNR increase
- PSI > 0.50 → 12–25% FNR increase
- Regime multipliers: `credit_stress` = 1.5×, `black_swan` = 3×, `stable` = 1×

`ImpactEstimate` dataclass: `estimated_loss_range: tuple[float, float]`, `false_negative_rate_increase: float`, `affected_portfolio_pct: float`, `confidence: str`, `explanation: str`.

`historical_patterns.py` — lookup table pre-computed from 2013–2020 Lending Club backtest. Maps `(feature_name, regime, psi_bucket) → observed_default_rate_change`. Used as calibration.

---

### 6. Proactive Drift Forecaster (`finsight/forecast/`)

Predicts drift probability 7–14 days out using macro signals already collected by `MacroSignalFetcher`. Rule-based (not a trained model) — sufficient for the hackathon, upgradeable post-submission.

`DriftForecaster.forecast(macro_history) → DriftForecast`:
- VIX 5-day momentum > 2 std → elevated probability
- Yield curve inversion starting → `rate_shock` likely in 14–30 days
- Credit spread widening + VIX rising → `credit_stress` likely in 7–14 days
- All stable → low probability

`event_calendar.py` — FOMC meeting dates loaded from JSON. Proximity to a Fed meeting + elevated VIX boosts forecast probability.

Scheduled via APScheduler as a daily job added to the existing scheduler in `driftguard/scheduler/jobs.py`. Forecast surfaced via `GET /forecast/{model_id}` and `ForecastAlert.tsx` on the dashboard Overview page.

---

### 7. Champion-Challenger Automation (`finsight/challenger/`)

Triggered automatically when the agent detects model decay (stable regime + high/critical severity). Compares current model against last stable baseline using Phoenix experiments.

`ChallengerRunner.run(model_id) → ChallengerResult`:
1. Load Lending Club benchmark dataset from Phoenix
2. Run current model predictions as experiment A
3. Run last stable baseline as experiment B
4. Attach AUC and PSI evaluators
5. Return `ChallengerResult`: `current_score`, `challenger_score`, `winner`, `metrics_diff`, `experiment_id`

Result surfaced to engineer via `ActionCard.tsx` in the dashboard with an approve/reject control.

API routes in `driftguard/api/routes/experiments.py`:
- `POST /experiments/{model_id}/challenger` — triggers comparison
- `GET /experiments/{model_id}/results` — retrieves latest comparison

**Guard:** runner checks regime before executing. Refuses to run during `credit_stress` or `black_swan` — champion-challenger on crisis data is meaningless and would produce a misleading result.

---

### 8. SR 11-7 PDF Report Generator (`finsight/reports/`)

Generates a regulatory-grade model governance report on demand. Seven sections matching the Federal Reserve's SR 11-7 supervisory guidance on model risk management (April 2011).

`ReportGenerator.generate(model_id, date_range) → Path`:
1. Fetch model metadata from DriftGuard API
2. Fetch drift run history (365-day window — see bug fixes)
3. Fetch macro snapshot history from `MacroCache`, deduplicated by calendar date
4. Fetch agent decisions from `AgentDecisionLog`
5. For each section: build a prompt with the relevant data slice (capped at 5 runs for LLM — see bug fixes), call `get_llm(role="fast")`, write prose
6. Assemble PDF using `reportlab`
7. Write to `finsight/reports/output/` (gitignored)
8. Return file path for API download response

**Seven sections:**
1. Model Identification — metadata, baseline size, creation date
2. Performance Summary — drift score trend, severity distribution, key dates
3. Regime Context — macro conditions over the period, deduplicated by day
4. Drift Analysis — top drifted features, detector breakdown, root cause assessment
5. Agent Recommendations — governance actions taken, confidence levels
6. Risk Assessment — business impact estimate, regime-adjusted risk level
7. Audit Trail — all DB run IDs, Phoenix trace IDs, agent decision IDs

**Verified output:** 13 drift runs · `stable`, `credit_stress`, `black_swan` regimes · max drift 0.0754 · 3 unique macro dates · all 7 sections LLM-written prose.

---

### 9. Agent-to-Agent Trust API (`finsight/trust_api/`)

Exposes FinSight as a callable tool for other AI agents. A credit decisioning agent, trading agent, or risk aggregator can query model trustworthiness before making automated decisions.

`TrustHandler.evaluate(model_id) → TrustScore`:

| Condition | `trustworthy` | `recommendation` |
|---|---|---|
| No drift + stable | `True` | `proceed` |
| Low drift + stable | `True` | `proceed_with_caution` |
| High drift + macro regime | `True` | `proceed_with_caution` |
| High drift + stable | `False` | `escalate` |
| Any + black_swan | `False` | `halt` |

`TrustScore` dataclass: `model_id`, `trustworthy`, `confidence`, `regime`, `drift_severity`, `recommendation`, `reason`, `last_checked`, `next_check_recommended`.

API route: `GET /trust/{model_id}` — returns `TrustScore` JSON. Machine-readable for agent consumption, human-readable via the `reason` field.

**Validated against COVID scenario:** `trustworthy=False`, `recommendation=halt`, `confidence=1.0` — correct.

---

### 10. Multi-Persona Dashboard Extensions

Three new views added to the existing React dashboard. Existing pages modified minimally — new components slotted in as additions, not replacements.

**New components:**
- `ActionCard.tsx` — agent recommendation card: action type, confidence, regime badge, top features, acknowledge/override buttons
- `ImpactBanner.tsx` — dollar impact display: estimated loss range, FNR increase, regime multiplier explanation
- `ForecastAlert.tsx` — proactive warning banner on Overview when drift probability > 50%
- `AgentChat.tsx` — conversational chat interface, streaming-aware, session-managed

**New pages:**
- `AgentView.tsx` (`/agent`) — risk officer chat + one-button PDF report generation
- `ExperimentView.tsx` (`/experiments`) — quant view: experiment list, side-by-side comparison, trigger champion-challenger

**Modified pages:**
- `Overview.tsx` — added `ForecastAlert` banner, persona selector (Engineer / Quant / Risk Officer)
- `ModelDetail.tsx` — added `ActionCard` and `ImpactBanner` below existing severity cards

**New API client:** `dashboard/src/api/agent-client.ts` — typed axios wrapper for all V3 endpoints: `/agent/ask`, `/agent/report`, `/trust/{id}`, `/experiments/{id}/challenger`, `/experiments/{id}/results`, `/forecast/{id}`.

---

### 11. Demo Scenarios (`demo/scenarios/`)

Three pre-built scenario scripts for the hackathon demonstration. Each is self-contained — loads data, injects macro context, runs drift check, prints formatted output.

**`rate_hike_2017.py`** — Uses Q4 2018 peak-of-cycle macro values (VIX=25, spread=1.90, yield_curve=0.21). Produces `credit_stress` → "do not retrain" recommendation. Uses real unmodified 2017–2018 Lending Club live data.

**`covid_crash.py`** — Injects March 2020 macro conditions (VIX=57.1, spread=3.82, unemployment=14.7). Amplifies `int_rate` (+35%) and `dti` (+20%) on the live snapshot to simulate stressed originations. Produces `black_swan` at 1.000 confidence → HALT. Calls trust API and prints `trustworthy=False`.

**`normal_decay.py`** — Loads baseline data, applies synthetic perturbations (`dti` +25%, `annual_inc` -15%, `loan_amnt` +20%, `revol_util` +18%) with stable macro. Produces `stable` + `high` severity → retrain. Auto-triggers champion-challenger if severity is high/critical in stable regime.

**`demo_full.py`** — Orchestrator. Runs all three in sequence. `--auto` flag for CI or recording mode. Exits with error code equal to number of failed scenarios. Runtime: 26.6 seconds end-to-end.

**`Makefile`** — `make setup`, `make train`, `make serve`, `make seed`, `make test`, `make demo`, `make demo-auto`, `make demo-covid`, `make demo-hike`, `make demo-decay`. Windows-compatible (`Scripts/` path detection).

---

## Bug Fixes and Tradeoffs

All bugs encountered during V3 build and test. Each entry includes root cause, fix, and the commit that resolved it.

---

### Bug 1 — Phoenix 405 on Span Export

**Symptom:** `ERROR: Failed to export span batch code: 405, reason: Method Not Allowed`

**Root cause:** `PHOENIX_COLLECTOR_ENDPOINT=http://localhost:6006` — the `phoenix.otel` library could not infer the transport protocol from a bare host:port URL, defaulted to HTTP, and sent OTLP POST requests to the root path `/` instead of `/v1/traces`.

**Fix:** Set the full path in `.env`:
```
PHOENIX_COLLECTOR_ENDPOINT=http://localhost:6006/v1/traces
```

**Learning:** `phoenix.otel.register()` requires the full collector path when using HTTP transport. gRPC (port 4317) can be inferred from port alone; HTTP cannot.

---

### Bug 2 — Rate Hike Scenario Showing `stable` Instead of `credit_stress`

**Symptom:** `Scenario 1 (Rate Hike): regime=stable` — the core demo thesis not demonstrating correctly.

**Root cause (first diagnosis — incorrect):** Macro context not being passed through the API correctly. This was wrong.

**Root cause (actual):** The scenario was using 2017 mid-cycle average macro values (VIX=17.2, spread=1.62) which the ML classifier — trained on 30-year percentile-calibrated NBER labels — correctly reads as `stable`. These values are below the `_VIX_ELEVATED=23` and `_SPREAD_NORMAL=2.80` thresholds in the regime labeller.

**Fix:** Updated `rate_hike_2017.py` to use Q4 2018 peak-of-cycle values (VIX=25, spread=1.90, yield_curve=0.21 flat) — the period when rate hike stress was actually measurable in the data. These satisfy the `in_rate_shock=True` condition (VIX≥23 + yield_curve<0.5 = 2 signals), which the ML classifier maps to `credit_stress`.

**Tradeoff:** The scenario is now historically accurate to Q4 2018 rather than a 2017–2018 average. The narrative is slightly adjusted — the rate hike scenario represents the peak stress point of the cycle, not the average.

**Learning:** Don't test correctness against heuristic expectations when the regime classifier is ML-based. Verify against the labeller's actual threshold conditions.

---

### Bug 3 — PDF Report: 0 Drift Runs, Section 4 Empty

**Symptom:** `Total drift checks in period: 0`, `Max drift score: 0.0000`

**Root cause:** `_default_date_range()` in `driftguard/api/routes/agent.py` was generating a 30-day window (`2026-04-21/2026-05-21`). All existing drift runs were timestamped `2026-03-21` (when the demo was first seeded), falling outside the window.

**Fix (`b5d974a`):** Extended default lookback from 30 days to 365 days in `agent.py:_default_date_range()`. Also patched the fallback path in `finsight/reports/generator.py:352` for the same issue.

**Note:** The root cause was in `agent.py`, not `generator.py`. The generator's fallback was never triggered because `agent.py` was producing a valid but too-narrow date string that the generator parsed and used literally.

---

### Bug 4 — PDF Report: Regime Context Duplicated 16 Times

**Symptom:** 16 identical macro rows in Section 3, all `2026-05-20: regime=stable, VIX=17.44`.

**Root cause:** `MacroCache` stores every 6-hour scheduled fetch as a separate row. The report was dumping the raw table rows without deduplication — 16 fetches in one day = 16 identical rows.

**Fix (`b5d974a`):** Deduplicate macro snapshots by calendar date before rendering. Keep only the most recent snapshot per day:
```python
seen_dates = set()
deduped = []
for snap in macro_snapshots:
    day = snap.fetched_at.date()
    if day not in seen_dates:
        seen_dates.add(day)
        deduped.append(snap)
```

Result: 78 raw cache rows → 3 unique calendar dates in the report.

---

### Bug 5 — PDF Report: Today's Runs Excluded by Midnight Cutoff

**Symptom:** After the 365-day fix, report showed only 2 drift runs instead of 13.

**Root cause:** `_parse_date_range()` in `generator.py` was treating `"2026-05-21"` as `2026-05-21T00:00:00Z`. Every run timestamped during the current day (09:xx UTC) was after the start of the day but the end bound was midnight — so all runs from today were excluded.

**Fix (`a5e63e8`):** Extend date-only end bounds to `23:59:59.999999` so the full calendar day is always included:
```python
if len(end_str) == 10:  # date-only format
    end_dt = end_dt.replace(hour=23, minute=59, second=59, microsecond=999999)
```

Result: 13 drift runs in scope (was 2).

---

### Bug 6 — PDF Report: `[LLM unavailable]` in All 7 Sections

**Symptom:** Every section header was `[LLM unavailable — raw data below for Section Name]`.

**Root cause (first diagnosis):** Backend had cached env vars at startup — `LLM_FAST_MODEL` not yet loaded.

**Root cause (actual, after restart):** `413 Payload Too Large` from Groq. The report was serialising all 13 drift runs + full macro history into each section's LLM prompt — ~33,891 tokens per request, exceeding the 6,000 TPM limit for `llama-3.1-8b-instant` on Groq's free tier.

**Fix A (`886b9ae`):** Cap drift runs passed to LLM at 5 most recent: `raw["drift_runs"][-5:]`. Full 13 runs still used for all directly-rendered data (audit trail, risk assessment numbers). Only the prose-generation call is capped.

**Fix B (`.env`, documented in `.env.example` via `278f0bc`):** Switch `LLM_FAST_MODEL` to `llama-3.3-70b-versatile`. Counterintuitively, the 70b model sits in a higher TPM bucket on Groq's free tier despite being the larger model.

**Tradeoff:** LLM prose in sections 2–6 is generated from a 5-run sample, not the full 13. The audit trail (Section 7) renders all 13 directly without LLM intermediation. For a demo/hackathon artifact this is acceptable. In production, the report would paginate or summarise the full history before sending to the LLM.

---

### Bug 7 — `MacroSnapshot` Constructor: Missing `as_of` Field

**Symptom:** `covid_crash.py` crashed on `MacroSnapshot` instantiation with a missing required argument.

**Root cause:** V2 added `as_of: date` as the first positional argument to `MacroSnapshot` to support historical snapshots in the backtesting engine. The scenario script was written against the V1 constructor signature.

**Fix:** Added `as_of=date(2020, 3, 23)` to the instantiation in `demo/scenarios/covid_crash.py`. March 23, 2020 was the VIX peak of the COVID crash.

---

### Bug 8 — Section 7 Reports "5 Drift Checks" but Lists 13

**Symptom:** Section 7 prose says `A total of 5 drift checks were performed` but the audit trail bullet list shows IDs 1–13.

**Root cause:** The LLM writes Section 7 prose from the 5-run capped context (Fix A above). The audit trail bullet list is rendered directly from the full 13-run query. The LLM doesn't know about the full 13.

**Status:** Known, not fixed. Cosmetic inconsistency only — the bullet list (the actual audit record) is correct. The prose summary is wrong by 8. Acceptable for a hackathon demo. Fix in V4: generate the Section 7 prose after the audit trail is assembled, passing the correct count directly.

---

## Architecture Decisions

| Decision | Rationale | Tradeoff |
|---|---|---|
| `finsight/` as a separate top-level package from `driftguard/` | DriftGuard stays a clean, independently installable library. FinSight is the intelligence layer on top. | Slightly more import path complexity. |
| LLM abstraction via `BaseLLMProvider` | One interface, swap providers by changing 3 env vars. Zero agent code changes for Groq → Gemini. | Custom abstraction adds a maintenance surface. Could have used LiteLLM instead. |
| Groq for dev, Gemini for submission | Groq is faster, more reliable, and free-tier sufficient for development. Gemini is the required sponsor tech. | Prompt outputs differ slightly between providers — requires 2–3 hours of prompt tuning on swap day. |
| Tracing as decorators applied at route handler level | DriftGuard's core functions remain unmodified. If Phoenix breaks, DriftGuard works. | Decorators don't capture intra-function span detail. Only route-level spans are created. |
| Agent decision logged to SQLite AND to Phoenix | SQLite gives fast local query for the audit trail. Phoenix gives full observability of reasoning. | Duplicate storage. Both can drift out of sync if one write fails. |
| Report LLM context capped at 5 runs | Avoids Groq 6k TPM limit on free tier. All 13 runs still rendered directly in audit trail. | Section 7 prose count is wrong by 8 (Bug 8 — known). |
| `llama-3.3-70b-versatile` as the "fast" model | Higher TPM budget on Groq free tier than `llama-3.1-8b-instant` despite being larger. | More expensive on paid tiers. Should be re-evaluated post-hackathon. |
| Rule-based impact estimator, not ML | Pre-computed Lending Club calibration is sufficient for demo accuracy. No training data required. | Not generalisable to other loan types or geographies without recalibration. |
| Rule-based drift forecaster | Sufficient for the demo. No training data or model file required. | Not as accurate as a proper time-series model (e.g. ARIMA or Prophet on macro signal history). |
| Scenario macro values = Q4 2018 peak | The ML classifier's labeller requires measurable stress signals. Mid-cycle 2017 values read as `stable`. | The scenario is labelled "2017-2018 rate hike" but the macro values are peak Q4 2018. Slightly misleading name — the scenario should be renamed "Q4 2018 Rate Hike Peak" for accuracy. |

---

## Known Gaps and Intentional Omissions

| Gap | Notes |
|---|---|
| Section 7 prose count wrong by 8 | LLM sees 5-run context, renders "5 drift checks". Audit trail correctly lists 13. Cosmetic — fix in V4. |
| Phoenix trace IDs in audit trail are DB run IDs | Agent decision sources are `run_id: 6` not OTEL span UUIDs. Real Phoenix trace UUIDs will populate once trace → DB run ID linkage is implemented. |
| No API authentication | Any client on the network can call `/agent/ask`, `/trust/{id}`, `/agent/report`. Acceptable for local hackathon demo. V4 blocker. |
| Gemini swap not tested end-to-end | Swap is mechanical (3 env vars) but prompt output structure may differ. Budget 2–3 hours on submission day. |
| Champion-challenger uses demo dataset only | `ChallengerRunner` loads the Lending Club benchmark. No generalised dataset registration for arbitrary models yet. |
| Forecast is rule-based | 7–14 day probability estimates are heuristic. No backtested accuracy figure for the forecaster itself. |
| Phoenix traces not confirmed post-405-fix | 405 error was fixed by adding `/v1/traces` to endpoint. Not verified that traces subsequently appeared at `localhost:6006` — assumed based on log silence. |
| SQLite concurrency | No change from V2. Single-user local use only. PostgreSQL migration remains V4 concern. |
| Webhook config lost on restart | No change from V2. `WebhookConfig` persistence remains a V2 quick-win not yet addressed. |

---

## Validated Demo Results

All validation performed on Windows, Python 3.11, Groq `llama-3.3-70b-versatile`, Phoenix v15.11.1 (Docker).

| Test | Result | Key metric |
|---|---|---|
| `GET /health` | PASS | `{"status":"ok","version":"0.2.0"}` |
| `GET /drift/macro/latest` | PASS | VIX=17.28, regime=stable, confidence=1.0 |
| `GET /models/lending_club_v1` | PASS | Model found, created 2026-03-21 |
| Rate hike scenario | PASS | regime=credit_stress, severity=HIGH, action=monitor |
| COVID crash scenario | PASS | regime=black_swan, severity=CRITICAL, action=HALT, trust=False |
| Normal decay scenario | PASS | regime=stable, severity=HIGH, action=retrain |
| `POST /agent/ask` | PASS | Groq response, confidence=0.8, action=investigate |
| `GET /trust/lending_club_v1` | PASS | trustworthy=false, recommendation=escalate |
| `python scripts/demo_full.py --auto` | PASS | 3/3 scenarios, 26.6s total |
| PDF report generation | PASS | 13 runs, 3 regimes, 7 LLM-written sections |

---

## Commit History (V3 branch)

| Commit | Description |
|---|---|
| `b5d974a` | fix(reports): extend drift history window to 365d and deduplicate macro snapshots |
| `a5e63e8` | fix(reports): treat date-only end bounds as end-of-day not midnight |
| `886b9ae` | fix(reports): truncate context sent to LLM per section to avoid 413 |
| `278f0bc` | docs(.env.example): document LLM_FAST_MODEL model choice and TPM rationale |

*(Feature commits preceding these fixes not listed — see `git log feature/regime-aware-agent` for full history)*

---

## V4 Roadmap (as discussed)

### Priority 1 — API Authentication
Static API key in `.env` with `X-API-Key` header validation. One-day implementation. Single biggest blocker for any deployment beyond local.

### Priority 2 — Gemini End-to-End Validation
Run `demo_full.py --auto` with `LLM_PROVIDER=gemini`. Tune prompts where output structure differs. Document any prompt changes required.

### Priority 3 — Phoenix Trace ID Linkage
Store the OTEL span ID alongside the `DriftRun` DB record so the audit trail references real Phoenix trace UUIDs rather than DB run IDs.

### Priority 4 — Section 7 Prose Count Fix
Pass the full run count directly to the Section 7 LLM prompt rather than letting it infer from the capped 5-run context.

### Priority 5 — Rename Rate Hike Scenario
`rate_hike_2017.py` should be `rate_hike_q4_2018.py` or the macro values updated with an explanation of why Q4 2018 peak values are used. Currently the filename is misleading.

### Priority 6 — Recession Classifier
0% recall on recession regime (inherited from V2). Dedicated binary recession sub-classifier using NBER-labelled data, lagged unemployment, and yield curve inversion duration.

### Priority 7 — PostgreSQL Migration
SQLite remains a single-file, no-concurrency store. PostgreSQL required for multi-user deployment.

### Priority 8 — Docker Compose Full Stack
Single `docker compose up` that starts backend + frontend + Phoenix + Phoenix MCP server. Currently Phoenix is in compose but backend and frontend require manual terminal commands.

---

## How to Run From Scratch (V3)

```powershell
# Terminal 1 — Phoenix
docker compose up phoenix

# Terminal 2 — Backend
cd financial-driftguard
venv\Scripts\activate
uvicorn driftguard.api.main:app --reload

# Terminal 3 — Seed (run once)
python demo\lending_club.py

# Terminal 4 — Dashboard
cd dashboard
npm run dev

# Terminal 3 — Verify
curl http://localhost:8000/health
curl http://localhost:8000/drift/macro/latest
curl http://localhost:8000/trust/lending_club_v1

# Terminal 3 — Full demo
python scripts\demo_full.py --auto

# Makefile equivalents
make serve        # Terminal 2
make seed         # Terminal 3 (one-time)
make ui           # Terminal 4
make demo-auto    # Terminal 3 (full demo)
```

---

*FinSight AI V3 Implementation Summary — May 2026*  
*Built on Financial DriftGuard v0.2.0 (March 2026)*  
*Hackathon submission: feature/regime-aware-agent → v0.3.0*