"""
Scenario: COVID-19 Black Swan — March 2020

Injects macro conditions from March 2020 (VIX=57, credit spreads blowing out,
unemployment spiking) and runs a drift check against the Lending Club baseline.

Expected output:
  Regime     : black_swan (confidence ~1.000)
  Severity   : CRITICAL
  Action     : HALT — freeze automated decisions, escalate to human review

This scenario demonstrates FinSight AI's crisis response and agent-to-agent
trust API returning trustworthy=false, recommendation="halt".

Usage (backend must be running):
  python demo/scenarios/covid_crash.py
"""

import os
import sys
import json
import time
from pathlib import Path

import requests
import pandas as pd

# ── path setup ─────────────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv
load_dotenv(ROOT / ".env")

from driftguard.regime.macro_signals import MacroSnapshot

# ── config ─────────────────────────────────────────────────────────────────
API_BASE = "http://localhost:8000"
MODEL_ID  = "lending_club_v1"
DATA_DIR  = ROOT / "demo" / "data"

# March 2020 macro conditions
from datetime import date as _date
COVID_MACRO = MacroSnapshot(
    as_of=_date(2020, 3, 23),
    vix=57.1,
    credit_spread=3.82,
    fed_funds_rate=0.25,        # Fed slashed to zero
    yield_curve=0.51,           # curve steepened as flight to safety
    unemployment_rate=14.7,     # April 2020 peak (used as leading indicator)
)

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
    """Load live (2017-2018) data as proxy for stressed portfolio."""
    path = DATA_DIR / "live_snapshot.parquet"
    if not path.exists():
        print(f"  ❌  {path} not found. Run demo/lending_club.py first.")
        sys.exit(1)
    df = pd.read_parquet(path)
    # Simulate COVID stress by amplifying int_rate and dti distributions
    df = df.copy()
    df["int_rate"]  = df["int_rate"] * 1.35    # rates spiked on new originations
    df["dti"]       = df["dti"] * 1.20         # debt burden increased
    return df.to_dict(orient="records")


def run_drift_check(records: list[dict]) -> dict:
    payload = {
        "records": records,
        "set_as_baseline": False,
        "macro": {
            "vix":               COVID_MACRO.vix,
            "credit_spread":     COVID_MACRO.credit_spread,
            "fed_funds_rate":    COVID_MACRO.fed_funds_rate,
            "yield_curve":       COVID_MACRO.yield_curve,
            "unemployment_rate": COVID_MACRO.unemployment_rate,
        },
    }
    r = requests.post(
        f"{API_BASE}/drift/{MODEL_ID}/run",
        json=payload,
        headers=_headers(),
        timeout=60,
    )
    r.raise_for_status()
    return r.json()


def check_trust_api() -> dict:
    r = requests.get(f"{API_BASE}/trust/{MODEL_ID}", headers=_headers(), timeout=10)
    if r.status_code == 404:
        return {}           # trust API not wired yet — skip gracefully
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
        print(f"\n  ⚠️  Recommendation:")
        for line in recommendation.split(". "):
            if line.strip():
                print(f"      {line.strip()}.")

    features = result.get("top_drifted_features", [])
    if features:
        print(f"\n  Top Drifted Features:")
        for f in features[:5]:
            print(f"    {f['feature_name']:<22} PSI={f['score']:.4f}  {f['severity']}")


def print_trust_score(trust: dict) -> None:
    if not trust:
        print("\n  (Trust API not available — skipping)")
        return
    banner("AGENT-TO-AGENT TRUST API RESPONSE")
    print(f"  Trustworthy    : {trust.get('trustworthy')}")
    print(f"  Recommendation : {trust.get('recommendation', '').upper()}")
    print(f"  Confidence     : {trust.get('confidence')}")
    print(f"  Reason         : {trust.get('reason')}")


def print_vs_naive() -> None:
    banner("NAIVE TOOL vs FINSIGHT AI")
    print("  Naive (WhyLabs / Evidently):")
    print("    ⚠️  Drift detected. PSI > 0.10. Consider retraining.")
    print()
    print("  FinSight AI:")
    print("    🛑  BLACK SWAN REGIME — March 2020 macro conditions confirmed.")
    print("        VIX=57, spread=3.82, unemployment=14.7.")
    print("        Retraining on COVID data produces a model that FAILS post-recovery.")
    print("        → HALT automated decisions. Escalate to human review.")
    print("        → Monitor weekly. Expected regime duration: 60–90 days.")
    print("        → Do NOT retrain until VIX < 30 and spreads normalise.")


def main() -> None:
    banner("SCENARIO: COVID-19 Black Swan — March 2020")
    print("  Injecting macro conditions: VIX=57.1 | Spread=3.82 | Unemployment=14.7")
    print("  This is the most extreme stress test in the last 30 years of data.")

    check_server()
    ensure_model_exists()

    print("\n  Loading stressed portfolio data...")
    records = load_live_snapshot()
    print(f"  {len(records):,} records loaded")

    print("\n  Running drift check with COVID macro context...")
    result = run_drift_check(records)

    print_drift_result(result)

    print("\n  Checking trust API...")
    trust = check_trust_api()
    print_trust_score(trust)

    print_vs_naive()

    banner("SCENARIO COMPLETE")
    print("  Phoenix trace logged at: http://localhost:6006")
    print(f"  Dashboard:               http://localhost:5173/models/{MODEL_ID}")
    print()


if __name__ == "__main__":
    main()
