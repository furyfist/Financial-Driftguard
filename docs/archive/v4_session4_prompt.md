Session 4 — ADK Migration + Natural Language Query + Tech Debt

We are building FinSight AI v4. Sessions 1–3 are complete. The codebase is at
c:\Users\himan\OneDrive\Desktop\financial-driftguard.

What Sessions 1–3 delivered (already done, don't redo):
  API Key middleware (driftguard/api/auth.py)
  phoenix_trace_id column on DriftRun
  Section 7 prose count fix
  HaltOverlay.tsx + DriftChart.tsx (A1, A2)
  POST /demo/scenarios/{name} + DemoPanel.tsx (A3)
  AgentResponseCard.tsx + suggestion chips (A4)
  PDF cover page in generator.py (A5)
  enricher.py + EmailNotifier (B1)
  Slack Block Kit enrichment + _maybe_notify in brain.py (B1)
  feature_metadata.py + explain_feature_drift tool + ActionCard Why-section (B3)
  DigestGenerator + weekly Monday 08:00 APScheduler job (B4)

Session 4 goal: CP4 (B2) + CP5 core (C1, C5). Three items: C1 (Google ADK 2.0
multi-agent scaffold with AGENT_FRAMEWORK config switch — native path stays fully
intact), B2 (natural language drift query tool + filter params on the history
endpoint), C5 (6 V2 tech debt items in order). Full spec is in
docs/versions/plan/v4_build_plan.md sections 5 and 6. Read it before starting.

Read these files before writing any code — they define the existing surfaces you
will extend:
  finsight/llm/provider.py           — BaseLLMProvider ABC, LLMResponse, ToolCall
  finsight/llm/config.py             — get_llm(), LLM_PROVIDER env var pattern
  finsight/agent/brain.py            — DriftGuardAgent, analyze(), ask(), ALL_TOOLS
  finsight/agent/prompts/orchestrator.py  — ORCHESTRATOR_PROMPT text
  finsight/agent/tools/drift_tools.py    — existing drift tools + DISPATCH + DRIFT_TOOLS
  driftguard/api/routes/drift.py     — GET /drift/{model_id}/history (extend this)
  driftguard/api/routes/alerts.py    — POST /alerts/webhooks/configure (extend for persistence)
  driftguard/api/main.py             — lifespan, health route, router includes
  driftguard/scheduler/jobs.py       — restore_baselines_from_db, start_scheduler
  driftguard/store/database.py       — all SQLModel table classes (add one new table here)
  driftguard/core/snapshot.py        — DataSnapshot.from_dataframe() (add row guard here)
  driftguard/core/drift_result.py    — DriftResult, drifted_features property (fix dedup here)
  .env.example                       — existing env key list (extend + use for validation)

Risk note for C1: google-adk 2.0 was released May 19, 2026 — wrap every ADK
import in try/except ImportError so the native path always works without it.
If `AGENT_FRAMEWORK=native` (the default), ADK code is never touched.

Execute in exactly these 5 phases, one at a time. Complete each phase fully
before moving to the next.

─────────────────────────────────────────────────────────────
Phase 1 — C1: ADK scaffold (new files only, do NOT modify anything)
─────────────────────────────────────────────────────────────

Create four new files. Do NOT modify any existing file in this phase.

FILE 1: finsight/adk/__init__.py  — empty.

FILE 2: finsight/adk/config.py

Two module-level helpers:

  `get_agent_framework() -> str`
    Returns `os.getenv("AGENT_FRAMEWORK", "native").lower()`.
    Valid values: "native" | "adk". Anything else is treated as "native".

  `is_adk_enabled() -> bool`
    Returns `get_agent_framework() == "adk"`.

Add a module-level constant `ADK_GOVERNANCE_MODEL = "gemini-2.5-pro"` and
`ADK_ANALYST_MODEL = "gemini-2.0-flash"`.

FILE 3: finsight/adk/tools.py

Wrap the existing tool dispatch functions as ADK `FunctionTool` objects so that
ADK agents can call them. All ADK imports must be inside try/except ImportError
with a clear message if google-adk is not installed.

  - Import existing tool call functions:
      `call_drift_tool` from finsight.agent.tools.drift_tools
      `call_macro_tool` from finsight.agent.tools.macro_tools
      `call_phoenix_tool` from finsight.agent.tools.phoenix_tools
      `call_trust_tool` from finsight.agent.tools.trust_tools

  - Define a helper `_make_adk_tool(name, description, call_fn, schema_params)` that
    builds and returns a `google.adk.tools.FunctionTool` wrapping `call_fn(**kwargs)`.
    The `schema_params` is a dict of parameter-name → type-string, used only for the
    ADK tool description — ADK infers actual schemas from the Python function signature
    when using FunctionTool, but keeping a params dict here is fine as documentation.

  - Build these 6 ADK tool wrappers (one per function — not one per tool file):
      `adk_get_latest_drift`    → calls call_drift_tool("get_latest_drift", kwargs)
      `adk_get_model_history`   → calls call_drift_tool("get_model_history", kwargs)
      `adk_explain_feature_drift` → calls call_drift_tool("explain_feature_drift", kwargs)
      `adk_get_current_macro`   → calls call_macro_tool("get_current_macro", kwargs)
      `adk_list_traces`         → calls call_phoenix_tool("list_recent_drift_traces", kwargs)
      `adk_get_trust_score`     → calls call_trust_tool("get_trust_score", kwargs)

  - Export a list `ADK_GOVERNANCE_TOOLS` containing the drift + macro + phoenix + trust wrappers.
  - Export a list `ADK_ANALYST_TOOLS` containing only the drift + explain wrappers.

  If `google.adk` is not installed, set `ADK_GOVERNANCE_TOOLS = []` and
  `ADK_ANALYST_TOOLS = []` and log a warning at module level. Never raise on import.

FILE 4: finsight/adk/agents.py

Define the three ADK `LlmAgent` objects. All construction must be inside a
`build_agents()` factory function (not at module level) so imports are lazy
and the file can be imported without google-adk installed.

  ```python
  def build_agents():
      from google.adk.agents import LlmAgent
      from finsight.adk.tools import ADK_GOVERNANCE_TOOLS, ADK_ANALYST_TOOLS
      from finsight.adk.config import ADK_GOVERNANCE_MODEL, ADK_ANALYST_MODEL
      from finsight.agent.prompts.orchestrator import ORCHESTRATOR_PROMPT

      analyst_agent = LlmAgent(
          name="analyst_agent",
          model=ADK_ANALYST_MODEL,
          instruction=(
              "You explain drift causes using macro context and feature domain knowledge. "
              "Use explain_feature_drift for any feature flagged at medium severity or above."
          ),
          tools=ADK_ANALYST_TOOLS,
      )

      report_agent = LlmAgent(
          name="report_agent",
          model=ADK_ANALYST_MODEL,
          instruction=(
              "You generate SR 11-7 compliant report section prose. "
              "Be concise, cite drift scores and regime directly."
          ),
          tools=[],
      )

      governance_agent = LlmAgent(
          name="governance_agent",
          model=ADK_GOVERNANCE_MODEL,
          instruction=ORCHESTRATOR_PROMPT,
          tools=ADK_GOVERNANCE_TOOLS,
          sub_agents=[analyst_agent, report_agent],
      )

      return governance_agent, analyst_agent, report_agent
  ```

  Add a module-level `run_adk_analysis(model_id: str, query: str) -> str` function
  that:
  - Calls `build_agents()` inside try/except ImportError — returns
    `"ADK not available"` if google-adk is not installed.
  - Uses `google.adk.runners.InMemoryRunner` to run the governance agent with
    the query string and returns the final text response.
  - Wraps everything in try/except Exception — logs warning, returns the exception
    message as a string so callers can display it. Never raises.

Phase 1 commit message:
  feat(adk): scaffold finsight/adk/ — config, tools wrappers, LlmAgent definitions


─────────────────────────────────────────────────────────────
Phase 2 — C1: Wire AGENT_FRAMEWORK switch into brain.py
─────────────────────────────────────────────────────────────

Modify one existing file only.

FILE: finsight/agent/brain.py

In both `analyze()` and `ask()`, add an early check at the top of the method
body (before the impact_hint / message building):

  ```python
  if is_adk_enabled():
      try:
          from finsight.adk.config import is_adk_enabled  # already imported above
          from finsight.adk.agents import run_adk_analysis
          query = f"Analyze model '{model_id}'" if calling analyze() \
                  else the user query string
          adk_text = run_adk_analysis(model_id or "", query)
          result = _parse_response(adk_text)
          result.model_id = model_id
          _maybe_notify(result, model_id)
          return result
      except Exception as exc:
          logger.warning("ADK path failed (%s) — falling back to native", exc)
  # native path continues as before
  ```

Add the import `from finsight.adk.config import is_adk_enabled` at the TOP of
brain.py inside a try/except ImportError so it fails silently:
  ```python
  try:
      from finsight.adk.config import is_adk_enabled as _is_adk_enabled
  except ImportError:
      def _is_adk_enabled() -> bool: return False
  ```

Then reference `_is_adk_enabled()` (with leading underscore) inside the methods.

Also update `.env.example` — append at the bottom:
  ```
  # ── FinSight AI — Agent framework ──────────────────────────────────────────
  # "native" uses Groq/Gemini directly. "adk" uses Google ADK 2.0 multi-agent.
  AGENT_FRAMEWORK=native
  GOOGLE_GENAI_API_KEY=your_google_genai_api_key_here
  ```

Phase 2 commit message:
  feat(adk): wire AGENT_FRAMEWORK switch into brain.py — native fallback preserved


─────────────────────────────────────────────────────────────
Phase 3 — B2: Natural language drift query
─────────────────────────────────────────────────────────────

Create one new file and modify two existing files.

FILE: finsight/agent/tools/query_tools.py

A single tool function `query_drift_history(model_id, regime=None, severity=None,
feature=None, since=None, until=None, limit=20)`:

  - All parameters except `model_id` are optional filters.
  - `since` / `until` are ISO date strings ("YYYY-MM-DD").
  - Query the `DriftRun` table directly (same DB session pattern as drift_tools.py).
  - Apply each non-None filter:
      - `regime`: `DriftRun.regime == regime`
      - `severity`: `DriftRun.overall_severity == severity`
      - `feature`: case-insensitive substring match on `DriftRun.feature_results_json`
        using `DriftRun.feature_results_json.contains(feature)`
      - `since`: `DriftRun.checked_at >= datetime.fromisoformat(since)`
      - `until`: `DriftRun.checked_at <= datetime.fromisoformat(until)`
  - Order by `DriftRun.checked_at` descending, apply `limit`.
  - Return a list of dicts with keys: run_id, checked_at, overall_severity,
    drift_score, regime, notes.
  - Wrap in try/except — return `{"error": str(exc)}` on failure.

Register it in `QUERY_TOOLS` schema (OpenAI-compatible) with name
`"query_drift_history"`. All 6 params listed, only `model_id` required.
Include a `_DISPATCH` dict and a `call_query_tool(name, arguments)` dispatcher.

FILE: driftguard/api/routes/drift.py — extend GET /drift/{model_id}/history

Add these optional query parameters to the existing `get_drift_history` handler:
  - `regime: str | None = None`
  - `severity: str | None = None`
  - `feature: str | None = None`
  - `since: str | None = None`   — ISO date string "YYYY-MM-DD"
  - `until: str | None = None`

Apply filters to the SQLModel query the same way as query_tools.py. `limit`
already exists — keep it. Return type stays `list[DriftRunOut]`. No schema changes
needed — `DriftRunOut` already has all the relevant fields.

FILE: finsight/agent/brain.py — register query_tools in the agent

At the top of brain.py (alongside the existing DRIFT_TOOLS import):
  ```python
  from finsight.agent.tools.query_tools import QUERY_TOOLS, call_query_tool
  ```

Add `QUERY_TOOLS` to `ALL_TOOLS`. Add a `_QUERY_NAMES` set and handle
`call_query_tool` in `_dispatch_tool_call`. Pattern is identical to how
`DRIFT_TOOLS` / `call_drift_tool` are wired in today — follow that pattern exactly.

Phase 3 commit message:
  feat(query): query_drift_history tool + /history filter params (regime, severity, feature, since, until)


─────────────────────────────────────────────────────────────
Phase 4 — C5: Six tech debt items
─────────────────────────────────────────────────────────────

Execute all six items. Each touches a different part of the codebase.

────── C5-1: drifted_features dedup ──────

FILE: driftguard/core/drift_result.py

The existing `drifted_features` property returns every `FeatureDriftResult` where
`severity != DriftSeverity.NONE`. With 3 detectors (PSI, KS, JS), a single drifted
feature produces 3 entries — callers counting drifted_features over-count by 3x.

Fix: add a new property `unique_drifted_features` that returns one
`FeatureDriftResult` per feature name — keep the entry with the highest severity
score (use the `score` field). `drifted_features` remains unchanged so no existing
caller breaks.

Then in `driftguard/api/routes/drift.py`, in the `trigger_drift_check` response
body, change `result.drifted_features` to `result.unique_drifted_features` in the
list returned under `"drifted_features"` key. This is the only caller to update.

────── C5-2: WebhookConfig persistence ──────

FILE: driftguard/store/database.py — add new table

Add a `WebhookConfigRecord` SQLModel table with fields:
  id: Optional[int] — primary key
  platform: str     — "slack" | "discord"
  webhook_url: str
  model_id: Optional[str] = None
  severity_threshold: str = "high"
  created_at: datetime — default now UTC

FILE: driftguard/api/routes/alerts.py — save on configure

In `configure_webhook`, after `register_notifier(notifier, model_id=...)`, persist
the config to SQLite:
  ```python
  from ...store.database import WebhookConfigRecord, get_session
  with Session(engine) as s:
      s.add(WebhookConfigRecord(
          platform=payload.platform,
          webhook_url=payload.webhook_url,
          model_id=payload.model_id,
          severity_threshold=payload.severity_threshold,
      ))
      s.commit()
  ```

FILE: driftguard/scheduler/jobs.py — load on startup

In `restore_baselines_from_db()`, after the existing model-baseline logging loop,
add a block that reads all `WebhookConfigRecord` rows and calls `register_notifier`
for each one. Import `WebhookConfigRecord` from the store. Wrap in try/except so a
DB read failure doesn't block startup.

────── C5-3: Scheduler health endpoint ──────

FILE: driftguard/api/main.py — add GET /health/scheduler

Add a new route directly in main.py (no new router file needed):

  ```python
  @app.get("/health/scheduler")
  def scheduler_health():
      from .scheduler.jobs import scheduler
      if not scheduler.running:
          return {"status": "stopped", "jobs": []}
      jobs = []
      for job in scheduler.get_jobs():
          jobs.append({
              "id": job.id,
              "next_run": str(job.next_run_time) if job.next_run_time else None,
              "trigger": str(job.trigger),
          })
      return {"status": "running", "jobs": jobs}
  ```

Note: the import path for `scheduler` is `driftguard.scheduler.jobs.scheduler` —
inside main.py use a relative import: `from ..scheduler.jobs import scheduler`.

────── C5-4: Async macro fetch on startup ──────

FILE: driftguard/scheduler/jobs.py

In `restore_baselines_from_db()`, the final `fetch_and_cache_macro()` call is
synchronous and can block the FastAPI lifespan for several seconds on slow FRED
connections. Move it to a background thread:

  Replace:
    ```python
    logger.info("Fetching initial macro snapshot...")
    fetch_and_cache_macro()
    ```
  With:
    ```python
    import threading
    logger.info("Fetching initial macro snapshot in background...")
    threading.Thread(target=fetch_and_cache_macro, daemon=True, name="macro-init").start()
    ```

────── C5-5: .env.example validation ──────

FILE: driftguard/api/main.py

In the `lifespan` function, after `create_db()` and before `start_scheduler()`,
add a startup validation call. Define a module-level function `_warn_missing_env()`
that checks for these keys and logs a WARNING for each one that is absent or
still set to its placeholder value (contains "your_" prefix):

  Required for core function:
    FRED_API_KEY, GROQ_API_KEY (or GEMINI_API_KEY if LLM_PROVIDER=gemini)

  Required for notifications (warn only if partially set):
    SLACK_WEBHOOK_URL, SMTP_HOST

  Required for Phoenix:
    PHOENIX_COLLECTOR_ENDPOINT

Log format: `"Startup warning: %s is not set — <feature> will be degraded"`.
Never raise. Call `_warn_missing_env()` in `lifespan` right after `create_db()`.

────── C5-6: Minimum row validation ──────

FILE: driftguard/core/snapshot.py

In `DataSnapshot.from_dataframe()`, after the existing loop that populates
`_features`, count the minimum non-NaN row count across all numeric columns.
If that minimum is less than 100, raise `ValueError` with this exact message:
  `"DataSnapshot requires at least 100 rows per feature; got {min_rows} in '{label}'."`

Only raise if there is at least one numeric column — if the DataFrame has no
numeric columns at all, let the snapshot be created (it will just be empty).

Phase 4 commit message:
  fix(tech-debt): C5 — drifted_features dedup, webhook persistence, scheduler health, async macro, env validation, row guard


─────────────────────────────────────────────────────────────
Phase 5 — Verify no imports are broken
─────────────────────────────────────────────────────────────

Run these checks from the project root with the venv active (venv is at `venv/`,
not `.venv/` — use `venv/Scripts/python.exe` on Windows):

Check 1:
  python -c "from finsight.adk.config import is_adk_enabled, get_agent_framework; print('adk config ok — framework:', get_agent_framework())"

Check 2:
  python -c "from finsight.adk.tools import ADK_GOVERNANCE_TOOLS, ADK_ANALYST_TOOLS; print(f'adk tools ok — governance: {len(ADK_GOVERNANCE_TOOLS)}, analyst: {len(ADK_ANALYST_TOOLS)}')"

Check 3:
  python -c "from finsight.adk.agents import build_agents, run_adk_analysis; print('adk agents ok')"

Check 4:
  python -c "from finsight.agent.tools.query_tools import query_drift_history, QUERY_TOOLS; print(f'query_tools ok — {len(QUERY_TOOLS)} tool(s)')"

Check 5:
  python -c "from driftguard.store.database import WebhookConfigRecord; print('WebhookConfigRecord ok')"

Check 6:
  python -c "from driftguard.core.drift_result import DriftResult; import inspect; assert 'unique_drifted_features' in [p for p in dir(DriftResult) if not p.startswith('_')]; print('unique_drifted_features ok')"

Check 7 (TypeScript):
  Run `npx tsc --noEmit` from `dashboard/` — output should be empty.

Report any errors and fix them before marking this phase done. Do not skip a check.

Phase 5 commit message:
  chore(verify): all import checks pass for C1/B2/C5 — ADK scaffold, query tools, debt fixes