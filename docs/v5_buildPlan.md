# FinSight AI — V5 Hackathon Submission Build Plan

**Document type:** Engineering build plan — hackathon submission sprint  
**Project:** `finsight-ai`  
**Current version:** `v0.4.0` (in progress, Sessions 1–3 complete)  
**Target version:** `v0.5.0` — hackathon submission  
**Hackathon:** Google Cloud Rapid Agent Hackathon (Arize Track)  
**Deadline:** June 11, 2026 @ 2:00 PM PDT  
**Prize bucket:** Arize — 1st $5,000 / 2nd $3,000 / 3rd $2,000  
**Author:** Internal engineering reference  
**Date:** June 2026

---

## 1. What V5 Is About

V5 is NOT a feature release. V5 is the surgical conversion of FinSight AI from a local dev tool into a hackathon-winning submission on the Arize track. Every change maps directly to either a hard requirement (disqualification if missing) or a judging criterion.

**The one-line pitch for judges:**  
> A Gemini-powered governance agent that monitors financial ML models, detects drift, classifies the market regime, and tells you the *opposite* action depending on whether it's a crisis or model decay — all fully traced in Phoenix, with a self-improvement loop via MCP.

---

## 2. Real-World Problem: Credit Model Governance During Market Stress

**The problem we're wiring this to (Financial Services track example from the rules):**

Banks deploy ML models to approve or deny loans. These models drift constantly. Every monitoring tool on the market (Arize AX, WhyLabs, Evidently, MLflow) detects drift and stops. They produce a number and a red alert. What happens next is on the human.

In financial ML, the same drift signal requires opposite actions:

- **Fed rate hike** → interest rate feature drifts → DON'T retrain (drift is macro-driven, retraining locks in cycle patterns)
- **Normal markets** → features drift → RETRAIN immediately (model is decaying)
- **Black swan (COVID)** → everything drifts → FREEZE automated decisions (human review only, retraining on crisis data destroys the model)

Nobody solves this. FinSight AI does. It sits on top of financial ML models, watches them through Arize Phoenix, understands *why* they're drifting using macro regime context, and tells each stakeholder exactly what to do — with a human approval gate before any action is taken.

**Impact statement for judges:** A single misclassified drift response on a $200M lending portfolio can cost $1.2M–$4.8M in unexpected defaults. FinSight prevents this by ensuring the operationally correct action is taken every time, with full audit trails for regulators.

---

## 3. Hackathon Requirements Checklist

### 3.1 Hard Requirements (Disqualifiers if Missing)

| # | Requirement | Current Status | V5 Action |
|---|---|---|---|
| H1 | **Gemini as the LLM** | Groq in dev, Gemini provider exists untested | Swap LLM_PROVIDER=gemini, test demo_full.py end-to-end |
| H2 | **Code-owned agent runtime** (ADK, Gemini SDK, or Cloud Run) | V4 ADK scaffold exists, not wired | Wire ADK with GoogleADKInstrumentor, deploy on Cloud Run |
| H3 | **Arize Phoenix MCP integrated** — agent queries own traces at runtime | ✅ Have this, points to localhost | Point to Phoenix Cloud, verify MCP tools work against cloud |
| H4 | **OpenInference auto-instrumentor** | Manual decorators in finsight/tracing/ | Replace with `openinference-instrumentation-google-adk` |
| H5 | **Traces sent to Phoenix Cloud** | Local Docker Phoenix | Sign up Phoenix Cloud, swap PHOENIX_COLLECTOR_ENDPOINT |
| H6 | **Live hosted URL** | Local only, SQLite | Deploy backend on GCP Cloud Run, frontend on Vercel |
| H7 | **Supabase migration** (replaces SQLite for cloud deploy) | SQLite everywhere | Swap DATABASE_URL to Supabase Postgres, add psycopg2-binary |
| H8 | **Public GitHub repo with LICENSE** | Repo exists, license status unclear | Add MIT LICENSE to repo root, verify GitHub About section |
| H9 | **3-minute demo video** | demo_full.py --auto exists as script basis | Record video with HALT overlay, demo panel, agent chat |
| H10 | **Devpost submission form** | Not started | Fill out on submission day |

### 3.2 Arize Track Scoring Criteria

From the Arize section on Devpost — these are what the judges actually evaluate:

| Criterion | Weight | Our Angle |
|---|---|---|
| **Technical implementation** | High | ADK multi-agent + Gemini + Cloud Run + Supabase — full GCP stack |
| **Meaningful use of tracing and MCP** | High | Agent queries its own Phoenix traces to understand past drift patterns — not just logging |
| **Quality of the agent's self-improvement loop** | High (bonus) | Agent evaluates its own past recommendations via LLM-as-Judge, adjusts confidence thresholds |
| **Overall impact** | Medium | Credit model governance during market stress — $M in prevented losses |

### 3.3 General Judging Criteria

| Criterion | Our Angle |
|---|---|
| **Technological Implementation** — Google Cloud + Partner integration quality | Cloud Run + ADK + Phoenix Cloud + Supabase + OpenInference = deep GCP integration |
| **Design** — UX quality | HALT overlay, demo panel (judges click buttons), structured agent chat cards, PDF reports |
| **Potential Impact** — impact on target communities | SR 11-7 regulatory compliance, prevents $M losses from wrong drift response |
| **Quality of Idea** — creativity and uniqueness | Regime-aware governance is genuinely novel — no other tool makes this distinction |

---

## 4. Architecture (V5 — Submission)

```
┌─────────────────────────────────────────────────────────────┐
│                    USER SURFACES                             │
│  ┌──────────┐  ┌──────────────┐  ┌───────────────────────┐  │
│  │ Engineer  │  │ Quant/DS     │  │ Risk Officer          │  │
│  │ Dashboard │  │ Experiments  │  │ Chat + PDF + Alerts   │  │
│  └─────┬────┘  └──────┬───────┘  └────────┬──────────────┘  │
│        └───────────────┼───────────────────┘                 │
│                        ▼                                     │
│  ┌─────────────────────────────────────────────────────┐     │
│  │     HUMAN GATE (Slack / Telegram Approve/Reject)    │     │
│  │     High-risk actions require explicit approval      │     │
│  └──────────────────┬──────────────────────────────────┘     │
│                     ▼                                        │
│  ┌─────────────────────────────────────────────────────┐     │
│  │         AGENT LAYER (Google ADK 2.0)                │     │
│  │         GovernanceAgent → AnalystAgent → ReportAgent │     │
│  │         Gemini 2.5 Pro (reasoning)                  │     │
│  │         Gemini 2.0 Flash (generation)               │     │
│  │         OpenInference GoogleADKInstrumentor          │     │
│  └──────────────────┬──────────────────────────────────┘     │
│                     │                                        │
│          ┌──────────┼──────────────┐                         │
│          ▼          ▼              ▼                          │
│  ┌──────────┐ ┌──────────┐ ┌──────────────────────┐         │
│  │ Phoenix  │ │ DriftGuard│ │ Self-Improvement     │         │
│  │ MCP      │ │ Tools    │ │ Loop (LLM-as-Judge)  │         │
│  │ Server   │ │          │ │                      │         │
│  └────┬─────┘ └────┬─────┘ └──────────┬───────────┘         │
│       │            │                   │                     │
│       ▼            ▼                   ▼                     │
│  ┌─────────────────────────────────────────────────────┐     │
│  │           PHOENIX CLOUD (app.phoenix.arize.com)     │     │
│  │  traces · datasets · experiments · evals · prompts  │     │
│  │  OpenInference auto-instrumented spans              │     │
│  └─────────────────────────────────────────────────────┘     │
│                                                              │
│  ┌─────────────────────────────────────────────────────┐     │
│  │      DRIFTGUARD ENGINE (existing, untouched)        │     │
│  │  PSI + KS + JS detectors · ML regime classifier     │     │
│  │  MacroSignalFetcher (FRED + VIX)                    │     │
│  └──────────────────┬──────────────────────────────────┘     │
│                     │                                        │
│  ┌──────────────────▼──────────────────────────────────┐     │
│  │         SUPABASE (PostgreSQL)                       │     │
│  │  Models · DriftRuns · Alerts · AgentDecisionLog     │     │
│  │  WebhookConfig · ApprovalQueue                      │     │
│  └─────────────────────────────────────────────────────┘     │
│                                                              │
│  ┌─────────────────────────────────────────────────────┐     │
│  │           GCP CLOUD RUN                             │     │
│  │  FastAPI backend · containerised · auto-scaling      │     │
│  └─────────────────────────────────────────────────────┘     │
└─────────────────────────────────────────────────────────────┘
```

---

## 5. Must-Do Items (Participation — 3 Days)

These are the items that MUST ship or the submission is invalid.

---

### M1. Supabase Migration (SQLite → Postgres)

**Why:** SQLite breaks on any cloud deploy. Ephemeral filesystem = data loss on every redeploy.

**How:**
- Create a Supabase project (free tier, already familiar from Journey AI)
- Change one env var: `DATABASE_URL=postgresql+psycopg2://user:pass@db.xxx.supabase.co:5432/postgres`
- Add `psycopg2-binary` to requirements.txt
- SQLModel uses SQLAlchemy under the hood — table definitions are already Postgres-compatible
- `create_db()` runs `SQLModel.metadata.create_all()` which creates tables on first connect
- Test: run `demo/lending_club.py` seed → verify tables exist in Supabase dashboard

**Files touched:**
- `driftguard/store/database.py` — change engine creation to read `DATABASE_URL` env var
- `.env.example` — add `DATABASE_URL` with Supabase template
- `requirements.txt` — add `psycopg2-binary`

**Risk:** Parquet baseline blobs stored as BLOB in SQLite need to become BYTEA in Postgres. SQLModel handles this transparently but verify the blob roundtrip.

**Effort:** 2–3 hours

---

### M2. Phoenix Cloud Setup

**Why:** Arize track requires traces in Phoenix Cloud (free SaaS) or self-hosted Phoenix. Cloud is 20 minutes vs deploying a Phoenix container.

**How:**
- Sign up at `app.phoenix.arize.com` — free, 10 GiB storage
- Create a space, get API key from Settings → API Keys
- Update `.env`:
  ```
  PHOENIX_COLLECTOR_ENDPOINT=https://app.phoenix.arize.com/s/<space-name>/v1/traces
  PHOENIX_API_KEY=<your-api-key>
  PHOENIX_PROJECT_NAME=finsight-ai
  ```
- Existing `finsight/tracing/setup.py` already reads these env vars — no code change needed
- Phoenix MCP server also points here:
  ```
  npx -y @arizeai/phoenix-mcp@latest --baseUrl https://app.phoenix.arize.com/s/<space-name> --apiKey <key>
  ```

**Effort:** 20 minutes

---

### M3. OpenInference Auto-Instrumentor (Replace Manual Decorators)

**Why:** Arize track explicitly requires OpenInference instrumentation. Manual decorators work but auto-instrumentors capture deeper span trees (tool calls, LLM reasoning steps, sub-agent invocations).

**How:**
- Install: `pip install openinference-instrumentation-google-adk`
- In `finsight/tracing/setup.py`, replace the custom `register()` wrapper:
  ```python
  from phoenix.otel import register
  from openinference.instrumentation.google_adk import GoogleADKInstrumentor

  def init_tracing(project_name="finsight-ai"):
      tracer_provider = register(
          project_name=project_name,
          auto_instrument=True,  # auto-trace all installed instrumentors
          batch=True,
      )
      # ADK instrumentor must run BEFORE any google.adk imports
      GoogleADKInstrumentor().instrument(tracer_provider=tracer_provider)
      return tracer_provider
  ```
- Keep existing manual decorators as fallback (they still fire for DriftGuard-specific spans like per-detector scores)
- The auto-instrumentor captures ADK agent invocations, tool calls, and Gemini LLM calls automatically

**Dependencies added:**
```
openinference-instrumentation-google-adk>=0.1.10
openinference-instrumentation>=0.1.0
```

**Effort:** 1–2 hours

---

### M4. Gemini End-to-End Swap

**Why:** Hard requirement — must use Gemini. Groq is dev only.

**How:**
- Set in `.env`:
  ```
  LLM_PROVIDER=gemini
  GEMINI_API_KEY=<key>
  LLM_REASONING_MODEL=gemini-2.5-pro
  LLM_FAST_MODEL=gemini-2.0-flash
  ```
- Run `python scripts/demo_full.py --auto` with Gemini
- Compare output structure vs Groq — fix any prompt differences
- Budget 2–3 hours for prompt tuning (known from V3 docs)
- Key areas to check: tool calling JSON format, response structure parsing, Section 7 prose

**Files touched:**
- `.env` — swap provider
- Possibly `finsight/agent/prompts/orchestrator.py` — adjust if Gemini structures responses differently
- Possibly `finsight/agent/brain.py` — adjust response parsing if needed

**Effort:** 2–3 hours

---

### M5. Google ADK 2.0 Wiring (Real, Not Scaffold)

**Why:** Arize track requires "code-owned agent runtime" — ADK qualifies. V4 Session 4 created the scaffold (`finsight/adk/`). V5 makes it real.

**How:**
- The V4 scaffold has `build_agents()` and `run_adk_analysis()` in `finsight/adk/agents.py`
- V5 completes: set `AGENT_FRAMEWORK=adk` in `.env`, verify the ADK path in `brain.py` works end-to-end
- Wire `GoogleADKInstrumentor` (from M3) so ADK agent calls are auto-traced
- The multi-agent split (GovernanceAgent → AnalystAgent → ReportAgent) is already defined in the scaffold
- Test: `POST /agent/ask` with `AGENT_FRAMEWORK=adk` returns a valid `AgentResponse`

**Critical ordering:** `GoogleADKInstrumentor().instrument()` MUST run before `from google.adk import ...` — this is an ADK requirement documented in the Arize docs.

**Effort:** 4–6 hours (includes debugging ADK + Gemini integration)

---

### M6. GCP Cloud Run Deployment

**Why:** Hosted URL is required. Cloud Run scores on "interaction with Google Cloud" criterion.

**How:**
- Create new GCP account (free $300 credits for 90 days)
- Create a `Dockerfile`:
  ```dockerfile
  FROM python:3.11-slim
  WORKDIR /app
  COPY requirements.txt .
  RUN pip install --no-cache-dir -r requirements.txt
  COPY . .
  CMD ["uvicorn", "driftguard.api.main:app", "--host", "0.0.0.0", "--port", "8080"]
  ```
- Deploy:
  ```bash
  gcloud run deploy finsight-ai \
    --source . \
    --region us-central1 \
    --allow-unauthenticated \
    --set-env-vars "DATABASE_URL=...,PHOENIX_API_KEY=...,GEMINI_API_KEY=..."
  ```
- Cloud Run auto-builds from source (no Docker locally required)
- Dashboard: deploy to Vercel (existing React + Vite setup)
- Update dashboard `VITE_API_URL` to point to Cloud Run URL

**Effort:** 3–4 hours

---

### M7. LICENSE File

**Why:** "The repository must be public and include a complete open source license file. This license should be detectable and visible at the top of the repository page."

**How:**
```bash
# In repo root
echo "MIT License\n\nCopyright (c) 2026 FinSight AI\n\n..." > LICENSE
git add LICENSE
git commit -m "chore: add MIT license"
git push
```
Verify it shows in GitHub's About section sidebar.

**Effort:** 5 minutes

---

### M8. Demo Video (3 minutes)

**Why:** Required submission item.

**Structure:**
- 0:00–0:30 — Problem statement: same drift, opposite actions. No existing tool solves this.
- 0:30–1:00 — Architecture overview: Gemini + ADK + Phoenix + DriftGuard
- 1:00–1:30 — Demo Panel: click Rate Hike → dashboard updates → agent says "don't retrain"
- 1:30–2:00 — Demo Panel: click COVID Crash → HALT overlay fires → trust API returns false
- 2:00–2:30 — Agent Chat: ask "Why did int_rate drift?" → explainable drift response
- 2:30–2:50 — Phoenix Cloud: show traces, show self-improvement eval results
- 2:50–3:00 — Impact: $1.2M–$4.8M prevented, SR 11-7 PDF report

**Effort:** 3–4 hours (recording + one edit pass)

---

## 6. Stand-Out Items (Winning — 2 Days)

These map directly to the Arize scoring criteria and differentiate from other submissions.

---

### S1. Self-Improvement Loop (Arize Bonus Points)

**Why:** Arize explicitly states "Bonus points for agents that use their own observability data to improve over time." This is the single highest-leverage differentiator.

**What it does:**
After the agent produces a recommendation, it queries its own recent traces via Phoenix MCP, evaluates whether its past recommendations were correct using LLM-as-Judge, and adjusts its confidence thresholds.

**How:**
- New tool: `finsight/agent/tools/self_eval_tools.py`
  - `evaluate_past_recommendations(model_id, window_days=30)`:
    1. Call `list_recent_drift_traces` via MCP to get last N agent decisions
    2. For each decision: compare recommended action vs actual regime outcome
    3. Run LLM-as-Judge eval: "Given this regime was {X} and the agent recommended {Y}, was this correct?"
    4. Calculate accuracy per regime type
    5. Return structured eval: `{regime: accuracy, adjustments: [...]}`
  - `get_confidence_adjustment(regime, historical_accuracy)`:
    - If agent was right 95%+ on black_swan → increase confidence for HALT recommendations
    - If agent was wrong on credit_stress → lower confidence, suggest more conservative action
    - Returns `ConfidenceAdjustment` dataclass

- New Phoenix eval pipeline: `finsight/evals/governance_eval.py`
  - Uses `arize-phoenix-evals` to run evaluations on the agent's trace dataset
  - Evaluator: "Did the agent's recommended action match the operationally correct action for this regime?"
  - Results appear in Phoenix Cloud under Experiments — judges can see them

- Agent uses this: in `brain.py`, before producing a recommendation, call `evaluate_past_recommendations()` and factor the confidence adjustment into the final response

**Why this wins:** Every other Arize submission will do generic "query my traces and summarize." Ours does: "I recommended HALT three times this week, all confirmed correct by LLM-as-Judge eval. My black_swan detection confidence is 98%. I'm increasing my automation threshold." That's a real self-improvement story grounded in financial domain knowledge.

**Effort:** 1 day

---

### S2. Slack / Telegram Human Approval Gate

**Why:** The hackathon rules say "agents that accomplish tasks for you... while keeping you in control." A human gate on high-risk actions is the strongest demonstration of this principle. Also extends existing V4 notification work (B1).

**What it does:**
When the agent recommends a high-impact action (HALT, retrain, freeze), the action is NOT auto-executed. Instead:
1. Agent creates an `ApprovalRequest` in the database
2. Fires a Slack/Telegram message with the recommendation + Approve/Reject buttons
3. Waits for human response
4. Only executes the action after explicit approval
5. Rejection triggers the agent to log "human override" and suggest alternatives

**How:**

**New DB table** — `ApprovalQueue`:
```python
class ApprovalQueue(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    model_id: str
    action: str           # "halt" | "retrain" | "freeze" | "escalate"
    recommendation: str   # full agent recommendation text
    regime: str
    confidence: float
    status: str = "pending"  # "pending" | "approved" | "rejected"
    responded_by: str | None = None
    responded_at: datetime | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
```

**Slack integration** (extends existing SlackNotifier from V4 B1):
- Use Slack Block Kit with interactive buttons:
  ```json
  {
    "blocks": [
      {"type": "header", "text": "⚠️ FinSight AI — Action Requires Approval"},
      {"type": "section", "text": "Model: lending_club_v1\nRegime: black_swan\nAction: HALT automated decisions\nConfidence: 0.98"},
      {"type": "section", "text": "Impact: $3.2M–$4.8M exposure"},
      {"type": "actions", "elements": [
        {"type": "button", "text": "✅ Approve", "action_id": "approve_action", "value": "req_123", "style": "primary"},
        {"type": "button", "text": "❌ Reject", "action_id": "reject_action", "value": "req_123", "style": "danger"}
      ]}
    ]
  }
  ```
- Slack interactivity webhook: `POST /webhooks/slack/interact` — receives button clicks, updates ApprovalQueue status
- Use `response_url` from Slack payload to update the original message with the decision result (already familiar pattern from Sentinel hackathon)

**Telegram integration:**
- Telegram Bot API with inline keyboard buttons
- `POST /webhooks/telegram` — receives callback queries
- Similar flow: message with Approve/Reject inline buttons → callback updates ApprovalQueue

**Dashboard component:**
- `ApprovalQueue.tsx` — table showing pending/approved/rejected actions
- Live polling or SSE for status updates
- Manual approve/reject buttons in the UI as fallback (if Slack/Telegram not configured)

**Agent integration:**
- In `brain.py`, after producing a recommendation:
  ```python
  if result.action in ("halt", "retrain", "freeze", "escalate"):
      approval = create_approval_request(model_id, result)
      await fire_approval_notification(approval)  # Slack or Telegram
      result.requires_approval = True
      result.approval_id = approval.id
  ```

**New files:**
- `driftguard/store/database.py` — add `ApprovalQueue` table
- `driftguard/api/routes/approvals.py` — CRUD for approval queue + webhook endpoints
- `finsight/notifications/approval_notifier.py` — Slack/Telegram approval message builder
- `dashboard/src/components/ApprovalQueue.tsx` — queue UI
- `dashboard/src/pages/ApprovalsView.tsx` — dedicated approvals page

**Effort:** 1.5 days

---

### S3. LLM-as-Judge Evals in Phoenix

**Why:** Arize explicitly lists "Run evaluations on your traces with LLM-as-a-Judge or code evals to demonstrate quality" as a requirement.

**How:**
- Install: `pip install arize-phoenix-evals`
- Create evaluator in `finsight/evals/governance_eval.py`:
  ```python
  from phoenix.evals import llm_classify

  # Eval 1: Was the regime classification correct?
  regime_eval_template = """
  Given these macro signals: VIX={vix}, Credit Spread={spread}, Yield Curve={yield_curve}
  The agent classified the regime as: {regime}
  Was this classification correct? Answer: correct or incorrect.
  """

  # Eval 2: Was the recommended action appropriate for the regime?
  action_eval_template = """
  Regime: {regime}
  Agent recommended: {action}
  Rule: black_swan → halt, credit_stress → monitor, stable+drift → retrain
  Was this action appropriate? Answer: correct or incorrect.
  """
  ```
- Run evals after each demo scenario completes
- Results appear in Phoenix Cloud under the Experiments tab
- Judges can see: "13 drift runs evaluated, 12/13 correct actions, 1 edge case flagged"

**Effort:** 4 hours

---

### S4. Dashboard Demo Panel (A3 from V4 — if not already done)

**Why:** Judges clicking buttons and seeing live results wins the Design criterion.

**Already specified in V4 build plan section A3.** If this shipped in Session 2, skip. If not, prioritize it.

**Effort:** 6 hours (4 frontend + 2 backend)

---

### S5. HALT Overlay (A1 from V4 — if not already done)

**Why:** The single most powerful demo moment. Screen goes red → judges understand the product in 2 seconds.

**Already specified in V4 build plan section A1.** If this shipped in Session 1, skip. If not, prioritize it.

**Effort:** 3 hours

---

## 7. New Dependencies (V5)

```
# Cloud + DB
psycopg2-binary>=2.9.0          # Supabase Postgres driver

# ADK + Instrumentation
google-adk>=2.0.0               # Google ADK 2.0
google-genai>=1.0.0             # Gemini SDK
openinference-instrumentation-google-adk>=0.1.10
openinference-instrumentation>=0.1.0
arize-phoenix-evals>=0.1.0      # LLM-as-Judge evals

# Already in requirements (verify versions)
arize-phoenix-otel>=0.16.0
arize-phoenix-client>=2.4.0
```

---

## 8. Environment Variables (V5)

```env
# ── Database ──────────────────────────────────────────────
DATABASE_URL=postgresql+psycopg2://user:pass@db.xxx.supabase.co:5432/postgres

# ── LLM ───────────────────────────────────────────────────
LLM_PROVIDER=gemini
GEMINI_API_KEY=your_gemini_api_key
LLM_REASONING_MODEL=gemini-2.5-pro
LLM_FAST_MODEL=gemini-2.0-flash

# ── Agent Framework ──────────────────────────────────────
AGENT_FRAMEWORK=adk
GOOGLE_GENAI_API_KEY=your_google_genai_api_key

# ── Phoenix Cloud ────────────────────────────────────────
PHOENIX_COLLECTOR_ENDPOINT=https://app.phoenix.arize.com/s/<space>/v1/traces
PHOENIX_API_KEY=your_phoenix_api_key
PHOENIX_PROJECT_NAME=finsight-ai

# ── Phoenix MCP ──────────────────────────────────────────
PHOENIX_MCP_BASE_URL=https://app.phoenix.arize.com/s/<space>
PHOENIX_MCP_API_KEY=your_phoenix_api_key

# ── Notifications ────────────────────────────────────────
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/...
SLACK_SIGNING_SECRET=your_slack_signing_secret
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
TELEGRAM_CHAT_ID=your_chat_id

# ── Macro Data ───────────────────────────────────────────
FRED_API_KEY=your_fred_api_key

# ── API Auth ─────────────────────────────────────────────
API_KEY=your_api_key_for_routes
```

---

## 9. Execution Schedule

### Day 1 — Infrastructure (June 6)
| Time | Task | Item |
|---|---|---|
| Morning | Supabase project + migration | M1 |
| Morning | Phoenix Cloud setup | M2 |
| Afternoon | GCP account + Cloud Run deploy | M6 |
| Afternoon | LICENSE file | M7 |
| Evening | Verify: backend on Cloud Run, traces in Phoenix Cloud | — |

### Day 2 — Gemini + ADK (June 7)
| Time | Task | Item |
|---|---|---|
| Morning | OpenInference auto-instrumentor | M3 |
| Morning | Gemini swap + prompt tuning | M4 |
| Afternoon | ADK wiring (real, not scaffold) | M5 |
| Evening | Verify: demo_full.py --auto passes with Gemini + ADK + Phoenix Cloud | — |

### Day 3 — Self-Improvement + Evals (June 8)
| Time | Task | Item |
|---|---|---|
| Morning | Self-improvement loop tools | S1 |
| Afternoon | LLM-as-Judge eval pipeline | S3 |
| Evening | Run evals, verify results in Phoenix Cloud Experiments tab | — |

### Day 4 — Human Gate + Polish (June 9)
| Time | Task | Item |
|---|---|---|
| Morning | ApprovalQueue DB + API routes | S2 |
| Afternoon | Slack/Telegram approval buttons + webhook handlers | S2 |
| Evening | Dashboard ApprovalQueue component | S2 |

### Day 5 — Video + Submission (June 10)
| Time | Task | Item |
|---|---|---|
| Morning | Record demo video | M8 |
| Afternoon | Edit video (one pass, keep it raw and technical) | M8 |
| Evening | Devpost submission form | M10 |

### Buffer Day (June 11 — deadline 2 PM PDT)
- Fix anything broken
- Final deploy + smoke test
- Submit by noon

---

## 10. Risk Register

| Risk | Impact | Mitigation |
|---|---|---|
| ADK + Gemini integration fails | Can't demo ADK multi-agent | Keep `AGENT_FRAMEWORK=native` as fallback. Use `google-genai` SDK directly with OpenInference instrumentor instead of ADK |
| Supabase connection from Cloud Run is slow | Slow API responses | Supabase and Cloud Run both in us-central1. Add connection pooling if needed |
| Gemini prompt output differs from Groq | Agent responses wrong structure | Budget 2–3 hours for prompt tuning. Keep response parsing flexible |
| Phoenix Cloud free tier rate limits | Traces drop during demo | Free tier is 10 GiB — more than enough. Rate limits are generous for single-user |
| Slack interactivity requires public URL | Can't receive button clicks locally | Cloud Run URL is public. Use ngrok for local dev testing |
| GCP free credits expire | Deployment dies | $300 lasts 90 days. Hackathon is 5 days. Not a concern |
| FRED API is slow/down during demo | Macro fetch blocks | V4 C5 already moved macro fetch to background thread. Cached values serve as fallback |

---

## 11. What We're NOT Doing (Scope Control)

These are explicitly out of scope for V5. Don't touch them.

- ❌ PostgreSQL migration to GCP Cloud SQL (Supabase is simpler and faster)
- ❌ Model version registry (V4 B5 — nice but not a judging criterion)
- ❌ Docker compose full stack (V4 C6 — Cloud Run replaces this)
- ❌ Recession classifier fix (V5 is about submission, not ML accuracy)
- ❌ Frontend redesign (existing dashboard + V4 visual work is sufficient)
- ❌ PyPI packaging (post-hackathon)
- ❌ Multi-model monitoring (single model demo is sufficient)

---

## 12. Submission Checklist (June 11)

- [ ] Live Cloud Run URL works — `/health` returns OK
- [ ] Dashboard on Vercel — loads and connects to Cloud Run backend
- [ ] Phoenix Cloud — traces visible at `app.phoenix.arize.com`
- [ ] `demo_full.py --auto` passes with Gemini + ADK
- [ ] 3 demo scenarios produce correct regime labels
- [ ] Agent chat returns structured recommendations
- [ ] Trust API returns correct TrustScore
- [ ] PDF report generates with cover page
- [ ] Self-improvement eval results visible in Phoenix Experiments
- [ ] Slack/Telegram approval buttons work
- [ ] GitHub repo public with MIT LICENSE visible
- [ ] Demo video uploaded (YouTube unlisted or Loom)
- [ ] Devpost form complete — Arize track selected

---

*FinSight AI V5 Build Plan — June 2026*  
*Built on V4 (in progress)*  
*Target: Arize track winner — Google Cloud Rapid Agent Hackathon*