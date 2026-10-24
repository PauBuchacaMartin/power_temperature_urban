"""Tests of the cold branch and the hysteresis test (notebook v0.12, sections 24 and 25).

Every estimator must recover a known parameter on synthetic data, and the hysteresis
test must NOT fire on the two nulls (linear memory; curved response without hysteresis).
"""
import numpy as np
import pandas as pd

import consum_temperatura as ct
from consum_temperatura import synthetic

WINTERS = [2021, 2022, 2023, 2024]


def test_winter_label_and_christmas():
    d = pd.to_datetime(["2021-11-01", "2022-03-31", "2022-12-24", "2023-01-06", "2023-01-07"])
    assert list(ct.winter_label(d)) == [2021, 2021, 2022, 2022, 2022]
    assert list(ct.christmas(d)) == [False, False, True, True, False]


def test_recovers_cold_response_by_winter():
    temp = synthetic.summer_temperature()
    chi_h = {2020: 1.0, 2021: 1.0, 2022: 1.5, 2023: 2.0, 2024: 2.5}
    cons = synthetic.annual_consumption(temp, th=15.0, chi_h_by_winter=chi_h)
    tab, beta, cov = ct.response_by_winter(cons, temp, th=15.0, winters=WINTERS)
    for w in WINTERS:
        assert abs(tab.loc[w, "chi_h"] - chi_h[w]) < 3 * tab.loc[w, "se"] + 0.15
    d, se = ct.growth(beta, cov, 2021, 2024, prefix="hdd")
    assert abs(d - 1.5) < 3 * se + 0.2


def test_light_cycle_does_not_leak_into_cold_response():
    # sense resposta al fred, el cicle de la llum (absorbit per la setmana ISO) no ha de crear-ne
    temp = synthetic.summer_temperature(seed=7)
    cons = synthetic.annual_consumption(temp, chi_h_by_winter={w: 0.0 for w in range(2019, 2026)},
                                        light=0.15, seed=8)
    r = ct.fit_winter(cons, temp, th=15.0, winters=WINTERS)
    assert abs(r["chi_h"]) < 3 * r["se"] + 0.1


def test_choose_th_finds_true_threshold():
    temp = synthetic.summer_temperature(seed=3)
    cons = synthetic.annual_consumption(temp, th=14.0, chi_h_by_winter={w: 3.0 for w in range(2019, 2026)}, seed=4)
    th, prof = ct.choose_th(cons, temp, candidates=np.arange(12.0, 16.5, 0.5), winters=WINTERS)
    assert abs(th - 14.0) <= 0.5


def test_asymmetry_ratio():
    r, se = ct.asymmetry(1.0, 0.1, 5.0, 0.2)
    assert abs(r - 0.2) < 1e-12
    assert abs(se - 0.2 * np.sqrt(0.01 + 0.0016)) < 1e-12


def _z(cons, temp, tc):
    return ct.hysteresis_test(cons, temp, tc)["z"]


def test_hysteresis_null_linear_memory():
    zs = []
    for s in range(6):
        temp = synthetic.summer_temperature(seed=100 + s)
        zs.append(_z(synthetic.consumption(temp, tc=22.0, seed=300 + s), temp, 22.0))
    assert np.mean(np.array(zs) > 2) <= 1 / 6


def test_hysteresis_null_curved_without_hysteresis():
    zs = []
    for s in range(6):
        temp = synthetic.summer_temperature(seed=100 + s)
        cons = synthetic.relay_consumption(temp, width=0.0, n_units=2000, seed=200 + s)[["data", "kwh"]]
        zs.append(_z(cons, temp, 20.0))
    assert np.mean(np.array(zs) > 2) <= 1 / 6


def test_hysteresis_detected():
    zs = []
    for s in range(4):
        temp = synthetic.summer_temperature(seed=100 + s)
        cons = synthetic.relay_consumption(temp, width=1.0, n_units=2000, seed=200 + s)[["data", "kwh"]]
        zs.append(_z(cons, temp, 20.0))
    assert min(zs) > 2


def test_linear_memory_version_gives_false_positives_with_curvature():
    # Per què fem servir la memòria flexible: amb CDD lineals, una resposta corbada sense histèresi
    # dona gamma > 0 sistemàticament. Aquesta prova documenta l'error.
    gs = []
    for s in range(4):
        temp = synthetic.summer_temperature(seed=100 + s)
        cons = synthetic.relay_consumption(temp, width=0.0, n_units=2000, seed=200 + s)[["data", "kwh"]]
        gs.append(ct.hysteresis_test(cons, temp, 20.0, linear=True)["gamma"]
                  - ct.hysteresis_test(cons, temp, 20.0)["gamma"])
    assert np.mean(gs) > 0


def test_response_by_phase_constant():
    temp = synthetic.summer_temperature()
    cons = synthetic.consumption(temp, tc=22.0, chi_by_year={a: 4.0 for a in range(2021, 2026)})
    tab, (d, se) = ct.response_by_phase(cons, temp, 22.0)
    assert abs(d) < 3 * se + 0.2


def test_winter_month_effects_absorb_level_jump():
    # un salt de nivell de les dades a mitjan hivern (com els de la tardor del 2023) no ha de canviar chi_h
    temp = synthetic.summer_temperature(seed=11)
    cons = synthetic.annual_consumption(temp, th=15.0, chi_h_by_winter={w: 2.0 for w in range(2019, 2026)}, seed=12)
    cons.loc[cons["data"] >= "2024-01-01", "kwh"] *= 0.85
    tab, beta, cov = ct.response_by_winter(cons, temp, th=15.0, winters=WINTERS, winter_month=True)
    for w in WINTERS:
        assert abs(tab.loc[w, "chi_h"] - 2.0) < 3 * tab.loc[w, "se"] + 0.15
