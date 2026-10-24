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
