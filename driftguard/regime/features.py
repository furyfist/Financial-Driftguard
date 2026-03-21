import numpy as np
import pandas as pd


# Window sizes for rolling features
_SHORT  = 5    # 1 trading week
_MEDIUM = 21   # 1 trading month
_LONG   = 63   # 1 trading quarter


def build_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Transforms raw macro signals into classifier features.

    Key insight: static values tell you where you are.
    Derivatives and momentum tell you where you're going.
    Regime transitions are detected by the *rate of change*,
    not the level.

    Input columns expected:
        vix, credit_spread, yield_curve, fed_funds, unemployment

    Returns a new DataFrame with engineered features only.
    Drops rows with NaN (from rolling window warmup period).
    """
    f = pd.DataFrame(index=df.index)

    # Raw levels — still useful as context
    f["vix"]            = df["vix"]
    f["credit_spread"]  = df["credit_spread"]
    f["yield_curve"]    = df["yield_curve"]
    f["fed_funds"]      = df["fed_funds"]
    f["unemployment"]   = df["unemployment"]

    # VIX features — volatility is the most informative signal
    f["vix_5d_mean"]    = df["vix"].rolling(_SHORT).mean()
    f["vix_21d_mean"]   = df["vix"].rolling(_MEDIUM).mean()
    f["vix_5d_max"]     = df["vix"].rolling(_SHORT).max()
    f["vix_21d_max"]    = df["vix"].rolling(_MEDIUM).max()
    f["vix_5d_change"]  = df["vix"].pct_change(_SHORT)
    f["vix_21d_change"] = df["vix"].pct_change(_MEDIUM)

    # VIX regime: ratio of short-term mean to long-term mean
    # > 1 means volatility is spiking relative to recent history
    f["vix_short_long_ratio"] = (
        df["vix"].rolling(_SHORT).mean() /
        df["vix"].rolling(_LONG).mean().clip(lower=0.1)
    )

    # VIX realised vs expected — how much has vol deviated from 63d norm
    vix_63d_mean = df["vix"].rolling(_LONG).mean()
    vix_63d_std  = df["vix"].rolling(_LONG).std().clip(lower=0.1)
    f["vix_zscore"] = (df["vix"] - vix_63d_mean) / vix_63d_std

    # Credit spread features — forward-looking financial conditions
    f["spread_5d_mean"]    = df["credit_spread"].rolling(_SHORT).mean()
    f["spread_21d_mean"]   = df["credit_spread"].rolling(_MEDIUM).mean()
    f["spread_5d_change"]  = df["credit_spread"].diff(_SHORT)
    f["spread_21d_change"] = df["credit_spread"].diff(_MEDIUM)
    f["spread_63d_change"] = df["credit_spread"].diff(_LONG)

    # Spread momentum — is it accelerating or decelerating?
    spread_5d_chg  = df["credit_spread"].diff(_SHORT)
    spread_21d_chg = df["credit_spread"].diff(_MEDIUM)
    f["spread_momentum"] = spread_5d_chg - (spread_21d_chg / (_MEDIUM / _SHORT))

    # Yield curve features — recession predictor par excellence
    f["yield_curve_5d_mean"]   = df["yield_curve"].rolling(_SHORT).mean()
    f["yield_curve_21d_mean"]  = df["yield_curve"].rolling(_MEDIUM).mean()
    f["yield_curve_slope"]     = df["yield_curve"].diff(_SHORT)
    f["yield_curve_inverted"]  = (df["yield_curve"] < 0).astype(int)

    # Inversion duration — persistent inversion is more predictive than brief
    # Counts consecutive days yield curve has been inverted
    inverted     = (df["yield_curve"] < 0).astype(int)
    inv_duration = inverted.groupby(
        (inverted != inverted.shift()).cumsum()
    ).cumcount()
    f["yield_inversion_days"] = inv_duration * inverted

    # Fed funds features — rate cycle detection
    f["fed_funds_5d_change"]  = df["fed_funds"].diff(_SHORT)
    f["fed_funds_21d_change"] = df["fed_funds"].diff(_MEDIUM)
    f["fed_funds_63d_change"] = df["fed_funds"].diff(_LONG)

    # Hiking/cutting signal: positive = hiking, negative = cutting
    f["rate_direction"] = np.sign(df["fed_funds"].diff(_MEDIUM))

    # Unemployment features — lagging but confirms recession
    f["unemp_21d_change"] = df["unemployment"].diff(_MEDIUM)
    f["unemp_63d_change"] = df["unemployment"].diff(_LONG)

    # Composite stress index — weighted combination of normalised signals
    # Each component normalised to [0,1] range using rolling 252d window
    def rolling_norm(series: pd.Series, window: int = 252) -> pd.Series:
        rolling_min = series.rolling(window, min_periods=50).min()
        rolling_max = series.rolling(window, min_periods=50).max()
        denom = (rolling_max - rolling_min).clip(lower=1e-6)
        return (series - rolling_min) / denom

    vix_norm    = rolling_norm(df["vix"])
    spread_norm = rolling_norm(df["credit_spread"])
    unemp_norm  = rolling_norm(df["unemployment"])

    f["composite_stress"] = (
        0.4 * vix_norm +
        0.4 * spread_norm +
        0.2 * unemp_norm
    )

    # Cross-signal features — interactions that capture regime transitions
    # High VIX + widening spreads = financial stress amplifying
    f["vix_x_spread"] = f["vix_zscore"] * f["spread_21d_change"].clip(-5, 5)

    # Inverted curve + rising VIX = classic recession setup
    f["curve_vix_signal"] = f["yield_curve_inverted"] * f["vix_zscore"].clip(0)

    return f.dropna()


def feature_names() -> list[str]:
    """Returns list of all feature column names — used by classifier."""
    dummy = pd.DataFrame({
        "vix":           [20.0] * 100,
        "credit_spread": [2.5]  * 100,
        "yield_curve":   [0.5]  * 100,
        "fed_funds":     [2.0]  * 100,
        "unemployment":  [4.5]  * 100,
    })
    return list(build_features(dummy).columns)