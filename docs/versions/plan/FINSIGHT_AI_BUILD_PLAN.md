# FinSight AI — Complete Build Plan

**Document type:** Engineering build plan — all 10 steps to completion  
**Project:** `financial-driftguard` → `finsight-ai`  
**Base version:** `v0.2.0` (DriftGuard, March 2026)  
**Target:** Hackathon submission + long-term open-source product  
**Author:** Internal engineering reference  
**Date:** May 2026  

---

## 1. Vision Statement

FinSight AI is the world's first **regime-aware financial model governance agent**. It sits on top of financial ML models, watches them through Arize Phoenix, understands *why* they're drifting using macro regime context, and tells each stakeholder exactly what to do — in their own language.

**One-liner:** A governance agent that tells engineers what's wrong, quants what to test, risk officers what to report, and other AI agents whether to trust your models.

---

## 2. The Problem Nobody Has Solved

Every monitoring tool (Arize AX, WhyLabs, Evidently, MLflow) detects drift and stops. They produce a number and a red alert. What happens next is on the human. In financial ML, that gap is catastrophic:

- Rate hike cycle → **don't retrain** (drift is macro-driven)
- Normal markets → **retrain immediately** (model is decaying)
- Black swan → **freeze automated decisions** (human review only)

Same drift signal, opposite actions. No tool makes this distinction and acts on it.

---

## 3. Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│                    USER SURFACES                         │
│  ┌──────────┐  ┌──────────────┐  ┌───────────────────┐  │
│  │ Engineer  │  │ Quant/DS     │  │ Risk Officer      │  │
│  │ Dashboard │  │ Experiments  │  │ Chat + PDF Report │  │
│  └─────┬────┘  └──────┬───────┘  └────────┬──────────┘  │
│        └───────────────┼───────────────────┘             │
│                        ▼                                 │
│  ┌─────────────────────────────────────────────────┐     │
│  │         AGENT LAYER (Gemini 2.5 Pro)            │     │
│  │         via Google Cloud Agent Builder           │     │
│  │         (dev: Groq — LLM abstraction layer)     │     │
│  └──────────────────┬──────────────────────────────┘     │
│                     │ MCP tools                          │
│  ┌──────────────────▼──────────────────────────────┐     │
│  │           ARIZE MCP SERVER                       │     │
│  │  traces · datasets · experiments · prompts       │     │
│  └──────────────────┬──────────────────────────────┘     │
│                     │ OTLP                               │
│  ┌──────────────────▼──────────────────────────────┐     │
│  │           PHOENIX OBSERVABILITY                  │     │
│  │  every drift run = a structured trace            │     │
│  └──────────────────┬──────────────────────────────┘     │
│                     │                                    │
│  ┌──────────────────▼──────────────────────────────┐     │
│  │      DRIFTGUARD ENGINE (existing codebase)       │     │
│  │  detectors · regime classifier · macro signals   │     │
│  │  FastAPI backend · SQLite · React dashboard      │     │
│  └──────────────────┬──────────────────────────────┘     │
│                     │                                    │
│  ┌──────────────────▼──────────────────────────────┐     │
│  │         FINANCIAL ML MODELS                      │     │
│  │  (client models being monitored)                 │     │
│  │  Demo: LightGBM credit default on Lending Club   │     │
│  └─────────────────────────────────────────────────┘     │
└─────────────────────────────────────────────────────────┘
```

---

## 4. Existing Codebase Reference

Everything below builds on top of the current `financial-driftguard` repository at `v0.2.0`. No rewrites — only extensions.

### Current Repository Structure (V2)

```
financial-driftguard/
├── driftguard/
│   ├── __init__.py
│   ├── core/
│   │   ├── monitor.py           # Monitor — .check() entry point
│   │   ├── snapshot.py          # DataSnapshot — typed ingestion
│   │   └── drift_result.py      # DriftResult, DriftSeverity, FeatureDriftResult
│   ├── detectors/
│   │   ├── base.py              # BaseDetector abstract
│   │   ├── psi.py               # Population Stability Index
│   │   ├── ks_test.py           # Kolmogorov-Smirnov
│   │   └── js_divergence.py     # Jensen-Shannon divergence
│   ├── regime/
│   │   ├── tagger.py            # RegimeTagger — ML primary, rule-based fallback
│   │   └── macro_signals.py     # MacroSignalFetcher, MacroSnapshot
│   ├── api/
│   │   ├── main.py              # FastAPI app + lifespan
│   │   ├── schemas.py           # Pydantic schemas
│   │   └── routes/
│   │       ├── models.py        # /models CRUD
│   │       ├── drift.py         # /drift history, latest, run trigger
│   │       └── alerts.py        # /alerts list, acknowledge
│   ├── store/
│   │   └── database.py          # SQLModel + SQLite
│   ├── scheduler/
│   │   └── jobs.py              # APScheduler + run_drift_check()
│   ├── backtesting/             # V2: BacktestRunner + BacktestReport
│   └── adapters/                # stub — sklearn/torch placeholders
├── dashboard/                   # React 18 + Vite + Tailwind v3
├── demo/
│   ├── lending_club.py
│   └── data/                    # .gitignored, generated from Kaggle
├── scripts/
│   ├── build_regime_labels.py
│   ├── train_regime_classifier.py
│   ├── run_backtest.py
│   └── sanity_check.py
├── tests/
│   └── test_detectors.py        # 20 passing
├── models/                      # trained LightGBM regime classifier
├── pyproject.toml
├── requirements.txt
└── README.md
```

### What's Stable and Loadbearing

These components are proven, tested, and will NOT be modified — only instrumented:

- **All three detectors** (PSI, KS, JS) — 20 passing tests, mathematically correct
- **Monitor SDK** — `.check()` is clean, typed, regime tagging is lazy
- **Baseline persistence** — parquet blobs in SQLite, survives restart
- **Regime classifier** — 93.9% walk-forward accuracy, COVID = black_swan at 1.000 confidence
- **MacroSignalFetcher** — FRED + VIX, graceful fallback, 6-hour cache
- **FastAPI routes** — `/models`, `/drift`, `/alerts` all working
- **React dashboard** — Overview, ModelDetail, MacroPanel, Settings all rendering

---

## 5. Target Repository Structure (Post Step 10)

This is the final folder layout. All new code lives in clearly separated directories. Zero overlap with existing files.

```
financial-driftguard/
├── driftguard/                          # EXISTING — untouched except tracing decorators
│   ├── __init__.py                      # add new exports for agent/llm modules
│   ├── core/
│   ├── detectors/
│   ├── regime/
│   ├── api/
│   │   ├── main.py                      # MODIFIED: add agent routes, auth middleware
│   │   ├── schemas.py                   # MODIFIED: add agent request/response schemas
│   │   └── routes/
│   │       ├── models.py
│   │       ├── drift.py
│   │       ├── alerts.py
│   │       ├── agent.py                 # NEW: /agent/ask, /agent/report, /agent/trust
│   │       └── experiments.py           # NEW: /experiments trigger + results
│   ├── store/
│   │   └── database.py                  # MODIFIED: add AgentDecisionLog table
│   ├── scheduler/
│   ├── backtesting/
│   └── adapters/
│
├── finsight/                            # NEW — all FinSight AI logic lives here
│   ├── __init__.py
│   ├── llm/                             # Step 1: LLM abstraction layer
│   │   ├── __init__.py
│   │   ├── provider.py                  # BaseLLMProvider abstract class
│   │   ├── groq_provider.py             # Groq implementation (dev)
│   │   ├── gemini_provider.py           # Gemini implementation (submission)
│   │   └── config.py                    # reads .env, selects provider
│   │
│   ├── tracing/                         # Step 2: Phoenix instrumentation
│   │   ├── __init__.py
│   │   ├── setup.py                     # register() wrapper, project config
│   │   ├── decorators.py                # @traced_drift_check, @traced_regime_tag
│   │   └── attributes.py               # custom span attributes for financial domain
│   │
│   ├── agent/                           # Steps 3+4: the governance agent
│   │   ├── __init__.py
│   │   ├── brain.py                     # main agent orchestrator
│   │   ├── tools/                       # tools the agent can call
│   │   │   ├── __init__.py
│   │   │   ├── phoenix_tools.py         # wrappers around MCP server calls
│   │   │   ├── drift_tools.py           # call Monitor.check(), read results
│   │   │   ├── macro_tools.py           # fetch macro signals, forecast
│   │   │   └── experiment_tools.py      # trigger Phoenix experiments
│   │   ├── prompts/                     # agent system prompts
│   │   │   ├── orchestrator.py          # main reasoning prompt
│   │   │   ├── analyst.py               # drift analysis prompt
│   │   │   └── report_writer.py         # regulatory report generation prompt
│   │   └── memory.py                    # conversation context for chat interface
│   │
│   ├── impact/                          # Step 5: business impact translator
│   │   ├── __init__.py
│   │   ├── estimator.py                 # maps PSI/KS scores → dollar impact
│   │   └── historical_patterns.py       # lookup table from Lending Club data
│   │
│   ├── forecast/                        # Step 6: proactive drift forecaster
│   │   ├── __init__.py
│   │   ├── predictor.py                 # time-series forecaster on macro signals
│   │   └── event_calendar.py            # Fed meetings, earnings dates, known events
│   │
│   ├── challenger/                      # Step 7: champion-challenger automation
│   │   ├── __init__.py
│   │   └── runner.py                    # auto-compare model versions via Phoenix experiments
│   │
│   ├── reports/                         # Step 8: regulatory report generation
│   │   ├── __init__.py
│   │   ├── generator.py                 # SR 11-7 compliant PDF builder
│   │   ├── templates/                   # report templates
│   │   │   └── sr_11_7.py               # Fed model risk management format
│   │   └── output/                      # .gitignored, generated PDFs
│   │
│   └── trust_api/                       # Step 9: agent-to-agent trust endpoint
│       ├── __init__.py
│       └── handler.py                   # structured trust score response
│
├── dashboard/                           # EXISTING — extended in Step 10
│   ├── src/
│   │   ├── api/
│   │   │   ├── client.ts                # EXISTING
│   │   │   └── agent-client.ts          # NEW: agent chat + trust API client
│   │   ├── components/
│   │   │   ├── RegimeBadge.tsx          # EXISTING
│   │   │   ├── SeverityBar.tsx          # EXISTING
│   │   │   ├── ModelHealthCard.tsx      # EXISTING
│   │   │   ├── AlertFeed.tsx            # EXISTING
│   │   │   ├── AgentChat.tsx            # NEW: conversational interface
│   │   │   ├── ActionCard.tsx           # NEW: structured recommendation card
│   │   │   ├── ImpactBanner.tsx         # NEW: dollar impact display
│   │   │   └── ForecastAlert.tsx        # NEW: proactive warning component
│   │   ├── pages/
│   │   │   ├── Overview.tsx             # EXISTING — add ForecastAlert
│   │   │   ├── ModelDetail.tsx          # EXISTING — add ActionCard, ImpactBanner
│   │   │   ├── AgentView.tsx            # NEW: risk officer chat page
│   │   │   └── ExperimentView.tsx       # NEW: quant experiment comparison page
│   │   └── App.tsx                      # MODIFIED: add new routes
│   └── ...
│
├── demo/                                # EXISTING — extended
│   ├── lending_club.py                  # EXISTING
│   ├── scenarios/                       # NEW: pre-built demo scenarios
│   │   ├── covid_crash.py               # VIX=57, black_swan
│   │   ├── rate_hike_2017.py            # fed hiking cycle, credit_stress
│   │   └── normal_decay.py              # stable regime, model decay
│   └── data/
│
├── tests/
│   ├── test_detectors.py                # EXISTING — 20 passing
│   ├── test_llm_abstraction.py          # NEW: provider swap tests
│   ├── test_tracing.py                  # NEW: span creation tests
│   ├── test_agent.py                    # NEW: agent reasoning tests
│   ├── test_impact.py                   # NEW: business impact mapping
│   └── test_trust_api.py               # NEW: structured trust response
│
├── scripts/
│   ├── build_regime_labels.py           # EXISTING
│   ├── train_regime_classifier.py       # EXISTING
│   ├── run_backtest.py                  # EXISTING
│   ├── sanity_check.py                  # EXISTING
│   └── demo_full.py                     # NEW: runs all 3 scenarios end-to-end
│
├── docker-compose.yml                   # NEW: backend + frontend + Phoenix
├── Makefile                             # NEW: make setup, make demo, make test
├── .env.example                         # MODIFIED: add LLM keys, Phoenix config
├── pyproject.toml                       # MODIFIED: add finsight dependencies
├── requirements.txt                     # MODIFIED: add new deps
└── README.md                            # MODIFIED: FinSight AI branding
```

### Key Design Decisions

**1. Separate `finsight/` directory — not inside `driftguard/`**
DriftGuard is the engine. FinSight is the intelligence layer on top. Keeping them separate means DriftGuard stays a clean, importable library (`pip install driftguard`) while FinSight adds the agent, reporting, and governance features. No tangling.

**2. No modification to detector or regime code**
We only ADD tracing decorators to existing functions. The mathematical core stays untouched. If Phoenix tracing breaks, DriftGuard still works.

**3. One LLM abstraction, all agents use it**
`finsight/llm/provider.py` defines the interface. Every component that needs an LLM — agent brain, report writer, impact explainer — imports from the same place. Swap once, swap everywhere.

**4. Agent tools are thin wrappers**
`finsight/agent/tools/` doesn't contain business logic. Each tool wraps either a DriftGuard function or an MCP server call. The agent orchestrator decides what to call and when.

**5. New API routes live alongside existing ones**
`/agent/ask`, `/agent/report`, `/agent/trust` are added to the existing FastAPI app. No separate server. One process, one port, one deployment.

---

## 6. The 10 Steps — Detailed

---

### Step 1: LLM Abstraction Layer

**Goal:** Build a provider-agnostic LLM client so all downstream code never calls Groq or Gemini directly.

**What gets built:**
- `finsight/llm/provider.py` — `BaseLLMProvider` abstract class with methods: `complete(messages, tools=None, temperature=0.7) → LLMResponse`, `stream(messages) → AsyncIterator[str]`
- `finsight/llm/groq_provider.py` — implements `BaseLLMProvider` using Groq's OpenAI-compatible API. Default model: `llama-3.3-70b-versatile` for reasoning, `llama-3.1-8b-instant` for fast generation tasks
- `finsight/llm/gemini_provider.py` — implements `BaseLLMProvider` using Google Generative AI SDK. Default model: `gemini-2.5-pro` for reasoning, `gemini-2.0-flash` for generation
- `finsight/llm/config.py` — reads `LLM_PROVIDER` from `.env` (`groq` or `gemini`), instantiates the correct provider. Single function: `get_llm(role="reasoning") → BaseLLMProvider`

**Design rules:**
- `LLMResponse` is a dataclass: `content: str`, `tool_calls: list[ToolCall] | None`, `usage: TokenUsage`, `model: str`
- `ToolCall` is a dataclass: `name: str`, `arguments: dict`
- Tool/function calling schema follows OpenAI format (both Groq and Gemini support it)
- All providers handle retries internally (3 retries, exponential backoff)
- Provider selection is ONLY in `config.py` — nowhere else in the codebase imports Groq or Gemini directly

**Environment variables added to `.env.example`:**
```
LLM_PROVIDER=groq              # or "gemini"
GROQ_API_KEY=your-key
GEMINI_API_KEY=your-key
LLM_REASONING_MODEL=llama-3.3-70b-versatile
LLM_FAST_MODEL=llama-3.1-8b-instant
```

**Tests:**
- `test_llm_abstraction.py` — mock both providers, verify `complete()` returns same `LLMResponse` shape
- Verify tool calling works with a simple calculator tool definition
- Verify provider swap works by changing one env var

**Dependencies added:**
```
groq>=0.9.0
google-generativeai>=0.8.0
```

**Touches existing files:** Only `.env.example` and `pyproject.toml`

---

### Step 2: Phoenix Observability Layer

**Goal:** Every DriftGuard operation emits structured traces to Phoenix. Zero changes to detection or regime logic — only instrumentation added.

**What gets built:**
- `finsight/tracing/setup.py` — wraps `phoenix.otel.register()` with DriftGuard-specific defaults:
  ```python
  def init_tracing(project_name="finsight-ai"):
      tracer_provider = register(
          project_name=project_name,
          endpoint=os.getenv("PHOENIX_COLLECTOR_ENDPOINT", "http://localhost:6006"),
          batch=True,
      )
      return tracer_provider
  ```
- `finsight/tracing/decorators.py` — reusable tracing decorators that wrap existing DriftGuard functions without modifying them:
  - `@traced_drift_check` — wraps `Monitor.check()`, creates a CHAIN span with attributes: `model_id`, `detector_count`, `feature_count`, `overall_severity`, `regime`
  - `@traced_regime_tag` — wraps `RegimeTagger.tag()`, creates a CHAIN span with attributes: `regime`, `confidence`, `signals_fired`
  - `@traced_detector` — wraps individual detector `.detect()`, creates a CHAIN span with: `detector_name`, `feature_name`, `score`, `threshold`, `severity`
  - `@traced_macro_fetch` — wraps `MacroSignalFetcher`, creates a TOOL span with: `vix`, `credit_spread`, `fed_funds`, `yield_curve`, `unemployment`
- `finsight/tracing/attributes.py` — custom OpenInference attribute constants for the financial domain:
  ```python
  DRIFT_SCORE = "drift.score"
  DRIFT_SEVERITY = "drift.severity"
  REGIME_CLASS = "regime.class"
  REGIME_CONFIDENCE = "regime.confidence"
  MACRO_VIX = "macro.vix"
  MACRO_SPREAD = "macro.credit_spread"
  MODEL_ID = "model.id"
  ```

**How it wires into existing code:**
The tracing decorators are applied in `driftguard/api/routes/drift.py` at the route handler level — wrapping the existing `run_drift_check()` call. The internal functions remain unmodified. This means:
- If Phoenix is down → DriftGuard still works (decorator catches the error and skips tracing)
- If tracing is disabled → zero overhead, decorator becomes a passthrough

**Phoenix setup:**
- `docker-compose.yml` entry for Phoenix:
  ```yaml
  phoenix:
    image: arizephoenix/phoenix:latest
    ports:
      - "6006:6006"
      - "4317:4317"
  ```
- Phoenix project name: `finsight-ai`
- Traces will appear at `http://localhost:6006`

**Environment variables added:**
```
PHOENIX_COLLECTOR_ENDPOINT=http://localhost:6006
PHOENIX_API_KEY=              # empty for local, set for cloud
PHOENIX_PROJECT_NAME=finsight-ai
```

**Dependencies added:**
```
arize-phoenix-otel>=0.16.0
arize-phoenix-client>=1.0.0
opentelemetry-api>=1.20.0
opentelemetry-sdk>=1.20.0
```

**Tests:**
- `test_tracing.py` — verify spans are created with correct attributes when a drift check runs
- Verify tracing gracefully degrades when Phoenix endpoint is unreachable

**Touches existing files:**
- `driftguard/api/main.py` — add `init_tracing()` call in lifespan
- `driftguard/api/routes/drift.py` — wrap `run_drift_check()` with tracing decorator
- `docker-compose.yml` — add Phoenix service
- `.env.example` — add Phoenix variables

---

### Step 3: Arize MCP Bridge

**Goal:** Connect the Phoenix MCP server so the agent layer can query all observability data through structured tool calls.

**What gets built:**
- `finsight/agent/tools/phoenix_tools.py` — Python wrappers that call the Phoenix MCP server tools. These are the tools the agent will have access to:
  - `list_traces(project_name, limit)` — calls MCP `list-traces`, returns recent drift run traces
  - `get_trace(trace_id)` — calls MCP `get-trace`, returns full trace tree for a specific drift run
  - `get_spans(trace_id)` — calls MCP `get-spans`, returns per-detector, per-feature span details
  - `list_datasets()` — calls MCP `list-datasets`, returns available benchmark datasets
  - `get_dataset_examples(dataset_id)` — calls MCP `get-dataset-examples`, returns drift run examples
  - `list_experiments(dataset_id)` — calls MCP `list-experiments-for-dataset`, returns experiment results
  - `get_experiment(experiment_id)` — calls MCP `get-experiment-by-id`, returns detailed experiment with scores

**MCP Server Configuration:**
The Arize MCP server runs as a sidecar. Configuration in `docker-compose.yml`:
```yaml
phoenix-mcp:
  command: npx -y @arizeai/phoenix-mcp@latest --baseUrl http://phoenix:6006
  depends_on:
    - phoenix
```

For local dev without Docker:
```bash
npx -y @arizeai/phoenix-mcp@latest --baseUrl http://localhost:6006
```

**Tool schema format:**
Each tool in `phoenix_tools.py` exposes an OpenAI-compatible function definition so the LLM agent can call them:
```python
PHOENIX_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "list_recent_drift_traces",
            "description": "Get recent drift run traces from Phoenix...",
            "parameters": { ... }
        }
    },
    ...
]
```

**Environment variables added:**
```
PHOENIX_MCP_BASE_URL=http://localhost:6006
```

**Tests:**
- Verify tool definitions conform to OpenAI function calling schema
- Verify MCP wrapper returns parseable structured data
- Verify graceful error when MCP server is unreachable

**Touches existing files:** Only `docker-compose.yml` and `.env.example`

---

### Step 4: The Governance Agent (Core Brain)

**Goal:** Build the main agent that reasons over Phoenix traces + regime context and produces actionable, regime-aware recommendations.

**What gets built:**
- `finsight/agent/brain.py` — the agent orchestrator:
  - Takes a user query or a drift event trigger
  - Uses the LLM abstraction layer (Step 1) for reasoning
  - Has access to Phoenix tools (Step 3) + DriftGuard tools
  - Follows a structured reasoning chain:
    1. Fetch latest drift traces from Phoenix
    2. Extract regime assessment from traces
    3. Cross-reference with current macro signals
    4. Produce a regime-aware recommendation
    5. Log the decision back to Phoenix as a new trace (agent decision is itself traced)

- `finsight/agent/tools/drift_tools.py` — tools that wrap existing DriftGuard SDK calls:
  - `run_drift_check(model_id)` — triggers `Monitor.check()` with current data
  - `get_latest_regime()` — fetches cached regime from `/drift/macro/latest`
  - `get_model_history(model_id, limit)` — fetches drift history from DriftGuard API
  - `get_feature_breakdown(model_id, run_id)` — fetches per-feature results

- `finsight/agent/tools/macro_tools.py` — tools for macro context:
  - `get_current_macro()` — calls `MacroSignalFetcher` for live signals
  - `get_macro_history(days)` — returns cached macro history from `MacroCache` table

- `finsight/agent/prompts/orchestrator.py` — system prompt for the agent:
  ```
  You are FinSight AI, a financial model governance agent.
  You have access to drift monitoring data from Phoenix traces,
  macro regime context, and historical patterns.

  Your job is to:
  1. Determine if drift is caused by market regime or model decay
  2. Recommend the operationally correct action
  3. Estimate confidence in your recommendation
  4. Explain your reasoning in a way the requesting persona understands

  Critical rules:
  - During credit_stress or rate_shock: NEVER recommend retraining
  - During black_swan: ALWAYS recommend freezing automated decisions
  - During stable + drift: investigate model decay, consider retraining
  - During recession: recommend champion-challenger approach

  Always cite the specific Phoenix trace data and macro signals
  that informed your recommendation.
  ```

- `finsight/agent/memory.py` — simple conversation context manager for the chat interface:
  - Stores last N messages (configurable, default 20)
  - Includes system prompt + tool results in context
  - Resets on new session

- New API routes in `driftguard/api/routes/agent.py`:
  - `POST /agent/ask` — accepts `{"query": str, "model_id": str | None}`, returns agent response
  - `POST /agent/analyze` — accepts `{"model_id": str}`, triggers full drift analysis and returns structured recommendation
  - Agent responses are structured: `{"recommendation": str, "action": enum, "confidence": float, "reasoning": str, "sources": list[trace_id]}`

- New database table in `driftguard/store/database.py`:
  - `AgentDecisionLog` — `model_id`, `query`, `recommendation`, `action`, `confidence`, `regime_context`, `trace_ids_referenced`, `created_at`
  - Every agent decision is persisted for auditability

**Agent decision is itself traced:**
When the agent produces a recommendation, that decision is logged as a Phoenix trace (using Step 2 tracing). This means Phoenix contains both:
- The drift data (what happened)
- The agent's reasoning (what was decided and why)

Full audit trail, fully observable.

**Tests:**
- `test_agent.py` — mock LLM + mock Phoenix tools, verify agent produces correct action for each regime
- Test: COVID macro → agent recommends "freeze", not "retrain"
- Test: Stable + drift → agent recommends "investigate and retrain"
- Test: Rate hike + drift → agent recommends "monitor, don't retrain"

**Touches existing files:**
- `driftguard/api/main.py` — register agent routes
- `driftguard/api/schemas.py` — add agent request/response schemas
- `driftguard/store/database.py` — add `AgentDecisionLog` table

---

### Step 5: Business Impact Translator

**Goal:** Convert ML drift metrics into estimated dollar impact so non-technical stakeholders understand the severity.

**What gets built:**
- `finsight/impact/estimator.py` — `ImpactEstimator` class:
  - Input: `DriftResult` + `RegimeAssessment` + `model_metadata` (portfolio size, avg loan amount)
  - Output: `ImpactEstimate` dataclass: `estimated_loss_range: tuple[float, float]`, `false_negative_rate_increase: float`, `affected_portfolio_pct: float`, `confidence: str`, `explanation: str`
  - Logic (rule-based, not ML):
    - PSI 0.1–0.2 (low drift) → 2–5% FNR increase → $X based on portfolio size
    - PSI 0.2–0.5 (medium drift) → 5–12% FNR increase
    - PSI > 0.5 (critical drift) → 12–25% FNR increase
    - Regime modifier: if regime is credit_stress, multiply impact by 1.5x (macro amplification)
    - Regime modifier: if regime is black_swan, multiply by 3x

- `finsight/impact/historical_patterns.py` — lookup table derived from the Lending Club dataset:
  - Maps (feature_name, regime, psi_range) → historically observed default rate change
  - Pre-computed from the existing backtest data (2013–2020)
  - Used as calibration for the estimator

- Agent prompt updated to include impact context in every recommendation:
  ```
  "Your credit model is showing elevated int_rate drift (PSI 0.18)
  consistent with the 2017 rate hike. Estimated impact: 6–9% increase
  in false negatives, approximately $1.2M–$1.8M in unexpected default
  exposure on your $200M portfolio. Recommended action: monitor weekly,
  do not retrain."
  ```

**Tests:**
- `test_impact.py` — verify impact estimates scale correctly with PSI and regime
- Verify regime modifiers apply correctly

**Touches existing files:**
- `finsight/agent/prompts/orchestrator.py` — add impact estimation instructions
- `finsight/agent/brain.py` — call `ImpactEstimator` as part of analysis chain

---

### Step 6: Proactive Drift Forecaster

**Goal:** Predict drift probability 7–14 days out using macro signals the system already collects.

**What gets built:**
- `finsight/forecast/predictor.py` — `DriftForecaster` class:
  - Input: `MacroSnapshot` history (from `MacroCache` table, already exists)
  - Output: `DriftForecast` dataclass: `probability: float`, `expected_regime: str`, `trigger_signals: list[str]`, `horizon_days: int`, `explanation: str`
  - Method: simple feature-based model (not deep learning):
    - VIX 5-day momentum > 2 std → high drift probability
    - Yield curve inversion starting → rate_shock likely in 14–30 days
    - Credit spread widening + VIX rising → credit_stress likely in 7–14 days
    - All signals stable → low drift probability
  - Can be upgraded to a proper time-series model in post-hackathon

- `finsight/forecast/event_calendar.py` — known macro events:
  - Fed meeting dates (FOMC schedule, publicly available)
  - Quarterly earnings seasons
  - Major economic data releases (NFP, CPI, GDP)
  - Stores as a simple JSON calendar, checked daily
  - If a Fed meeting is within 7 days AND VIX is elevated → boost forecast probability

- New API route: `GET /forecast/{model_id}` — returns current drift forecast
- New scheduled job: runs daily, stores forecast in `MacroCache` extension
- Dashboard component: `ForecastAlert.tsx` — yellow/orange banner on Overview page when probability > 50%

**Tests:**
- Verify forecaster produces elevated probability when VIX momentum spikes
- Verify FOMC proximity boosts probability

**Touches existing files:**
- `driftguard/scheduler/jobs.py` — add daily forecast job
- `driftguard/api/routes/drift.py` — add forecast route
- `dashboard/src/pages/Overview.tsx` — add ForecastAlert component

---

### Step 7: Champion-Challenger Automation

**Goal:** When drift is diagnosed as model decay (not macro), automatically compare current model vs last stable version using Phoenix experiments.

**What gets built:**
- `finsight/challenger/runner.py` — `ChallengerRunner` class:
  - Triggered by agent when: regime = `stable` AND severity = `high` or `critical`
  - Steps:
    1. Load the Lending Club benchmark dataset from Phoenix (created in Step 2)
    2. Run current model predictions as one experiment
    3. Run last stable baseline predictions as another experiment
    4. Attach evaluators (AUC comparison, PSI between outputs)
    5. Return structured comparison: `ChallengerResult` dataclass with `current_score`, `challenger_score`, `winner`, `metrics_diff`
  - Result surfaced to engineer via agent recommendation

- `finsight/agent/tools/experiment_tools.py` — tools for the agent:
  - `trigger_challenger(model_id)` — starts the comparison
  - `get_challenger_results(experiment_id)` — retrieves results

- New API route: `POST /experiments/{model_id}/challenger` — triggers champion-challenger
- New API route: `GET /experiments/{model_id}/results` — retrieves comparison

- Dashboard: `ExperimentView.tsx` page — side-by-side comparison table showing both models' performance on the same dataset

**Tests:**
- Verify challenger only triggers on stable regime + high/critical drift
- Verify it does NOT trigger on credit_stress or black_swan

**Touches existing files:**
- `driftguard/api/main.py` — register experiment routes
- `finsight/agent/brain.py` — add challenger trigger to decision logic

---

### Step 8: Regulatory Report Generation

**Goal:** One-button PDF report compliant with SR 11-7 (Fed model risk management guidance). Pulls data from Phoenix traces, auto-generated by agent.

**What gets built:**
- `finsight/reports/generator.py` — `ReportGenerator` class:
  - Input: `model_id`, `date_range`
  - Fetches from Phoenix via MCP: all drift traces, regime assessments, agent decisions
  - Fetches from DriftGuard API: model metadata, alert history
  - Calls LLM (fast model via abstraction layer) to generate prose sections
  - Outputs structured PDF

- `finsight/reports/templates/sr_11_7.py` — report structure following SR 11-7:
  - **Section 1: Model Identification** — model ID, version, deployment date, purpose
  - **Section 2: Performance Summary** — drift score trends, feature-level breakdown
  - **Section 3: Regime Context** — current market regime, macro signals, regime history
  - **Section 4: Drift Analysis** — which features drifted, which detectors caught it, root cause
  - **Section 5: Agent Recommendations** — what was recommended, what actions were taken
  - **Section 6: Risk Assessment** — estimated business impact, confidence level
  - **Section 7: Audit Trail** — all Phoenix trace IDs referenced, timestamps, decision log

- PDF generation using `reportlab` or `weasyprint` (both available via pip)

- New API route: `POST /agent/report` — accepts `{"model_id": str, "date_range": str}`, returns PDF download link
- Agent can also generate reports on command: user asks "Generate compliance report for my lending model" → agent triggers report generation

**Tests:**
- Verify report contains all 7 sections
- Verify all trace IDs in report exist in Phoenix
- Verify PDF renders without errors

**Dependencies added:**
```
reportlab>=4.0.0     # or weasyprint
```

**Touches existing files:**
- `driftguard/api/routes/agent.py` — add `/agent/report` route
- `finsight/agent/prompts/report_writer.py` — prompt for prose generation

---

### Step 9: Agent-to-Agent Trust API

**Goal:** Expose FinSight as a callable tool for other AI agents. A credit decisioning agent asks "Is this model trustworthy?" and gets a structured answer.

**What gets built:**
- `finsight/trust_api/handler.py` — `TrustHandler` class:
  - Input: `model_id`, optionally `context` (what the calling agent wants to do)
  - Output: `TrustScore` dataclass:
    ```python
    @dataclass
    class TrustScore:
        model_id: str
        trustworthy: bool           # binary go/no-go
        confidence: float           # 0-1
        regime: str                 # current regime
        drift_severity: str         # current drift level
        recommendation: str         # "proceed" | "proceed_with_caution" | "escalate" | "halt"
        reason: str                 # one-sentence explanation
        last_checked: datetime
        next_check_recommended: datetime
    ```
  - Logic:
    - No drift + stable regime → `trustworthy=True, recommendation="proceed"`
    - Low drift + stable → `trustworthy=True, recommendation="proceed_with_caution"`
    - High drift + macro regime → `trustworthy=True, recommendation="proceed_with_caution"` (drift is expected)
    - High drift + stable → `trustworthy=False, recommendation="escalate"`
    - Black swan → `trustworthy=False, recommendation="halt"`

- New API route: `GET /trust/{model_id}` — returns `TrustScore` JSON
  - No auth required for hackathon (add API key gating in production)
  - Response is machine-readable, designed for agent consumption
  - Also human-readable — includes `reason` field

- MCP tool definition so other agents using MCP can call it:
  ```json
  {
    "name": "check_model_trust",
    "description": "Check if a financial ML model is currently trustworthy",
    "parameters": {
      "model_id": {"type": "string"},
      "context": {"type": "string", "description": "What you plan to do with this model"}
    }
  }
  ```

**Tests:**
- `test_trust_api.py` — verify all regime × severity combinations produce correct trust scores
- Verify response conforms to `TrustScore` schema

**Touches existing files:**
- `driftguard/api/main.py` — register trust route
- `driftguard/api/schemas.py` — add `TrustScore` response schema

---

### Step 10: Multi-Persona Dashboard

**Goal:** Three views on one dashboard — Engineer, Quant, Risk Officer. Each sees what they need.

**What gets built:**

**Engineer View (enhanced existing Overview + ModelDetail):**
- `ActionCard.tsx` — structured recommendation card from the agent:
  - Shows: recommended action, confidence, regime context, top drifted features
  - Colour-coded by action type: green (monitor), amber (investigate), red (freeze)
  - One-click to acknowledge or override
- `ImpactBanner.tsx` — estimated dollar impact banner on ModelDetail page
- `ForecastAlert.tsx` — proactive warning on Overview when forecast probability > 50%
- These extend existing pages — no new routes needed

**Quant View (new page):**
- `ExperimentView.tsx` — new page at `/experiments`
  - Lists all Phoenix experiments for the selected model
  - Side-by-side comparison of experiment results
  - Drill-down into per-example scores
  - Link to Phoenix UI for full trace exploration
  - Trigger new champion-challenger from the UI

**Risk Officer View (new page):**
- `AgentView.tsx` — new page at `/agent`
  - Conversational chat interface
  - Uses `POST /agent/ask` endpoint
  - Shows agent responses with regime badges, severity bars, and sourced reasoning
  - One-button report generation: "Generate compliance report" → PDF downloads
  - No technical jargon — the agent translates to business language

**Navigation update:**
- `App.tsx` — add routes: `/agent`, `/experiments`
- Sidebar/nav: add "Agent" and "Experiments" links
- Overview page gets a persona selector: "I am a..." → Engineer / Quant / Risk Officer
  - Each selection filters and reorders the dashboard content

**New API client:**
- `dashboard/src/api/agent-client.ts` — typed axios client for:
  - `POST /agent/ask`
  - `POST /agent/report`
  - `GET /trust/{model_id}`
  - `POST /experiments/{model_id}/challenger`
  - `GET /experiments/{model_id}/results`
  - `GET /forecast/{model_id}`

**Gemini Swap:**
- Before submission: change `LLM_PROVIDER=gemini` in `.env`
- Run full demo through all 3 scenarios
- Tune prompts if output structure differs (budget 2–3 hours)

---

## 7. Checkpoint Map

| Checkpoint | Steps | What's True When Done | Priority |
|---|---|---|---|
| **CP1: Foundation** | 1 + 2 | LLM abstraction working. Phoenix traces appear for every drift run. | MUST SHIP |
| **CP2: Agent Alive** | 3 + 4 | Agent queries Phoenix via MCP and produces regime-aware recommendations. | MUST SHIP |
| **CP3: Business Layer** | 5 + 6 | Agent speaks in dollars and predicts drift before it happens. | SHOULD SHIP |
| **CP4: Automation** | 7 + 8 | Champion-challenger auto-triggers. PDF reports drop on command. | NICE TO HAVE |
| **CP5: Demo Ready** | 9 + 10 | Trust API exposed. All 3 persona views working. Gemini swapped. | NICE TO HAVE |

---

## 8. Demo Script (3 Scenarios)

The hackathon demo runs these three scenarios in sequence. Each shows a different regime and a different agent response.

**Scenario 1: 2017–2018 Federal Reserve Rate Hike**
- Baseline: Lending Club 2013–2015
- Current: Lending Club 2017–2018
- `int_rate` drifts (PSI ~0.10)
- Regime tagger: `credit_stress`
- Agent: "Macro-driven drift. Don't retrain. Monitor weekly. Expected duration: until rate cycle stabilises."
- Impact: "$800K–$1.2M estimated exposure increase"
- Demonstrates: regime-aware intelligence vs naive "retrain" advice

**Scenario 2: COVID March 2020 Black Swan**
- Macro inject: VIX=57, spread=3.8, unemployment=14.7
- Regime tagger: `black_swan` at 1.000 confidence
- Agent: "HALT. Freeze automated decisions. Escalate to human review. Retraining on current data will produce a model that fails post-recovery."
- Trust API returns: `trustworthy=false, recommendation="halt"`
- Demonstrates: crisis response, agent-to-agent trust

**Scenario 3: Normal Model Decay**
- Baseline: clean 2013–2015 data
- Current: synthetically perturbed data (shift DTI and annual_inc distributions)
- Regime: `stable`
- Agent: "Model decay detected. No macro explanation. Recommend champion-challenger. Triggering experiment..."
- Champion-challenger runs automatically
- Demonstrates: full automation loop

---

## 9. Risk Register

| Risk | Mitigation |
|---|---|
| Groq → Gemini prompt differences | Budget 2–3 hours pre-submission for prompt tuning. Keep prompts simple and structured. |
| Phoenix MCP server instability | Phoenix tools in agent have try/catch + fallback to direct DriftGuard API calls |
| Groq rate limits during dev | Use `llama-3.1-8b-instant` for iteration, `llama-3.3-70b` for final testing |
| SQLite concurrent access | Single-user local use only. Not a hackathon concern. |
| Demo data not reproducible | Add `demo/scenarios/` with pre-computed snapshots that don't require Kaggle |

---

## 10. Dependency Summary

### New Python Dependencies (on top of existing requirements.txt)

```
# LLM providers
groq>=0.9.0
google-generativeai>=0.8.0
litellm>=1.40.0               # optional: alternative to custom abstraction

# Phoenix / tracing
arize-phoenix>=8.0.0           # local Phoenix server (dev only)
arize-phoenix-otel>=0.16.0     # OTEL tracing wrapper
arize-phoenix-client>=1.0.0    # REST client for Phoenix API
opentelemetry-api>=1.20.0
opentelemetry-sdk>=1.20.0

# Report generation
reportlab>=4.0.0

# Forecasting (Step 6)
# No new deps — uses existing scipy + numpy
```

### New Node Dependencies (dashboard)

```
# No new major deps — existing axios + React Router sufficient
# AgentChat component uses native fetch for streaming
```

---

## 11. Non-Negotiable Standards

1. **Every new module has `__init__.py` with explicit exports** — no `*` imports
2. **Every new function has a type signature** — no `Any` unless unavoidable
3. **Every new file has a module docstring** — one sentence explaining what it does
4. **No business logic in route handlers** — routes call into `finsight/` modules
5. **No LLM provider imports outside `finsight/llm/`** — everything goes through the abstraction
6. **No Phoenix imports outside `finsight/tracing/`** — centralised tracing setup
7. **Tests for every step** — minimum: one happy path, one error case
8. **`.env.example` updated with every new env var** — with comments explaining each
9. **Existing tests must still pass after every step** — 20/20 detectors, always green

---

*FinSight AI Build Plan — May 2026*  
*Built on Financial DriftGuard v0.2.0*  
*Target: Hackathon submission + long-term open-source governance tool*
