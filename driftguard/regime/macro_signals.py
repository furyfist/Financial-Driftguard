from dataclasses import dataclass
from datetime import date
from typing import Optional
import logging

logger = logging.getLogger(__name__)


@dataclass
class MacroSnapshot:
    """
    A point-in-time snapshot of macro indicators.
    All fields are Optional — signals may be unavailable offline.
    """
    as_of: date

    # Volatility
    vix: Optional[float] = None          # >30 = stress, >40 = crisis

    # Credit conditions
    credit_spread: Optional[float] = None  # BAA - AAA spread in bps, >150 = stress

    # Rate environment
    fed_funds_rate: Optional[float] = None
    yield_curve: Optional[float] = None   # 10Y - 2Y spread, <0 = inversion

    # Labour / real economy
    unemployment_rate: Optional[float] = None

    def is_complete(self) -> bool:
        return all(v is not None for v in [
            self.vix, self.credit_spread, self.fed_funds_rate,
            self.yield_curve, self.unemployment_rate
        ])


class MacroSignalFetcher:
    """
    Pulls macro indicators from FRED and Yahoo Finance.
    Requires FRED API key — free at https://fred.stlouisfed.org/docs/api/api_key.html
    Falls back gracefully if key is missing or network is unavailable.
    """

    # FRED series IDs
    _FRED_SERIES = {
        "fed_funds_rate":    "FEDFUNDS",
        "unemployment_rate": "UNRATE",
        "yield_curve":       "T10Y2Y",   # 10Y minus 2Y treasury spread
        "credit_spread":     "BAA10Y",   # Moody's BAA minus 10Y treasury
    }

    def __init__(self, fred_api_key: Optional[str] = None):
        self._fred_api_key = fred_api_key
        self._fred = None

        if fred_api_key:
            try:
                from fredapi import Fred
                self._fred = Fred(api_key=fred_api_key)
            except ImportError:
                logger.warning("fredapi not installed — FRED signals unavailable")

    def fetch(self, as_of: Optional[date] = None) -> MacroSnapshot:
        """
        Fetch macro snapshot as of a given date.
        Defaults to most recent available data.
        """
        target_date = as_of or date.today()
        snapshot = MacroSnapshot(as_of=target_date)

        snapshot.vix = self._fetch_vix(target_date)

        if self._fred:
            snapshot.fed_funds_rate   = self._fetch_fred("fed_funds_rate", target_date)
            snapshot.unemployment_rate = self._fetch_fred("unemployment_rate", target_date)
            snapshot.yield_curve      = self._fetch_fred("yield_curve", target_date)
            snapshot.credit_spread    = self._fetch_fred("credit_spread", target_date)
        else:
            logger.warning("FRED API key not set — only VIX available")

        return snapshot

    def _fetch_vix(self, as_of: date) -> Optional[float]:
        try:
            import yfinance as yf
            ticker = yf.Ticker("^VIX")
            hist = ticker.history(period="5d")
            if hist.empty:
                return None
            return round(float(hist["Close"].iloc[-1]), 2)
        except Exception as e:
            logger.warning(f"VIX fetch failed: {e}")
            return None

    def _fetch_fred(self, signal: str, as_of: date) -> Optional[float]:
        try:
            series_id = self._FRED_SERIES[signal]
            series = self._fred.get_series(
                series_id,
                observation_start=str(as_of.replace(day=1)),  # from month start
                observation_end=str(as_of),
            )
            if series.empty:
                return None
            return round(float(series.dropna().iloc[-1]), 4)
        except Exception as e:
            logger.warning(f"FRED fetch failed for {signal}: {e}")
            return None