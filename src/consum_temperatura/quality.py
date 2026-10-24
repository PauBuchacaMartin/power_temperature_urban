"""Data quality for city-scale series (notebook v0.13, section 3).

The Open Data BCN / Datadis file has undocumented artefacts (audit of 24/10/2026):
postcode recoding, sector reclassifications, a coverage gap in services
(January-April 2023), single bad days and a change in the time-band split since 2024.

Rules used here:
- The article works at CITY scale: postcode recoding cancels out in the city sum.
- A day is kept only if every postcode alive in that quarter reports (complete days).
- Anomalies are found on the residual of a flexible TEMPERATURE model, so that
  heatwaves and cold spells (the signal) are never flagged as data errors.
- Two kinds of anomaly: single days (|z| > k) and blocks (rolling median of the
  residual beyond a threshold during >= min_days), which catch coverage gaps.

Comments in Catalan follow the style of the thesis notebooks.
"""
import numpy as np
import pandas as pd


def city_series(daily, sector=None, band=None, days=None):
    """Daily city total (columns 'data', 'kwh') from the postcode file.

    sector: a sector name, a list of names, or None (all sectors).
    band: a time band, or None (whole day). days: optional set of dates to keep.
    """
    d = daily
    if sector is not None:
        d = d[d["sector"].isin([sector] if isinstance(sector, str) else list(sector))]
    if band is not None:
        d = d[d["tram"] == band]
    s = d.groupby("data")["kwh"].sum()
    if days is not None:
        s = s[s.index.isin(pd.to_datetime(list(days)))]
    s = s[s > 0]
    return s.rename("kwh").reset_index()


def temperature_residuals(series, temp, holidays=(), col="tmean"):
    """Residual of ln E after a flexible model: 1 °C temperature bins + year + ISO week + weekday + holiday.

    The temperature bins absorb any shape of the V, so heatwaves and cold spells are explained
    and do not show up as anomalies. Returns a Series indexed by date.
    """
    v = series.merge(temp[["data", col]], on="data").dropna()
    v = v[v["kwh"] > 0].sort_values("data").reset_index(drop=True)
    hol = pd.to_datetime(pd.Series(list(holidays))) if len(holidays) else pd.Series([], dtype="datetime64[ns]")
    fe = pd.get_dummies(pd.DataFrame({
        "tbin": np.floor(v[col]).astype(int).astype(str),
        "any": v["data"].dt.year.astype(str),
        "setmana": v["data"].dt.isocalendar().week.astype(int).astype(str).values,
        "dia": v["data"].dt.dayofweek.astype(str),
        "festiu": v["data"].isin(hol).astype(str),
    }), drop_first=True).astype(float)
    X = np.column_stack([np.ones(len(v)), fe.values])
    y = np.log(v["kwh"].values)
    b, *_ = np.linalg.lstsq(X, y, rcond=None)
    return pd.Series(y - X @ b, index=v["data"].values)


def anomalies(series, temp, holidays=(), k=6.0, sigma_min=0.02, block_window=15, block_threshold=0.12,
              block_min_days=7, iterations=2, protect=()):
    """Find anomalous days of a city series, conditioned on temperature.

    Single days: |residual| > k robust sigmas, except the days in `protect` (extreme heat or
    cold: the signal), which are only reported.
    Blocks: centred rolling median of the residual BELOW -block_threshold (in log units)
    for at least block_min_days in a row: coverage gaps, weeks of missing supplies.
    Positive blocks are NOT data errors by default: a fortnight of persistent heat
    (5-14/08/2024) raises consumption above a daily-temperature model. They are reported
    in the column 'block_pos' and never excluded.
    The model is refitted without the flagged days (iterations), because a long gap
    biases the year effect of its own year.
    Returns a DataFrame indexed by date with columns residual, single, block, block_pos, protected.
    """
    s = series.copy()
    protect = pd.DatetimeIndex(pd.to_datetime(list(protect)))
    flagged = pd.DatetimeIndex([])
    for _ in range(iterations):
        r = temperature_residuals(s[~s["data"].isin(flagged)], temp, holidays)
        # residu de TOTS els dies amb el model ajustat sense els dolents
        r_all = _predict_residuals(series, s[~s["data"].isin(flagged)], temp, holidays)
        sigma = max(1.4826 * np.median(np.abs(r - np.median(r))), sigma_min)
        extreme = (r_all.abs() > k * sigma)
        is_protected = pd.Series(r_all.index.isin(protect), index=r_all.index)
        single = extreme & ~is_protected
        med = r_all.rolling(block_window, center=True, min_periods=block_window // 2).median()
        block = _runs(med < -block_threshold, block_min_days)
        block_pos = _runs(med > block_threshold, block_min_days)
        flagged = r_all.index[single | block]
    return pd.DataFrame({"residual": r_all, "single": single, "block": block, "block_pos": block_pos,
                         "protected": extreme & is_protected, "sigma": sigma})


def _runs(mask, min_days):
    """True on the days that belong to a run of at least min_days consecutive True values."""
    run = (mask != mask.shift()).cumsum()
    return mask & (mask.groupby(run).transform("sum") >= min_days)


def extreme_days(temp, summer_months=(6, 7, 8, 9), winter_months=(11, 12, 1, 2, 3), q=0.05):
    """Days of extreme heat (tmax above the summer 1-q quantile) or cold (tmean below the winter q quantile)."""
    hot = temp["tmax"] >= temp.loc[temp["data"].dt.month.isin(summer_months), "tmax"].quantile(1 - q)
    cold = temp["tmean"] <= temp.loc[temp["data"].dt.month.isin(winter_months), "tmean"].quantile(q)
    return set(temp.loc[hot | cold, "data"])


def _predict_residuals(series_all, series_fit, temp, holidays, col="tmean"):
    """Residuals of every day of series_all with the model fitted on series_fit (same design)."""
    def design(v, cols=None):
        hol = pd.to_datetime(pd.Series(list(holidays))) if len(holidays) else pd.Series([], dtype="datetime64[ns]")
        fe = pd.get_dummies(pd.DataFrame({
            "tbin": np.floor(v[col]).astype(int).astype(str),
            "any": v["data"].dt.year.astype(str),
            "setmana": v["data"].dt.isocalendar().week.astype(int).astype(str).values,
            "dia": v["data"].dt.dayofweek.astype(str),
            "festiu": v["data"].isin(hol).astype(str),
        })).astype(float)
        fe.insert(0, "const", 1.0)
        return fe if cols is None else fe.reindex(columns=cols, fill_value=0.0)
    vf = series_fit.merge(temp[["data", col]], on="data").dropna()
    vf = vf[vf["kwh"] > 0].sort_values("data").reset_index(drop=True)
    Xf = design(vf)
    b, *_ = np.linalg.lstsq(Xf.values, np.log(vf["kwh"].values), rcond=None)
    va = series_all.merge(temp[["data", col]], on="data").dropna()
    va = va[va["kwh"] > 0].sort_values("data").reset_index(drop=True)
    Xa = design(va, Xf.columns)
    return pd.Series(np.log(va["kwh"].values) - Xa.values @ b, index=va["data"].values)


def clean_days(series, temp, holidays=(), complete=None, **kw):
    """Days to analyse for one series: complete days without single-day or block anomalies.

    Returns (set of good days, anomalies DataFrame).
    """
    s = series if complete is None else series[series["data"].isin(pd.to_datetime(list(complete)))]
    an = anomalies(s, temp, holidays, **kw)
    bad = set(an.index[an["single"] | an["block"]])
    good = set(s["data"]) - bad
    return good, an


def anomaly_blocks(an, col="block"):
    """Summary of the block anomalies: one row per run (start, end, days, median residual in %)."""
    b = an[col]
    if not b.any():
        return pd.DataFrame(columns=["inici", "fi", "dies", "residu_mediana_pct"])
    run = (b != b.shift()).cumsum()
    rows = []
    for _, g in an[b].groupby(run[b]):
        rows.append({"inici": g.index.min().date(), "fi": g.index.max().date(), "dies": len(g),
                     "residu_mediana_pct": round(100 * float(np.median(g["residual"])), 1)})
    return pd.DataFrame(rows)


def sector_shares(daily, freq="Q"):
    """Share (%) of each sector in the city total, by period: reclassifications show up as jumps."""
    d = daily.groupby(["data", "sector"])["kwh"].sum().unstack().fillna(0)
    p = d.groupby(d.index.to_period(freq)).sum()
    return 100 * p.div(p.sum(axis=1), axis=0)
