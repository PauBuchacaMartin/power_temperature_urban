"""Minimal physical model of the city's cooling response, and its inverse (pilot, v0.5).

The forward model is a Wiener chain: a linear filter followed by a static non-linearity.

1. Each dwelling feels a smoothed outdoor temperature. A first-order (1R1C) envelope with time
   constant tau (days) turns the daily outdoor temperature T(d) into

       x(d) = a x(d-1) + (1 - a) T(d),       a = exp(-1/tau).

   This is the "free-floating" indoor temperature, up to a constant offset from internal gains
   (the offset cannot be told apart from the comfort threshold; only their difference is
   identified).
2. A dwelling with air conditioning switches on when x exceeds its own comfort threshold T*.
   Thresholds are spread across households, T* ~ Normal(mu, sigma). Summing over dwellings,
   the city's cooling consumption per unit of base consumption is

       R(x) = E[(x - T*)_+] = sigma [phi(z) + z Phi(z)],     z = (x - mu) / sigma,

   so g''(x) is the threshold density P(T*), as in the reading of lambda in article 1.
3. Daily consumption: E(d) = B(d) [1 + A_y R(x(d))], with B(d) the base (calendar effects) and
   A_y = n_AC(y) u(y) / B the amplitude of summer y (number of air conditioners times use per
   unit, per unit of base). n_AC and u only appear as a product: separating them needs data from
   outside (energy certificates, surveys).

The inverse fits (mu, sigma, tau, A_y) by non-linear least squares on ln E, with the same fixed
effects as article 1 (year, ISO week, weekday, holiday) projected out.

Physical caveat: with a thermostat that is ALWAYS on, the envelope mass does not create memory in
the electricity (the AC removes the instantaneous load). Memory appears because use is
intermittent and the decision to switch on depends on the indoor temperature x, which remembers.
tau here is therefore an effective behavioural-thermal time constant, not a pure RC.

Comments in Catalan follow the style of the thesis notebooks.
"""
import numpy as np
import pandas as pd
from scipy import optimize, stats

from .response import design_matrix


def filtered_temperature(temp, tau, col="tmean"):
    """x(d) = a x(d-1) + (1-a) T(d), a = exp(-1/tau). temp: daily DataFrame (all days, in order)."""
    t = temp.sort_values("data")
    T = t[col].values.astype(float)
    a = np.exp(-1.0 / tau)
    x = np.empty_like(T)
    x[0] = T[0]
    for i in range(1, len(T)):
        x[i] = a * x[i - 1] + (1 - a) * T[i]
    return pd.Series(x, index=t["data"].values)


def threshold_response(x, mu, sigma):
    """E[(x - T*)_+] with T* ~ N(mu, sigma): sum over dwellings of the exceedance (K)."""
    z = (np.asarray(x) - mu) / sigma
    return sigma * (stats.norm.pdf(z) + z * stats.norm.cdf(z))


def simulate_city(temp, years, mu=23.0, sigma=2.0, tau=1.2, amp_by_year=None, base=1e5,
                  weekend=-0.08, noise=0.02, months=(6, 7, 8, 9), seed=0):
    """Synthetic daily city consumption from the forward model (only the chosen months).

    amp_by_year: dict year -> A_y (fraction of the base per K of exceedance), e.g. 0.06.
    """
    rng = np.random.default_rng(seed)
    x = filtered_temperature(temp, tau)
    d = pd.DataFrame({"data": x.index, "x": x.values})
    d = d[d["data"].dt.month.isin(months) & d["data"].dt.year.isin(years)].reset_index(drop=True)
    amp = d["data"].dt.year.map(amp_by_year or {a: 0.06 for a in years}).values
    ln_b = np.log(base) + np.where(d["data"].dt.dayofweek.values >= 5, weekend, 0.0)
    ln_e = ln_b + np.log1p(amp * threshold_response(d["x"].values, mu, sigma)) + rng.normal(0, noise, len(d))
    return pd.DataFrame({"data": d["data"], "kwh": np.exp(ln_e)})


def fit_inverse(consumption, temp, years, holidays=(), months=(6, 7, 8, 9), exclude=None,
                init=(23.0, 2.0, 1.2, 0.06), bounds_tau=(0.05, 15.0)):
    """Non-linear least squares for (mu, sigma, tau, A_y), fixed effects projected out.

    Returns dict with mu, sigma, tau, amp (Series by year), Q (A_last / A_first), se (from the
    Jacobian, NOT cluster-robust: use the week bootstrap for honest intervals), rss, n.
    """
    years = list(years)
    c = consumption[consumption["data"].dt.month.isin(months) & consumption["data"].dt.year.isin(years)]
    if exclude is not None:
        c = c[~c["data"].isin(pd.to_datetime(list(exclude)))]
    c = c.sort_values("data").reset_index(drop=True)
    y = np.log(c["kwh"].values)
    tab = c[["data"]].assign(cdd0=0.0)
    F = design_matrix(tab, lags=0, years=years, holidays=holidays).values      # només efectes fixos
    Qf, _ = np.linalg.qr(F)
    M = lambda v: v - Qf @ (Qf.T @ v)                                          # treu els efectes fixos
    yr = c["data"].dt.year.values
    idx = {a: i for i, a in enumerate(years)}
    iy = np.array([idx[a] for a in yr])
    temp_all = temp[["data", "tmean"]].dropna()

    def resid(p):
        mu, ls, lt = p[:3]
        amp = np.exp(p[3:])
        x = filtered_temperature(temp_all, np.exp(lt)).reindex(c["data"].values).values
        pred = np.log1p(amp[iy] * threshold_response(x, mu, np.exp(ls)))
        return M(y - pred)

    p0 = np.r_[init[0], np.log(init[1]), np.log(init[2]), np.full(len(years), np.log(init[3]))]
    lo = np.r_[10.0, np.log(0.2), np.log(bounds_tau[0]), np.full(len(years), np.log(1e-4))]
    hi = np.r_[35.0, np.log(10.0), np.log(bounds_tau[1]), np.full(len(years), np.log(5.0))]
    r = optimize.least_squares(resid, p0, bounds=(lo, hi), x_scale="jac")
    n, k = len(y), len(r.x) + F.shape[1]
    s2 = float(r.fun @ r.fun) / max(n - k, 1)
    try:
        cov = np.linalg.inv(r.jac.T @ r.jac) * s2
        se_raw = np.sqrt(np.diag(cov))
    except np.linalg.LinAlgError:
        cov, se_raw = None, np.full(len(r.x), np.nan)
    amp = pd.Series(np.exp(r.x[3:]), index=years)
    return {"mu": r.x[0], "sigma": np.exp(r.x[1]), "tau": np.exp(r.x[2]), "amp": amp,
            "Q": amp.iloc[-1] / amp.iloc[0],
            "se": {"mu": se_raw[0], "ln_sigma": se_raw[1], "ln_tau": se_raw[2], "ln_amp": se_raw[3:]},
            "rss": float(r.fun @ r.fun), "n": n, "ok": bool(r.success)}
