<div align="center">

# 🛡️ Financial DriftGuard

**ML model drift monitoring with financial regime awareness**

[![Python](https://img.shields.io/badge/Python-3.11+-blue?style=flat-square&logo=python)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.109+-green?style=flat-square&logo=fastapi)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-18+-61DAFB?style=flat-square&logo=react)](https://react.dev)
[![License](https://img.shields.io/badge/License-MIT-yellow?style=flat-square)](LICENSE)
[![Tests](https://img.shields.io/badge/Tests-20%20passing-brightgreen?style=flat-square)]()

> The only drift monitoring library that distinguishes genuine market regime changes from model decay — something no horizontal tool like Arize or WhyLabs does.

[Quick Start](#quick-start) · [How It Works](#how-it-works) · [API Reference](#api-reference) · [Dashboard](#dashboard) · [Roadmap](#roadmap)

</div>

---

## The Problem

When a credit model's performance degrades during a recession, standard monitoring tools fire an alert: **"drift detected — retrain."**

That's wrong. Retraining a credit model *during* a recession on recession data produces a model that is useless once conditions normalise. The model isn't decaying — the world shifted.

**DriftGuard tells you which one it is.**

| Scenario | Standard Tool | DriftGuard |
|---|---|---|
| Feature distribution shifts during rate hike | "Drift detected" | "Rate shock regime — monitor, don't retrain" |
| Feature pipeline silently breaks | "Drift detected" | "Stable macro — likely model decay, investigate pipeline" |
| COVID black swan event | "Drift detected" | "Extreme stress — freeze automated decisions, human review required" |

---

## Features

- **3 statistical detectors** — PSI (industry standard for credit), KS test, JS divergence
- **5 regime classes** — stable, rate shock, recession, credit stress, black swan
- **Rule-based regime tagger** — combines VIX, FRED macro signals, yield curve, credit spreads
- **Model-agnostic** — works with sklearn, PyTorch, XGBoost, LightGBM
- **FastAPI backend** — REST API with SQLite persistence and auto-alerting
- **React dashboard** — real-time model health overview with feature-level drill-down
- **Lending Club demo** — pre-trained LightGBM credit default model, validated on real data

---

## Quick Start

### Requirements

- Python 3.11+
- Node.js 18+

### Installation
```bash
git clone https://github.com/yourusername/financial-driftguard
cd financial-driftguard

# Backend
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # macOS/Linux

pip install -r requirements.txt
pip install -e .
```

### Run the sanity check
```bash
python scripts/sanity_check.py
```

Expected output:
```
Overall severity: DriftSeverity.CRITICAL
Drift score: 0.4121
  annual_inc [psi] → DriftSeverity.CRITICAL (score=0.514926)
  dti [psi] → DriftSeverity.CRITICAL (score=0.934571)
  ...
Regime: black_swan
Note: Extreme market stress. Freeze automated decisions...
```

### Start the API
```bash
uvicorn driftguard.api.main:app --reload
```

API docs available at `http://localhost:8000/docs`

### Start the dashboard
```bash
cd dashboard
npm install
npm run dev
```

Dashboard available at `http://localhost:5173`

---

## How It Works

### 1. Wrap your data
```python
from driftguard import Monitor, DataSnapshot
import pandas as pd

baseline = DataSnapshot.from_dataframe(baseline_df, label="2019-baseline")
current  = DataSnapshot.from_dataframe(current_df,  label="2020-live")
```

### 2. Run drift detection
```python
monitor = Monitor(model_id="credit_model_v1")
result  = monitor.check(baseline, current)

print(result.overall_severity)   # DriftSeverity.HIGH
print(result.drift_score)        # 0.0493
```

### 3. Add regime context
```python
from driftguard.regime.macro_signals import MacroSnapshot

macro = MacroSnapshot(
    as_of=date(2020, 4, 1),
    vix=57.0,
    credit_spread=3.8,
    fed_funds_rate=0.25,
    yield_curve=-0.5,
    unemployment_rate=14.7,
)

result = monitor.check(baseline, current, macro=macro)

print(result.regime)   # black_swan
print(result.notes)    # "Extreme market stress. Freeze automated decisions..."
```

### 4. Inspect per-feature drift
```python
for feature in result.drifted_features:
    print(f"{feature.feature_name} [{feature.detector}] → {feature.severity}")

# int_rate [psi] → low      ← Fed hiking cycle signal
# dti [ks]       → medium
```

---

## Architecture
```
financial-driftguard/
├── driftguard/
│   ├── core/
│   │   ├── monitor.py          # public SDK entry point
│   │   ├── snapshot.py         # data ingestion
│   │   └── drift_result.py     # typed result dataclasses
│   ├── detectors/
│   │   ├── base.py             # abstract BaseDetector
│   │   ├── psi.py              # Population Stability Index
│   │   ├── ks_test.py          # Kolmogorov-Smirnov test
│   │   └── js_divergence.py    # Jensen-Shannon divergence
│   ├── regime/
│   │   ├── tagger.py           # regime classifier (rule-based v1)
│   │   └── macro_signals.py    # FRED API + VIX ingestion
│   ├── api/
│   │   ├── main.py             # FastAPI app
│   │   └── routes/             # models, drift, alerts
│   ├── store/
│   │   └── database.py         # SQLite via SQLModel
│   └── scheduler/
│       └── jobs.py             # periodic drift checks
├── dashboard/                  # React + Tailwind + Recharts
├── demo/
│   └── lending_club.py         # end-to-end demo
└── tests/
    └── test_detectors.py       # 20 passing tests
```

---

## Regime Classes

| Regime | Signals | Recommendation |
|---|---|---|
| `stable` | VIX < 25, spreads normal | Monitor normally |
| `credit_stress` | VIX 25–40, spreads elevated | Monitor closely, avoid retraining |
| `rate_shock` | Credit conditions tightening + VIX stress | Wait for stabilisation |
| `recession` | Unemployment elevated + yield curve inverted | Adjust thresholds, champion-challenger |
| `black_swan` | VIX > 40 + credit spread crisis | Freeze automated decisions, human review |

---

## Demo — Lending Club Credit Default

A LightGBM model trained on 791k loan records (2013–2016), validated on 434k records (2016–2017), and monitored through the 2017–2018 Fed hiking cycle.
```bash
python demo/lending_club.py
```

**Results:**

| Feature | PSI Score | Signal |
|---|---|---|
| `int_rate` | 0.1013 | Fed hiking cycle — rates shifting on new loans |
| `fico_range_low` | 0.0616 | Credit score distribution tightening |
| `revol_util` | 0.0488 | Revolving utilisation creeping up |

**Key insight:** DriftGuard correctly tagged this as `credit_stress` (not model decay) and recommended monitoring rather than retraining — because the drift is macro-driven, not pipeline-driven.

---

## API Reference

### Models

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/models/` | Register a model |
| `GET` | `/models/` | List all models |
| `GET` | `/models/{id}` | Get model details |
| `DELETE` | `/models/{id}` | Remove a model |

### Drift

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/drift/{id}/run` | Trigger a drift check |
| `GET` | `/drift/{id}/latest` | Get latest drift run |
| `GET` | `/drift/{id}/history` | Get drift history |
| `GET` | `/drift/{id}/features/{run_id}` | Get per-feature results |

### Alerts

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/alerts/` | List alerts |
| `GET` | `/alerts/{model_id}` | Alerts for a model |
| `POST` | `/alerts/acknowledge` | Acknowledge an alert |

Full interactive docs: `http://localhost:8000/docs`

---

## Running Tests
```bash
pytest tests/test_detectors.py -v
```
```
20 passed in 3.16s
```

---

## Roadmap

### V1 — Complete ✅
- PSI, KS, JS drift detectors
- Rule-based regime tagger
- FastAPI backend + SQLite
- React dashboard
- Lending Club demo

### V2 — In Progress
- [ ] Trained ML regime classifier (replace rule-based)
- [ ] FRED API live macro ingestion
- [ ] Discord / Telegram / Slack webhook alerts
- [ ] Historical backtesting against NBER recession dates

### V3 — Planned
- [ ] Model registry with version tracking
- [ ] LLM-powered drift explanation
- [ ] Automated retraining trigger signals
- [ ] Team collaboration on dashboard

---

## Contributing

Contributions welcome. Please open an issue before submitting a PR for significant changes.
```bash
# run tests before submitting
pytest tests/ -v

# install dev dependencies
pip install -e ".[dev]"
```

---

## License

MIT — see [LICENSE](LICENSE)

---

<div align="center">

Built with domain knowledge, not just statistics.

</div>