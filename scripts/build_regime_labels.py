import logging
import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

from driftguard.regime.labeller import RegimeLabeller

labeller = RegimeLabeller()

print("Fetching 30 years of macro data from FRED...")
df = labeller.build(start="1990-01-01")

print(f"\nTotal trading days labelled: {len(df):,}")
print(f"\nRegime distribution:")
counts = df["regime"].value_counts()
total  = len(df)
for regime, count in counts.items():
    pct = count / total * 100
    print(f"  {regime:<15} {count:>5,} days  ({pct:.1f}%)")

print(f"\nConfidence stats:")
print(f"  Mean:   {df['confidence'].mean():.3f}")
print(f"  Median: {df['confidence'].median():.3f}")
print(f"  Low-confidence days (<0.4): {(df['confidence'] < 0.4).sum():,}")

print(f"\nSpot checks — known events:")
checks = {
    "2008-10-15": "recession",    # GFC peak
    "2009-03-09": "recession",    # GFC bottom
    "2020-03-16": "black_swan",   # COVID crash week
    "2020-06-01": "recession",    # COVID recovery start
    "2018-12-24": "credit_stress", # Fed overtightening selloff
    "2017-01-03": "rate_shock",   # Fed hiking cycle
    "2014-01-02": "stable",       # calm period
}

print(f"\n  {'Date':<12} {'Expected':<15} {'Got':<15} {'Conf':<6} {'Match'}")
print(f"  {'─'*12} {'─'*15} {'─'*15} {'─'*6} {'─'*5}")
for date_str, expected in checks.items():
    if date_str in df.index.strftime("%Y-%m-%d").tolist():
        row = df[df.index.strftime("%Y-%m-%d") == date_str].iloc[0]
        got   = row["regime"]
        conf  = row["confidence"]
        match = "✓" if got == expected else "✗"
        print(f"  {date_str:<12} {expected:<15} {got:<15} {conf:<6.2f} {match}")
    else:
        print(f"  {date_str:<12} {expected:<15} {'(no data)':<15}")

labeller.save(df)
print(f"\nSaved to demo/data/regime_labels.parquet")
print(f"\nSignal distribution diagnostics:")
print(f"\nVIX percentiles:")
for p in [25, 50, 75, 90, 95, 99]:
    print(f"  {p}th: {df['vix'].quantile(p/100):.2f}")

print(f"\nCredit spread percentiles:")
for p in [25, 50, 75, 90, 95, 99]:
    print(f"  {p}th: {df['credit_spread'].quantile(p/100):.2f}")

print(f"\nYield curve percentiles:")
for p in [10, 25, 50, 75, 90]:
    print(f"  {p}th: {df['yield_curve'].quantile(p/100):.2f}")

print(f"\nDays above each threshold:")
print(f"  VIX > 25:     {(df['vix'] > 25).sum():,}  ({(df['vix'] > 25).mean()*100:.1f}%)")
print(f"  VIX > 35:     {(df['vix'] > 35).sum():,}  ({(df['vix'] > 35).mean()*100:.1f}%)")
print(f"  VIX > 45:     {(df['vix'] > 45).sum():,}  ({(df['vix'] > 45).mean()*100:.1f}%)")
print(f"  Spread > 1.5: {(df['credit_spread'] > 1.5).sum():,}  ({(df['credit_spread'] > 1.5).mean()*100:.1f}%)")
print(f"  Spread > 2.5: {(df['credit_spread'] > 2.5).sum():,}  ({(df['credit_spread'] > 2.5).mean()*100:.1f}%)")
print(f"  Spread > 4.0: {(df['credit_spread'] > 4.0).sum():,}  ({(df['credit_spread'] > 4.0).mean()*100:.1f}%)")
print(f"  Yield < 0:    {(df['yield_curve'] < 0).sum():,}  ({(df['yield_curve'] < 0).mean()*100:.1f}%)")

print(f"\nSpread during known regimes:")
gfc = df["2007-12-01":"2009-06-30"]
covid = df["2020-02-01":"2020-04-30"]
calm = df["2012-01-01":"2014-12-31"]
print(f"  GFC (2007-2009) spread mean:   {gfc['credit_spread'].mean():.2f}")
print(f"  COVID (2020 Q1) spread mean:   {covid['credit_spread'].mean():.2f}")
print(f"  Calm (2012-2014) spread mean:  {calm['credit_spread'].mean():.2f}")
print(f"\nVIX during known regimes:")
print(f"  GFC (2007-2009) VIX mean:      {gfc['vix'].mean():.2f}")
print(f"  COVID (2020 Q1) VIX mean:      {covid['vix'].mean():.2f}")
print(f"  Calm (2012-2014) VIX mean:     {calm['vix'].mean():.2f}")