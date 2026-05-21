"""
Scenario: Normal Model Decay — Stable Market Regime

Synthetic perturbation of the Lending Club feature distributions in a stable
macro environment (VIX normal, spreads tight, no regime stress). This represents
genuine model decay — the kind that SHOULD trigger retraining.

Expected output:
  Regime     : stable
  Severity   : HIGH or CRITICAL
  Action     : Investigate model decay. Trigger champion-challenger. Retrain.

This scenario demonstrates the contrast with the other two scenarios —
same severity, but now retraining IS the correct call because the regime
says the drift is internal, not macro-driven.

Usage (backend must be running):
  python demo/scenarios/normal_decay.py
"""

import sys
import time
import numpy as np
from pathlib import Path

import requests
import pandas as pd

# ── path setup ─────────────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

# ── config ─────────────────────────────────────────────────────────────────
API_BASE   = "http://localhost:8000"
MODEL_ID   = "lending_club_v1"
DATA_DIR   = ROOT / "demo" / "data"
RANDOM_SEED = 42

# Stable macro environment — no stress signals
STABLE_MACRO = {
    "vix":               14.5,    # below long-run average (~19)
    "credit_spread":     1.10,    # tight spreads, credit benign
    "fed_funds_rate":    2.50,    # rates stable, no hike in sight
    "yield_curve":       0.80,    # healthy positive slope
    "unemployment_rate": 3.7,     # near full employment
}

SEPARATOR = "─" * 60


def banner(title: str) -> None:
    print(f"\n{SEPARATOR}")
    print(f"  {title}")
    print(SEPARATOR)


def check_server() -> None:
    try:
        r = requests.get(f"{API_BASE}/health", timeout=5)
        r.raise_for_status()
    except Exception:
        print("\n❌  Backend not running. Start it with:")
        print("    uvicorn driftguard.api.main:app --reload")
        sys.exit(1)


def ensure_model_exists() -> None:
    r = requests.get(f"{API_BASE}/models/{MODEL_ID}", timeout=10)
    if r.status_code == 404:
        print(f"  Model '{MODEL_ID}' not found — run demo/lending_club.py first")
        sys.exit(1)


def load_and_perturb() -> tuple[list[dict], dict]:
    """
    Load baseline data and synthetically perturb it to simulate model decay.
    Returns (perturbed_records, perturbation_summary).

    Perturbations applied (simulate data pipeline drift or population shift):
      - dti:           +25% mean shift (debt burden of new applicants changed)
      - annual_inc:    -15% mean shift (income of applicants declined)
      - loan_amnt:     +20% mean shift (loan sizes increased)
      - revol_util:    +18% mean shift (revolving utilisation increased)
    """
    path = DATA_DIR / "baseline_snapshot.parquet"
    if not path.exists():
        print(f"  ❌  {path} not found. Run demo/lending_club.py first.")
        sys.exit(1)

    rng = np.random.default_rng(RANDOM_SEED)
    df  = pd.read_parquet(path).copy()

    perturbations = {
        "dti":        ("mean_shift", +0.25),
        "annual_inc": ("mean_shift", -0.15),
        "loan_amnt":  ("mean_shift", +0.20),
        "revol_util": ("mean_shift", +0.18),
    }

    applied = {}
    for col, (kind, factor) in perturbations.items():
        if col not in df.columns:
            continue
        if kind == "mean_shift":
            original_mean = df[col].mean()
            df[col] = df[col] * (1 + factor) + rng.normal(0, df[col].std() * 0.05, len(df))
            # clip to original range bounds to keep values plausible
            df[col] = df[col].clip(lower=0)
            applied[col] = {
                "original_mean": round(float(original_mean), 2),
                "new_mean":      round(float(df[col].mean()), 2),
                "shift_pct":     f"{factor:+.0%}",
            }

    return df.to_dict(orient="records"), applied


def run_drift_check(records: list[dict]) -> dict:
    payload = {
        "records": records,
        "set_as_baseline": False,
        "macro": STABLE_MACRO,
    }
    r = requests.post(
        f"{API_BASE}/drift/{MODEL_ID}/run",
        json=payload,
        timeout=60,
    )
    r.raise_for_status()
    return r.json()


def trigger_challenger() -> dict | None:
    """Attempt to trigger champion-challenger automation."""
    r = requests.post(
        f"{API_BASE}/experiments/{MODEL_ID}/challenger",
        timeout=30,
    )
    if r.status_code in (404, 501):
        return None         # endpoint not wired yet — skip gracefully
    r.raise_for_status()
    return r.json()


def print_perturbations(applied: dict) -> None:
    banner("SYNTHETIC PERTURBATIONS APPLIED")
    print("  Simulating applicant population shift (no macro cause):\n")
    for col, info in applied.items():
        print(
            f"  {col:<20}  {info['original_mean']:>10.1f} → {info['new_mean']:>10.1f}  "
            f"({info['shift_pct']})"
        )
    print()
    print("  Root cause: data pipeline change or underlying population drift.")
    print("  No macro signal explains this. This IS model decay.")


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


def print_key_contrast() -> None:
    banner("WHY THIS IS DIFFERENT FROM THE OTHER SCENARIOS")
    print()
    print("  Scenario 1 (Rate Hike 2017):  HIGH severity + credit_stress → DON'T retrain")
    print("  Scenario 2 (COVID 2020):      CRITICAL      + black_swan    → HALT")
    print("  Scenario 3 (This):            HIGH severity + stable        → RETRAIN ✅")
    print()
    print("  Same drift score. Same severity. Opposite recommended action.")
    print("  The regime is the deciding variable. No other tool makes this call.")


def main() -> None:
    banner("SCENARIO: Normal Model Decay — Stable Market Regime")
    print("  Synthetically perturbing applicant features in a calm macro environment.")
    print("  This simulates a data pipeline change or population shift — real model decay.")

    check_server()
    ensure_model_exists()

    print("\n  Loading and perturbing baseline data...")
    records, applied = load_and_perturb()
    print(f"  {len(records):,} records loaded and perturbed")

    print_perturbations(applied)

    print("\n  Running drift check with stable macro context...")
    result = run_drift_check(records)

    print_drift_result(result)

    # Try to trigger champion-challenger automation
    severity = result.get("overall_severity", "none")
    regime   = result.get("regime", "unknown")
    if severity in ("high", "critical") and regime == "stable":
        print("\n  Triggering champion-challenger automation...")
        challenger = trigger_challenger()
        if challenger:
            banner("CHAMPION-CHALLENGER TRIGGERED")
            print(f"  Experiment ID : {challenger.get('experiment_id', 'N/A')}")
            print(f"  Status        : {challenger.get('status', 'N/A')}")
            print("  View in Phoenix: http://localhost:6006")
        else:
            print("  (Champion-challenger endpoint not available — skipping)")

    print_key_contrast()

    banner("SCENARIO COMPLETE")
    print("  Phoenix trace logged at: http://localhost:6006")
    print(f"  Dashboard:               http://localhost:5173/models/{MODEL_ID}")
    print()


if __name__ == "__main__":
    main()
