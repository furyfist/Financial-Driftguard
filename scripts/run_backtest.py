import logging
import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

from driftguard.backtesting.runner import BacktestRunner
from driftguard.backtesting.report import BacktestReport

LABELS_PATH = "demo/data/regime_labels.parquet"

print("Loading labelled history...")
labelled = pd.read_parquet(LABELS_PATH)
print(f"Loaded {len(labelled):,} days ({labelled.index[0].date()} → {labelled.index[-1].date()})")

# Run backtest — weekly sampling, full 30yr history
print("\nRunning backtest (weekly sampling — ~1,900 data points)...")
runner  = BacktestRunner(use_classifier=True)
results = runner.run(
    labelled,
    start="1993-01-01",   # 3yr warmup for rolling features
    sample_every_n_days=5,
)

# Generate and print report
report = BacktestReport(results)
report.print_full_report()

# Save results
df = runner.to_dataframe(results)
df.to_parquet("demo/data/backtest_results.parquet")
print(f"\nResults saved to demo/data/backtest_results.parquet")
print(f"Total rows: {len(df):,}")