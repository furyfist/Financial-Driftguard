# FinSight AI — V5 Execution Plan
# 35 Subphases — Hackathon Submission Sprint

**Deadline:** June 11, 2026 @ 2:00 PM PDT
**Target:** Arize track — Google Cloud Rapid Agent Hackathon
**Rule:** Each phase ends with a commit. No phase bleeds into the next.

---

## Phase Map

| # | Phase | Area | Blocks |
|---|---|---|---|
| P01 | LICENSE file | Repo hygiene | nothing |
| P02 | .env.example + env var audit | Config | P03+ |
| P03 | requirements.txt — V5 deps | Dependencies | all Python phases |
| P04 | database.py — DATABASE_URL env var | Supabase/M1 | P05 |
| P05 | ApprovalQueue DB model | Supabase/S2 | P06, P27 |
| P06 | Supabase blob roundtrip verify | Supabase/M1 | P04 |
| P07 | tracing/setup.py — GoogleADKInstrumentor | OpenInference/M3 | P08, P09 |
| P08 | tracing/attributes.py — ADK span attributes | OpenInference/M3 | P07 |
| P09 | adk/config.py — ADK env wiring | ADK/M5 | P10 |
| P10 | adk/tools.py — DriftGuard tool wrappers for ADK | ADK/M5 | P11 |
| P11 | adk/agents.py — GovernanceAgent complete | ADK/M5 | P12 |
| P12 | adk/agents.py — AnalystAgent + ReportAgent | ADK/M5 | P13 |
| P13 | brain.py — AGENT_FRAMEWORK=adk branch | ADK/M5 | P14 |
| P14 | llm/gemini_provider.py — Gemini 2.5 Pro wiring | Gemini/M4 | P15 |
| P15 | agent/prompts/ — Gemini-compatible prompts | Gemini/M4 | P16 |
| P16 | brain.py — response parsing for Gemini output | Gemini/M4 | P17 |
| P17 | self_eval_tools.py — evaluate_past_recommendations | Self-improve/S1 | P18 |
| P18 | self_eval_tools.py — get_confidence_adjustment | Self-improve/S1 | P19 |
| P19 | brain.py — wire self-eval before recommendation | Self-improve/S1 | P20 |
| P20 | evals/governance_eval.py — regime eval template | LLM-Judge/S3 | P21 |
| P21 | evals/governance_eval.py — action eval + runner | LLM-Judge/S3 | P22 |
| P22 | evals/governance_eval.py — Phoenix Experiments push | LLM-Judge/S3 | P23 |
| P23 | driftguard/store/models.py — ApprovalQueue table | Human gate/S2 | P24 |
| P24 | driftguard/api/routes/approvals.py — CRUD routes | Human gate/S2 | P25 |
| P25 | driftguard/api/routes/approvals.py — Slack webhook | Human gate/S2 | P26 |
| P26 | driftguard/api/routes/approvals.py — Telegram webhook | Human gate/S2 | P27 |
| P27 | finsight/notifications/approval_notifier.py — Slack Block Kit | Human gate/S2 | P28 |
| P28 | finsight/notifications/approval_notifier.py — Telegram inline KB | Human gate/S2 | P29 |
| P29 | brain.py — fire approval gate for high-risk actions | Human gate/S2 | P30 |
| P30 | dashboard ApprovalQueue.tsx component | Human gate/S2 | P31 |
| P31 | dashboard ApprovalsView.tsx page + routing | Human gate/S2 | P32 |
| P32 | Dockerfile — production backend image | Cloud Run/M6 | P33 |
| P33 | driftguard/api/main.py — register approvals router | Wiring | P34 |
| P34 | scripts/demo_full.py — Gemini + ADK smoke path | Demo/M8 | P35 |
| P35 | demo video script + submission checklist | Demo/M8 | — |

---

## Detailed Phases

---

### P01 — LICENSE File
**Covers:** M7
**Goal:** MIT license visible at repo root so GitHub shows it in the About sidebar.
**Files:**
- `LICENSE` — create at repo root

**Done when:** `LICENSE` file exists at root with MIT text and 2026 copyright.
**Commit:** `chore: add MIT license`

---

### P02 — .env.example + env var audit
**Covers:** M1, M2, M4, M5, S2 (config layer)
**Goal:** Single source of truth for every env var V5 needs. No surprises when someone clones and runs.
**Files:**
- `.env.example` — add all V5 vars (DATABASE_URL, GEMINI_API_KEY, LLM_PROVIDER, AGENT_FRAMEWORK, PHOENIX_COLLECTOR_ENDPOINT, PHOENIX_API_KEY, PHOENIX_PROJECT_NAME, PHOENIX_MCP_BASE_URL, PHOENIX_MCP_API_KEY, SLACK_WEBHOOK_URL, SLACK_SIGNING_SECRET, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID)

**Done when:** Every V5 env var has a placeholder entry with a comment explaining it.
**Commit:** `chore: add V5 env vars to .env.example`

---

### P03 — requirements.txt V5 deps
**Covers:** M1, M3, S1, S3
**Goal:** All new packages declared so pip install works on a clean machine.
**Packages to add:**
- `psycopg2-binary>=2.9.0`
- `google-adk>=2.0.0`
- `google-genai>=1.0.0`
- `openinference-instrumentation-google-adk>=0.1.10`
- `openinference-instrumentation>=0.1.0`
- `arize-phoenix-evals>=0.1.0`

**Files:**
- `requirements.txt`

**Done when:** All six packages are in requirements.txt with version pins.
**Commit:** `chore: add V5 python dependencies`

---

### P04 — database.py — DATABASE_URL env var
**Covers:** M1 core
**Goal:** Engine creation reads `DATABASE_URL` from env. Falls back to SQLite if not set so local dev still works without Supabase.
**Files:**
- `driftguard/store/database.py`

**Change:** Replace hardcoded SQLite path with:
```python
import os
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./driftguard.db")
engine = create_engine(DATABASE_URL, ...)
```
For Postgres connections, disable `check_same_thread` guard (SQLite-only param).

**Done when:** `create_engine` reads env var, SQLite fallback works, Postgres URL accepted.
**Commit:** `feat(db): read DATABASE_URL from env with SQLite fallback`

---

### P05 — ApprovalQueue model in database.py
**Covers:** S2 DB layer
**Goal:** `ApprovalQueue` SQLModel table defined alongside existing tables. Created automatically on `create_db()`.
**Files:**
- `driftguard/store/database.py` or `driftguard/store/models.py` (whichever holds table defs)

**Schema:**
```python
class ApprovalQueue(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    model_id: str
    action: str           # halt | retrain | freeze | escalate
    recommendation: str
    regime: str
    confidence: float
    status: str = "pending"   # pending | approved | rejected
    responded_by: str | None = None
    responded_at: datetime | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
```

**Done when:** Model defined, imported in `create_db()`, table creates on engine init.
**Commit:** `feat(db): add ApprovalQueue table`

---

### P06 — Supabase blob roundtrip verify
**Covers:** M1 risk item
**Goal:** Confirm that parquet baseline BLOBs stored as `bytes` in SQLModel survive a Postgres `BYTEA` roundtrip without corruption. Write a small test or inline assertion in `database.py`.
**Files:**
- `tests/test_db_blob.py` — new test file (or inline check in existing `test_agent.py`)

**Done when:** Test writes 100 bytes to a model's baseline blob column and reads them back equal.
**Commit:** `test(db): verify blob roundtrip for Postgres BYTEA`

---

### P07 — tracing/setup.py — GoogleADKInstrumentor
**Covers:** M3 core
**Goal:** Replace manual `register()` wrapper with `GoogleADKInstrumentor` auto-instrumentation. Keep existing manual decorators in `decorators.py` as additive (they still fire for DriftGuard-specific spans).
**Files:**
- `finsight/tracing/setup.py`

**Change:**
```python
from phoenix.otel import register
from openinference.instrumentation.google_adk import GoogleADKInstrumentor

def init_tracing(project_name="finsight-ai"):
    tracer_provider = register(
        project_name=project_name,
        auto_instrument=True,
        batch=True,
    )
    GoogleADKInstrumentor().instrument(tracer_provider=tracer_provider)
    return tracer_provider
```
**Critical:** This function must be called before any `google.adk` import anywhere.

**Done when:** `init_tracing()` runs without error when ADK is installed, `GoogleADKInstrumentor` registered.
**Commit:** `feat(tracing): swap to GoogleADKInstrumentor auto-instrumentation`

---

### P08 — tracing/attributes.py — ADK span attributes
**Covers:** M3 span quality
**Goal:** Add semantic attribute constants for ADK-specific span fields (agent_name, tool_name, regime, confidence) so manual decorators and ADK auto-spans share the same attribute keys.
**Files:**
- `finsight/tracing/attributes.py`

**Done when:** ADK attribute constants defined and exported.
**Commit:** `feat(tracing): add ADK span attribute constants`

---

### P09 — adk/config.py — ADK env wiring
**Covers:** M5 config
**Goal:** Read all ADK-related env vars in one place. Export a typed config object the agents import.
**Files:**
- `finsight/adk/config.py`

**Vars to read:** `AGENT_FRAMEWORK`, `GOOGLE_GENAI_API_KEY`, `LLM_REASONING_MODEL`, `LLM_FAST_MODEL`.

**Done when:** `ADKConfig` dataclass instantiates from env, raises clear error if `GOOGLE_GENAI_API_KEY` missing when `AGENT_FRAMEWORK=adk`.
**Commit:** `feat(adk): typed config from env vars`

---

### P10 — adk/tools.py — DriftGuard tool wrappers for ADK
**Covers:** M5 tool layer
**Goal:** Wrap existing `drift_tools.py`, `macro_tools.py`, `trust_tools.py`, `phoenix_tools.py` as ADK-compatible `FunctionTool` definitions. ADK agents call these instead of invoking the functions directly.
**Files:**
- `finsight/adk/tools.py`

**Tools to wrap:**
- `run_drift_analysis` → ADK FunctionTool
- `get_macro_signals` → ADK FunctionTool
- `get_trust_score` → ADK FunctionTool
- `query_phoenix_traces` → ADK FunctionTool
- `evaluate_past_recommendations` → ADK FunctionTool (from P17)

**Done when:** All five tool wrappers defined with ADK schema annotations.
**Commit:** `feat(adk): DriftGuard tool wrappers for ADK agents`

---

### P11 — adk/agents.py — GovernanceAgent complete
**Covers:** M5 agent layer
**Goal:** `GovernanceAgent` fully wired — receives model_id + scenario, calls drift + macro tools, returns structured governance decision. This is the top-level orchestrator.
**Files:**
- `finsight/adk/agents.py`

**Done when:** `GovernanceAgent` instantiates with ADK, accepts a drift scenario, routes to sub-agents, returns `AgentResponse`-compatible dict.
**Commit:** `feat(adk): GovernanceAgent implementation`

---

### P12 — adk/agents.py — AnalystAgent + ReportAgent
**Covers:** M5 sub-agents
**Goal:** `AnalystAgent` (deep drift analysis, regime classification) and `ReportAgent` (formats final output, generates PDF trigger) added to the same file. GovernanceAgent delegates to them.
**Files:**
- `finsight/adk/agents.py`

**Done when:** Both agents defined, GovernanceAgent calls them in sequence, full chain returns structured output.
**Commit:** `feat(adk): AnalystAgent and ReportAgent sub-agents`

---

### P13 — brain.py — AGENT_FRAMEWORK=adk branch
**Covers:** M5 wiring into existing API
**Goal:** `brain.py` reads `AGENT_FRAMEWORK` env var. When `adk`, routes to `run_adk_analysis()` from `finsight/adk/agents.py`. When `native` (default), existing path unchanged. No breakage to current flow.
**Files:**
- `finsight/agent/brain.py`

**Done when:** `POST /agent/ask` works with both `AGENT_FRAMEWORK=native` and `AGENT_FRAMEWORK=adk` (adk path returns valid `AgentResponse` shape).
**Commit:** `feat(agent): route to ADK agents when AGENT_FRAMEWORK=adk`

---

### P14 — llm/gemini_provider.py — Gemini 2.5 Pro wiring
**Covers:** M4 LLM swap
**Goal:** `GeminiProvider` uses `LLM_REASONING_MODEL` (gemini-2.5-pro) for reasoning calls and `LLM_FAST_MODEL` (gemini-2.0-flash) for generation. Verify tool-calling JSON format matches what brain.py expects.
**Files:**
- `finsight/llm/gemini_provider.py`
- `finsight/llm/config.py`

**Done when:** `GeminiProvider.complete()` and `GeminiProvider.stream()` use correct model names from env, tool-call format consistent with existing `AgentResponse` parsing.
**Commit:** `feat(llm): wire Gemini 2.5 Pro and 2.0 Flash from env`

---

### P15 — agent/prompts/ — Gemini-compatible prompts
**Covers:** M4 prompt tuning
**Goal:** Orchestrator and analyst prompts adjusted for Gemini's output structure. Gemini is more verbose than Groq — trim system prompts, be explicit about JSON output format, add `respond only with valid JSON` constraints where needed.
**Files:**
- `finsight/agent/prompts/orchestrator.py`
- `finsight/agent/prompts/analyst.py`
- `finsight/agent/prompts/report_writer.py`

**Done when:** Prompts have Gemini-specific output format instructions. Section 7 prose prompt uses `LLM_FAST_MODEL`.
**Commit:** `feat(prompts): Gemini-compatible output format instructions`

---

### P16 — brain.py — response parsing for Gemini output
**Covers:** M4 parsing
**Goal:** Response parser in `brain.py` handles Gemini's JSON wrapping (Gemini sometimes wraps JSON in markdown fences). Add a strip/parse step before the existing parser runs.
**Files:**
- `finsight/agent/brain.py`

**Done when:** `brain.py` strips ` ```json ... ``` ` fences if present before parsing. Existing Groq path unaffected.
**Commit:** `fix(agent): strip markdown fences from Gemini JSON responses`

---

### P17 — self_eval_tools.py — evaluate_past_recommendations
**Covers:** S1 self-improvement loop (first half)
**Goal:** `evaluate_past_recommendations(model_id, window_days=30)` tool:
1. Calls `list_recent_drift_traces` via Phoenix MCP to get last N agent decisions
2. For each decision: compares recommended action vs actual regime outcome
3. Runs LLM-as-Judge: "Given regime {X} and agent recommended {Y}, was this correct?"
4. Returns `{regime: accuracy_score, adjustments: [...]}`
**Files:**
- `finsight/agent/tools/self_eval_tools.py` — new file

**Done when:** Function defined, Phoenix MCP call wired, LLM judge call wired, returns structured eval dict.
**Commit:** `feat(self-eval): evaluate_past_recommendations tool`

---

### P18 — self_eval_tools.py — get_confidence_adjustment
**Covers:** S1 self-improvement loop (second half)
**Goal:** `get_confidence_adjustment(regime, historical_accuracy)` returns a `ConfidenceAdjustment` dataclass. Logic:
- `black_swan` + accuracy ≥ 0.95 → increase HALT confidence
- `credit_stress` + accuracy < 0.80 → lower confidence, suggest conservative action
- All others → no adjustment
**Files:**
- `finsight/agent/tools/self_eval_tools.py`

**Done when:** `ConfidenceAdjustment` dataclass defined, logic correct for all three branches.
**Commit:** `feat(self-eval): get_confidence_adjustment logic`

---

### P19 — brain.py — wire self-eval before recommendation
**Covers:** S1 integration
**Goal:** Before `brain.py` returns a final recommendation, call `evaluate_past_recommendations()` and apply the returned `ConfidenceAdjustment` to the confidence score and action in the response.
**Files:**
- `finsight/agent/brain.py`

**Done when:** `AgentResponse` includes `self_eval_accuracy` and `confidence_adjustment` fields when self-eval runs. Self-eval is skipped gracefully if Phoenix MCP is unreachable.
**Commit:** `feat(agent): apply self-improvement confidence adjustment before recommendation`

---

### P20 — evals/governance_eval.py — regime eval template
**Covers:** S3 LLM-as-Judge (first template)
**Goal:** Define the regime classification evaluator using `arize-phoenix-evals`. Template: given macro signals (VIX, spread, yield curve) and agent's regime label, was the classification correct?
**Files:**
- `finsight/evals/governance_eval.py` — new file
- `finsight/evals/__init__.py` — new file

**Done when:** `REGIME_EVAL_TEMPLATE` string defined, `run_regime_eval(traces_df)` function skeleton written.
**Commit:** `feat(evals): regime classification eval template`

---

### P21 — evals/governance_eval.py — action eval + runner
**Covers:** S3 LLM-as-Judge (second template + runner)
**Goal:** Define action appropriateness evaluator. Template: given regime and action, was the action correct per the governance rules (black_swan→halt, credit_stress→monitor, stable+drift→retrain). Add `run_evals(model_id)` runner that pulls traces from Phoenix and runs both evals.
**Files:**
- `finsight/evals/governance_eval.py`

**Done when:** Both templates defined, `run_evals()` calls `llm_classify` for each, returns combined results.
**Commit:** `feat(evals): action appropriateness eval and runner`

---

### P22 — evals/governance_eval.py — Phoenix Experiments push
**Covers:** S3 visibility for judges
**Goal:** After evals run, push results to Phoenix Cloud Experiments tab using `phoenix-client`. Judges can navigate to the Experiments tab and see "13 evaluated, 12/13 correct."
**Files:**
- `finsight/evals/governance_eval.py`

**Done when:** `push_eval_results_to_phoenix(results, experiment_name)` defined and called at end of `run_evals()`.
**Commit:** `feat(evals): push eval results to Phoenix Experiments`

---

### P23 — driftguard/store/models.py — ApprovalQueue export
**Covers:** S2 model availability
**Goal:** Ensure `ApprovalQueue` is importable from `driftguard.store.models` so routes and notifiers can import it cleanly.
**Files:**
- `driftguard/store/models.py`

**Done when:** `from driftguard.store.models import ApprovalQueue` works.
**Commit:** `feat(store): export ApprovalQueue from models`

---

### P24 — driftguard/api/routes/approvals.py — CRUD routes
**Covers:** S2 API layer
**Goal:** REST routes for the approval queue:
- `GET /approvals` — list all (filter by status)
- `GET /approvals/{id}` — get one
- `POST /approvals/{id}/approve` — set status=approved
- `POST /approvals/{id}/reject` — set status=rejected
**Files:**
- `driftguard/api/routes/approvals.py` — new file

**Done when:** All four routes work, status updates persist to DB.
**Commit:** `feat(api): ApprovalQueue CRUD routes`

---

### P25 — approvals.py — Slack webhook handler
**Covers:** S2 Slack interactivity
**Goal:** `POST /webhooks/slack/interact` — receives Slack interactive button payload, verifies signing secret, extracts `action_id` (approve/reject) and `value` (approval_id), updates ApprovalQueue, calls `response_url` to update original Slack message with decision.
**Files:**
- `driftguard/api/routes/approvals.py`

**Done when:** Route defined, payload parsed, DB updated, Slack message updated via `response_url`.
**Commit:** `feat(api): Slack interactive webhook for approval buttons`

---

### P26 — approvals.py — Telegram webhook handler
**Covers:** S2 Telegram interactivity
**Goal:** `POST /webhooks/telegram` — receives Telegram callback query, extracts `data` (approve_{id} or reject_{id}), updates ApprovalQueue, answers callback to remove loading state.
**Files:**
- `driftguard/api/routes/approvals.py`

**Done when:** Route defined, callback data parsed, DB updated, `answerCallbackQuery` called.
**Commit:** `feat(api): Telegram callback webhook for approval buttons`

---

### P27 — approval_notifier.py — Slack Block Kit builder
**Covers:** S2 notification layer
**Goal:** `SlackApprovalNotifier.send(approval: ApprovalQueue)` builds Slack Block Kit message with header, regime/action/confidence/impact fields, and Approve/Reject buttons. Posts via `SLACK_WEBHOOK_URL` or Slack Web API.
**Files:**
- `finsight/notifications/approval_notifier.py` — new file

**Block Kit shape:**
- Header: "FinSight AI — Action Requires Approval"
- Section: model, regime, action, confidence, impact estimate
- Actions: Approve (primary) + Reject (danger) buttons with `approval.id` as value

**Done when:** `SlackApprovalNotifier.send()` builds correct payload, posts successfully (mock test if no key).
**Commit:** `feat(notifications): Slack Block Kit approval message builder`

---

### P28 — approval_notifier.py — Telegram inline keyboard builder
**Covers:** S2 notification layer
**Goal:** `TelegramApprovalNotifier.send(approval: ApprovalQueue)` builds message text + inline keyboard with Approve/Reject buttons. Posts via Telegram Bot API `sendMessage`.
**Files:**
- `finsight/notifications/approval_notifier.py`

**Done when:** `TelegramApprovalNotifier.send()` builds correct `reply_markup` with `callback_data`, posts successfully.
**Commit:** `feat(notifications): Telegram inline keyboard approval message builder`

---

### P29 — brain.py — fire approval gate for high-risk actions
**Covers:** S2 agent integration
**Goal:** After `brain.py` produces a recommendation, if `result.action in ("halt", "retrain", "freeze", "escalate")`:
1. Create `ApprovalQueue` record in DB
2. Call `approval_notifier.send()` (Slack or Telegram based on config)
3. Set `result.requires_approval = True` and `result.approval_id = approval.id`
**Files:**
- `finsight/agent/brain.py`

**Done when:** High-risk actions create DB record and fire notification. Low-risk actions bypass gate entirely.
**Commit:** `feat(agent): fire human approval gate for high-risk actions`

---

### P30 — dashboard ApprovalQueue.tsx component
**Covers:** S2 frontend
**Goal:** Table component showing pending/approved/rejected approval requests. Columns: model, regime, action, confidence, status, timestamp. Approve/Reject buttons for pending rows. Polls `/approvals` every 5 seconds.
**Files:**
- `dashboard/src/components/ApprovalQueue.tsx` — new file

**Done when:** Component renders approval rows, Approve/Reject buttons call the API routes, status updates refresh the table.
**Commit:** `feat(dashboard): ApprovalQueue component with approve/reject actions`

---

### P31 — dashboard ApprovalsView.tsx page + routing
**Covers:** S2 frontend page
**Goal:** Dedicated `/approvals` page in the dashboard. Add nav link in `App.tsx`. Page renders `ApprovalQueue` component plus a header explaining the human gate concept for judges.
**Files:**
- `dashboard/src/pages/ApprovalsView.tsx` — new file
- `dashboard/src/App.tsx` — add route + nav link

**Done when:** `/approvals` route renders the page, nav shows the link, component loads real data from API.
**Commit:** `feat(dashboard): ApprovalsView page and routing`

---

### P32 — Dockerfile — production backend image
**Covers:** M6 containerisation
**Goal:** Production-ready `Dockerfile` for the FastAPI backend. Slim image, no dev dependencies, `uvicorn` on port 8080. Cloud Run expects this exact port.
**Files:**
- `Dockerfile` (update existing)

**Target:**
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["uvicorn", "driftguard.api.main:app", "--host", "0.0.0.0", "--port", "8080"]
```
Remove dev-only layers if present.

**Done when:** `Dockerfile` builds cleanly, CMD points to correct app path, port 8080.
**Commit:** `feat(docker): production backend Dockerfile for Cloud Run`

---

### P33 — driftguard/api/main.py — register approvals router
**Covers:** Wiring
**Goal:** Import and register the approvals router so all the new routes are reachable. Also register the Slack and Telegram webhook routes under `/webhooks`.
**Files:**
- `driftguard/api/main.py`

**Done when:** `GET /approvals`, `POST /approvals/{id}/approve`, `POST /webhooks/slack/interact`, `POST /webhooks/telegram` all return non-404.
**Commit:** `feat(api): register approvals and webhook routers`

---

### P34 — scripts/demo_full.py — Gemini + ADK smoke path
**Covers:** M4, M5 validation
**Goal:** Update `demo_full.py --auto` to run the three demo scenarios (rate_hike, normal_decay, covid_crash) through the full Gemini + ADK path. Add assertions that each scenario returns the correct regime label and action. This is the smoke test judges run.
**Files:**
- `scripts/demo_full.py`

**Done when:** `--auto` flag runs all three scenarios, prints pass/fail per scenario, exits 0 on all pass.
**Commit:** `feat(demo): Gemini + ADK smoke path in demo_full.py`

---

### P35 — demo video script + submission checklist
**Covers:** M8, M10
**Goal:** Write the demo script (narration + screen actions timed to 3 minutes) and verify the submission checklist from section 12 of the build plan. Not code — a markdown doc.
**Files:**
- `docs/demo_script.md` — new file
- `docs/v5_buildPlan.md` — tick off checklist items as complete

**Done when:** `demo_script.md` has timed narration for all 6 demo moments. Checklist in v5_buildPlan.md shows all items checked.
**Commit:** `docs: demo video script and submission checklist`

---

## Dependency Tree (Critical Path)

```
P01 P02 P03 (parallel — no deps)
         │
         P04 → P05 → P06 (Supabase chain)
         │
         P07 → P08 (tracing chain)
         │
         P09 → P10 → P11 → P12 → P13 (ADK chain)
         │
         P14 → P15 → P16 (Gemini chain)
         │
         P17 → P18 → P19 (self-eval chain)
         │
         P20 → P21 → P22 (evals chain)
         │
         P23 → P24 → P25 → P26 (approval API chain)
         │
         P27 → P28 → P29 (notifier chain)
         │
         P30 → P31 (dashboard chain)
         │
         P32 → P33 → P34 → P35 (deploy + demo chain)
```

---

## Day-by-Day Assignment

| Day | Phases | Focus |
|---|---|---|
| Day 1 (June 6) | P01–P06 | Repo hygiene + Supabase migration + deps |
| Day 2 (June 7) | P07–P16 | Tracing + ADK agents + Gemini swap |
| Day 3 (June 8) | P17–P22 | Self-improvement loop + LLM-as-Judge evals |
| Day 4 (June 9) | P23–P31 | Human approval gate (backend + frontend) |
| Day 5 (June 10) | P32–P35 | Docker + wiring + demo script |
| Buffer (June 11) | — | Fix, smoke test, submit |

---

*35 phases. Each ships a commit. Nothing left dangling.*
*Built against v5_buildPlan.md — every M and S item covered.*
