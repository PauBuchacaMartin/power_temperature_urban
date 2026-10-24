"""Synthetic data with a known response, to check that the estimators recover it.

Rule of the thesis: no method is used on real data before it recovers known
parameters on synthetic data.
"""
import numpy as np
import pandas as pd


def summer_temperature(years=(2021, 2022, 2023, 2024, 2025), seed=0):
    """Daily temperature with a seasonal cycle and AR(1) weather noise (all year)."""
    rng = np.random.default_rng(seed)
    days = pd.date_range(f"{min(years)}-01-01", f"{max(years)}-12-31", freq="D")
    doy = days.dayofyear.values
    seasonal = 16 + 8 * np.sin(2 * np.pi * (doy - 110) / 365)
    noise = np.zeros(len(days))
    for i in range(1, len(days)):
        noise[i] = 0.7 * noise[i - 1] + rng.normal(0, 1.5)
    tmean = seasonal + noise
    return pd.DataFrame({"data": days, "tmean": tmean, "tmax": tmean + 5})


def consumption(temp, tc=22.0, chi_by_year=None, lag_weights=(0.5, 0.3, 0.15, 0.05),
                base=1e5, sigma=0.02, seed=1):
    """Daily kWh with ln E = ln base + chi(year)/100 * sum_k w_k CDD(d-k) + weekday effect + noise.

    chi_by_year: dict year -> static susceptibility (% per degree-day).
    """
    rng = np.random.default_rng(seed)
    t = temp.sort_values("data").reset_index(drop=True)
    cdd = np.maximum(t["tmean"] - tc, 0)
    if chi_by_year is None:
        chi_by_year = {a: 3.0 for a in t["data"].dt.year.unique()}
    chi = t["data"].dt.year.map(chi_by_year).values / 100
    resp = sum(w * cdd.shift(k).fillna(0).values for k, w in enumerate(lag_weights))
    weekday = np.where(t["data"].dt.dayofweek.values >= 5, -0.08, 0.0)
    ln_e = np.log(base) + chi * resp + weekday + rng.normal(0, sigma, len(t))
    return pd.DataFrame({"data": t["data"], "kwh": np.exp(ln_e)})


def annual_consumption(temp, tc=22.0, chi_c_by_year=None, th=15.0, chi_h_by_winter=None,
                       lag_weights=(0.5, 0.3, 0.15, 0.05), base=1e5, light=0.10,
                       christmas_effect=0.06, sigma=0.02, seed=2):
    """Whole-year daily kWh with a heat branch and a cold branch (the V).

    ln E = ln base + chi_c(year)/100 * sum_k w_k CDD(d-k) + chi_h(winter)/100 * sum_k w_k HDD(d-k)
           + light * cos(day of year) + weekday + Christmas + noise

    chi_c_by_year: dict year -> % per degree-day above tc.
    chi_h_by_winter: dict winter (starting year) -> % per degree-day below th.
    The deterministic 'light' cycle mimics the hours of darkness (more lighting in winter):
    the ISO-week fixed effect must absorb it.
    """
    from .seasonal import winter_label, christmas
    rng = np.random.default_rng(seed)
    t = temp.sort_values("data").reset_index(drop=True)
    years = t["data"].dt.year
    winters = pd.Series(winter_label(t["data"]))
    if chi_c_by_year is None:
        chi_c_by_year = {a: 5.0 for a in years.unique()}
    if chi_h_by_winter is None:
        chi_h_by_winter = {w: 1.5 for w in winters.unique()}
    cdd = np.maximum(t["tmean"] - tc, 0)
    hdd = np.maximum(th - t["tmean"], 0)
    resp_c = sum(w * cdd.shift(k).fillna(0).values for k, w in enumerate(lag_weights))
    resp_h = sum(w * hdd.shift(k).fillna(0).values for k, w in enumerate(lag_weights))
    chi_c = years.map(chi_c_by_year).fillna(0).values / 100
    chi_h = winters.map(chi_h_by_winter).fillna(0).values / 100
    doy = t["data"].dt.dayofyear.values
    ln_e = (np.log(base) + chi_c * resp_c + chi_h * resp_h
            + light * np.cos(2 * np.pi * doy / 365.25)                   # més llum encesa a l'hivern
            + np.where(t["data"].dt.dayofweek.values >= 5, -0.08, 0.0)
            + christmas_effect * christmas(t["data"])
            + rng.normal(0, sigma, len(t)))
    return pd.DataFrame({"data": t["data"], "kwh": np.exp(ln_e)})


def relay_consumption(temp, on_mean=23.0, on_sd=1.5, width=2.0, n_units=4000, amplitude=0.30,
                      base=1e5, sigma=0.015, seed=5):
    """Daily kWh from a population of air conditioners that behave as relays (Preisach model).

    Unit i switches ON when T > a_i and OFF when T < a_i - width; between the two it keeps
    its state. width > 0 gives true hysteresis; width = 0 gives a smooth, non-linear
    response WITHOUT hysteresis (heterogeneous thresholds only): the null of the fronts test.
    ln E = ln base + amplitude * (fraction of units ON) + weekday + noise.
    """
    rng = np.random.default_rng(seed)
    t = temp.sort_values("data").reset_index(drop=True)
    a = rng.normal(on_mean, on_sd, n_units)       # llindar d'encesa de cada aparell
    b = a - width                                  # llindar d'apagada
    state = np.zeros(n_units, dtype=bool)
    frac = np.empty(len(t))
    for i, T in enumerate(t["tmean"].values):
        state = np.where(T > a, True, np.where(T < b, False, state))
        frac[i] = state.mean()
    ln_e = (np.log(base) + amplitude * frac
            + np.where(t["data"].dt.dayofweek.values >= 5, -0.08, 0.0)
            + rng.normal(0, sigma, len(t)))
    return pd.DataFrame({"data": t["data"], "kwh": np.exp(ln_e), "frac_on": frac})
