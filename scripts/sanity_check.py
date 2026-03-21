import pandas as pd
import numpy as np
from driftguard import Monitor, DataSnapshot

# Simulate pre-COVID vs COVID credit data
np.random.seed(42)
baseline_df = pd.DataFrame({
    "annual_inc": np.random.normal(65000, 15000, 1000),
    "dti":        np.random.normal(18, 5, 1000),
    "fico_score": np.random.normal(700, 40, 1000),
})
current_df = pd.DataFrame({
    "annual_inc": np.random.normal(52000, 22000, 1000),  # income dropped, variance up
    "dti":        np.random.normal(26, 8, 1000),          # debt-to-income spiked
    "fico_score": np.random.normal(680, 45, 1000),
})

baseline = DataSnapshot.from_dataframe(baseline_df, label="pre-covid")
current  = DataSnapshot.from_dataframe(current_df,  label="covid-2020")

monitor = Monitor(model_id="lending_club_v1")
result = monitor.check(baseline, current)

print(f"Overall severity: {result.overall_severity}")
print(f"Drift score: {result.drift_score}")
for f in result.drifted_features:
    print(f"  {f.feature_name} [{f.detector}] → {f.severity} (score={f.score})")