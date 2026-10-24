"""Day–night response (notebook v0.13, section 7).

Instead of the daily mean temperature, two forcings:

    CDD_day(d)   = max(T_day(d)   - Tc_day, 0),    T_day   = mean temperature 12-18 h
    CDD_night(d) = max(T_night(d) - Tc_night, 0),  T_night = mean temperature 0-6 h (the night that ends day d)

each with the same day and the day before. For a time band (e.g. 0-6 h) we ask to which
heat it responds, and whether that response grows across summers.

Alert 2 (time-band split changes in 2024-2025) affects any band analysis: a regime dummy
is included and the robust version uses only regime-A days.

Comments in Catalan follow the style of the thesis notebooks.
"""
import numpy as np
import pandas as pd

from .response import prepare, design_matrix, fit_cluster

DN = ["cdd_dia0", "cdd_dia1", "cdd_nit0", "cdd_nit1"]


def day_night_forcings(bands, tc_day=27.0, tc_night=20.0):
    """bands: DataFrame with 'data', 't_dia' (12-18 h) and 't_nit' (0-6 h). Adds the four forcings."""
    f = bands.sort_values("data").reset_index(drop=True).copy()
    for name, col, tc in [("dia", "t_dia", tc_day), ("nit", "t_nit", tc_night)]:
        f[f"cdd_{name}0"] = np.maximum(f[col] - tc, 0)
        f[f"cdd_{name}1"] = f[f"cdd_{name}0"].shift(1)     # el dia abans
    return f[["data"] + DN]


def day_night_response(consumption, temp, forcings, tc, lags=3, years=None, holidays=(), regime_b=(),
                       exclude=None, by_year=False):
    """Response of a series to day heat and night heat.

    The fixed effects are those of the main model (year, ISO week, weekday, holiday); the CDD of the
    daily mean is replaced by the four day/night forcings. regime_b: days of the alert-2 regime
    (a dummy is added). by_year: one pair of responses per summer.
    Returns (beta, cov).
    """
    t = prepare(consumption, temp, tc, lags, years=years)
    t = t.merge(forcings, on="data", how="left").dropna(subset=DN).reset_index(drop=True)
    if exclude is not None:
        t = t[~t["data"].isin(pd.to_datetime(list(exclude)))].reset_index(drop=True)
    yrs = sorted(t["data"].dt.year.unique()) if years is None else list(years)
    X = design_matrix(t, lags, years=yrs, holidays=holidays).drop(columns=[f"cdd{k}" for k in range(lags + 1)])
    if by_year:
        for a in yrs:
            m = (t["data"].dt.year == a).values.astype(float)
            for c in DN:
                X[f"{c}_{a}"] = t[c].values * m
    else:
        for c in DN:
            X[c] = t[c].values
    rb = t["data"].isin(pd.to_datetime(list(regime_b))).astype(float).values
    if rb.any():
        X["regim_B"] = rb
    X = X.loc[:, X.abs().sum() > 0]
    beta, cov, _ = fit_cluster(t, X)
    return beta, cov


def combo(beta, cov, weights):
    """Linear combination sum_i w_i beta_i (×100, % per K) and its standard error. weights: dict name -> w."""
    names = [n for n in weights if n in beta.index]
    w = np.array([weights[n] for n in names])
    return 100 * float(beta[names].values @ w), 100 * float(np.sqrt(w @ cov.loc[names, names].values @ w))


def day_night_summary(beta, cov, by_year=False, y0=None, y1=None):
    """Static responses to day and night heat (sum of the two lags) and, if by_year, their change y0→y1."""
    out = {}
    for name in ["dia", "nit"]:
        cols = [f"cdd_{name}0", f"cdd_{name}1"]
        if by_year:
            w = {f"{c}_{y1}": 1.0 for c in cols}
            w.update({f"{c}_{y0}": -1.0 for c in cols})
            out[f"canvi_{name}"], out[f"se_canvi_{name}"] = combo(beta, cov, w)
            out[f"{name}_{y0}"], out[f"se_{name}_{y0}"] = combo(beta, cov, {f"{c}_{y0}": 1.0 for c in cols})
            out[f"{name}_{y1}"], out[f"se_{name}_{y1}"] = combo(beta, cov, {f"{c}_{y1}": 1.0 for c in cols})
        else:
            out[name], out[f"se_{name}"] = combo(beta, cov, {c: 1.0 for c in cols})
    return out
