# scripts/train_regime_classifier.py
import logging
import pandas as pd

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s: %(message)s"
)

from driftguard.regime.labeller import RegimeLabeller
from driftguard.regime.classifier import RegimeClassifier
from driftguard.regime.macro_signals import MacroSnapshot
from datetime import date

print("=" * 60)
print("DriftGuard — Regime Classifier Training")
print("=" * 60)

# Load pre-built labels — build if missing
LABELS_PATH = "demo/data/regime_labels.parquet"
try:
    labelled = pd.read_parquet(LABELS_PATH)
    print(f"\nLoaded existing labels: {len(labelled):,} days")
except FileNotFoundError:
    print("\nLabels not found — building from FRED...")
    labeller = RegimeLabeller()
    labelled  = labeller.build(start="1990-01-01")
    labeller.save(labelled)

print(f"Date range: {labelled.index[0].date()} → {labelled.index[-1].date()}")
print(f"Label distribution:\n{labelled['regime'].value_counts().to_string()}")

# Train — walk-forward split at end of 2019
print(f"\nTraining on 1990-2019, validating on 2020-present...")
print(f"KEY TEST: must identify 2020 COVID crash as black_swan\n")

clf = RegimeClassifier()
metrics = clf.train(labelled, train_end="2019-12-31", verbose=True)

# Feature importance
print(f"\nTop 15 most important features:")
importance = clf.feature_importance(top_n=15)
for _, row in importance.iterrows():
    bar = "█" * int(row["importance"] / importance["importance"].max() * 20)
    print(f"  {row['feature']:<28} {bar} {row['importance']:.0f}")

# The key validation test
print(f"\n{'='*60}")
print(f"KEY VALIDATION TESTS")
print(f"{'='*60}")

test_cases = [
    {
        "label": "COVID crash (Mar 2020)",
        "expected": "black_swan",
        "macro": MacroSnapshot(
            as_of=date(2020, 3, 16),
            vix=82.0,
            credit_spread=4.5,
            fed_funds_rate=1.0,
            yield_curve=-0.3,
            unemployment_rate=4.4,
        ),
    },
    {
        "label": "GFC peak (Oct 2008)",
        "expected": "black_swan",
        "macro": MacroSnapshot(
            as_of=date(2008, 10, 15),
            vix=69.0,
            credit_spread=6.5,
            fed_funds_rate=1.5,
            yield_curve=2.1,
            unemployment_rate=6.5,
        ),
    },
    {
        "label": "Fed hiking cycle (Jan 2017)",
        "expected": "stable",
        "macro": MacroSnapshot(
            as_of=date(2017, 1, 3),
            vix=11.3,
            credit_spread=2.4,
            fed_funds_rate=0.66,
            yield_curve=1.26,
            unemployment_rate=4.7,
        ),
    },
    {
        "label": "Calm period (Jan 2014)",
        "expected": "stable",
        "macro": MacroSnapshot(
            as_of=date(2014, 1, 2),
            vix=14.2,
            credit_spread=2.73,
            fed_funds_rate=0.09,
            yield_curve=2.73,
            unemployment_rate=6.7,
        ),
    },
    {
        "label": "Rate shock (Dec 2018)",
        "expected": "credit_stress",
        "macro": MacroSnapshot(
            as_of=date(2018, 12, 24),
            vix=36.0,
            credit_spread=3.2,
            fed_funds_rate=2.4,
            yield_curve=0.1,
            unemployment_rate=3.9,
        ),
    },
]

print(f"\n  {'Test case':<30} {'Expected':<15} {'Got':<15} {'Conf':<6} {'Match'}")
print(f"  {'─'*30} {'─'*15} {'─'*15} {'─'*6} {'─'*5}")
passed = 0
for tc in test_cases:
    regime, conf, proba = clf.predict(tc["macro"])
    match  = "✓" if regime == tc["expected"] else "✗"
    passed += (regime == tc["expected"])
    print(f"  {tc['label']:<30} {tc['expected']:<15} {regime:<15} {conf:<6.3f} {match}")

print(f"\n  Passed: {passed}/{len(test_cases)}")

# Save
clf.save()
print(f"\nClassifier saved to demo/data/regime_classifier.pkl")
print(f"\n{'='*60}")
print(f"Training complete")
print(f"{'='*60}")