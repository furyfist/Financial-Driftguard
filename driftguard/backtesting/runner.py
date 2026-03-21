# driftguard/backtesting/runner.py
import logging
from dataclasses import dataclass
from datetime import date
from pathlib import Path

import pandas as pd

from ..regime.macro_signals import MacroSnapshot
from ..regime.tagger import RegimeTagger, Regime

logger = logging.getLogger(__name__)


@dataclass
class BacktestResult:
    date: date
    true_regime: str
    predicted_regime: str
    confidence: float
    vix: float
    credit_spread: float
    yield_curve: float
    fed_funds: float
    correct: bool


class BacktestRunner:
    """
    Replays 30 years of labelled macro history through the regime classifier.
    Compares ML predictions against ground truth labels from RegimeLabeller.

    This is the rigorous validation — not just spot checks.
    """

    def __init__(self, use_classifier: bool = True):
        self.tagger = RegimeTagger(use_classifier=use_classifier)

    def run(
        self,
        labelled_df: pd.DataFrame,
        start: str = "1990-01-01",
        end: str | None = None,
        sample_every_n_days: int = 5,   # weekly sampling — full daily is slow
    ) -> list[BacktestResult]:
        """
        Run backtest over labelled history.

        Args:
            labelled_df: output of RegimeLabeller.build()
            start: start date for backtest
            end: end date (defaults to last row)
            sample_every_n_days: sample frequency — 1=daily, 5=weekly, 21=monthly

        Returns:
            list of BacktestResult — one per sampled day
        """
        end = end or labelled_df.index[-1].strftime("%Y-%m-%d")

        df = labelled_df[
            (labelled_df.index >= pd.Timestamp(start)) &
            (labelled_df.index <= pd.Timestamp(end))
        ].copy()

        # Sample every N days to keep runtime reasonable
        df = df.iloc[::sample_every_n_days]

        logger.info(
            f"Backtesting {len(df):,} days "
            f"({start} → {end}, every {sample_every_n_days} days)"
        )

        results = []
        for dt, row in df.iterrows():
            macro = MacroSnapshot(
                as_of=dt.date(),
                vix=row.get("vix"),
                credit_spread=row.get("credit_spread"),
                fed_funds_rate=row.get("fed_funds"),
                yield_curve=row.get("yield_curve"),
                unemployment_rate=row.get("unemployment"),
            )

            # Use a neutral drift result — we're testing regime only
            from ..core.drift_result import DriftResult, DriftSeverity
            from datetime import datetime, timezone
            neutral = DriftResult(
                model_id="__backtest__",
                checked_at=datetime.now(timezone.utc),
                feature_results=[],
                overall_severity=DriftSeverity.NONE,
            )

            assessment = self.tagger.tag(neutral, macro)
            true_regime = row["regime"]

            results.append(BacktestResult(
                date=dt.date(),
                true_regime=true_regime,
                predicted_regime=assessment.regime.value,
                confidence=assessment.confidence,
                vix=row.get("vix", 0),
                credit_spread=row.get("credit_spread", 0),
                yield_curve=row.get("yield_curve", 0),
                fed_funds=row.get("fed_funds", 0),
                correct=(assessment.regime.value == true_regime),
            ))

        correct = sum(r.correct for r in results)
        logger.info(
            f"Backtest complete — "
            f"{correct}/{len(results)} correct "
            f"({correct/len(results)*100:.1f}%)"
        )
        return results

    def to_dataframe(self, results: list[BacktestResult]) -> pd.DataFrame:
        return pd.DataFrame([
            {
                "date":             r.date,
                "true_regime":      r.true_regime,
                "predicted_regime": r.predicted_regime,
                "confidence":       r.confidence,
                "correct":          r.correct,
                "vix":              r.vix,
                "credit_spread":    r.credit_spread,
                "yield_curve":      r.yield_curve,
                "fed_funds":        r.fed_funds,
            }
            for r in results
        ]).set_index("date")