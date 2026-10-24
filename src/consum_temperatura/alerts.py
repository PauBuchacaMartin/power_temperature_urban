"""Data-quality alerts found while building article 1 (see docs/article1.md).

Alert 1: postcode recoding (meters moving between postcodes, zero-sum at city level).
Alert 2: change of regime in the time-band split of consumption since 2024.
"""
import numpy as np
import pandas as pd


def band_regime(daily_bands, evening="18-24", morning="06-12", ref_until=2023, threshold=-2.5):
    """Days whose evening share departs from the reference-weeks climatology.

    daily_bands: DataFrame index = date, columns include the two band names (kWh).
    Share = evening / (evening + morning). Anomaly in percentage points against the
    median of the same ISO week in years <= ref_until. Returns (anomaly Series, set of regime-B days).
    """
    share = daily_bands[evening] / (daily_bands[evening] + daily_bands[morning])
    ref = share[share.index.year <= ref_until]
    clim = ref.groupby(ref.index.isocalendar().week.values).median()
    anom = 100 * (share - clim.reindex(share.index.isocalendar().week.values).values)
    return anom, set(anom.index[anom < threshold])


def complete_days(daily_cp):
    """Days on which every postcode alive in that quarter reports data (city sums are then comparable)."""
    n_day = daily_cp.groupby("data")["cp"].nunique()
    alive = daily_cp.groupby(daily_cp["data"].dt.to_period("Q"))["cp"].nunique()
    expected = pd.Series(alive.reindex(n_day.index.to_period("Q")).values, index=n_day.index)
    return n_day.index[n_day >= expected]


def level_jumps(series, window=60, threshold=0.15):
    """Persistent level shifts of a daily series: log-ratio of window means after/before each date.

    Returns a DataFrame of candidate jump dates with the log-ratio, |log-ratio| > threshold.
    """
    s = np.log(series.sort_index())
    # mitjanes de les finestres anterior (fins al dia d-1) i posterior (des del dia d):
    # el contrast és màxim just al dia del salt
    before = s.rolling(window, min_periods=window).mean().shift(1)
    after = s[::-1].rolling(window, min_periods=window).mean()[::-1]
    jump = (after - before).dropna()
    cand = jump[jump.abs() > threshold]
    if cand.empty:
        return pd.DataFrame(columns=["data", "log_ratio"])
    # una data per salt: el màxim absolut de cada grup de dates seguides
    grp = (cand.index.to_series().diff().dt.days.fillna(1) > 1).cumsum()
    rows = [(g.abs().idxmax(), float(g.loc[g.abs().idxmax()])) for _, g in cand.groupby(grp.values)]
    return pd.DataFrame(rows, columns=["data", "log_ratio"])
