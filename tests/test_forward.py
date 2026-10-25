"""Tests of the forward (physical) model and its inverse, on synthetic data with known parameters."""
import numpy as np
import pandas as pd

from consum_temperatura import forward as fw
from consum_temperatura import synthetic

YEARS = [2021, 2022, 2023, 2024]


def test_filter_is_exponential_kernel():
    days = pd.date_range("2024-01-01", periods=30)
    T = np.zeros(30); T[10] = 1.0                      # un impuls
    x = fw.filtered_temperature(pd.DataFrame({"data": days, "tmean": T}), tau=2.0).values
    a = np.exp(-0.5)
    assert np.isclose(x[10], 1 - a) and np.isclose(x[13], (1 - a) * a ** 3)


def test_threshold_response_limits():
    x = np.linspace(15, 35, 41)
    r = fw.threshold_response(x, 25.0, 1e-3)
    assert np.allclose(r, np.maximum(x - 25.0, 0), atol=1e-3)          # sigma -> 0: (x - mu)+
    h = 1e-4                                                             # derivada = Phi(z)
    d = (fw.threshold_response(25.5 + h, 25, 2) - fw.threshold_response(25.5 - h, 25, 2)) / (2 * h)
    assert abs(d - 0.5987) < 1e-3


def test_inverse_recovers_parameters():
    temp = synthetic.summer_temperature(years=YEARS, seed=3)
    temp["tmean"] += 4                                                   # estius més calents
    amp = {2021: 0.05, 2022: 0.06, 2023: 0.07, 2024: 0.08}
    s = fw.simulate_city(temp, YEARS, mu=23, sigma=2, tau=1.2, amp_by_year=amp, noise=0.005, seed=1)
    f = fw.fit_inverse(s, temp, YEARS)
    assert abs(f["tau"] - 1.2) < 0.1 and abs(f["mu"] - 23) < 0.6 and abs(f["sigma"] - 2) < 0.5
    assert abs(f["Q"] - 1.6) < 0.1
