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

# VIX regime thresholds — calibrated to historical distribution
# Below 15: calm. 15-25: normal. 25-35: elevated. 35+: crisis.
_VIX_CALM       = 15.0
_VIX_ELEVATED   = 25.0
_VIX_CRISIS     = 35.0
_VIX_BLACK_SWAN = 45.0

# Credit spread thresholds (BAA minus 10Y Treasury, in percentage points)
_SPREAD_NORMAL  = 1.5
_SPREAD_STRESS  = 2.5
_SPREAD_CRISIS  = 4.0


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
        Returns (regime_label, confidence, sources_agreed).

        Priority order matters — black_swan before recession,
        recession before rate_shock, etc.
        """
        # black_swan: extreme VIX AND extreme spread — both must fire
        if vix >= _VIX_BLACK_SWAN and spread >= _SPREAD_CRISIS:
            sources = sum([
                vix >= _VIX_BLACK_SWAN,
                spread >= _SPREAD_CRISIS,
                in_recession,
            ])
            return "black_swan", round(sources / 3, 2), sources

        # recession: NBER official OR (high VIX + yield inversion + spread stress)
        vix_recession  = vix >= _VIX_CRISIS
        spread_stress  = spread >= _SPREAD_STRESS
        curve_inverted = yield_curve < 0.0

        recession_signals = sum([
            in_recession,
            vix_recession and spread_stress,
            curve_inverted and spread_stress,
        ])
        if recession_signals >= 2:
            return "recession", round(recession_signals / 3, 2), recession_signals

        if in_recession:
            return "recession", 0.6, 1

        # rate_shock: in Fed tightening cycle + VIX elevated
        if in_rate_shock and vix >= _VIX_ELEVATED:
            sources = sum([in_rate_shock, vix >= _VIX_ELEVATED, spread >= _SPREAD_NORMAL])
            return "rate_shock", round(sources / 3, 2), sources

        # credit_stress: elevated VIX OR spread stress, outside recession
        if vix >= _VIX_ELEVATED or spread >= _SPREAD_NORMAL:
            sources = sum([
                vix >= _VIX_ELEVATED,
                spread >= _SPREAD_NORMAL,
                yield_curve < 0.5,
            ])
            return "credit_stress", round(sources / 3, 2), sources

        # stable: nothing firing
        sources = sum([
            vix < _VIX_ELEVATED,
            spread < _SPREAD_NORMAL,
            yield_curve > 0.0,
        ])
        return "stable", round(sources / 3, 2), sources

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