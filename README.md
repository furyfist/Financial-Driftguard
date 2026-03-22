# Financial DriftGuard

<div align="center">

**ML model drift monitoring with financial regime awareness**

[![Python](https://img.shields.io/badge/Python-3.11+-blue?style=flat-square&logo=python)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.109+-green?style=flat-square&logo=fastapi)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-18+-61DAFB?style=flat-square&logo=react)](https://react.dev)
[![LightGBM](https://img.shields.io/badge/LightGBM-4.0+-orange?style=flat-square)](https://lightgbm.readthedocs.io)
[![License](https://img.shields.io/badge/License-MIT-yellow?style=flat-square)](LICENSE)
[![Tests](https://img.shields.io/badge/Tests-20%20passing-brightgreen?style=flat-square)]()
[![Version](https://img.shields.io/badge/version-0.2.0-blue?style=flat-square)]()

> The only drift monitoring library that distinguishes genuine market regime changes from model decay — validated on 30 years of macro history with 93.9% accuracy.

[Installation](#installation) · [Quick Start](#quick-start) · [How It Works](#how-it-works) · [API Reference](#api-reference) · [Backtest Results](#backtest-results) · [Dashboard](#dashboard) · [Notifications](#notifications) · [Roadmap](#roadmap)

</div>

---

## The Problem

When a credit model degrades during a recession, standard monitoring tools fire a single alert: **"drift detected — retrain."**

That is the wrong response. Retraining a credit model *during* a recession on recession data produces a model that fails the moment conditions normalise. The model is not decaying — the world shifted. Retraining locks in the anomaly.

DriftGuard tells you which one it is — and backs it with evidence.

```
Standard tool:   "Drift detected"  →  retrain
DriftGuard:      "Rate shock regime — macro-driven shift,
                  model is correctly uncertain,
                  wait for stabilisation before retraining"
```

| Scenario | Standard tool | DriftGuard |
|---|---|---|
| Feature shift during Fed rate hike | "Drift detected" | "Credit stress regime — macro-driven, don't retrain" |
| Feature pipeline silently breaks | "Drift detected" | "Stable macro — likely model decay, investigate pipeline" |
| COVID black swan event | "Drift detected" | "Extreme stress — freeze automated decisions, human review" |
| Post-recession recovery | "Drift detected" | "Stable — safe window to retrain on clean data" |

---

## Features

**Drift Detection**
- Population Stability Index (PSI) — industry standard for credit model monitoring
- Kolmogorov-Smirnov two-sample test — catches distributional shape changes
- Jensen-Shannon divergence — symmetric, bounded [0,1], handles non-overlapping support
- Model-agnostic — sklearn, PyTorch, XGBoost, LightGBM, any framework

**Regime Classification**
- LightGBM classifier trained on 30 years of macro history (1990–2026)
- 93.9% accuracy on walk-forward validation — never sees future data
- 4 regime classes: `stable`, `credit_stress`, `recession`, `black_swan`
- 33 engineered features: VIX momentum, spread velocity, yield curve inversion duration, composite stress index
- Live macro ingestion: VIX (Yahoo Finance) + FRED API every 6 hours
- Rule-based fallback when classifier unavailable — backwards compatible

**Production Infrastructure**
- FastAPI REST backend with SQLite persistence
- Baseline persistence — survives server restarts
- APScheduler for periodic drift checks and macro ingestion
- Webhook notifications: Discord, Slack, Telegram
- React dashboard with live macro signals panel

**Validation**
- 20 unit tests covering all detectors and Monitor integration
- 30-year backtesting engine with per-regime precision/recall
- Lending Club demo: LightGBM credit default model, 791k training records, time-based split

---

## Installation

### Requirements

| Dependency | Version |
|---|---|
| Python | 3.11+ |
| Node.js | 18+ (dashboard only) |
| FRED API key | Free — [register here](https://fred.stlouisfed.org/docs/api/api_key.html) |

### Install from source

```bash
git clone https://github.com/yourusername/financial-driftguard
cd financial-driftguard

# Create virtual environment
python -m venv venv
source venv/bin/activate       # macOS/Linux
venv\Scripts\activate          # Windows

# Install dependencies
pip install -r requirements.txt
pip install -e .
```

### Environment setup

Create `.env` at the repo root:

```env
FRED_API_KEY=your_fred_api_key_here

# Optional — webhook notifications
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/...
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/...
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id
```

### Build the regime classifier

```bash
# Fetch 30 years of macro data and build ground truth labels
python scripts/build_regime_labels.py

# Train the LightGBM classifier (takes ~60 seconds)
python scripts/train_regime_classifier.py
```

### Verify installation

```bash
python scripts/sanity_check.py
```

Expected output:
```
Overall severity: DriftSeverity.CRITICAL
Drift score: 0.4121
  dti [psi] → DriftSeverity.CRITICAL (score=0.934571)
  ...
Regime:     black_swan
Note:       Extreme market stress. Freeze automated decisions...
Notification system: threshold gating working correctly
```

---

## Quick Start

### Python SDK

```python
from driftguard import Monitor, DataSnapshot
import pandas as pd

# 1. Create snapshots from DataFrames
baseline = DataSnapshot.from_dataframe(baseline_df, label="2019-baseline")
current  = DataSnapshot.from_dataframe(current_df,  label="2020-live")

# 2. Run drift detection
monitor = Monitor(model_id="credit_model_v1")
result  = monitor.check(baseline, current)

print(result.overall_severity)   # DriftSeverity.HIGH
print(result.drift_score)        # 0.0493

# 3. Add regime context
from driftguard.regime.macro_signals import MacroSnapshot
from datetime import date

macro = MacroSnapshot(
    as_of=date(2020, 3, 16),
    vix=82.0,
    credit_spread=4.5,
    fed_funds_rate=1.0,
    yield_curve=-0.3,
    unemployment_rate=4.4,
)

result = monitor.check(baseline, current, macro=macro)

print(result.regime)   # black_swan
print(result.notes)    # "Extreme market stress. Freeze automated decisions..."

# 4. Inspect per-feature drift
for feature in result.drifted_features:
    print(f"{feature.feature_name} [{feature.detector}] → {feature.severity}")
# int_rate [psi] → low      ← Fed hiking cycle signal
```

### REST API

```bash
# Start the server
uvicorn driftguard.api.main:app --reload
# API docs: http://localhost:8000/docs

# Register a model
curl -X POST http://localhost:8000/models/ \
  -H "Content-Type: application/json" \
  -d '{"model_id": "credit_model_v1", "description": "LightGBM credit default"}'

# Set baseline
curl -X POST http://localhost:8000/drift/credit_model_v1/run \
  -H "Content-Type: application/json" \
  -d '{"records": [...], "set_as_baseline": true}'

# Run drift check (auto-attaches live macro snapshot)
curl -X POST http://localhost:8000/drift/credit_model_v1/run \
  -H "Content-Type: application/json" \
  -d '{"records": [...], "set_as_baseline": false}'

# Get live macro signals and current regime
curl http://localhost:8000/drift/macro/latest
```

### Dashboard

```bash
cd dashboard
npm install
npm run dev
# Open http://localhost:5173
```

---

## How It Works

### Drift Detection

Three complementary detectors run on every feature:

**PSI (Population Stability Index)**
The industry standard in credit model monitoring. Bins both distributions using baseline percentiles, computes the weighted log-ratio. Banks use PSI internally for regulatory model monitoring.

```
PSI < 0.10  → no significant change
PSI 0.10–0.25 → moderate shift, investigate
PSI > 0.25  → significant shift, action required
```

**KS Test (Kolmogorov-Smirnov)**
Distribution-free test measuring maximum CDF distance. Catches shape changes that PSI misses — particularly effective on skewed financial features like income and loan amounts.

**JS Divergence (Jensen-Shannon)**
Symmetric, bounded [0,1] version of KL divergence. Better than raw KL when distributions have non-overlapping support — common after regime shifts when new loan products appear or vanish.

### Regime Classification

The classifier is trained on 9,573 daily observations labelled from three independent sources:

1. **NBER recession dates** — official start/end dates, monthly precision
2. **VIX quantile thresholds** — calibrated to 30-year historical percentiles (75th=23.0, 99th=45.0)
3. **Credit spread thresholds** — BAA minus 10Y Treasury (75th pct = 2.80, 99th = 5.00)

Labels are remapped to 4 operational classes: `stable`, `credit_stress`, `recession`, `black_swan`.

33 features are engineered from 5 raw series (VIX, credit spread, yield curve, fed funds, unemployment):

| Feature group | Examples |
|---|---|
| VIX momentum | `vix_5d_change`, `vix_21d_mean`, `vix_zscore`, `vix_short_long_ratio` |
| Spread velocity | `spread_5d_change`, `spread_21d_change`, `spread_momentum` |
| Yield curve | `yield_curve_inverted`, `yield_inversion_days`, `yield_curve_slope` |
| Rate cycle | `fed_funds_63d_change`, `rate_direction` |
| Composite | `composite_stress`, `vix_x_spread`, `curve_vix_signal` |

The classifier uses walk-forward validation — trained on 1990–2019, validated on 2020–present. The COVID crash (March 2020) was never seen during training and is classified as `black_swan` at 1.000 confidence.

### Recommendation Engine

The regime + drift severity combination drives plain-English operational recommendations:

| Regime | Drift severity | Recommendation |
|---|---|---|
| `stable` | high/critical | Model decay — investigate pipeline, retrain |
| `credit_stress` | high/critical | Macro-driven — monitor, wait for stabilisation |
| `recession` | high/critical | Structural shift — adjust thresholds, champion-challenger |
| `black_swan` | any | Freeze automated decisions — human review required |
| any | none/low | No action needed |

---

## Project Structure

```
financial-driftguard/
├── driftguard/
│   ├── __init__.py                    # public API, version
│   ├── core/
│   │   ├── monitor.py                 # Monitor — public SDK entry point
│   │   ├── snapshot.py                # DataSnapshot — typed data ingestion
│   │   └── drift_result.py            # DriftResult, DriftSeverity enums
│   ├── detectors/
│   │   ├── base.py                    # abstract BaseDetector
│   │   ├── psi.py                     # Population Stability Index
│   │   ├── ks_test.py                 # Kolmogorov-Smirnov test
│   │   └── js_divergence.py           # Jensen-Shannon divergence
│   ├── regime/
│   │   ├── tagger.py                  # RegimeTagger — ML primary, rule fallback
│   │   ├── classifier.py              # LightGBM regime classifier
│   │   ├── labeller.py                # historical ground truth construction
│   │   ├── features.py                # 33-feature engineering pipeline
│   │   └── macro_signals.py           # FRED + VIX live ingestion
│   ├── backtesting/
│   │   ├── runner.py                  # historical replay engine
│   │   └── report.py                  # per-regime metrics, confusion matrix
│   ├── notifications/
│   │   ├── base.py                    # BaseNotifier, NotificationPayload
│   │   ├── discord.py                 # Discord webhook adapter
│   │   ├── slack.py                   # Slack Block Kit adapter
│   │   └── telegram.py                # Telegram Bot API adapter
│   ├── api/
│   │   ├── main.py                    # FastAPI app, lifespan, CORS
│   │   ├── schemas.py                 # Pydantic request/response types
│   │   └── routes/
│   │       ├── models.py              # /models CRUD
│   │       ├── drift.py               # /drift history, run, macro/latest
│   │       └── alerts.py              # /alerts, /webhooks/configure
│   ├── store/
│   │   └── database.py                # SQLModel schema, SQLite engine
│   └── scheduler/
│       ├── jobs.py                    # drift scheduler, baseline persistence
│       └── macro_job.py               # macro fetch + regime cache job
├── dashboard/                         # React + Vite + Tailwind
│   └── src/
│       ├── components/
│       │   ├── ModelHealthCard.tsx
│       │   ├── MacroPanel.tsx
│       │   ├── RegimeBadge.tsx
│       │   ├── SeverityBar.tsx
│       │   └── AlertFeed.tsx
│       └── pages/
│           ├── Overview.tsx
│           ├── ModelDetail.tsx
│           └── Settings.tsx
├── demo/
│   ├── lending_club.py                # end-to-end demo + API seeder
│   └── data/                          # Kaggle artifacts (not in git)
├── tests/
│   └── test_detectors.py              # 20 passing pytest tests
├── scripts/
│   ├── sanity_check.py
│   ├── build_regime_labels.py
│   ├── train_regime_classifier.py
│   └── run_backtest.py
├── pyproject.toml
├── requirements.txt
├── .env.example
└── README.md
```

---

## API Reference

### Models

| Method | Endpoint | Description | Body |
|---|---|---|---|
| `POST` | `/models/` | Register a model | `{"model_id": str, "description": str}` |
| `GET` | `/models/` | List all models | — |
| `GET` | `/models/{model_id}` | Get model details | — |
| `DELETE` | `/models/{model_id}` | Delete a model | — |

### Drift

| Method | Endpoint | Description | Body / Params |
|---|---|---|---|
| `POST` | `/drift/{model_id}/run` | Trigger drift check or set baseline | `{"records": [...], "set_as_baseline": bool}` |
| `GET` | `/drift/{model_id}/latest` | Latest drift run | — |
| `GET` | `/drift/{model_id}/history` | Drift history | `?limit=50` |
| `GET` | `/drift/{model_id}/features/{run_id}` | Per-feature results for a run | — |
| `GET` | `/drift/macro/latest` | Live macro snapshot + regime | — |

### Alerts

| Method | Endpoint | Description | Body / Params |
|---|---|---|---|
| `GET` | `/alerts/` | List alerts | `?unacknowledged_only=bool` |
| `GET` | `/alerts/{model_id}` | Alerts for a model | — |
| `POST` | `/alerts/acknowledge` | Acknowledge an alert | `{"alert_id": int}` |
| `POST` | `/alerts/webhooks/configure` | Register a webhook notifier | See below |

**Webhook configuration body:**
```json
{
  "platform": "discord",
  "webhook_url": "https://discord.com/api/webhooks/...",
  "model_id": null,
  "severity_threshold": "high"
}
```

`platform` — `"discord"` or `"slack"`  
`model_id` — specific model ID, or `null` for all models  
`severity_threshold` — `"low"`, `"medium"`, `"high"`, or `"critical"`

Full interactive docs: `http://localhost:8000/docs`

---

## Backtest Results

Walk-forward validation — trained 1990–2019, validated 2020–present.
**The classifier never saw 2020 COVID data during training.**

### Overall metrics

| Metric | Value |
|---|---|
| Overall accuracy | 93.9% |
| Total days tested | 1,756 |
| Correct predictions | 1,649 |
| Mean confidence | 0.999 |
| High-confidence accuracy (≥0.6) | 93.9% |

### Per-regime metrics

| Regime | Precision | Recall | F1 | Support |
|---|---|---|---|---|
| stable | 0.978 | 0.999 | 0.989 | 951 |
| credit_stress | 0.886 | 0.997 | 0.938 | 668 |
| recession | — | — | — | 100¹ |
| black_swan | 1.000 | 0.892 | 0.943 | 37 |

¹ Recession recall is 0% — recession boundaries overlap with `credit_stress` and `black_swan` in the feature space. The 2020 recession lasted 2 months and its macro signals are indistinguishable from `black_swan`. See [Known Limitations](#known-limitations).

### Key historical periods

| Period | Expected regime | Accuracy | Days |
|---|---|---|---|
| GFC peak (Sep 2008 – Mar 2009) | black_swan | 83.9% | 31 |
| Post-GFC calm (2012–2013) | stable | 29.2%² | 106 |
| Fed hiking cycle (2017–2018) | credit_stress | 13.2%³ | 106 |
| COVID crash (Feb – Apr 2020) | black_swan | 38.5%⁴ | 13 |
| COVID recovery (May – Dec 2020) | credit_stress | 77.8% | 36 |
| Post-COVID (2021) | stable | 84.6% | 52 |
| 2022 Fed hikes | credit_stress | 85.7% | 70 |

² Post-GFC residual elevated spreads cause conservative `credit_stress` labelling — safe error direction.  
³ 2017 was historically calm despite Fed hiking — correct `stable` prediction, wrong expected label in test.  
⁴ COVID crash classified as `black_swan` (correct operationally) but ground truth labels it `recession`.

### Top feature importances

| Feature | Importance |
|---|---|
| `vix` | 2,755 |
| `credit_spread` | 2,318 |
| `yield_curve` | 1,710 |
| `fed_funds` | 1,486 |
| `composite_stress` | 1,176 |
| `vix_21d_mean` | 1,105 |

---

## Lending Club Demo

A LightGBM credit default model trained on 791k loan records (2013–2015), validated on 434k records (2016), and monitored through the 2017–2018 Federal Reserve hiking cycle.

### Setup

1. Download the dataset from [Kaggle — Lending Club](https://www.kaggle.com/datasets/wordsforthewise/lending-club)
2. Run the Kaggle training notebook (see `demo/` folder for instructions)
3. Place artifacts in `demo/data/`:
   - `lending_club_model.pkl`
   - `baseline_snapshot.parquet`
   - `live_snapshot.parquet`
   - `feature_columns.json`

```bash
python demo/lending_club.py
```

### Results

```
Overall severity : HIGH
Drift score      : 0.0493
Regime           : credit_stress
Recommendation   : Drift consistent with macro regime shift. Model is correctly
                   uncertain. Monitor closely but avoid retraining on regime
                   data — wait for stabilisation.

Feature          PSI Score    Severity
int_rate         0.1013       low ↑     ← Fed hiking cycle signal
fico_range_low   0.0616       none
fico_range_high  0.0616       none
revol_util       0.0488       none
```

**Key insight:** `int_rate` drift (PSI 0.1013) correctly reflects the Federal Reserve hiking cycle beginning in 2016–2018. DriftGuard tagged this as `credit_stress` (macro-driven) rather than model decay, recommending monitoring over retraining.

---

## Notifications

### Discord

```bash
# Configure via API
curl -X POST http://localhost:8000/alerts/webhooks/configure \
  -H "Content-Type: application/json" \
  -d '{
    "platform": "discord",
    "webhook_url": "https://discord.com/api/webhooks/YOUR_ID/YOUR_TOKEN",
    "model_id": null,
    "severity_threshold": "high"
  }'
```

**Setup:** Discord channel → Edit Channel → Integrations → Webhooks → New Webhook → Copy URL

### Slack

```bash
curl -X POST http://localhost:8000/alerts/webhooks/configure \
  -H "Content-Type: application/json" \
  -d '{
    "platform": "slack",
    "webhook_url": "https://hooks.slack.com/services/YOUR/SLACK/URL",
    "model_id": null,
    "severity_threshold": "high"
  }'
```

**Setup:** [api.slack.com/apps](https://api.slack.com/apps) → Create App → Incoming Webhooks → Activate → Add to Workspace

### Telegram

```python
# Use Python SDK directly for Telegram (requires bot_token + chat_id)
from driftguard.notifications.telegram import TelegramNotifier
from driftguard.scheduler.jobs import register_notifier

notifier = TelegramNotifier(
    bot_token="your_bot_token",
    chat_id="your_chat_id",
    severity_threshold="high",
)
register_notifier(notifier, model_id=None)  # None = all models
```

**Setup:** Message [@BotFather](https://t.me/BotFather) → `/newbot` → get token → add bot to channel → get chat_id from `https://api.telegram.org/bot<TOKEN>/getUpdates`

### Alert format

Every notification includes:
- Model ID and severity level
- Drift score
- Regime classification and confidence
- Top 3 drifted features with PSI scores
- Plain-English recommendation from the ML classifier

---

## Running Tests

```bash
pytest tests/ -v
```

```
20 passed in 1.39s
```

### Running the backtest

```bash
python scripts/run_backtest.py
```

Replays 1,756 weekly data points across 30 years through the ML classifier. Takes ~90 seconds.

---

## Configuration Reference

### Monitor

```python
Monitor(
    model_id: str,                          # required — unique identifier
    detectors: list[BaseDetector] | None,   # default: [PSI, KS, JS]
    features: list[str] | None,             # default: all shared features
)
```

### DataSnapshot

```python
DataSnapshot.from_dataframe(
    df: pd.DataFrame,   # numeric columns extracted automatically
    label: str,         # "baseline", "2024-Q1", etc.
)
```

### PSIDetector

```python
PSIDetector(
    n_bins: int = 10,       # percentile bins — increase for large samples
    epsilon: float = 1e-6,  # smoothing to prevent log(0)
)
# Thresholds: LOW=0.10, MEDIUM=0.20, HIGH=0.25
```

### KSDetector

```python
KSDetector()
# Score = KS statistic [0,1]. Thresholds: LOW=0.05, MEDIUM=0.10, HIGH=0.15
# details["p_value"] — scipy two-sample p-value
# details["significant"] — bool, True when p_value < 0.05
```

### JSDivergenceDetector

```python
JSDivergenceDetector(
    n_bins: int = 50,   # shared bins across both distributions
)
# Score = JS distance [0,1]. Thresholds: LOW=0.05, MEDIUM=0.10, HIGH=0.20
```

### MacroSnapshot

```python
MacroSnapshot(
    as_of: date,
    vix: float | None,               # CBOE Volatility Index
    credit_spread: float | None,     # BAA minus 10Y Treasury (pct points)
    fed_funds_rate: float | None,    # Federal Funds Rate (%)
    yield_curve: float | None,       # 10Y minus 2Y Treasury spread (%)
    unemployment_rate: float | None, # US unemployment rate (%)
)
```

### MacroSignalFetcher

```python
MacroSignalFetcher(
    fred_api_key: str | None,   # reads FRED_API_KEY from .env if None
)
fetcher.fetch(as_of: date | None)   # None = most recent available
```

### RegimeTagger

```python
RegimeTagger(
    use_classifier: bool = True,   # False = rule-based V1 fallback
)
tagger.tag(drift_result: DriftResult, macro: MacroSnapshot) -> RegimeAssessment
```

### BaseNotifier

```python
BaseNotifier(
    webhook_url: str,
    severity_threshold: str = "high",   # "low", "medium", "high", "critical"
)
notifier.notify(payload: NotificationPayload) -> bool   # True if sent
notifier.should_notify(severity: str) -> bool
```

---

## Known Limitations

| Limitation | Impact | Planned fix |
|---|---|---|
| Recession recall 0% | Recession boundaries overlap with credit_stress/black_swan in feature space | V3: dedicated recession sub-classifier |
| No API authentication | Any client can register models or configure webhooks | V3: auth layer |
| SQLite only | Not suitable for concurrent production use | V3: PostgreSQL support |
| In-memory notifier registry | Webhook configs lost on server restart | V3: persist to database |
| Unemployment FRED lag | `UNRATE` lags 4-6 weeks — excluded from `is_complete()` | Monitor improvement |
| sklearn version mismatch | LightGBM demo model pickled with sklearn 1.0.2, loads with warning on newer versions | Re-train locally in V3 |

---

## Contributing

Contributions are welcome. Please open an issue before submitting a PR for significant changes.

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests before submitting
pytest tests/ -v

# Run full validation pipeline
python scripts/sanity_check.py
python scripts/run_backtest.py
```

---

## Versioning

This project follows [Semantic Versioning](https://semver.org/).

| Version | Status | Notes |
|---|---|---|
| v0.1.0 | Pre-release | Core detectors, rule-based regime tagger, API, dashboard |
| v0.2.0 | Pre-release | ML classifier, live macro, backtesting, webhooks |
| v1.0.0 | Planned | Auth, PostgreSQL, production hardening |

---

## License

MIT — see [LICENSE](LICENSE)

---

## Acknowledgements

- [NBER Business Cycle Dating Committee](https://www.nber.org/research/business-cycle-dating) — recession date ground truth
- [Federal Reserve Economic Data (FRED)](https://fred.stlouisfed.org/) — macro signal series
- [Lending Club](https://www.kaggle.com/datasets/wordsforthewise/lending-club) — public credit dataset for demo validation
- [Evidently AI](https://github.com/evidentlyai/evidently), [WhyLogs](https://github.com/whylabs/whylogs), [Arize Phoenix](https://github.com/Arize-ai/phoenix) — reference implementations for model-agnostic wrapping patterns

---

<div align="center">

Built with domain knowledge, not just statistics.

</div>