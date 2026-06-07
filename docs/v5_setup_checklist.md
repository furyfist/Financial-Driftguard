# V5 Setup Checklist

## Keys Status

| What | Status | Note |
|---|---|---|
| FRED API key | done | working |
| Groq API key | done | working |
| Phoenix space slug | done | `himanshu290304` set in .env |
| Phoenix API key | **MISSING** | get from app.phoenix.arize.com → Settings → API Keys |
| Supabase DB | **MISSING** | get pooler URL from Supabase dashboard → Project Settings → Database → URI tab |
| GCP | on hold | not needed — deploying to Railway |
| Slack | on hold | — |
| Telegram | on hold | — |

---

## What Needs Fixing Before You Can Run

### 1 — Supabase connection string

Get the pooler URL from Supabase (not the direct `db.xxx` URL — that doesn't resolve).

1. Supabase dashboard → your project → **Project Settings → Database → URI tab**
2. Copy the pooler connection string (contains `pooler.supabase.com:6543`)
3. In `.env` update `DATABASE_URL`:
   ```
   DATABASE_URL=postgresql+psycopg2://postgres.<ref>:financialdriftguard@aws-0-us-east-1.pooler.supabase.com:6543/postgres
   ```

### 2 — Phoenix API key

1. Go to https://app.phoenix.arize.com/s/himanshu290304
2. **Settings → API Keys** → Create a key
3. In `.env` set:
   ```
   PHOENIX_API_KEY=<key>
   PHOENIX_MCP_API_KEY=<key>
   ```

---

## Run Order (Local)

```bash
# 1. Check all connections
python scripts/check_connections.py

# 2. Create DB tables
python -c "from dotenv import load_dotenv; load_dotenv(); from driftguard.store.database import create_db; create_db(); print('DB ok')"

# 3. Start backend
uvicorn driftguard.api.main:app --reload
# verify: http://localhost:8000/health

# 4. Seed demo data (in a second terminal)
python demo/lending_club.py

# 5. Run demo scenarios
python scripts/demo_full.py --auto

# 6. Test agent tool loop
python scripts/test_agent.py

# 7. Run evals
python scripts/run_evals.py

# 8. Start frontend
cd dashboard && npm install && npm run dev
# verify: http://localhost:5173
```

---

## Deploy Order

### Railway (backend)

1. Push this branch to GitHub
2. Railway dashboard → New Project → Deploy from GitHub repo
3. Set all env vars from `railway-env.example`
4. Railway auto-builds from `Dockerfile` and deploys
5. Verify: `curl https://<railway-url>/health`
6. Seed data against Railway: edit `demo/lending_club.py` BASE to Railway URL, run it

### Vercel (frontend)

1. Vercel dashboard → New Project → import from GitHub
2. Set **Root Directory** to `dashboard`
3. Add env vars:
   - `VITE_API_URL` = `https://<railway-url>`
   - `VITE_API_KEY` = same value as `API_KEY` in Railway
4. Deploy
5. Update `FRONTEND_URL` in Railway env vars to the Vercel URL (for CORS)

---

## Final Smoke Test

Run after both services are deployed:

```bash
# Set your URLs
RAILWAY_URL=https://<your-app>.railway.app
VERCEL_URL=https://<your-app>.vercel.app

# Backend health
curl $RAILWAY_URL/health
curl $RAILWAY_URL/models/
curl $RAILWAY_URL/approvals -H "X-API-Key: <your-api-key>"

# Agent responds
curl -X POST $RAILWAY_URL/agent/ask \
  -H "Content-Type: application/json" \
  -H "X-API-Key: <your-api-key>" \
  -d '{"query": "What is the current drift status?", "model_id": "lending_club_v1"}'
```

Then open `$VERCEL_URL` — confirm Overview, ModelDetail, Agent, Approvals all load.
Open Phoenix → confirm traces from Railway agent calls are flowing in.

---

## On Hold

- Slack webhook + signing secret
- Telegram bot token + chat_id
- GCP (not needed — using Railway)
