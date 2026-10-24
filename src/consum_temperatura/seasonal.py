"""The whole year: the cold branch of the V and the hysteresis test.

Two new lines of article 1 (notebook v0.12, sections 24 and 25):

1. Cold branch. Winter model (November to March):

       ln E(d) = sum_k chi_h,k * HDD(d - k) + fixed effects (winter, ISO week, weekday,
                 holiday, Christmas) + eps,      HDD = max(Th - T, 0)

   The ISO-week fixed effect absorbs the daylight cycle (hours of light are almost the
   same in the same week every year), so chi_h is identified from weather anomalies
   within the same week of different years. The ratio chi_h / chi_c measures how
   symmetric the V is. In Barcelona heating is mostly gas: electricity only sees the
   electrified part (heat pumps, electric radiators). If chi_h grows over the years,
   that is a signature of electrification of heating.

2. Hysteresis test ("fronts" test). At the same temperature, do we consume more when
   the heat is leaving (temperature falling) than when it is arriving (rising), once the
   linear memory (lags) is accounted for?

       ln E(d) = sum_k chi_k CDD(d - k) + gamma * CDD(d) * 1[T(d) < T(d-1)] + FE + eps

   A linear response with memory predicts gamma = 0 (the lags already describe the
   difference between rising and falling days). Relays with hysteresis (an air
   conditioner switched on above T_on and off below T_off < T_on) predict gamma > 0.
   This is the C3 criterion: linear memory closes the loop, true hysteresis does not.

Comments in Catalan follow the style of the thesis notebooks.
"""
import numpy as np
import pandas as pd

from .forcings import cooling_degree_days, heating_degree_days
from .response import fit_cluster, prepare, design_matrix, static_susceptibility

WINTER_MONTHS = (11, 12, 1, 2, 3)


# ---------------------------------------------------------------------------
# 1. Branca de fred
# ---------------------------------------------------------------------------

def winter_label(dates):
    """Winter of each date, labelled by the year in which it starts (Nov 2021 - Mar 2022 -> 2021)."""
    d = pd.to_datetime(pd.Series(dates))
    return np.where(d.dt.month.values >= 7, d.dt.year.values, d.dt.year.values - 1)


def christmas(dates):
    """True from 24 December to 6 January (Christmas holidays: the ISO week does not capture them)."""
    d = pd.to_datetime(pd.Series(dates))
    m, day = d.dt.month.values, d.dt.day.values
    return ((m == 12) & (day >= 24)) | ((m == 1) & (day <= 6))


def prepare_winter(consumption, temp, th, lags=3, months=WINTER_MONTHS, winters=None):
    """Merge daily consumption ('data', 'kwh') with HDD lags; keep winter days.

    winters: list of winter labels to keep (e.g. [2021, 2022, 2023, 2024]).
    """
    t = heating_degree_days(temp, th, lags)
    table = consumption.merge(t, on="data")
    table = table[table["data"].dt.month.isin(months)].copy()
    table["hivern"] = winter_label(table["data"])
    if winters is not None:
        table = table[table["hivern"].isin(winters)]
    return table.dropna().reset_index(drop=True)


def winter_design(table, lags=3, holidays=(), by_winter=False, winter_month=False):
    """Regressors: HDD lags (optionally one set per winter) + fixed effects.

    Fixed effects: winter, ISO week (daylight cycle), weekday, holiday, Christmas.
    winter_month=True adds winter x month effects (absorbs level jumps of the data inside a winter).
    """
    winters = sorted(table["hivern"].unique())
    hdd_cols = [f"hdd{k}" for k in range(lags + 1)]
    if by_winter:
        # una funció de resposta per hivern: HDD x indicador d'hivern
        parts = {}
        w = table["hivern"].values
        for a in winters:
            for c in hdd_cols:
                parts[f"{c}_{a}"] = table[c].values * (w == a)
        X_h = pd.DataFrame(parts)
    else:
        X_h = table[hdd_cols].reset_index(drop=True)
    cat = lambda v, cats: pd.Categorical(v, categories=cats)
    hol = pd.to_datetime(pd.Series(list(holidays))) if len(holidays) else pd.Series([], dtype="datetime64[ns]")
    fe = pd.get_dummies(pd.DataFrame({
        "hivern": cat(table["hivern"].values, winters),
        "setmana": cat(table["data"].dt.isocalendar().week.astype(int).values, list(range(1, 54))),
        "dia": cat(table["data"].dt.dayofweek.values, list(range(7))),
        "festiu": cat(table["data"].isin(hol).values, [False, True]),
        "nadal": cat(christmas(table["data"]), [False, True]),
    }), drop_first=True).astype(float)
    if winter_month:
        # efectes fixos hivern x mes: un nivell propi per a cada mes de cada hivern
        wm = pd.Series(table["hivern"].astype(str).values + "_" + table["data"].dt.month.astype(str).values)
        fe = pd.concat([fe, pd.get_dummies(wm, prefix="hm", drop_first=True).astype(float)], axis=1)
    X = pd.concat([X_h.reset_index(drop=True), fe.reset_index(drop=True)], axis=1)
    X = X.loc[:, X.abs().sum() > 0]              # treu columnes buides
    X.insert(0, "const", 1.0)
    return X


def fit_winter(consumption, temp, th, lags=3, holidays=(), winters=None, exclude=None,
               months=WINTER_MONTHS, winter_month=False):
    """Static cold response chi_h (% per degree-day below th) of a whole series."""
    table = prepare_winter(consumption, temp, th, lags, months=months, winters=winters)
    if exclude is not None:
        table = table[~table["data"].isin(pd.to_datetime(list(exclude)))].reset_index(drop=True)
    X = winter_design(table, lags, holidays, winter_month=winter_month)
    beta, cov, res = fit_cluster(table, X)
    chi, se = static_susceptibility(beta, cov, lags, prefix="hdd")
    return {"chi_h": chi, "se": se, "beta": beta, "cov": cov, "n": len(table),
            "mse": float(np.mean(res ** 2))}


def choose_th(consumption, temp, candidates=np.arange(10.0, 19.5, 0.5), lags=3, holidays=(), winters=None,
              exclude=None):
    """Heating threshold that minimises the in-sample mean squared error (same rule as choose_tc)."""
    rows = [(th, fit_winter(consumption, temp, th, lags, holidays, winters, exclude)["mse"]) for th in candidates]
    prof = pd.DataFrame(rows, columns=["th", "mse"])
    return float(prof.loc[prof["mse"].idxmin(), "th"]), prof


def response_by_winter(consumption, temp, th, lags=3, winters=None, holidays=(), exclude=None,
                       months=WINTER_MONTHS, winter_month=False):
    """chi_h for each winter (HDD x winter interaction). Returns (table, beta, cov)."""
    table = prepare_winter(consumption, temp, th, lags, months=months, winters=winters)
    if exclude is not None:
        table = table[~table["data"].isin(pd.to_datetime(list(exclude)))].reset_index(drop=True)
    X = winter_design(table, lags, holidays, by_winter=True, winter_month=winter_month)
    beta, cov, _ = fit_cluster(table, X)
    out = {a: static_susceptibility(beta, cov, lags, suffix=f"_{a}", prefix="hdd")
           for a in sorted(table["hivern"].unique())}
    return pd.DataFrame(out, index=["chi_h", "se"]).T, beta, cov


def asymmetry(chi_h, se_h, chi_c, se_c):
    """Ratio R = chi_h / chi_c and its standard error (delta method, independent estimates).

    R = 1: symmetric V (each degree of cold moves electricity as much as each degree of heat).
    R << 1: heating mostly not electric.
    """
    r = chi_h / chi_c
    se = abs(r) * np.sqrt((se_h / chi_h) ** 2 + (se_c / chi_c) ** 2)
    return float(r), float(se)


# ---------------------------------------------------------------------------
# 2. Histèresi
# ---------------------------------------------------------------------------

def falling_days(temp, col="tmean"):
    """True on days whose mean temperature is lower than the day before (the heat is leaving)."""
    t = temp.sort_values("data")
    return pd.Series((t[col] < t[col].shift(1)).values, index=t["data"].values)


def flexible_memory(table, temp, tc, lags=3, knots=(0, 2, 4, 6), col="tmean"):
    """Additive, curved memory: hinge functions max(T(d-k) - (tc + knot), 0) for every lag k.

    Any additive response sum_k f_k(T(d-k)), linear or curved, is well approximated by these
    columns. Hysteresis is NOT additive (the state depends on the path), so it cannot hide here.
    """
    t = temp.sort_values("data").set_index("data")[col]
    cols = {}
    for k in range(lags + 1):
        tk = t.shift(k).reindex(table["data"]).values
        for kn in knots:
            cols[f"m{k}_{kn:g}"] = np.maximum(tk - (tc + kn), 0)
    return pd.DataFrame(cols)


def hysteresis_test(consumption, temp, tc, lags=3, holidays=(), months=(6, 7, 8, 9), years=None,
                    exclude=None, knots=(0, 2, 4, 6), linear=False):
    """Fronts test: extra response on falling days at the same temperature, net of memory.

        ln E(d) = memory(T(d), T(d-1), ..., T(d-lags)) + gamma * CDD(d) * 1[T(d) < T(d-1)] + FE + eps

    memory = flexible additive hinge basis (default) or plain CDD lags (linear=True, kept only
    to show why it fails: with a curved response it gives false positives).
    Synthetic checks (tests/test_seasonal.py): gamma ~ 0 for a linear response with memory and
    for a curved response without hysteresis; gamma > 0 for relays with a hysteresis band of
    1-2 K. A band of 3 K or more looks like memory in daily data and is NOT detected.
    Returns dict with gamma (% per degree-day), se, z, n and the share of hot days that are falling.
    """
    table = prepare(consumption, temp, tc, lags, months=months, years=years)
    if exclude is not None:
        table = table[~table["data"].isin(pd.to_datetime(list(exclude)))].reset_index(drop=True)
    fall = falling_days(temp).reindex(table["data"].values).fillna(False).values.astype(bool)
    X = design_matrix(table, lags, years=years, holidays=holidays)
    if not linear:
        # memòria flexible: substituïm els CDD lineals per frontisses a diverses temperatures
        X = X.drop(columns=[f"cdd{k}" for k in range(lags + 1)])
        X = pd.concat([X, flexible_memory(table, temp, tc, lags, knots)], axis=1)
    # gamma: CDD del dia x indicador "la temperatura baixa respecte d'ahir"
    X["cdd0_baixa"] = table["cdd0"].values * fall
    beta, cov, _ = fit_cluster(table, X)
    g = 100 * float(beta["cdd0_baixa"])
    se = 100 * float(np.sqrt(cov.loc["cdd0_baixa", "cdd0_baixa"]))
    hot = table["cdd0"].values > 0
    return {"gamma": g, "se": se, "z": g / se if se > 0 else np.nan, "n": len(table),
            "frac_baixa": float(np.mean(fall[hot])) if hot.any() else np.nan}


PHASES = {"arribada": ((6, 1), (7, 15)), "plena": ((7, 16), (8, 15)), "sortida": ((8, 16), (9, 30))}


def summer_phase(dates):
    """Phase of the summer: 'arribada' (1 Jun - 15 Jul), 'plena' (16 Jul - 15 Aug), 'sortida' (16 Aug - 30 Sep)."""
    d = pd.to_datetime(pd.Series(dates))
    md = d.dt.month.values * 100 + d.dt.day.values
    out = np.full(len(d), None, dtype=object)
    for name, ((m0, d0), (m1, d1)) in PHASES.items():
        out[(md >= m0 * 100 + d0) & (md <= m1 * 100 + d1)] = name
    return out


def response_by_phase(consumption, temp, tc, lags=3, holidays=(), years=None, exclude=None):
    """chi0 in each phase of the summer (arrival, full, departure) with week fixed effects.

    Returns (table phase -> chi0, se; difference departure - arrival with se).
    Caution: August occupancy also changes the slope; this is a descriptive complement
    to the fronts test, not a test of hysteresis by itself.
    """
    table = prepare(consumption, temp, tc, lags, months=(6, 7, 8, 9), years=years)
    if exclude is not None:
        table = table[~table["data"].isin(pd.to_datetime(list(exclude)))].reset_index(drop=True)
    ph = summer_phase(table["data"])
    X = design_matrix(table, lags, years=years, holidays=holidays)
    cdd_cols = [f"cdd{k}" for k in range(lags + 1)]
    X = X.drop(columns=cdd_cols)
    for name in PHASES:
        for c in cdd_cols:
            X[f"{c}_{name}"] = table[c].values * (ph == name)
    beta, cov, _ = fit_cluster(table, X)
    out = {name: static_susceptibility(beta, cov, lags, suffix=f"_{name}") for name in PHASES}
    n0 = [f"cdd{k}_arribada" for k in range(lags + 1)]
    n1 = [f"cdd{k}_sortida" for k in range(lags + 1)]
    w = np.r_[-np.ones(len(n0)), np.ones(len(n1))]
    d = 100 * float(beta[n0 + n1].values @ w)
    se = 100 * float(np.sqrt(w @ cov.loc[n0 + n1, n0 + n1].values @ w))
    return pd.DataFrame(out, index=["chi0", "se"]).T, (d, se)
