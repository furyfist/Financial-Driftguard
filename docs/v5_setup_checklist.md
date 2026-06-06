# V5 Setup Checklist — Keys, Config, and Verification

This document tells you exactly what to get, where to put it, and how to
verify the full system works end to end.

---

## Part 1 — Get the Keys

Work through these in order. Each one unlocks the next.

---

### Step 1 — Gemini API Key (required — blocks everything)

1. Go to https://aistudio.google.com
2. Sign in with a Google account
3. Click **Get API key** → **Create API key**
4. Copy the key (starts with `AIza...`)

This key is used for both `GEMINI_API_KEY` and `GOOGLE_GENAI_API_KEY`.

---

### Step 2 — Phoenix Cloud (required — Arize track criterion)

1. Go to https://app.phoenix.arize.com
2. Sign up for a free account (10 GiB storage, no credit card)
3. Create a new **Space** — name it `finsight-ai`
4. Go to **Settings → API Keys** → Create a key
5. Note your **space slug** from the URL: `app.phoenix.arize.com/s/<space-slug>`

You need: space slug + API key.

---

### Step 3 — Supabase (required — cloud deploy)

1. Go to https://supabase.com
2. Sign up / log in → **New project**
3. Name: `finsight-ai` | Region: US East (or closest to you)
4. Set a database password — save it
5. Go to **Project Settings → Database**
6. Find **Connection string (URI)** under the **URI** tab
7. Copy it — looks like: `postgresql://postgres.[ref]:[password]@aws-0-us-east-1.pooler.supabase.com:6543/postgres`
8. Replace `[YOUR-PASSWORD]` with your password

You need: the full connection URI.

---

### Step 4 — GCP (required — live hosted URL)

1. Go to https://console.cloud.google.com
2. Sign up — you get **$300 free credits for 90 days**
3. Create a new project — name it `finsight-ai`
4. Enable the following APIs (search each in the console):
   - **Cloud Run API**
   - **Cloud Build API**
   - **Artifact Registry API**
5. Install the gcloud CLI: https://cloud.google.com/sdk/docs/install
6. Run: `gcloud auth login` then `gcloud config set project finsight-ai`

You need: project ID confirmed + gcloud CLI authenticated.

---

### Step 5 — Slack (optional but highly recommended for judging)

1. Go to https://api.slack.com/apps → **Create New App → From scratch**
2. Name: `FinSight AI` | Pick your workspace
3. Go to **Incoming Webhooks** → turn on → **Add New Webhook to Workspace**
4. Pick a channel (e.g. `#finsight-approvals`) → copy the webhook URL
5. Go to **Interactivity & Shortcuts** → turn on
6. Set **Request URL** to: `https://<your-cloud-run-url>/webhooks/slack/interact`
7. Go to **Basic Information** → copy **Signing Secret**

You need: webhook URL + signing secret.

---

### Step 6 — Telegram (optional)

1. Open Telegram → search for `@BotFather`
2. Send `/newbot` → follow prompts → copy the **bot token**
3. Start a conversation with your bot, then run:
   `curl https://api.telegram.org/bot<TOKEN>/getUpdates`
4. Send a message to the bot, re-run the curl — copy your **chat_id** from the response

You need: bot token + chat_id.

---

## Part 2 — Update .env

Open `.env` in the project root and update these values.
Everything already set (FRED, GROQ) can stay as-is during dev.

```env
# ── Database ──────────────────────────────────────────────
DATABASE_URL=postgresql+psycopg2://postgres.[ref]:[password]@aws-0-us-east-1.pooler.supabase.com:6543/postgres

# ── LLM ───────────────────────────────────────────────────
LLM_PROVIDER=gemini
GEMINI_API_KEY=AIza...
LLM_REASONING_MODEL=gemini-2.5-pro
LLM_FAST_MODEL=gemini-2.0-flash

# ── ADK ───────────────────────────────────────────────────
AGENT_FRAMEWORK=adk
GOOGLE_GENAI_API_KEY=AIza...     # same key as GEMINI_API_KEY

# ── Phoenix Cloud ─────────────────────────────────────────
PHOENIX_COLLECTOR_ENDPOINT=https://app.phoenix.arize.com/s/<space-slug>/v1/traces
PHOENIX_API_KEY=<your-phoenix-api-key>
PHOENIX_PROJECT_NAME=finsight-ai
PHOENIX_MCP_BASE_URL=https://app.phoenix.arize.com/s/<space-slug>
PHOENIX_MCP_API_KEY=<your-phoenix-api-key>

# ── Slack (optional) ──────────────────────────────────────
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/...
SLACK_SIGNING_SECRET=<your-signing-secret>

# ── Telegram (optional) ───────────────────────────────────
TELEGRAM_BOT_TOKEN=<your-bot-token>
TELEGRAM_CHAT_ID=<your-chat-id>

# ── API auth ──────────────────────────────────────────────
API_KEY=pick-any-secret-string
```

---

## Part 3 — Install Dependencies

```bash
pip install -r requirements.txt
```

Verify V5 packages installed:

```bash
python -c "import psycopg2; print('psycopg2 ok')"
python -c "import openinference.instrumentation; print('openinference ok')"
```

---

## Part 4 — Verify Locally (Before Cloud Deploy)

Run these checks in order. Stop and fix if one fails before moving on.

---

### Check 1 — Env smoke test

```bash
python scripts/demo_full.py --smoke
```

Expected: all 10 checks pass. If any fail, the output tells you exactly which var is missing.

---

### Check 2 — Database connects

```bash
python -c "
from driftguard.store.database import create_db
create_db()
print('DB ok — tables created')
"
```

For Supabase: go to your Supabase dashboard → **Table Editor** — you should see
`modelrecord`, `driftrun`, `approvalqueue`, etc. created automatically.

---

### Check 3 — Backend starts

```bash
uvicorn driftguard.api.main:app --reload
```

Open http://localhost:8000/health — should return `{"status": "ok", "version": "0.2.0"}`.

Open http://localhost:8000/docs — FastAPI docs should list all routes including `/approvals`.

---

### Check 4 — Seed demo data

In a second terminal:

```bash
python demo/lending_club.py
```

Expected: prints model created, baseline set, drift runs seeded.

---

### Check 5 — Run demo scenarios

```bash
python scripts/demo_full.py --auto
```

Expected: all 3 scenarios print PASSED. Each scenario creates drift runs in the DB.

---

### Check 6 — Gemini agent call

```bash
python -c "
import os
os.environ['LLM_PROVIDER'] = 'gemini'
os.environ['AGENT_FRAMEWORK'] = 'native'  # test Gemini without ADK first
from finsight.agent.brain import DriftGuardAgent
agent = DriftGuardAgent()
result = agent.analyze('lending_club_v1')
print('Action:', result.action)
print('Confidence:', result.confidence)
print('Recommendation:', result.recommendation[:100])
"
```

Expected: prints a valid action (monitor/investigate/retrain/freeze/escalate) with confidence 0.0–1.0.

---

### Check 7 — ADK agent call

```bash
python -c "
import os
os.environ['LLM_PROVIDER'] = 'gemini'
os.environ['AGENT_FRAMEWORK'] = 'adk'
from finsight.tracing.setup import init_tracing
init_tracing()
from finsight.agent.brain import DriftGuardAgent
agent = DriftGuardAgent()
result = agent.analyze('lending_club_v1')
print('Framework: adk')
print('Action:', result.action)
print('Confidence:', result.confidence)
"
```

Expected: same as Check 6 but routed through ADK multi-agent chain.

---

### Check 8 — Traces visible in Phoenix Cloud

After running Check 7, open https://app.phoenix.arize.com — go to your space.
You should see the `finsight-ai` project with traces from the agent run.

Click a trace — you should see the span tree:
`governance_agent` → `analyst_agent` → tool calls → LLM calls.

---

### Check 9 — Approval gate fires

Run a scenario that triggers a high-risk action:

```bash
python -c "
import os
os.environ['LLM_PROVIDER'] = 'gemini'
os.environ['AGENT_FRAMEWORK'] = 'native'
from finsight.agent.brain import DriftGuardAgent
agent = DriftGuardAgent()
result = agent.ask('There is a black swan event. What should I do?', model_id='lending_club_v1')
print('Action:', result.action)
print('Requires approval:', result.requires_approval)
print('Approval ID:', result.approval_id)
"
```

Then check: http://localhost:8000/approvals — should show the pending approval item.

If Slack is configured: check your Slack channel for the Block Kit message with Approve/Reject buttons.

---

### Check 10 — Dashboard loads

```bash
cd dashboard && npm install && npm run dev
```

Open http://localhost:5173

Verify:
- Overview page shows the lending_club_v1 model
- Model detail page shows drift runs and regime badge
- `/agent` page — type a question, get a structured response card
- `/approvals` page — shows the pending approval from Check 9

---

### Check 11 — LLM-as-Judge evals

```bash
python -c "
from finsight.evals.governance_eval import run_evals
results = run_evals(model_id='lending_club_v1')
print('Total evaluated:', results['total_evaluated'])
print('Accuracy:', results['accuracy'])
print('Pushed to Phoenix:', 'experiment_name' in results)
"
```

Expected: prints eval counts. Check Phoenix Cloud → Experiments tab for the results.

---

## Part 5 — Cloud Run Deploy

Once all local checks pass:

```bash
gcloud run deploy finsight-ai \
  --source . \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars "DATABASE_URL=<supabase-url>,GEMINI_API_KEY=<key>,GOOGLE_GENAI_API_KEY=<key>,LLM_PROVIDER=gemini,AGENT_FRAMEWORK=adk,PHOENIX_COLLECTOR_ENDPOINT=<endpoint>,PHOENIX_API_KEY=<key>,PHOENIX_PROJECT_NAME=finsight-ai,FRED_API_KEY=<key>,API_KEY=<your-api-key>"
```

After deploy:
- Copy the Cloud Run URL (looks like `https://finsight-ai-xxxx-uc.a.run.app`)
- Test: `curl https://finsight-ai-xxxx-uc.a.run.app/health`

---

## Part 6 — Frontend Deploy to Vercel

1. Go to https://vercel.com → New Project → import from GitHub
2. Set root directory to `dashboard`
3. Add environment variable: `VITE_API_URL=https://finsight-ai-xxxx-uc.a.run.app`
4. Deploy

After deploy: open the Vercel URL, verify it loads and connects to Cloud Run.

Update Slack **Request URL** to: `https://finsight-ai-xxxx-uc.a.run.app/webhooks/slack/interact`

---

## Part 7 — Final Submission Smoke Test

Run this after everything is deployed:

```bash
curl https://finsight-ai-xxxx-uc.a.run.app/health
curl https://finsight-ai-xxxx-uc.a.run.app/models/
curl https://finsight-ai-xxxx-uc.a.run.app/approvals
```

All should return JSON, no 500s.

Open the Vercel dashboard URL — confirm it loads real data from Cloud Run.

Open Phoenix Cloud — confirm recent traces are flowing in.

---

## Summary — What You Need Before You Can Run

| What | Where to get it | Time |
|---|---|---|
| Gemini API key | aistudio.google.com | 2 min |
| Phoenix Cloud account + API key + space slug | app.phoenix.arize.com | 10 min |
| Supabase project + connection string | supabase.com | 10 min |
| GCP account + gcloud CLI | console.cloud.google.com | 20 min |
| Slack webhook + signing secret | api.slack.com/apps | 10 min |
| Telegram bot token + chat_id | @BotFather in Telegram | 5 min |

Total setup time before first full run: ~1 hour.
