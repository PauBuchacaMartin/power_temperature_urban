"""Linear response of log electricity consumption to temperature forcing.

Model (per spatial unit, summer days):

    ln E(d) = sum_k chi_k * CDD(d - k) + fixed effects (year, ISO week, weekday, holiday) + eps

The static susceptibility chi0 = sum_k chi_k is the % change of consumption per
degree-day (x100). Standard errors are cluster-robust by ISO week, because
residuals of consecutive days are correlated.
"""
import numpy as np
import pandas as pd

from .forcings import cooling_degree_days


def design_matrix(table, lags=3, years=None, holidays=(), by_year=False):
    """Regressors: CDD lags (optionally interacted with year) + fixed effects.

    table must contain 'data' and cdd0..cdd{lags}. holidays: iterable of dates.
    """
    years = sorted(table["data"].dt.year.unique()) if years is None else list(years)
    cdd_cols = [f"cdd{k}" for k in range(lags + 1)]
    if by_year:
        # una funció de resposta per estiu: CDD x indicador d'any
        parts = {}
        yr = table["data"].dt.year.values
        for a in years:
            for c in cdd_cols:
                parts[f"{c}_{a}"] = table[c].values * (yr == a)
        X_cdd = pd.DataFrame(parts)
    else:
        X_cdd = table[cdd_cols].reset_index(drop=True)
    cat = lambda v, cats: pd.Categorical(v, categories=cats)
    hol = pd.to_datetime(pd.Series(list(holidays))) if len(holidays) else pd.Series([], dtype="datetime64[ns]")
    fe = pd.get_dummies(pd.DataFrame({
        "any": cat(table["data"].dt.year.values, years),
        "setmana": cat(table["data"].dt.isocalendar().week.astype(int).values, list(range(1, 54))),
        "dia": cat(table["data"].dt.dayofweek.values, list(range(7))),
        "festiu": cat(table["data"].isin(hol).values, [False, True]),
    }), drop_first=True).astype(float)
    X = pd.concat([X_cdd.reset_index(drop=True), fe.reset_index(drop=True)], axis=1)
    X = X.loc[:, X.abs().sum() > 0]              # treu columnes buides (efectes sense dades)
    X.insert(0, "const", 1.0)
    return X


def fit_cluster(table, X, y=None):
    """OLS with cluster-robust covariance by ISO week. Returns (beta, cov, residuals)."""
    if y is None:
        y = np.log(table["kwh"].values)
    Xv = X.values.astype(float)
    beta, *_ = np.linalg.lstsq(Xv, y, rcond=None)
    res = y - Xv @ beta
    n, p = Xv.shape
    pinv = np.linalg.pinv(Xv.T @ Xv)
    iso = table["data"].dt.isocalendar()
    g = (iso["year"].astype(int) * 100 + iso["week"].astype(int)).values
    groups = np.unique(g)
    if len(groups) > 1:
        meat = np.zeros((p, p))
        for gi in groups:
            s = Xv[g == gi].T @ res[g == gi]
            meat += np.outer(s, s)
        G = len(groups)
        cov = pinv @ meat @ pinv * (G / (G - 1)) * ((n - 1) / max(n - p, 1))
    else:
        cov = (res @ res / max(n - p, 1)) * pinv
    return pd.Series(beta, index=X.columns), pd.DataFrame(cov, index=X.columns, columns=X.columns), res


def prepare(consumption, temp, tc, lags=3, months=(6, 7, 8, 9), years=None):
    """Merge daily consumption ('data','kwh') with CDD lags; keep summer days of the chosen years."""
    t = cooling_degree_days(temp, tc, lags)
    table = consumption.merge(t, on="data")
    table = table[table["data"].dt.month.isin(months)]
    if years is not None:
        table = table[table["data"].dt.year.isin(years)]
    return table.dropna().reset_index(drop=True)


def static_susceptibility(beta, cov, lags=3, suffix="", prefix="cdd"):
    """chi0 = 100 * sum_k chi_k (% per degree-day) and its standard error.

    prefix: "cdd" (heat branch) or "hdd" (cold branch).
    """
    names = [f"{prefix}{k}{suffix}" for k in range(lags + 1)]
    names = [n for n in names if n in beta.index]
    w = np.ones(len(names))
    chi = 100 * float(beta[names].values @ w)
    se = 100 * float(np.sqrt(w @ cov.loc[names, names].values @ w))
    return chi, se


def fit_city(consumption, temp, tc, lags=3, holidays=(), exclude=None, **kw):
    """Static response of a whole series. exclude: iterable of dates to drop (e.g. heatwave days)."""
    table = prepare(consumption, temp, tc, lags, **kw)
    if exclude is not None:
        table = table[~table["data"].isin(pd.to_datetime(list(exclude)))].reset_index(drop=True)
    X = design_matrix(table, lags, holidays=holidays)
    beta, cov, res = fit_cluster(table, X)
    chi, se = static_susceptibility(beta, cov, lags)
    return {"chi0": chi, "se": se, "beta": beta, "cov": cov, "n": len(table), "mse": float(np.mean(res ** 2))}


def choose_tc(consumption, temp, candidates=np.arange(18.0, 25.5, 0.5), lags=3, holidays=(), **kw):
    """Comfort temperature that minimises the in-sample mean squared error."""
    rows = []
    for tc in candidates:
        r = fit_city(consumption, temp, tc, lags, holidays, **kw)
        rows.append((tc, r["mse"]))
    prof = pd.DataFrame(rows, columns=["tc", "mse"])
    return float(prof.loc[prof["mse"].idxmin(), "tc"]), prof


def response_by_year(consumption, temp, tc, lags=3, years=None, holidays=(), exclude=None, **kw):
    """chi0 for each summer (CDD x year interaction) and growth between two years.

    exclude: iterable of dates to drop (e.g. heatwave days, as in section 20d of the notebook).
    """
    table = prepare(consumption, temp, tc, lags, years=years, **kw)
    if exclude is not None:
        table = table[~table["data"].isin(pd.to_datetime(list(exclude)))].reset_index(drop=True)
    years = sorted(table["data"].dt.year.unique()) if years is None else list(years)
    X = design_matrix(table, lags, years=years, holidays=holidays, by_year=True)
    beta, cov, _ = fit_cluster(table, X)
    out = {}
    for a in years:
        out[a] = static_susceptibility(beta, cov, lags, suffix=f"_{a}")
    return pd.DataFrame(out, index=["chi0", "se"]).T, beta, cov


def growth(beta, cov, y0, y1, lags=3, prefix="cdd"):
    """Difference chi0(y1) - chi0(y0) with its standard error (covariances included).

    prefix: "cdd" for summers (labels = years), "hdd" for winters (labels = starting year).
    """
    n0 = [f"{prefix}{k}_{y0}" for k in range(lags + 1)]
    n1 = [f"{prefix}{k}_{y1}" for k in range(lags + 1)]
    names = n0 + n1
    w = np.r_[-np.ones(len(n0)), np.ones(len(n1))]
    d = 100 * float(beta[names].values @ w)
    se = 100 * float(np.sqrt(w @ cov.loc[names, names].values @ w))
    return d, se


def threshold_factor(curves, errors, ref=None, max_iter=200):
    """Common shape x factor per year: curves[b, year] ~ g(b) * lambda(year), lambda(ref) = 1.

    curves, errors: DataFrames (index = temperature bins above the threshold, columns = years).
    Weighted alternating least squares, as in section 20k of the v0.11 notebook.
    Returns (lambda Series, se Series, shape g Series, chi2, dof).
    """
    y, s = curves, errors
    ref = y.columns[0] if ref is None else ref
    lam = pd.Series(1.0, index=y.columns)
    for _ in range(max_iter):
        g = (y * lam / s ** 2).sum(axis=1) / ((lam ** 2) / s ** 2).sum(axis=1)
        new = (y.mul(g, axis=0) / s ** 2).sum() / ((s ** -2).mul(g ** 2, axis=0)).sum()
        new = new / new[ref]
        if np.allclose(new, lam, atol=1e-10):
            lam = new
            break
        lam = new
    g = (y * lam / s ** 2).sum(axis=1) / ((lam ** 2) / s ** 2).sum(axis=1)
    pred = pd.DataFrame(np.outer(g, lam), index=y.index, columns=y.columns)
    chi2 = float((((y - pred) / s) ** 2).sum().sum())
    dof = int(y.notna().sum().sum()) - len(y.index) - (len(y.columns) - 1)
    se = 1 / np.sqrt(((s ** -2).mul(g ** 2, axis=0)).sum())
    return lam, se, g, chi2, dof


def extensive_share(n0, n1, lam0, lam1):
    """Share of the log-growth of the response explained by more appliances.

    Minimal model chi ∝ n_AC · u  =>  ln(lam1/lam0) = ln(n1/n0) + ln(u1/u0).
    """
    return float(np.log(n1 / n0) / np.log(lam1 / lam0))
