"""Tests with synthetic data: the estimators must recover known parameters."""
import numpy as np
import pandas as pd

import consum_temperatura as ct
from consum_temperatura import synthetic


def test_recovers_static_chi():
    temp = synthetic.summer_temperature()
    cons = synthetic.consumption(temp, tc=22.0, chi_by_year={a: 3.0 for a in range(2021, 2026)})
    r = ct.fit_city(cons, temp, tc=22.0)
    assert abs(r["chi0"] - 3.0) < 3 * r["se"] + 0.1
    assert r["se"] > 0


def test_recovers_growth_by_year():
    temp = synthetic.summer_temperature()
    chi = {2021: 2.0, 2022: 2.5, 2023: 3.0, 2024: 3.5, 2025: 3.5}
    cons = synthetic.consumption(temp, tc=22.0, chi_by_year=chi)
    tab, beta, cov = ct.response_by_year(cons, temp, tc=22.0)
    for a, v in chi.items():
        assert abs(tab.loc[a, "chi0"] - v) < 3 * tab.loc[a, "se"] + 0.15
    d, se = ct.growth(beta, cov, 2021, 2024)
    assert abs(d - 1.5) < 3 * se + 0.2


def test_choose_tc_finds_true_threshold():
    temp = synthetic.summer_temperature(seed=3)
    cons = synthetic.consumption(temp, tc=21.0, seed=4)
    tc, prof = ct.choose_tc(cons, temp, candidates=np.arange(19.0, 23.5, 0.5))
    assert abs(tc - 21.0) <= 0.5


def test_threshold_factor():
    bins = [24, 25, 26, 27]
    years = [2021, 2022, 2023]
    g = pd.Series([1.0, 2.0, 3.0, 4.0], index=bins)
    lam = pd.Series([1.0, 1.3, 1.8], index=years)
    curves = pd.DataFrame(np.outer(g, lam), index=bins, columns=years)
    errors = pd.DataFrame(0.1, index=bins, columns=years)
    lam_hat, se, g_hat, chi2, dof = ct.threshold_factor(curves, errors, ref=2021)
    assert np.allclose(lam_hat.values, lam.values, atol=1e-6)
    assert chi2 < 1e-8


def test_extensive_share():
    # 9 % more appliances while the response grows 83 % -> about 15 % of the log-growth
    s = ct.extensive_share(45.6, 49.9, 1.00, 1.83)
    assert 0.14 < s < 0.16


def test_band_regime_detects_shift():
    days = pd.date_range("2021-01-01", "2024-12-31", freq="D")
    eve = np.where(days.year >= 2024, 30.0, 40.0)
    df = pd.DataFrame({"18-24": eve, "06-12": 60.0}, index=days)
    anom, regime_b = ct.band_regime(df)
    assert all(d.year == 2024 for d in regime_b)
    assert len(regime_b) > 300


def test_cache(tmp_path):
    calls = []
    def download():
        calls.append(1)
        return pd.DataFrame({"data": pd.to_datetime(["2024-01-01"]), "x": [1]})
    a = ct.from_cache(str(tmp_path), "f.csv", download)
    b = ct.from_cache(str(tmp_path), "f.csv", download)
    assert len(calls) == 1 and len(a) == len(b) == 1


def test_level_jumps():
    days = pd.date_range("2024-01-01", periods=400, freq="D")
    s = pd.Series(np.where(np.arange(400) < 200, 100.0, 130.0), index=days)
    j = ct.level_jumps(s)
    assert len(j) == 1
    assert abs((j["data"].iloc[0] - days[200]).days) <= 2
