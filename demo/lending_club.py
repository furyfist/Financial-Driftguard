import json
import pickle
import pandas as pd
from pathlib import Path
import requests, json

from driftguard import Monitor, DataSnapshot
from driftguard.regime.macro_signals import MacroSnapshot
from driftguard.regime.tagger import RegimeTagger
from datetime import date

BASE = "http://localhost:8000"
DATA_DIR = Path(__file__).parent / "data"


def load_artifacts():
    with open(DATA_DIR / "lending_club_model.pkl", "rb") as f:
        model = pickle.load(f)
    with open(DATA_DIR / "feature_columns.json") as f:
        features = json.load(f)
    baseline_df = pd.read_parquet(DATA_DIR / "baseline_snapshot.parquet")
    live_df     = pd.read_parquet(DATA_DIR / "live_snapshot.parquet")
    return model, features, baseline_df, live_df


def run_demo():
    print("=" * 60)
    print("DriftGuard — Lending Club Credit Default Demo")
    print("=" * 60)

    model, features, baseline_df, live_df = load_artifacts()
    print(f"\nModel loaded: {model.__class__.__name__}")
    print(f"Features:     {len(features)}")
    print(f"Baseline rows:{len(baseline_df):,}  (2016 loans)")
    print(f"Live rows:    {len(live_df):,}  (2017-2018 loans)")

    # Build snapshots
    baseline_snap = DataSnapshot.from_dataframe(baseline_df, label="baseline-2016")
    live_snap     = DataSnapshot.from_dataframe(live_df,     label="live-2017-2018")

    # Simulate macro context for the live period
    # 2017-2018: Fed was hiking rates — credit stress building
    macro = MacroSnapshot(
        as_of=date(2018, 1, 1),
        vix=17.0,              # calm but rising
        credit_spread=1.6,     # slightly elevated
        fed_funds_rate=1.5,    # Fed hiking cycle underway
        yield_curve=0.5,       # flattening
        unemployment_rate=4.1, # low but credit stress building
    )

    # Run DriftGuard
    monitor = Monitor(model_id="lending_club_lgbm_v1", features=features)
    result  = monitor.check(baseline_snap, live_snap, macro=macro)

    # Print results
    print(f"\n{'─'*60}")
    print(f"Overall severity : {result.overall_severity.value.upper()}")
    print(f"Drift score      : {result.drift_score:.4f}")
    print(f"Regime           : {result.regime}")
    print(f"Recommendation   : {result.notes}")
    print(f"{'─'*60}")

    print(f"\nPer-feature drift (sorted by PSI score):")
    psi_results = [f for f in result.feature_results if f.detector == "psi"]
    psi_results.sort(key=lambda x: x.score, reverse=True)

    print(f"  {'Feature':<22} {'PSI Score':<12} {'Severity'}")
    print(f"  {'─'*22} {'─'*12} {'─'*10}")
    for f in psi_results:
        flag = " ⚠" if f.score > 0.25 else (" ↑" if f.score > 0.10 else "")
        print(f"  {f.feature_name:<22} {f.score:<12.4f} {f.severity.value}{flag}")

    print(f"\nDrifted features : {len(result.drifted_features)} / {len(features)}")

    # Show prediction distribution shift
    print(f"\n{'─'*60}")
    print("Prediction distribution shift:")
    baseline_preds = model.predict_proba(baseline_df.fillna(baseline_df.median()))[:, 1]
    live_preds     = model.predict_proba(live_df.fillna(live_df.median()))[:, 1]
    print(f"  Baseline mean score : {baseline_preds.mean():.4f}")
    print(f"  Live mean score     : {live_preds.mean():.4f}")
    print(f"  Delta               : {live_preds.mean() - baseline_preds.mean():+.4f}")

    return result

def seed_api():
    _, features, baseline_df, live_df = load_artifacts()

    # Set baseline
    requests.post(f"{BASE}/drift/lending_club_v1/run", json={
        "records": baseline_df.fillna(0).to_dict("records"),
        "set_as_baseline": True
    })
    print("Baseline set via API")

    # Run drift check with live data
    resp = requests.post(f"{BASE}/drift/lending_club_v1/run", json={
        "records": live_df.fillna(0).to_dict("records"),
        "set_as_baseline": False
    })
    print("Drift run:", resp.json())

if __name__ == "__main__":
    run_demo()
    seed_api()