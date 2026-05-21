# FinSight AI — V4 Session Execution Plan

**Document type:** Session-by-session build guide  
**Parent plan:** [v4_build_plan.md](v4_build_plan.md)  
**Sessions:** 5  
**Date:** May 2026

---

## Overview

Each session is scoped to one area of concern to keep context tight. Sessions map directly to the checkpoint structure in `v4_build_plan.md` section 7.

---

## Session 1 — Foundation & Visual Core

**Checkpoint target:** CP1 + auth + quick fixes  
**Effort estimate:** ~11h  
**Files in play:** backend auth middleware, DB migration, `HaltOverlay.tsx`, `DriftChart.tsx`

| Item | Spec section | Notes |
|---|---|---|
| C4 — Section 7 prose count fix | §6 C4 | 30 min warm-up |
| C2 — API Key authentication | §6 C2 | Middleware only, contained |
| C3 — Phoenix trace ID linkage | §6 C3 | One new DB column + agent plumbing |
| A1 — HALT overlay | §4 A1 | New component `HaltOverlay.tsx` |
| A2 — Drift score chart | §4 A2 | New component `DriftChart.tsx` |

**Kickoff prompt:**
> "We're starting V4 Session 1. Goal: ship C4 (section 7 fix), C2 (API auth middleware), C3 (Phoenix trace ID on DriftRun), A1 (HALT overlay), A2 (drift chart with regime bands). Read docs/versions/plan/v4_build_plan.md sections 4 and 6 for spec. Start with C4 then C2."

---

## Session 2 — Demo Polish

**Checkpoint target:** CP2  
**Effort estimate:** ~11h  
**Files in play:** frontend components, `POST /demo/scenarios/{name}` endpoint, `finsight/reports/generator.py`

| Item | Spec section | Notes |
|---|---|---|
| A3 — Demo scenario control panel | §4 A3 | 4h frontend + 2h backend endpoint |
| A4 — Agent chat structured cards | §4 A4 | New `AgentResponseCard.tsx` + suggestion chips |
| A5 — PDF cover page | §4 A5 | Modify `generator.py`, insert before Section 1 |

**Kickoff prompt:**
> "V4 Session 2. Session 1 is complete (auth, trace ID, HALT overlay, drift chart). Goal now: A3 (demo panel + `/demo/scenarios` endpoint), A4 (agent chat cards), A5 (PDF cover page). Spec in v4_build_plan.md sections 4 and 5. Start with the backend endpoint for A3, then frontend."

---

## Session 3 — Intelligence & Notifications

**Checkpoint target:** CP3 + CP4 (partial)  
**Effort estimate:** ~5 days  
**Files in play:** `brain.py`, new agent tools, notifier adapters, APScheduler jobs

| Item | Spec section | Notes |
|---|---|---|
| B1 — Slack/email alerts | §5 B1 | Enrich `SlackNotifier` + new `EmailNotifier` + wire into `brain.py` |
| B3 — Explainable drift | §5 B3 | New tool + `feature_metadata.py` + expandable UI in `ActionCard.tsx` |
| B4 — Weekly digest | §5 B4 | `DigestGenerator` + APScheduler job — reuses B1 notification stack |

**Build order within session:** B1 → B3 → B4 (B4 depends on B1 notifier infrastructure)

**Kickoff prompt:**
> "V4 Session 3. Sessions 1–2 done (visual polish, demo panel, PDF cover). Goal: B1 (Slack/email alerts with regime context), B3 (explainable drift tool + feature metadata), B4 (weekly digest scheduler). All three are backend-heavy. Spec in v4_build_plan.md section 5. Start with B1 enricher since B4 depends on it."

---

## Session 4 — ADK Migration + Natural Language Query + Tech Debt

**Checkpoint target:** CP4 + CP5 (core)  
**Effort estimate:** ~8 days  
**Files in play:** new `finsight/adk/` module, `query_tools.py`, assorted debt items

| Item | Spec section | Notes |
|---|---|---|
| C1 — Google ADK 2.0 migration | §6 C1 | New `finsight/adk/` dir, `AGENT_FRAMEWORK` config switch, native path stays intact |
| B2 — Natural language drift query | §5 B2 | New `query_tools.py` tool + query params on `/drift/{id}/history` |
| C5 — V2 tech debt cleanup | §6 C5 | 6 items — do in order: webhook persistence → dedup → scheduler health → async macro → env validation → row validation |

**Risk note:** ADK 2.0 is new — if it causes friction, finish B2 + C5 first. The `AGENT_FRAMEWORK=native` fallback means ADK never blocks anything.

**Kickoff prompt:**
> "V4 Session 4. Sessions 1–3 done (all visual, notifications, explainable drift, digest). Goal: C1 (Google ADK 2.0 — additive, keep native fallback), B2 (NL drift query tool + API params), C5 (6 tech debt items). Spec in v4_build_plan.md sections 5 and 6. Start with ADK since it's the riskiest — scaffold `finsight/adk/` first, wire `AGENT_FRAMEWORK` switch, then move to B2."

---

## Session 5 — Version Registry + Docker + Finish Line

**Checkpoint target:** CP6 + C6  
**Effort estimate:** ~5 days  
**Files in play:** DB schema migration, 4 new API routes, frontend version selector, Dockerfiles

| Item | Spec section | Notes |
|---|---|---|
| B5 — Model version registry | §5 B5 | Schema migration → 4 API routes → version selector in `ModelDetail.tsx` |
| C6 — Docker compose full stack | §6 C6 | `Dockerfile` (backend), `dashboard/Dockerfile`, updated `docker-compose.yml` |

**Build order within session:** B5 DB migration → B5 API → B5 frontend → C6 (Docker is packaging, always last)

**Kickoff prompt:**
> "V4 Session 5 — final session. Sessions 1–4 done (all features except version registry and Docker). Goal: B5 (ModelVersion schema + 4 API routes + version selector in dashboard) and C6 (full Docker compose). Spec in v4_build_plan.md sections 5 and 6. Start with B5 DB migration, then API, then frontend, then Docker last since it's packaging."

---

## Summary

| Session | Theme | Items | Risk |
|---|---|---|---|
| 1 | Foundation + Visual Core | C4, C2, C3, A1, A2 | Low |
| 2 | Demo Polish | A3, A4, A5 | Low |
| 3 | Notifications + Intelligence | B1, B3, B4 | Medium |
| 4 | ADK + NL Query + Debt | C1, B2, C5 | High |
| 5 | Registry + Docker | B5, C6 | Medium |

---

*FinSight AI V4 Session Plan — May 2026*  
*Companion to [v4_build_plan.md](v4_build_plan.md)*
