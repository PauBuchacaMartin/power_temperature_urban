"""Block bootstrap by ISO week (notebook v0.14, section 9).

Consecutive days are correlated, and the comfort threshold Tc is estimated from the same
data. An honest interval for the growth of the response must therefore (1) resample whole
weeks, not days, and (2) repeat EVERY data-driven choice inside each replicate (Tc
included). This module only resamples; the statistic passed in does the choices.

Comments in Catalan follow the style of the thesis notebooks.
"""
import numpy as np
import pandas as pd


def resample_weeks(series, rng, by_year=True):
    """One bootstrap sample: ISO weeks drawn with replacement (within each year if by_year).

    series: DataFrame with 'data' and 'kwh'. Weeks keep their real dates, so weather, calendar
    and lags stay aligned; a week drawn twice appears twice.
    """
    s = series.copy()
    iso = s["data"].dt.isocalendar()
    s["_setmana"] = iso["year"].astype(int).values * 100 + iso["week"].astype(int).values
    s["_any"] = s["data"].dt.year
    parts = []
    groups = s.groupby("_any") if by_year else [(None, s)]
    for _, g in groups:
        weeks = g["_setmana"].unique()
        drawn = rng.choice(weeks, size=len(weeks), replace=True)
        parts += [g[g["_setmana"] == w] for w in drawn]
    return pd.concat(parts, ignore_index=True).drop(columns=["_setmana", "_any"])


def block_bootstrap(series, statistic, n=200, seed=0, by_year=True):
    """Apply statistic(sample) -> dict of numbers to n week-resampled samples.

    Returns a DataFrame with one row per replicate (failed replicates are dropped and counted).
    """
    rng = np.random.default_rng(seed)
    rows, failed = [], 0
    for _ in range(n):
        try:
            rows.append(statistic(resample_weeks(series, rng, by_year)))
        except Exception:
            failed += 1
    out = pd.DataFrame(rows)
    out.attrs["failed"] = failed
    return out


def percentile_interval(values, level=0.95):
    """Central percentile interval (lo, hi) of a bootstrap distribution."""
    a = (1 - level) / 2
    v = pd.Series(values).dropna()
    return float(v.quantile(a)), float(v.quantile(1 - a))
