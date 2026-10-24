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


def response_by_year(consumption, temp, tc, lags=3, years=None, holidays=(), exclude=None, extra=None, **kw):
    """chi0 for each summer (CDD x year interaction) and growth between two years.

    exclude: iterable of dates to drop (e.g. heatwave days, as in section 22d of notebook v0.12.1).
    extra: optional function table -> DataFrame of additional regressors (same row order), e.g. a
    common quadratic term, humidity or price controls. Their coefficients are in the returned beta.
    """
    table = prepare(consumption, temp, tc, lags, years=years, **kw)
    if exclude is not None:
        table = table[~table["data"].isin(pd.to_datetime(list(exclude)))].reset_index(drop=True)
    years = sorted(table["data"].dt.year.unique()) if years is None else list(years)
    X = design_matrix(table, lags, years=years, holidays=holidays, by_year=True)
    if extra is not None:
        X = pd.concat([X, extra(table).reset_index(drop=True)], axis=1)
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
    Weighted alternating least squares, as in section 22k of notebook v0.12.1 (20k in v0.11).
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


# ---------------------------------------------------------------------------
# v0.13: funcions de l'article 1 (resposta absoluta, onades, corbes, correlacions)
# ---------------------------------------------------------------------------

def absolute_response_by_year(consumption, temp, tc, lags=3, years=None, holidays=(), exclude=None, scale=1e3):
    """Response in absolute units (default MWh/day per degree-day) for each summer.

    Same design as response_by_year but on kWh/scale instead of ln kWh: if only the
    baseline fell, the relative response could grow while the absolute one does not.
    Returns a DataFrame year -> (resp, se).
    """
    table = prepare(consumption, temp, tc, lags, years=years)
    if exclude is not None:
        table = table[~table["data"].isin(pd.to_datetime(list(exclude)))].reset_index(drop=True)
    years = sorted(table["data"].dt.year.unique()) if years is None else list(years)
    X = design_matrix(table, lags, years=years, holidays=holidays, by_year=True)
    beta, cov, _ = fit_cluster(table, X, y=table["kwh"].values / scale)
    out = {}
    for a in years:
        names = [f"cdd{k}_{a}" for k in range(lags + 1) if f"cdd{k}_{a}" in beta.index]
        w = np.ones(len(names))
        out[a] = (float(beta[names].values @ w), float(np.sqrt(w @ cov.loc[names, names].values @ w)))
    return pd.DataFrame(out, index=["resp", "se"]).T


def heatwave_residuals(consumption, temp, tc, waves, lags=3, years=None, holidays=()):
    """Linearity test with a response that may change every summer.

    The model with one response function per summer is fitted WITHOUT the heatwave days and
    then predicts them with the response of their own summer. Residual = ln E observed − predicted
    (×100 ≈ %). Positive: amplification; negative: saturation.
    Returns (per-day DataFrame, per-year summary, standard deviation of normal-day residuals in %).
    """
    table = prepare(consumption, temp, tc, lags, years=years)
    waves = pd.to_datetime(list(waves))
    years = sorted(table["data"].dt.year.unique()) if years is None else list(years)
    normal = table[~table["data"].isin(waves)].reset_index(drop=True)
    hot = table[table["data"].isin(waves)].reset_index(drop=True)
    Xn = design_matrix(normal, lags, years=years, holidays=holidays, by_year=True)
    beta, cov, res_n = fit_cluster(normal, Xn)
    sd = 100 * float(np.std(res_n, ddof=Xn.shape[1]))
    if hot.empty:
        return hot, pd.DataFrame(), sd
    Xh = design_matrix(hot, lags, years=years, holidays=holidays, by_year=True).reindex(columns=Xn.columns, fill_value=0.0)
    hot["residu_pct"] = 100 * (np.log(hot["kwh"].values) - Xh.values @ beta.values)
    summ = hot.groupby(hot["data"].dt.year)["residu_pct"].agg(["mean", "count"])
    summ["se_aprox"] = sd / np.sqrt(summ["count"])        # optimista: els dies d'una onada no són independents
    return hot[["data", "tmean", "residu_pct"]], summ, sd


def response_curves(consumption, temp, years, holidays=(), bins=range(21, 29), floor=20, window=3,
                    months=(6, 7, 8, 9), exclude=None):
    """Non-parametric response curve of each summer (no imposed shape).

    Regressors: indicators of 1 °C bins of the `window`-day mean temperature (≤ floor is the
    reference; the last bin collects everything above), one set per summer, plus year, ISO week,
    weekday and holiday effects. Returns (curves, errors) in log units ×100 (≈ % above the
    reference), index = bins, columns = years.
    """
    bins = list(bins)
    t = consumption.merge(temp[["data", "tmean"]], on="data")
    tm = temp.sort_values("data").set_index("data")["tmean"].rolling(window).mean()
    t["tm"] = t["data"].map(tm)
    t = t[t["data"].dt.month.isin(months) & t["data"].dt.year.isin(years)].dropna().reset_index(drop=True)
    if exclude is not None:
        t = t[~t["data"].isin(pd.to_datetime(list(exclude)))].reset_index(drop=True)
    t["bin"] = np.clip(np.floor(t["tm"]), floor, bins[-1]).astype(int)
    cat = lambda v, c: pd.Categorical(v, categories=c)
    hol = pd.to_datetime(pd.Series(list(holidays))) if len(holidays) else pd.Series([], dtype="datetime64[ns]")
    parts = [pd.get_dummies(pd.DataFrame({
        "setmana": cat(t["data"].dt.isocalendar().week.astype(int).values, list(range(1, 54))),
        "dia": cat(t["data"].dt.dayofweek.values, list(range(7))),
        "festiu": cat(t["data"].isin(hol).values, [False, True])}), drop_first=True).astype(float)]
    for a in years:
        m = (t["data"].dt.year == a).values
        parts.append(pd.DataFrame({f"any{a}": m.astype(float)}))
        parts.append(pd.DataFrame({f"b{b}_{a}": (m & (t["bin"] == b).values).astype(float) for b in bins}))
    X = pd.concat(parts, axis=1)
    X = X.loc[:, X.abs().sum() > 0]
    beta, cov, _ = fit_cluster(t, X)
    Y = pd.DataFrame({a: {b: 100 * beta[f"b{b}_{a}"] for b in bins if f"b{b}_{a}" in beta.index} for a in years})
    S = pd.DataFrame({a: {b: 100 * np.sqrt(cov.loc[f"b{b}_{a}", f"b{b}_{a}"]) for b in bins if f"b{b}_{a}" in beta.index}
                      for a in years})
    return Y, S


def curves_equal(curves, errors):
    """Chi-square test that every summer has the same value in each bin (weighted mean per bin).

    Returns (chi2, degrees of freedom).
    """
    chi2, dof = 0.0, 0
    for b in curves.index:
        y, s = curves.loc[b].dropna(), errors.loc[b].dropna()
        w = 1 / s ** 2
        m = (w * y).sum() / w.sum()
        chi2 += float((((y - m) / s) ** 2).sum())
        dof += len(y) - 1
    return chi2, dof


def correlation_check(consumption, temp, tc, lags=3, years=None, holidays=(), exclude=None):
    """Response function from lagged covariances (a fluctuation-response consistency check).

    After projecting out the fixed effects, chi = C_TT^{-1} C_ET, with C the lagged covariances
    of the CDD forcing and of ln E. For a linear system driven by an observed forcing it must
    agree with the regression estimate. Returns (chi by regression, chi by correlations), in % per K.
    """
    table = prepare(consumption, temp, tc, lags, years=years)
    if exclude is not None:
        table = table[~table["data"].isin(pd.to_datetime(list(exclude)))].reset_index(drop=True)
    table = table.sort_values("data").reset_index(drop=True)
    X = design_matrix(table, lags, years=years, holidays=holidays)
    beta, _, _ = fit_cluster(table, X)
    chi_reg = np.array([beta[f"cdd{k}"] for k in range(lags + 1)])
    F = X.drop(columns=[f"cdd{k}" for k in range(lags + 1)]).values
    proj = lambda v: v - F @ np.linalg.lstsq(F, v, rcond=None)[0]
    rE = pd.Series(proj(np.log(table["kwh"].values)), index=table["data"])
    rT = pd.Series(proj(table["cdd0"].values.astype(float)), index=table["data"])

    def lagcov(a, b, k):
        # Cov(a(t), b(t-k)) amb els parells de dies que existeixen tots dos
        bb = b.copy()
        bb.index = bb.index + pd.Timedelta(days=k)
        j = pd.concat([a, bb], axis=1, join="inner").dropna()
        return float((j.iloc[:, 0] * j.iloc[:, 1]).mean())

    CTT = np.array([[lagcov(rT, rT, abs(k - j)) for j in range(lags + 1)] for k in range(lags + 1)])
    CET = np.array([lagcov(rE, rT, k) for k in range(lags + 1)])
    return 100 * chi_reg, 100 * np.linalg.solve(CTT, CET)


def slope_over_years(beta, cov, years, lags=3, prefix="cdd"):
    """Linear trend of chi0 across years (% per K per year), with its standard error."""
    yrs = [a for a in years if all(f"{prefix}{k}_{a}" in beta.index for k in range(lags + 1))]
    aa = np.array(yrs, float)
    wts = (aa - aa.mean()) / ((aa - aa.mean()) ** 2).sum()
    w = pd.Series(0.0, index=beta.index)
    for a, p in zip(yrs, wts):
        for k in range(lags + 1):
            w[f"{prefix}{k}_{a}"] = p
    return 100 * float(w @ beta), 100 * float(np.sqrt(w.values @ cov.values @ w.values))
