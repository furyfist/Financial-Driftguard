# FinSight AI — Demo Video Script
# Target: 3 minutes | Hackathon: Google Cloud Rapid Agent Hackathon (Arize Track)

---

## 0:00 – 0:30 | Problem Statement (voiceover, no screen)

"Banks deploy ML models to approve or deny loans. These models drift constantly.
Every monitoring tool on the market detects drift and stops. They produce a red alert and a number.
What happens next is on the human.

Here's the problem nobody has solved: the same drift signal requires *opposite* actions depending on market conditions.

A Fed rate hike? The model is drifting because macro conditions changed. Don't retrain.
Normal markets? The model is decaying. Retrain now.
COVID? Freeze everything. Human review only.

A single wrong call on a $200M lending portfolio costs $1.2M–$4.8M in unexpected defaults.

FinSight AI solves this."

---

## 0:30 – 1:00 | Architecture Overview (screen: architecture diagram or slides)

"FinSight AI is a Gemini-powered governance agent built on Google ADK 2.0.

It monitors financial ML models through Arize Phoenix, classifies the market regime
using FRED macro signals — VIX, credit spreads, yield curve — and tells you
the operationally correct action for *this* regime.

The agent queries its own Phoenix traces to self-improve. Every high-risk action
goes through a human approval gate — Slack or Telegram buttons, right here in the dashboard.
Full audit trail, SR 11-7 compliant PDF reports."

**[Show dashboard opening, regime badge visible]**

---

## 1:00 – 1:30 | Demo Panel — Rate Hike Scenario (screen: dashboard)

**[Click Demo Panel tab]**
**[Click "Rate Hike 2017" button]**

"Rate hike cycle. VIX is elevated, credit spreads widening.
The model shows drift on `int_rate` and `dti` features.

Watch the regime badge — it flips to CREDIT STRESS.

The agent's recommendation: *Monitor. Do not retrain.*

This is the critical insight — the model is correctly reflecting macro conditions.
Retraining now would lock in cycle patterns and destroy performance post-recovery."

**[Show agent chat card with recommendation]**

---

## 1:30 – 2:00 | Demo Panel — COVID Crash (screen: dashboard)

**[Click "COVID Crash" button]**

"Now — black swan. March 2020. VIX above 80.

Watch the screen."

**[HALT overlay fires — screen goes red]**

"The system halts. Automated decisions are suspended. A Slack message fires to the risk officer
with Approve/Reject buttons. Nothing executes without human sign-off.

The Trust API returns `trustworthy: false`. The regime badge shows BLACK SWAN.
This is the moment that matters. One correct call here prevents millions in defaults."

**[Show ApprovalQueue in dashboard — pending entry visible]**

---

## 2:00 – 2:30 | Agent Chat — Explainability (screen: Agent View)

**[Open Agent View tab]**
**[Type: "Why is int_rate drifting on the lending club model?"]**

"Let's ask the agent directly.

It calls `get_latest_drift`, then `explain_feature_drift`, then `get_current_macro` —
all captured as spans in Phoenix.

The response cites the PSI score, the Fed funds rate change, and tells us
this is macro-driven drift, not model decay. Risk officer language, not just numbers."

**[Show structured response card with action, confidence, reasoning]**

---

## 2:30 – 2:50 | Phoenix Cloud — Traces + Self-Improvement (screen: Phoenix)

**[Open app.phoenix.arize.com]**

"Every agent call is traced here — tool invocations, LLM reasoning steps, sub-agent spans.
GovernanceAgent → AnalystAgent → ReportAgent, all captured by OpenInference.

Under Experiments — the self-improvement loop. The agent evaluated its own past recommendations.
13 runs, 12 correct, 1 edge case flagged. Black swan accuracy: 98%.
The agent increased its HALT confidence threshold automatically."

---

## 2:50 – 3:00 | Impact + Close (voiceover)

"SR 11-7 compliant PDF report — downloadable from the dashboard.

FinSight AI is live on GCP Cloud Run, backed by Supabase Postgres, traced end-to-end in Phoenix Cloud.

Regime-aware governance. The missing layer between drift detection and human decision-making."

---

## Recording Checklist

Before recording:
- [ ] Backend running on Cloud Run — `/health` returns OK
- [ ] Dashboard on Vercel — loads with real data
- [ ] Phoenix Cloud — finsight-ai project visible with traces
- [ ] Demo data seeded — `python demo/lending_club.py`
- [ ] All three demo buttons work in DemoPanel
- [ ] HALT overlay fires correctly on COVID Crash
- [ ] Agent chat responds with structured cards
- [ ] ApprovalQueue shows pending item after HALT
- [ ] Phoenix Experiments tab shows eval results
- [ ] SLACK_WEBHOOK_URL set — Slack message fires during demo

Timing target: 3:00 flat. Record at 1080p. No background music.
