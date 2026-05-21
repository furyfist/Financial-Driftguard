# Financial DriftGuard – Project Progress Snapshot – March 2026

---

## 1. Project Identity & Core Thesis

Financial DriftGuard is an open-source Python library for monitoring financial ML models in production. Its defining feature is a **regime classifier** that distinguishes genuine market regime changes (rate hikes, recessions, black swan events) from actual model decay — a distinction no horizontal tool like Arize, WhyLabs, or Evidently makes, because they carry no financial domain knowledge.

> Standard monitoring tools treat a model degrading during COVID identically to a model whose feature pipeline broke. Both fire "drift detected — retrain." In financial ML, those are opposite responses. Retraining a credit model during a crisis on crisis data produces a model that fails the moment conditions normalise. DriftGuard separates the signal from the regime.

The thesis is validated on a LightGBM credit default model trained on Lending Club data (2013–2015), deployed through the 2017–2018 Federal Reserve hiking cycle. The system correctly identifies `int_rate` drift as macro-driven (`credit_stress`) rather than model decay, and recommends monitoring over retraining — the operationally correct call.

---

## 2. Current Version & Status

| Property | Value |
|---|---|
| Version | `v0.2.0` |
| Release stage | Pre-release (tagged, not on PyPI) |
| Key claim | 93.9% regime classification accuracy on 30-year walk-forward backtest |
| Python | 3.11+ |
| Backend | FastAPI + SQLite via SQLModel + APScheduler |
| ML | LightGBM (regime classifier), scipy (drift detectors) |
| Data | FRED API + Yahoo Finance (VIX) |
| Frontend | React 18 + Vite + Tailwind CSS v3 + Recharts |
| Notifications | Discord (working), Slack (partial), Telegram (partial) |

---

## 3. Implemented Features – March 2026

| Feature | Status | Notes / Limitations |
|---|---|---|
| **PSI detector** | ✅ Stable | Percentile binning on baseline; epsilon smoothing; 7 unit tests passing |
| **KS test detector** | ✅ Stable | scipy `ks_2samp`; p-value and significance flag surfaced |
| **JS divergence detector** | ✅ Stable | Shared bins; bounded [0,1]; symmetric |
| **BaseDetector interface** | ✅ Stable | Abstract class; input validation; severity mapping |
| **Monitor (Python SDK)** | ✅ Stable | `.check(baseline, current, macro=None)`; multi-detector; lazy regime tagging |
| **DataSnapshot** | ✅ Stable | DataFrame ingestion; numeric-only; NaN-safe per feature |
| **Regime labeller** | ✅ Stable | NBER + VIX + FRED; 4 classes; rate_shock merged into credit_stress |
| **Feature engineering** | ✅ Stable | 33 features; rolling momentum, z-scores, composite stress index |
| **Regime classifier (LightGBM)** | ✅ Working | 93.9% accuracy; walk-forward split; recession recall 0% (known) |
| **RegimeTagger v2** | ✅ Working | ML primary; rule-based fallback if model file missing; backwards compatible |
| **MacroSignalFetcher** | ✅ Working | VIX via yfinance; FRED: BAA10Y, T10Y2Y, DFF, UNRATE; graceful fallback |
| **Live macro scheduler** | ✅ Working | Fetches every 6 hours; caches to `MacroCache` table; runs on startup |
| **Baseline persistence** | ✅ Stable | Parquet blob in SQLite `ModelRecord`; survives server restart |
| **FastAPI backend** | ✅ Working | `/models`, `/drift`, `/alerts` routes; CORS configured; lifespan managed |
| **Drift run API** | ✅ Working | POST trigger; baseline auto-loaded from DB; macro auto-attached |
| **`GET /drift/macro/latest`** | ✅ Working | Returns live VIX, spread, yield curve, regime, confidence |
| **Alert persistence** | ✅ Working | Auto-created on high/critical runs; acknowledge endpoint working |
| **Webhook configure endpoint** | ✅ Working | `POST /alerts/webhooks/configure`; runtime config; no restart needed |
| **Discord notifier** | ✅ Working | Rich embeds; severity colour coding; threshold gating verified |
| **Slack notifier** | ⚠️ Partial | Block Kit format built; not tested against live Slack URL |
| **Telegram notifier** | ⚠️ Partial | MarkdownV2 built; requires manual bot setup; not end-to-end tested |
| **Backtesting engine** | ✅ Working | `BacktestRunner` + `BacktestReport`; 1,756 weekly points; per-regime metrics |
| **Lending Club demo** | ✅ Working | LightGBM AUC 0.69; time-based split; `seed_api()` seeder; end-to-end verified |
| **React dashboard — Overview** | ✅ Working | Model health grid; alert feed; macro panel; live data from API |
| **React dashboard — ModelDetail** | ⚠️ Partial | Summary cards and PSI table work; drift history chart has only one data point |
| **React dashboard — Settings** | ✅ Working | Webhook config UI for Discord/Slack |
| **MacroPanel component** | ✅ Working | Live VIX, spread, yield curve, fed funds; colour-coded status; confidence bar |
| **RegimeBadge component** | ✅ Working | Pulsing dot on non-stable regimes; all 5 regime classes handled |
| **pytest suite** | ✅ Stable | 20/20 passing; PSI, KS, JS, Monitor integration |
| **pyproject.toml** | ✅ Working | `pip install -e .` works; `setuptools.build_meta` backend |

---

## 4. What Works Reliably Right Now

The following components are stable enough to depend on without babysitting:

- **All three drift detectors** — PSI, KS, JS produce consistent, mathematically correct results. Unit test suite covers edge cases including empty arrays, small samples, and identical distributions.
- **Monitor SDK** — `.check()` is the cleanest part of the codebase. Inputs are validated, outputs are typed, regime tagging is optional and lazy.
- **Baseline persistence** — baselines survive server restarts. Verified across multiple stop/start cycles.
- **Regime classifier** — 5/5 key validation tests pass at 1.000 confidence including COVID crash. Walk-forward validation is clean.
- **FastAPI core routes** — `/models/` CRUD, `/drift/{id}/run`, `/drift/{id}/latest`, `/drift/{id}/history`, `/drift/macro/latest` all return correct data.
- **Lending Club demo pipeline** — `python demo/lending_club.py` runs end-to-end without intervention and produces the correct regime label.
- **Live macro fetch** — VIX and most FRED series fetch correctly on startup and every 6 hours. Unemployment has an expected lag.

---

## 5. Known Issues & Pain Points (March 2026)

### Bugs

- **Unemployment always null in live macro** — `UNRATE` from FRED lags 4–6 weeks. Excluded from `is_complete()` as a workaround. Confidence stays at ~0.30 instead of ~0.85 until the next monthly release.
- **Drift score displayed as 4.84 in dashboard after toy data** — PSI binning on 3-row test data produces nonsensical scores. Cleared by deleting the database and re-seeding with real data. No input validation on minimum row count.
- **`drifted_features` count is inflated** — counts detector hits, not unique features. A feature appearing in PSI + KS + JS counts three times. Misleading in the dashboard and API response.
- **Swagger route shadowing** — `/drift/macro/latest` was being matched as `/drift/{model_id}/latest` with `model_id="macro"`. Fixed by reordering routes, but fragile — any new static route under `/drift/` must be placed before the parameterised ones.

### Fragile Systems

- **Scheduler jobs fail silently** — APScheduler catches exceptions internally. A FRED fetch failure logs a warning but does not surface to the API or dashboard. There is no dead-letter queue, no retry logic, and no health endpoint for scheduler state.
- **Notifier registry is in-memory** — webhook configurations registered via `POST /alerts/webhooks/configure` are lost on server restart. No persistence for notification config.
- **`RegimeTagger` file had duplicate class definitions** — V1 code was appended to the bottom of the file during an edit, causing Python to use the last definition (V1) silently. Fixed, but indicates the file edit workflow is risky.

### Missing Safeguards

- **No API authentication** — any client on the network can register models, delete them, set baselines, configure webhooks, or trigger drift checks. No token, no API key, no rate limiting.
- **No minimum sample size validation** — `Monitor.check()` will run on DataSnapshots with 3 rows. Results will be statistically meaningless but no error is raised.
- **No concurrency protection on baseline writes** — two simultaneous `set_as_baseline=true` requests for the same model will both write, with last-write-wins behaviour.

### Performance Concerns

- **Macro fetch blocks server startup** — `fetch_and_cache_macro()` is called synchronously in `restore_baselines_from_db()`. If FRED is slow, the server startup hangs for several seconds.
- **`predict()` in RegimeClassifier repeats a snapshot 100 times** — to satisfy the 63-day rolling warmup, the input row is repeated 100 times and feature engineering is run on the full frame. Wasteful but fast enough to not matter yet (~50ms).
- **SQLite is a single file** — no concurrency, no connection pooling. Adequate for single-user local use; will fail under concurrent load.

### DevEx Issues

- **No Docker setup** — getting started requires Python 3.11 venv, Node 18, a FRED API key, a Kaggle account, and 4 manually downloaded demo files. High friction for a new contributor.
- **Demo data not in git** — `demo/data/` is gitignored. The Kaggle notebook must be run manually to reproduce the demo. No automated download or synthetic fallback.
- **Database must be manually deleted on schema change** — no migration tooling. Adding a column requires `del driftguard.db` and full re-seeding.

### Documentation Gaps

- Telegram setup not documented with working example
- No contribution guide
- No docstrings on `RegimeLabeller`, `BacktestRunner`, or `MacroSignalFetcher`

---

## 6. Recently Completed Work (Last 1–3 Months)

This represents the full V1 → V2 development cycle.

**ML Regime Classifier (the core V2 deliverable)**
Replaced hand-coded VIX/spread thresholds with a LightGBM multi-class classifier trained on 30 years of labelled macro history. Ground truth constructed from NBER recession dates, VIX quantile thresholds, and FRED credit spread series. Walk-forward split enforces zero data leakage. COVID crash (March 2020) classified as `black_swan` at 1.000 confidence despite never appearing in training data.

**Feature engineering pipeline**
33 features engineered from 5 raw macro series: rolling VIX momentum (5d, 21d, 63d), credit spread velocity and momentum, yield curve inversion duration counter, composite stress index (weighted normalised combination of VIX + spread + unemployment), and two cross-signal interaction features.

**Baseline persistence**
Baselines moved from in-memory dictionary to parquet blobs stored in the `ModelRecord` SQLite table. Server restart no longer loses registered baselines. Verified across multiple restart cycles.

**Live macro ingestion**
`MacroSignalFetcher` promoted from a utility class to a scheduled background job. Runs on startup and every 6 hours. Results cached in a new `MacroCache` table. Every drift API run now automatically attaches the latest cached macro snapshot — regime tag populates without caller intervention.

**Backtesting engine**
New `driftguard/backtesting/` module. `BacktestRunner` replays labelled history through the classifier at configurable frequency. `BacktestReport` produces per-regime precision/recall, confusion matrix, misclassification analysis, and key historical period accuracy checks across GFC, COVID, post-COVID, and 2022 hiking cycle periods.

**Webhook notification system**
Three platform adapters built on a common `BaseNotifier` interface. All share configurable severity thresholds, regime and confidence in every payload, and top PSI-sorted features. `POST /alerts/webhooks/configure` enables runtime registration without server restart.

**Dashboard V2**
`MacroPanel` component added to Overview page — live VIX, credit spread, yield curve, fed funds with colour-coded status indicators and ML classifier confidence bar. Settings page added for webhook UI configuration.

---

## 7. Current Technical Debt & Quick Wins

Items estimated at 1–2 days of work each, high reliability or usability impact.

| # | Item | Effort | Impact |
|---|---|---|---|
| 1 | Add minimum row count validation to `DataSnapshot.from_dataframe()` — raise `ValueError` if fewer than 100 rows | 1h | Prevents nonsensical PSI scores on toy data |
| 2 | Fix `drifted_features` count — deduplicate by feature name, not detector hit | 2h | Removes misleading count in API responses and dashboard |
| 3 | Persist webhook configs to SQLite — new `WebhookConfig` table, load on startup | 1d | Eliminates loss of notification setup on restart |
| 4 | Add scheduler health endpoint `GET /health/scheduler` — returns job states, last run times, failure counts | 4h | Makes silent scheduler failures visible |
| 5 | Make macro fetch async in startup — run in background thread, don't block lifespan | 2h | Eliminates slow server startup on FRED latency |
| 6 | Add `--dry-run` flag to `demo/lending_club.py` — skip API calls, print what would be sent | 2h | Safer local testing without needing server running |
| 7 | Add `pytest` fixtures for common DataSnapshot patterns — reuse across test files | 4h | Removes boilerplate in future test files |
| 8 | Add `.env.example` validation on startup — warn if `FRED_API_KEY` is missing rather than failing silently | 1h | Better onboarding error message |
| 9 | Add a `Makefile` with `make setup`, `make train`, `make serve`, `make test` targets | 2h | Dramatically reduces getting-started friction |
| 10 | Add `CONTRIBUTING.md` — dev setup, test commands, PR checklist | 4h | Enables external contributions |

---

## 8. Next Milestones – Short-Term Roadmap (1–3 Months)

Ordered by priority.

### Priority 1 — Recession classifier (V3 core)

Recession recall is 0%. The current classifier conflates recession signals with `credit_stress` and `black_swan`. A dedicated binary recession sub-classifier (NBER-labelled, lagged unemployment + yield curve inversion duration as primary features) would fix this without destabilising the main classifier. This is the biggest remaining gap in the regime layer.

### Priority 2 — API authentication

A static API key in `.env` with `X-API-Key` header validation on all routes is a one-day implementation. Without it, the system cannot be deployed anywhere accessible. This is the single biggest blocker for any external use.

### Priority 3 — Dashboard ModelDetail charts

The detail page has one data point in the drift history chart. The chart becomes meaningful only with multiple drift runs over time. A realistic demo dataset with 30 seeded runs across different dates would immediately make the dashboard credible for demos and screenshots.

### Priority 4 — Docker compose setup

A `docker-compose.yml` with backend + frontend containers, `.env` passthrough, and volume mounts for SQLite and demo data would reduce new contributor onboarding from ~45 minutes to `docker compose up`. Essential before any public sharing.

### Priority 5 — PyPI packaging

`pip install financial-driftguard` is the proof-of-concept moment for the library. Requires cleaning up `pyproject.toml`, pinning dependencies correctly, adding a `MANIFEST.in`, and setting up a GitHub Actions release workflow. Estimated 2 days.

### Priority 6 — LLM-powered drift explanation

Given a `DriftResult` and `RegimeAssessment`, use an LLM to generate a one-paragraph natural-language explanation: "Your credit model is showing elevated `int_rate` drift (PSI 0.10) consistent with the 2016–2018 Federal Reserve hiking cycle. This matches a historical pattern from 2004–2006 tightening. Recommended action: monitor feature distributions weekly, avoid retraining until rate cycle stabilises." This is the V3 flagship feature.

---

## 9. Open Questions / Decisions Needed

**Architecture**

- Should the regime classifier be retrained automatically when new macro data accumulates, or always triggered manually? Automatic retraining risks silent drift in the classifier itself.
- Should baselines be versioned (multiple baselines per model with timestamps) or always single/overwrite? Versioning adds complexity but enables drift comparisons across multiple reference windows.
- SQLite → PostgreSQL migration: when is the right trigger? Concurrent users? A hosted deployment? A specific scale threshold?

**Product Direction**

- Is the primary user a solo MLOps engineer running this locally, or a team with shared access? The answer changes authentication design, database choice, and dashboard collaboration features significantly.
- Should V3 include a model registry (track model versions, not just model IDs)? This would make DriftGuard a more complete MLOps tool but significantly expands scope.
- Should the Python SDK and the server be separate packages? Currently tightly coupled. Separating them would allow `pip install driftguard` (library only) vs `pip install driftguard[server]`.

**Trade-offs Not Yet Resolved**

- The composite stress index weights (0.4 VIX + 0.4 spread + 0.2 unemployment) were set heuristically. They have not been optimised. Changing them would require retraining the classifier and re-running the backtest. Worth formalising before V1.0.
- `rate_shock` was merged into `credit_stress` for classifier simplicity. This loses operational nuance — the recommended response to a rate shock is slightly different from credit stress (rate shock = wait for the Fed to pause, credit stress = watch spreads). Should this distinction be restored in V3?
- The 93.9% backtest accuracy is on weekly-sampled data with the same labelling logic used for training. This is in-sample label evaluation, not truly out-of-sample. An independent labelling exercise (e.g., using Bloomberg or alternative recession indicators) would give a cleaner accuracy estimate.

---

## 10. Quick Reference – Run Instructions

### Setup

```bash
git clone https://github.com/yourusername/financial-driftguard
cd financial-driftguard
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # macOS/Linux
pip install -r requirements.txt
pip install -e .
cp .env.example .env
# Edit .env — add FRED_API_KEY
```

### Build macro labels and train classifier

```bash
python scripts/build_regime_labels.py
python scripts/train_regime_classifier.py
```

### Run backtest validation

```bash
python scripts/run_backtest.py
```

### Start backend

```bash
uvicorn driftguard.api.main:app --reload
# API docs: http://localhost:8000/docs
# Macro endpoint: http://localhost:8000/drift/macro/latest
```

### Seed demo data (server must be running)

```bash
python demo/lending_club.py
```

### Start dashboard

```bash
cd dashboard
npm install   # first time only
npm run dev
# Open: http://localhost:5173
```

### Sanity check (no server required)

```bash
python scripts/sanity_check.py
```

Expected terminal output:
```
Overall severity: DriftSeverity.CRITICAL
Regime:     black_swan
Note:       Extreme market stress. Freeze automated decisions...
Notification system: threshold gating working correctly
```

### Run tests

```bash
pytest tests/test_detectors.py -v
# Expected: 20 passed
```

---

*Financial DriftGuard v0.2.0 — March 2026*  
*Prepared as internal engineering snapshot before V3 development phase.*
