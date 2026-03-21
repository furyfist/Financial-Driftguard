import logging
import os
from dataclasses import dataclass
from datetime import date, timedelta

import numpy as np
import pandas as pd
from dotenv import load_dotenv
from fredapi import Fred

load_dotenv()
logger = logging.getLogger(__name__)


# NBER recession periods — official start/end dates
# Source: https://www.nber.org/research/business-cycle-dating
# These are monthly precision dates — we treat the first of each month
# as the boundary. Labelled in hindsight, but that's correct for training.
_NBER_RECESSIONS = [
    ("1990-07-01", "1991-03-31"),  # Gulf War recession
    ("2001-03-01", "2001-11-30"),  # Dot-com bust
    ("2007-12-01", "2009-06-30"),  # Global Financial Crisis
    ("2020-02-01", "2020-04-30"),  # COVID-19 (shortest on record)
]

# Fed tightening cycles — rapid rate hike periods
# Identified by Fed Funds rate rising > 200bps within 12 months
_RATE_SHOCK_PERIODS = [
    ("1994-02-01", "1995-02-28"),  # Greenspan tightening
    ("1999-06-01", "2000-05-31"),  # Pre dot-com tightening
    ("2004-06-01", "2006-06-30"),  # Measured pace tightening
    ("2015-12-01", "2018-12-31"),  # Post-GFC normalisation
    ("2022-03-01", "2023-07-31"),  # Post-COVID inflation fight
]

# Updated threshold constants — data-driven from 30-year percentiles
# VIX: 75th=22.72, 90th=28.60, 95th=32.95, 99th=46.68
_VIX_CALM       = 18.0   # below median (50th=17.59)
_VIX_ELEVATED   = 23.0   # ~75th percentile
_VIX_CRISIS     = 30.0   # ~90th percentile
_VIX_BLACK_SWAN = 45.0   # ~99th percentile

# Credit spread: 25th=1.75, 50th=2.15, 75th=2.69, 90th=3.16, 99th=5.46
# Old 1.5 threshold fired on 94.9% of days — recalibrated to 75th+
_SPREAD_NORMAL  = 2.80   # above 75th percentile — genuinely elevated
_SPREAD_STRESS  = 3.50   # ~90th percentile
_SPREAD_CRISIS  = 5.00   # ~99th percentile


@dataclass
class LabelledDay:
    date: date
    regime: str
    confidence: float       # 0–1, how many sources agreed
    vix: float
    credit_spread: float
    yield_curve: float
    fed_funds: float
    in_nber_recession: bool
    in_rate_shock: bool
    sources_agreed: int     # how many of 3 sources gave same signal


class RegimeLabeller:
    """
    Constructs a daily regime label series from 1990 to present.
    Uses three independent sources — NBER, VIX, credit spreads.
    Confidence is proportional to source agreement.

    This is the ground truth the ML classifier trains on.
    """

    def __init__(self, fred_api_key: str | None = None):
        key = fred_api_key or os.getenv("FRED_API_KEY")
        if not key:
            raise ValueError(
                "FRED API key required. Set FRED_API_KEY in .env "
                "or pass fred_api_key= to RegimeLabeller()"
            )
        self._fred = Fred(api_key=key)

    def build(
        self,
        start: str = "1990-01-01",
        end: str | None = None,
    ) -> pd.DataFrame:
        """
        Build and return the full labelled regime dataframe.

        Columns: date, regime, confidence, vix, credit_spread,
                 yield_curve, fed_funds, in_nber_recession,
                 in_rate_shock, sources_agreed
        """
        end = end or date.today().isoformat()
        logger.info(f"Fetching macro data {start} → {end}")

        raw = self._fetch_all(start, end)
        logger.info(f"Raw data fetched — {len(raw)} trading days")

        labelled = self._label(raw)

        # V2: merge rate_shock into credit_stress
        # Both mean "macro-driven shift, monitor don't retrain"
        # Keeping them separate hurts classifier recall with no operational benefit
        labelled["regime"] = labelled["regime"].replace("rate_shock", "credit_stress")

        logger.info(
            f"Labelling complete\n"
            f"{labelled['regime'].value_counts().to_string()}"
        )
        return labelled

    def _fetch_all(self, start: str, end: str) -> pd.DataFrame:
        series = {
            "vix":           self._fetch("VIXCLS",   start, end),
            "credit_spread": self._fetch("BAA10Y",   start, end),
            "yield_curve":   self._fetch("T10Y2Y",   start, end),
            "fed_funds":     self._fetch("FEDFUNDS",  start, end),
            "unemployment":  self._fetch("UNRATE",    start, end),
        }

        df = pd.DataFrame(series)
        df.index = pd.to_datetime(df.index)
        df.index.name = "date"

        # Forward-fill missing values — macro series have gaps (weekends,
        # monthly releases). ffill is correct here: the last known value
        # is our best estimate until the next release.
        df = df.ffill().dropna()

        # Unemployment is monthly — ffill propagates it to daily correctly
        return df

    def _fetch(self, series_id: str, start: str, end: str) -> pd.Series:
        try:
            s = self._fred.get_series(
                series_id,
                observation_start=start,
                observation_end=end,
            )
            return s
        except Exception as e:
            logger.error(f"Failed to fetch {series_id}: {e}")
            raise

    def _label(self, df: pd.DataFrame) -> pd.DataFrame:
        result = []

        nber_mask       = self._nber_mask(df.index)
        rate_shock_mask = self._rate_shock_mask(df.index)

        for dt, row in df.iterrows():
            vix    = row["vix"]
            spread = row["credit_spread"]
            yc     = row["yield_curve"]
            ff     = row["fed_funds"]

            in_recession  = nber_mask.get(dt, False)
            in_rate_shock = rate_shock_mask.get(dt, False)

            regime, confidence, sources = self._classify_day(
                vix=vix,
                spread=spread,
                yield_curve=yc,
                in_recession=in_recession,
                in_rate_shock=in_rate_shock,
            )

            result.append({
                "date":              dt,
                "regime":            regime,
                "confidence":        confidence,
                "vix":               vix,
                "credit_spread":     spread,
                "yield_curve":       yc,
                "fed_funds":         ff,
                "unemployment":      row["unemployment"],
                "in_nber_recession": in_recession,
                "in_rate_shock":     in_rate_shock,
                "sources_agreed":    sources,
            })

        return pd.DataFrame(result).set_index("date")

    def _classify_day(
        self,
        vix: float,
        spread: float,
        yield_curve: float,
        in_recession: bool,
        in_rate_shock: bool,
    ) -> tuple[str, float, int]:
        """
        Priority: black_swan → recession → rate_shock → credit_stress → stable

        Key insight from data diagnostics:
        - Spread median is 2.15 — old 1.5 threshold fired on 95% of days
        - VIX 75th percentile is 22.72 — 23.0 is genuinely elevated
        - COVID peak VIX hit 82 intraday — daily data clears 45 threshold
        - GFC peak VIX hit 80 — clears black_swan correctly
        """
        # black_swan: extreme VIX OR (crisis VIX + crisis spread)
        # Either signal alone can trigger if extreme enough
        if vix >= _VIX_BLACK_SWAN:
            sources = sum([
                vix >= _VIX_BLACK_SWAN,
                spread >= _SPREAD_STRESS,
                in_recession,
            ])
            return "black_swan", round(min(sources / 3 + 0.33, 1.0), 2), sources

        if vix >= _VIX_CRISIS and spread >= _SPREAD_CRISIS:
            return "black_swan", 1.0, 3

        # recession: NBER official + supporting signals
        # NBER alone = 0.6 confidence, with supporting signals = higher
        if in_recession:
            supporting = sum([
                vix >= _VIX_ELEVATED,
                spread >= _SPREAD_NORMAL,
                yield_curve < 0.0,
            ])
            confidence = round(0.5 + (supporting / 3) * 0.5, 2)
            return "recession", confidence, supporting + 1

        # recession without NBER label — leading indicators firing
        recession_signals = sum([
            vix >= _VIX_CRISIS and spread >= _SPREAD_STRESS,
            yield_curve < 0.0 and spread >= _SPREAD_STRESS,
            spread >= _SPREAD_CRISIS,
        ])
        if recession_signals >= 2:
            return "recession", round(recession_signals / 3, 2), recession_signals

        # rate_shock: in Fed tightening cycle AND market showing stress
        # Pure rate hike into calm market = stable, not rate_shock
        # Requires VIX above calm threshold as minimum condition
        if in_rate_shock:
            stress_present = sum([
                vix >= _VIX_ELEVATED,           # market pricing in risk
                spread >= _SPREAD_NORMAL,        # credit conditions tightening
                yield_curve < 0.5,              # curve flattening under hikes
            ])
            # Only label rate_shock if at least 2 stress signals present
            # Pure hiking into calm = stable
            if stress_present >= 2:
                confidence = round(0.4 + (stress_present / 3) * 0.4, 2)
                return "rate_shock", confidence, stress_present

        # credit_stress: elevated VIX or spread above normal
        # Uses recalibrated _SPREAD_NORMAL = 2.80 (75th pct) — not 1.5
        stress_signals = sum([
            vix >= _VIX_ELEVATED,
            spread >= _SPREAD_NORMAL,
            yield_curve < 0.5 and vix > _VIX_CALM,
        ])
        if stress_signals >= 1:
            return "credit_stress", round(stress_signals / 3, 2), stress_signals

        # stable: everything calm
        stable_signals = sum([
            vix < _VIX_ELEVATED,
            spread < _SPREAD_NORMAL,
            yield_curve > 0.0,
        ])
        return "stable", round(stable_signals / 3, 2), stable_signals

    def _nber_mask(self, index: pd.DatetimeIndex) -> dict:
        mask = {}
        for start_str, end_str in _NBER_RECESSIONS:
            start = pd.Timestamp(start_str)
            end   = pd.Timestamp(end_str)
            for dt in index:
                if start <= dt <= end:
                    mask[dt] = True
        return mask

    def _rate_shock_mask(self, index: pd.DatetimeIndex) -> dict:
        mask = {}
        for start_str, end_str in _RATE_SHOCK_PERIODS:
            start = pd.Timestamp(start_str)
            end   = pd.Timestamp(end_str)
            for dt in index:
                if start <= dt <= end:
                    mask[dt] = True
        return mask

    def save(self, df: pd.DataFrame, path: str = "demo/data/regime_labels.parquet"):
        df.to_parquet(path)
        logger.info(f"Regime labels saved to {path}")

    def load(self, path: str = "demo/data/regime_labels.parquet") -> pd.DataFrame:
        return pd.read_parquet(path)
        