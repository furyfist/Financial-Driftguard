# FinSight AI — V5 Implementation Summary

**Document type:** Internal engineering milestone summary
**Version tagged:** `v0.5.0` — hackathon submission
**Hackathon:** Google Cloud Rapid Agent Hackathon (Arize Track)
**Deadline:** June 11, 2026 @ 2:00 PM PDT
**Built on top of:** V4 — visual polish, notifications, ADK scaffold, Docker Compose
**Date:** June 2026

---

## What V5 Was About

V5 was not a feature release. It was a surgical conversion of FinSight AI from a local dev tool into a **hackathon-winning submission** on the Arize track. Every change mapped directly to either a hard disqualification requirement or a judging criterion.

**One-line pitch:**
> A Gemini-powered governance agent that monitors financial ML models, detects drift, classifies the market regime, and tells you the *opposite* action depending on whether it's a crisis or model decay — fully traced in Phoenix, with a self-improvement loop via MCP.

---

## Hard Requirements Completed (35 Phases)

### Infrastructure (P01–P06)
- **P01** — MIT LICENSE added to repo root
- **P02** — `.env.example` with all 13 V5 env vars documented
- **P03** — `requirements.txt` updated: `psycopg2-binary`, `google-adk`, `google-genai`, `openinference-instrumentation-google-adk`, `openinference-instrumentation`, `arize-phoenix-evals`
- **P04** — `database.py` reads `DATABASE_URL` from env, falls back to SQLite if unset
- **P05** — `ApprovalQueue` SQLModel table defined and created on startup
- **P06** — Blob roundtrip test for Postgres `BYTEA` (parquet baseline survives Supabase)

### Tracing — OpenInference + ADK (P07–P08)
- **P07** — `finsight/tracing/setup.py` swapped to `GoogleADKInstrumentor` auto-instrumentation via `openinference-instrumentation-google-adk`. Must be called before any `google.adk` import.
- **P08** — `finsight/tracing/attributes.py` — ADK span attribute constants (`agent_name`, `tool_name`, `regime`, `confidence`)

### Google ADK 2.0 — Full Wire (P09–P13)
- **P09** — `finsight/adk/config.py` — typed `ADKConfig` dataclass from env. Raises clear error if `GOOGLE_GENAI_API_KEY` missing when `AGENT_FRAMEWORK=adk`.
- **P10** — `finsight/adk/tools.py` — 5 ADK `FunctionTool` wrappers: `run_drift_analysis`, `get_macro_signals`, `get_trust_score`, `query_phoenix_traces`, `evaluate_past_recommendations`
- **P11** — `finsight/adk/agents.py` — `GovernanceAgent` fully wired as top-level ADK orchestrator
- **P12** — `finsight/adk/agents.py` — `AnalystAgent` (drift analysis, regime classification) and `ReportAgent` (PDF trigger, final output formatting) added
- **P13** — `finsight/agent/brain.py` — `AGENT_FRAMEWORK=adk` branch routes to `run_adk_analysis()`. `AGENT_FRAMEWORK=native` (default) leaves existing Groq path fully intact.

### Gemini 2.5 Pro (P14–P16)
- **P14** — `finsight/llm/gemini_provider.py` — `LLM_REASONING_MODEL` (gemini-2.5-pro) for reasoning, `LLM_FAST_MODEL` (gemini-2.0-flash) for generation. Tool-call format consistent with existing `AgentResponse` parsing.
- **P15** — Prompts in `orchestrator.py`, `analyst.py`, `report_writer.py` updated for Gemini output structure: explicit JSON format instructions, "respond only with valid JSON" constraints, trimmed system prompts.
- **P16** — `brain.py` strips markdown fences (` ```json ... ``` `) from Gemini responses before parsing. Groq path unaffected.

### Self-Improvement Loop (P17–P19)
- **P17** — `finsight/agent/tools/self_eval_tools.py` — `evaluate_past_recommendations(model_id, window_days=30)`: calls Phoenix MCP for last N agent decisions, runs LLM-as-Judge on each ("was this action correct for this regime?"), returns `{regime: accuracy_score, adjustments: [...]}`.
- **P18** — `get_confidence_adjustment(regime, historical_accuracy)` — returns `ConfidenceAdjustment` dataclass. Logic: `black_swan` + accuracy ≥ 0.95 → increase HALT confidence; `credit_stress` + accuracy < 0.80 → lower confidence, suggest conservative action.
- **P19** — `brain.py` calls `evaluate_past_recommendations()` before returning final recommendation. Applies `ConfidenceAdjustment` to confidence score and action. Skips gracefully if Phoenix MCP is unreachable. `AgentResponse` gains `self_eval_accuracy` and `confidence_adjustment` fields.

### LLM-as-Judge Governance Evals (P20–P22)
- **P20** — `finsight/evals/governance_eval.py` — `REGIME_EVAL_TEMPLATE`: given macro signals + agent's regime label, was the classification correct?
- **P21** — `ACTION_EVAL_TEMPLATE`: given regime + action, was the action correct per governance rules (black_swan→halt, credit_stress→monitor, stable+drift→retrain)? `run_evals(model_id)` runner pulls traces from Phoenix, runs both evaluators via `llm_classify`.
- **P22** — `push_eval_results_to_phoenix(results, experiment_name)` pushes results to Phoenix Cloud Experiments tab. Judges see "13 evaluated, 12/13 correct" directly in the UI.

### Human Approval Gate (P23–P29)
- **P23** — `ApprovalQueue` exported from `driftguard/store/models.py`
- **P24** — `driftguard/api/routes/approvals.py` — CRUD routes: `GET /approvals`, `GET /approvals/{id}`, `POST /approvals/{id}/approve`, `POST /approvals/{id}/reject`
- **P25** — `POST /webhooks/slack/interact` — receives Slack interactive button payload, verifies HMAC signing secret, updates `ApprovalQueue`, calls `response_url` to update original Slack message
- **P26** — `POST /webhooks/telegram` — receives Telegram callback query, parses `approve_{id}` / `reject_{id}` from `data`, updates `ApprovalQueue`, answers callback to remove loading state
- **P27** — `finsight/notifications/approval_notifier.py` — `SlackApprovalNotifier.send(approval)` builds Slack Block Kit message: header, model/regime/action/confidence/impact fields, Approve (primary) + Reject (danger) buttons
- **P28** — `TelegramApprovalNotifier.send(approval)` builds message text + inline keyboard with `callback_data=approve_{id}` / `reject_{id}`. Posts via Telegram Bot API `sendMessage`.
- **P29** — `brain.py` fires approval gate after recommendation: if action in `{halt, retrain, freeze, escalate}` → creates `ApprovalQueue` DB record → calls notifier → sets `result.requires_approval=True` + `result.approval_id`

### Dashboard — Approval UI (P30–P31)
- **P30** — `dashboard/src/components/ApprovalQueue.tsx` — table of pending/approved/rejected approvals. Columns: model, regime, action, confidence, status, timestamp. Approve/Reject buttons for pending rows. Polls `/approvals` every 5 seconds.
- **P31** — `dashboard/src/pages/ApprovalsView.tsx` — dedicated `/approvals` page. Nav link added in `App.tsx`. Header explains the human gate concept for judges.

### Deploy + Demo (P32–P35)
- **P32** — `Dockerfile` updated for Cloud Run: `python:3.11-slim`, no dev deps, `uvicorn` on port 8080 (`$PORT` respected via Railway env)
- **P33** — `driftguard/api/main.py` — approvals router and webhook routes registered. All new endpoints return non-404.
- **P34** — `scripts/demo_full.py --auto` runs all three scenarios through the full Gemini + ADK path. Per-scenario pass/fail assertions. Exits 0 on all pass.
- **P35** — `docs/demo_script.md` written (3-minute timed narration). Submission checklist complete.

---

## Stack Pivot: ADK → Groq/Native

After completing the 35 phases, the ADK + Gemini path was tested end-to-end. Due to ADK 2.0 being 2 days old at implementation and Groq being faster/more reliable for the demo window, the submission was switched to **Groq + native agent loop** with Phoenix Cloud traces. Key commits:

- `feat: switch to Groq/native, drop Google ADK, fix Railway deploy config`
- `feat: wire Phoenix Arize auth headers across tracing, tools, and evals`
- `feat: harden Groq rate-limit retry, reduce tool iterations, add agent smoke test`
- `feat: add connection smoke-test script and DB startup logging`
- `feat: wire VITE_API_URL and VITE_API_KEY for frontend env-aware API config`
- `feat: add Vercel config with SPA rewrite rule for React Router`

---

## Deployed Infrastructure

| Service | Platform | URL |
|---|---|---|
| Backend (FastAPI) | Railway | `$PORT` dynamic, `/health` healthcheck |
| Frontend (React) | Vercel | SPA rewrite via `vercel.json` |
| Database | Supabase PostgreSQL | Pooler URL via `DATABASE_URL` |
| Tracing | Arize Phoenix Cloud | `app.phoenix.arize.com/s/himanshu290304` |
| Macro data | FRED API + Yahoo Finance | Background job, 6h refresh |

---

## External Services Config

```bash
DATABASE_URL=postgresql+psycopg2://postgres.<ref>:...@aws-0-us-east-1.pooler.supabase.com:5432/postgres
LLM_PROVIDER=groq
GROQ_API_KEY=gsk_...
LLM_REASONING_MODEL=llama-3.3-70b-versatile
LLM_FAST_MODEL=llama-3.3-70b-versatile
AGENT_FRAMEWORK=native
FRED_API_KEY=...
PHOENIX_COLLECTOR_ENDPOINT=https://app.phoenix.arize.com/s/himanshu290304/v1/traces
PHOENIX_API_KEY=...
PHOENIX_MCP_BASE_URL=https://app.phoenix.arize.com/s/himanshu290304
PHOENIX_PROJECT_NAME=finsight-ai
API_KEY=finsight-dev-key
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/...
SLACK_SIGNING_SECRET=...
TELEGRAM_BOT_TOKEN=...
TELEGRAM_CHAT_ID=...
```

---

## Demo Flow (3-Minute Video Script)

| Time | Scene | Action |
|---|---|---|
| 0:00–0:30 | Problem statement | Voiceover — same drift, opposite actions, $1.2M–$4.8M impact |
| 0:30–1:00 | Architecture | Dashboard opens, regime badge visible, macro panel live |
| 1:00–1:30 | Rate Hike scenario | Click Demo Panel → Rate Hike → regime=credit_stress, "Do NOT retrain" |
| 1:30–2:00 | COVID scenario | Click COVID Crash → HALT overlay fires, ApprovalQueue entry created |
| 2:00–2:30 | Agent chat | "Why is int_rate drifting?" → structured response card, tool spans visible |
| 2:30–2:50 | Phoenix traces | Experiments tab: 13 evaluated, 12/13 correct, black_swan accuracy 98% |
| 2:50–3:00 | Close | SR 11-7 PDF download, "regime-aware governance, the missing layer" |

---

## Demo Smoke Check

```bash
python scripts/check_connections.py
# Expected: [ OK ] Database, Groq, Phoenix, FRED

python scripts/demo_full.py --smoke
# Expected: 11/11 checks passed

python scripts/demo_full.py --auto
# Expected: 3/3 scenarios, all correct regime + action
```

---

## What V5 Left Open

| Gap | Notes |
|---|---|
| Recession classifier recall = 0% | Binary sub-classifier on NBER dates needed. Inherited from V2. |
| PostgreSQL migration complete but SQLite fallback still default | `DATABASE_URL` env var controls which backend is used |
| ADK 2.0 path deprioritised | Scaffold and instrumentation are in place; switched to Groq/native for reliability |
| Multi-model monitoring | Registry and dashboard support multiple models; agent reasoning is single-model |
| PyPI packaging | `pip install finsight-ai` not yet published |

---

*FinSight AI V5 — June 2026*
*Hackathon submission: Google Cloud Rapid Agent Hackathon (Arize Track)*
*Built on V4 (v0.4.0, May–June 2026)*
