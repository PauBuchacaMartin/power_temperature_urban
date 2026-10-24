"""Forcings: turn temperature series into the regressors of the response model.

Comments in Catalan follow the style of the thesis notebooks.
"""
import numpy as np
import pandas as pd


def cooling_degree_days(temp, tc, lags=3, col="tmean"):
    """Add cooling degree days with lags: cdd_k(d) = max(T(d-k) - tc, 0), k = 0..lags.

    temp: DataFrame with a 'data' (date) column and a temperature column `col`.
    """
    t = temp.sort_values("data").copy()
    for k in range(lags + 1):
        # graus-dia de refrigeració del dia d-k
        t[f"cdd{k}"] = np.maximum(t[col].shift(k) - tc, 0)
    return t


def heating_degree_days(temp, th, lags=3, col="tmean"):
    """Add heating degree days with lags: hdd_k(d) = max(th - T(d-k), 0)."""
    t = temp.sort_values("data").copy()
    for k in range(lags + 1):
        t[f"hdd{k}"] = np.maximum(th - t[col].shift(k), 0)
    return t


def heatwaves(temp, percentile=0.95, min_days=3, months=(6, 7, 8, 9), col="tmax"):
    """Boolean Series: days inside a run of >= min_days with tmax above the summer percentile."""
    summer = temp[temp["data"].dt.month.isin(months)]
    threshold = summer[col].quantile(percentile)
    hot = temp[col] >= threshold
    run_id = (hot != hot.shift()).cumsum()          # numera les ratxes consecutives
    run_len = hot.groupby(run_id).transform("sum")
    return hot & (run_len >= min_days)


def band_temperatures(hourly, bands=None):
    """Daily mean temperature in hour bands (e.g. night 0-6 h, day 12-18 h).

    hourly: DataFrame with 'hora' (timestamp) and 'temp'.
    bands: dict name -> (first_hour, last_hour_exclusive).
    """
    if bands is None:
        bands = {"nit": (0, 6), "dia": (12, 18)}
    h = hourly.copy()
    h["data"] = h["hora"].dt.normalize()
    h["h"] = h["hora"].dt.hour
    out = None
    for name, (a, b) in bands.items():
        m = h[(h["h"] >= a) & (h["h"] < b)].groupby("data", as_index=False)["temp"].mean()
        m = m.rename(columns={"temp": f"t_{name}"})
        out = m if out is None else out.merge(m, on="data", how="outer")
    return out.sort_values("data").reset_index(drop=True)
