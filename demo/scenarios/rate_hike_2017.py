"""
Scenario: Federal Reserve Rate Hike Cycle — 2017-2018

Uses real Lending Club data from the 2017–2018 period when the Fed hiked rates
7 times from 0.91% to 2.27%. int_rate on new loans shifted first — before the
real economy felt the impact — causing PSI drift that looks like model decay
but is actually macro-driven.

Expected output:
  Regime     : credit_stress
  Severity   : HIGH
  Action     : Monitor closely. Do NOT retrain. Wait for rate cycle to stabilise.

This scenario demonstrates the core thesis: same drift signal, opposite action
vs. what a naive tool would recommend.

Usage (backend must be running):
  python demo/scenarios/rate_hike_2017.py
"""

import os
import sys
import time
from pathlib import Path

import requests
import pandas as pd

# ── path setup ─────────────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv
load_dotenv(ROOT / ".env")

# ── config ─────────────────────────────────────────────────────────────────
API_BASE = "http://localhost:8000"
MODEL_ID  = "lending_club_v1"
DATA_DIR  = ROOT / "demo" / "data"

# Q4 2018 peak-of-cycle macro conditions — the moment hike stress became visible.
# Fed Funds hit 2.27%, yield curve nearly flat at 0.21, VIX spiked to 25+.
# Labeller: in_rate_shock=True + VIX>=23 + yield_curve<0.5 → rate_shock (credit_stress).
RATE_HIKE_MACRO = {
    "vix":               25.0,    # elevated — Q4 2018 VIX spike (peaked at 36 in Dec)
    "credit_spread":     1.90,    # widening into year-end — credit markets tightening
    "fed_funds_rate":    2.27,    # end-of-cycle peak rate
    "yield_curve":       0.21,    # nearly flat — market pricing in policy error
    "unemployment_rate": 3.7,     # historically low — strong labour market
}

SEPARATOR = "─" * 60


def _headers() -> dict:
    key = os.getenv("API_KEY", "")
    return {"X-API-Key": key} if key else {}


def banner(title: str) -> None:
    print(f"\n{SEPARATOR}")
    print(f"  {title}")
    print(SEPARATOR)


def check_server() -> None:
    try:
        r = requests.get(f"{API_BASE}/health", timeout=5)
        r.raise_for_status()
    except Exception:
        print("\n  Backend not running. Start it with:")
        print("    uvicorn driftguard.api.main:app --reload")
        sys.exit(1)


def ensure_model_exists() -> None:
    r = requests.get(f"{API_BASE}/models/{MODEL_ID}", headers=_headers(), timeout=10)
    if r.status_code == 404:
        print(f"  Model '{MODEL_ID}' not found — run demo/lending_club.py first")
        sys.exit(1)


def load_live_snapshot() -> list[dict]:
    """Load the real 2017-2018 Lending Club data."""
    path = DATA_DIR / "live_snapshot.parquet"
    if not path.exists():
        print(f"  ❌  {path} not found. Run demo/lending_club.py first.")
        sys.exit(1)
    df = pd.read_parquet(path)
    return df.to_dict(orient="records")


def run_drift_check(records: list[dict]) -> dict:
    payload = {
        "records": records,
        "set_as_baseline": False,
        "macro": RATE_HIKE_MACRO,
    }
    r = requests.post(
        f"{API_BASE}/drift/{MODEL_ID}/run",
        json=payload,
        headers=_headers(),
        timeout=60,
    )
    r.raise_for_status()
    return r.json()


def print_drift_result(result: dict) -> None:
    banner("DRIFT DETECTION RESULT")
    print(f"  Model        : {MODEL_ID}")
    print(f"  Drift Score  : {result.get('drift_score', 'N/A'):.4f}")
    print(f"  Severity     : {result.get('overall_severity', 'N/A').upper()}")
    print(f"  Regime       : {result.get('regime', 'N/A')}")
    print(f"  Confidence   : {result.get('regime_confidence', 'N/A')}")

    recommendation = result.get("recommendation", "")
    if recommendation:
        print(f"\n  Recommendation:")
        for line in recommendation.split(". "):
            if line.strip():
                print(f"      {line.strip()}.")

    features = result.get("top_drifted_features", [])
    if features:
        print(f"\n  Top Drifted Features:")
        for f in features[:5]:
            print(f"    {f['feature_name']:<22} PSI={f['score']:.4f}  {f['severity']}")


def print_the_key_insight() -> None:
    banner("THE KEY INSIGHT")
    print("  int_rate is the leading signal of the Fed hiking cycle.")
    print("  New loan originations priced in higher rates BEFORE")
    print("  the economy felt the impact. This is not model decay —")
    print("  the model is correctly uncertain about new applicants")
    print("  who are borrowing at higher rates.")
    print()
    print("  Naive tool: 'Drift detected (PSI 0.10). Retrain.'")
    print()
    print("  FinSight AI: 'credit_stress regime. Macro-driven drift.")
    print("    Retraining now locks in rate-hike-period patterns.")
    print("    Post-cycle, that model will underperform. Wait.")
    print("    Monitor weekly. Expected stabilisation: 6–12 months.'")


def print_macro_context() -> None:
    banner("MACRO CONTEXT — Q4 2018 PEAK RATE HIKE STRESS")
    print("  Fed Funds Rate : 2.27% (peak — 7 hikes over 24 months)")
    print("  VIX            : 25.0 (elevated — spiked to 36 in Dec 2018)")
    print("  Credit Spread  : 1.90% (widening — year-end credit stress)")
    print("  Yield Curve    : 0.21% (nearly flat — pricing in policy error)")
    print("  Unemployment   : 3.7% (historically low — strong labour market)")
    print()
    print("  Interpretation: Rate hike stress regime. Not a crisis or recession.")
    print("  Yield curve nearly flat + VIX elevated = market doubting the Fed.")
    print("  Model drift is EXPECTED. It will self-resolve post-cycle.")


def main() -> None:
    banner("SCENARIO: Fed Rate Hike Cycle — 2017-2018")
    print("  Using real Lending Club 2017-2018 portfolio data.")
    print("  Fed hiked 7 times. int_rate on new loans shifted ahead of the economy.")

    check_server()
    ensure_model_exists()

    print_macro_context()

    print("\n  Loading 2017-2018 live portfolio data...")
    records = load_live_snapshot()
    print(f"  {len(records):,} records loaded")

    print("\n  Running drift check with 2017-2018 macro context...")
    result = run_drift_check(records)

    print_drift_result(result)
    print_the_key_insight()

    banner("SCENARIO COMPLETE")
    print("  Phoenix trace logged at: http://localhost:6006")
    print(f"  Dashboard:               http://localhost:5173/models/{MODEL_ID}")
    print()


if __name__ == "__main__":
    main()
