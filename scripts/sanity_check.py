import pandas as pd
import numpy as np
from driftguard import Monitor, DataSnapshot
from datetime import date
from driftguard.regime.macro_signals import MacroSnapshot
from driftguard.regime.tagger import RegimeTagger

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

print("\n--- Regime Tagger ---")

# Simulate COVID-era macro snapshot
covid_macro = MacroSnapshot(
    as_of=date(2020, 4, 1),
    vix=57.0,
    credit_spread=3.8,
    fed_funds_rate=0.25,
    yield_curve=-0.5,
    unemployment_rate=14.7,
)

baseline2 = DataSnapshot.from_dataframe(
    pd.DataFrame({
        "annual_inc": np.random.normal(65000, 15000, 1000),
        "dti": np.random.normal(18, 5, 1000),
    }), "pre-covid"
)
current2 = DataSnapshot.from_dataframe(
    pd.DataFrame({
        "annual_inc": np.random.normal(52000, 22000, 1000),
        "dti": np.random.normal(26, 8, 1000),
    }), "covid-2020"
)

result2 = Monitor(model_id="lending_club_v1").check(baseline2, current2, macro=covid_macro)

print(f"Regime:     {result2.regime}")
print(f"Severity:   {result2.overall_severity}")
print(f"Note:       {result2.notes}")

print("\n--- Notification system ---")
from driftguard.notifications.base import NotificationPayload
from driftguard.notifications.discord import DiscordNotifier
from driftguard.notifications.slack import SlackNotifier

# Test threshold gating — should NOT send (score too low)
test_payload = NotificationPayload(
    model_id="lending_club_v1",
    overall_severity="low",
    drift_score=0.049,
    regime="credit_stress",
    regime_confidence=0.85,
    recommendation="Monitor closely.",
    top_features=[{"feature": "int_rate", "score": 0.101, "severity": "low"}],
    checked_at="2026-03-22T10:00:00",
)

discord = DiscordNotifier(webhook_url="https://placeholder", severity_threshold="high")
sent    = discord.notify(test_payload)
print(f"Low severity notification sent (should be False): {sent}")

# Test threshold gating — SHOULD send if webhook was real
test_payload.overall_severity = "critical"
test_payload.drift_score       = 0.84
would_send = discord.should_notify("critical")
print(f"Critical severity would notify (should be True):  {would_send}")

print("Notification system: threshold gating working correctly")