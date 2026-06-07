# V5 Setup Checklist — Keys, Config, and Verification

## Keys Status

| What | Status | Note |
|---|---|---|
| FRED API key | done | working |
| Groq API key | done | working (dev fallback) |
| Gemini API key | **BROKEN** | key format wrong — starts with `AQ.` not `AIza.` — needs replacement |
| Phoenix space | done | slug `himanshu290304` set in .env |
| Phoenix API key | **MISSING** | get from app.phoenix.arize.com → Settings → API Keys, then set `PHOENIX_API_KEY` and `PHOENIX_MCP_API_KEY` |
| Supabase DB | **BROKEN** | host `db.ollauqzcliuclhxsacra.supabase.co` can't resolve — get new connection string from Supabase dashboard → Project Settings → Database → URI tab (pooler URL) |
| GCP | on hold | will add later |
| Slack | on hold | — |
| Telegram | on hold | — |

---

## What Needs Fixing Now

### 1 — Gemini API Key (blocks everything)

Current key starts with `AQ.` — that is not a valid Gemini API key format. Valid keys start with `AIza`.

1. Go to https://aistudio.google.com
2. Click **Get API key** → **Create API key**
3. Copy the new key (starts with `AIza...`)
4. In `.env` replace both:
   ```
   GEMINI_API_KEY=AIza...
   GOOGLE_GENAI_API_KEY=AIza...   # same key
   ```

### 2 — Supabase Connection String

The host in `.env` doesn't resolve. Supabase changed their connection format.

1. Go to https://supabase.com → your `finsight-ai` project
2. **Project Settings → Database → Connection string → URI tab**
3. Copy the pooler URL — looks like:
   `postgresql://postgres.ollauqzcliuclhxsacra:[password]@aws-0-us-east-1.pooler.supabase.com:6543/postgres`
4. In `.env` update `DATABASE_URL` — prefix must be `postgresql+psycopg2://...`:
   ```
   DATABASE_URL=postgresql+psycopg2://postgres.ollauqzcliuclhxsacra:financialdriftguard@aws-0-us-east-1.pooler.supabase.com:6543/postgres
   ```

### 3 — Phoenix API Key (blocks tracing)

`PHOENIX_API_KEY` is blank — tracing won't connect.

1. Go to https://app.phoenix.arize.com/s/himanshu290304
2. **Settings → API Keys** → Create a key
3. In `.env` set:
   ```
   PHOENIX_API_KEY=<key>
   PHOENIX_MCP_API_KEY=<key>   # same key
   ```

---

## After Fixes — Run These in Order

```bash
# 1. DB connects
python -c "
from dotenv import load_dotenv; load_dotenv()
from driftguard.store.database import create_db
create_db()
print('DB ok')
"

# 2. Gemini responds
python -c "
from dotenv import load_dotenv; load_dotenv()
import os, google.genai as genai
client = genai.Client(api_key=os.getenv('GEMINI_API_KEY'))
r = client.models.generate_content(model='gemini-2.0-flash', contents='Say: OK')
print(r.text)
"

# 3. Backend starts
uvicorn driftguard.api.main:app --reload
# then open http://localhost:8000/health

# 4. Seed demo data
python demo/lending_club.py

# 5. Full demo
python scripts/demo_full.py --auto

# 6. ADK agent + tracing
python -c "
import os; os.environ['LLM_PROVIDER']='gemini'; os.environ['AGENT_FRAMEWORK']='adk'
from dotenv import load_dotenv; load_dotenv()
from finsight.tracing.setup import init_tracing
init_tracing()
from finsight.agent.brain import DriftGuardAgent
agent = DriftGuardAgent()
result = agent.analyze('lending_club_v1')
print('Action:', result.action)
print('Confidence:', result.confidence)
"
# then check https://app.phoenix.arize.com/s/himanshu290304 for traces
```

---

## On Hold

- GCP / Cloud Run deploy — add project ID and gcloud auth when ready
- Slack webhook + signing secret
- Telegram bot token + chat_id
- Frontend deploy to Vercel (depends on Cloud Run URL)
