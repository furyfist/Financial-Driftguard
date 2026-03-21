import pandas as pd
import numpy as np
from sklearn.metrics import (
    classification_report,
    confusion_matrix,
    accuracy_score,
)

from .runner import BacktestResult

_REGIME_ORDER = [
    "stable",
    "credit_stress",
    "recession",
    "black_swan",
]


class BacktestReport:
    """
    Generates a comprehensive validation report from backtest results.
    This is the proof the classifier generalises across 30 years.
    """

    def __init__(self, results: list[BacktestResult]):
        self.results = results
        self.df      = pd.DataFrame([
            {
                "date":             r.date,
                "true":             r.true_regime,
                "predicted":        r.predicted_regime,
                "confidence":       r.confidence,
                "correct":          r.correct,
                "vix":              r.vix,
                "credit_spread":    r.credit_spread,
            }
            for r in results
        ])

    def summary(self) -> dict:
        total   = len(self.df)
        correct = self.df["correct"].sum()
        return {
            "total_days_tested":  total,
            "correct":            int(correct),
            "accuracy":           round(correct / total, 4),
            "mean_confidence":    round(self.df["confidence"].mean(), 4),
            "high_conf_accuracy": round(
                self.df[self.df["confidence"] >= 0.6]["correct"].mean(), 4
            ),
        }

    def per_regime_metrics(self) -> pd.DataFrame:
        true      = self.df["true"].tolist()
        predicted = self.df["predicted"].tolist()

        report = classification_report(
            true, predicted,
            labels=_REGIME_ORDER,
            output_dict=True,
            zero_division=0,
        )

        rows = []
        for regime in _REGIME_ORDER:
            if regime in report:
                m = report[regime]
                rows.append({
                    "regime":    regime,
                    "precision": round(m["precision"], 3),
                    "recall":    round(m["recall"],    3),
                    "f1":        round(m["f1-score"],  3),
                    "support":   int(m["support"]),
                })
        return pd.DataFrame(rows).set_index("regime")

    def confusion_matrix(self) -> pd.DataFrame:
        true      = self.df["true"].tolist()
        predicted = self.df["predicted"].tolist()
        cm = confusion_matrix(true, predicted, labels=_REGIME_ORDER)
        return pd.DataFrame(cm, index=_REGIME_ORDER, columns=_REGIME_ORDER)

    def errors_by_period(self) -> pd.DataFrame:
        """Shows where the classifier was wrong — useful for debugging."""
        errors = self.df[~self.df["correct"]].copy()
        errors["date"] = pd.to_datetime(errors["date"])
        return errors.sort_values("date")

    def regime_timeline(self) -> pd.DataFrame:
        """Returns true vs predicted regime over time — for chart."""
        timeline = self.df[["date", "true", "predicted", "confidence"]].copy()
        timeline["date"] = pd.to_datetime(timeline["date"])
        return timeline.set_index("date")

    def print_full_report(self):
        s = self.summary()
        print("=" * 60)
        print("DRIFTGUARD REGIME CLASSIFIER — BACKTEST REPORT")
        print("=" * 60)
        print(f"\nOverall accuracy:      {s['accuracy']*100:.1f}%")
        print(f"Total days tested:     {s['total_days_tested']:,}")
        print(f"Correct predictions:   {s['correct']:,}")
        print(f"Mean confidence:       {s['mean_confidence']:.3f}")
        print(f"High-conf accuracy:    {s['high_conf_accuracy']*100:.1f}%  (conf ≥ 0.6)")

        print(f"\n{'─'*60}")
        print("Per-regime metrics:")
        print(f"{'─'*60}")
        metrics = self.per_regime_metrics()
        print(f"  {'Regime':<15} {'Precision':>10} {'Recall':>8} {'F1':>8} {'Support':>9}")
        print(f"  {'─'*15} {'─'*10} {'─'*8} {'─'*8} {'─'*9}")
        for regime, row in metrics.iterrows():
            flag = ""
            if regime == "black_swan" and row["recall"] >= 0.8:
                flag = "  ← key test ✓"
            elif regime == "recession" and row["recall"] >= 0.5:
                flag = "  ← improved"
            print(
                f"  {regime:<15} {row['precision']:>10.3f} "
                f"{row['recall']:>8.3f} {row['f1']:>8.3f} "
                f"{row['support']:>9}{flag}"
            )

        print(f"\n{'─'*60}")
        print("Confusion matrix (rows=actual, cols=predicted):")
        print(f"{'─'*60}")
        cm = self.confusion_matrix()
        print(cm.to_string())

        print(f"\n{'─'*60}")
        print("Most common misclassifications:")
        print(f"{'─'*60}")
        errors = self.errors_by_period()
        if len(errors) > 0:
            mistake_counts = (
                errors.groupby(["true", "predicted"])
                .size()
                .reset_index(name="count")
                .sort_values("count", ascending=False)
                .head(8)
            )
            for _, row in mistake_counts.iterrows():
                print(
                    f"  {row['true']:<15} → predicted as "
                    f"{row['predicted']:<15} ({row['count']} times)"
                )
        else:
            print("  No misclassifications!")

        print(f"\n{'─'*60}")
        print("Key historical period checks:")
        print(f"{'─'*60}")
        periods = {
            "GFC peak":        ("2008-09-01", "2009-03-31", "black_swan"),
            "Post-GFC calm":   ("2012-01-01", "2013-12-31", "stable"),
            "Rate hike cycle": ("2017-01-01", "2018-12-31", "credit_stress"),  # was rate_shock
            "COVID crash":     ("2020-02-01", "2020-04-30", "black_swan"),
            "COVID recovery":  ("2020-05-01", "2020-12-31", "credit_stress"),  # new
            "Post-COVID":      ("2021-01-01", "2021-12-31", "stable"),
            "2022 hikes":      ("2022-03-01", "2023-06-30", "credit_stress"),  # was rate_shock
        }
        df_timeline = self.df.copy()
        df_timeline["date"] = pd.to_datetime(df_timeline["date"])

        print(f"  {'Period':<20} {'Expected':<15} {'Accuracy':>10} {'Days':>6}")
        print(f"  {'─'*20} {'─'*15} {'─'*10} {'─'*6}")
        for label, (start, end, expected) in periods.items():
            mask = (
                (df_timeline["date"] >= start) &
                (df_timeline["date"] <= end)
            )
            period_df = df_timeline[mask]
            if len(period_df) == 0:
                continue
            acc = (period_df["predicted"] == expected).mean()
            print(
                f"  {label:<20} {expected:<15} "
                f"{acc*100:>9.1f}%  {len(period_df):>5}"
            )