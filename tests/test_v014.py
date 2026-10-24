"""Tests of the v0.14 functions (answer to the external review): day–night difference test,
PV (radiation) control, weekday subset, block bootstrap, summer coverage rule and station IDW.
All on synthetic data with a known answer."""
import numpy as np
import pandas as pd

import consum_temperatura as ct
from consum_temperatura import synthetic

YEARS = [2021, 2022, 2023, 2024, 2025]


def _temp():
    return synthetic.summer_temperature(seed=0)


def _dn(night_growth=0.04, day_growth=0.0, pv=0.0, seed=8):
    """Synthetic day/night data. pv: share of DAY response hidden on sunny days, growing each year."""
    temp = _temp().sort_values("data").reset_index(drop=True)
    rng = np.random.default_rng(seed)
    bands = pd.DataFrame({"data": temp["data"], "t_nit": temp["tmean"] - 3 + rng.normal(0, 1.2, len(temp)),
                          "t_dia": temp["tmean"] + 4 + rng.normal(0, 1.2, len(temp))})
    f = ct.day_night_forcings(bands, 27, 20).fillna(0)
    yr = temp["data"].dt.year.values
    late = (yr >= 2024)
    rad = rng.normal(0, 1, len(temp))
    night = 0.04 + night_growth * late
    day = 0.02 + day_growth * late
    ln_e = (11 + night * f["cdd_nit0"].values + day * f["cdd_dia0"].values
            - pv * (yr - 2021) * rad + rng.normal(0, 0.01, len(temp)))
    cons = pd.DataFrame({"data": temp["data"], "kwh": np.exp(ln_e)})
    return temp, f, cons, pd.DataFrame({"data": temp["data"], "rad": rad})


def test_difference_detects_night_minus_day():
    temp, f, cons, _ = _dn(night_growth=0.04, day_growth=0.0)
    b, c = ct.day_night_response(cons, temp, f, 22.0, years=YEARS, by_year=True)
    d, se, z = ct.day_night_difference(b, c, 2021, 2024)
    assert abs(d - 4.0) < 3 * se + 0.3 and z > 3


def test_difference_null_when_both_grow_equally():
    temp, f, cons, _ = _dn(night_growth=0.03, day_growth=0.03)
    b, c = ct.day_night_response(cons, temp, f, 22.0, years=YEARS, by_year=True)
    d, se, z = ct.day_night_difference(b, c, 2021, 2024)
    assert abs(z) < 3


def test_difference_se_uses_covariance():
    # the se of the difference is NOT the quadrature sum of the two separate se
    temp, f, cons, _ = _dn()
    b, c = ct.day_night_response(cons, temp, f, 22.0, years=YEARS, by_year=True)
    s = ct.day_night_summary(b, c, True, 2021, 2024)
    _, se, _ = ct.day_night_difference(b, c, 2021, 2024)
    quad = np.hypot(s["se_canvi_nit"], s["se_canvi_dia"])
    assert not np.isclose(se, quad, rtol=1e-3)


def test_radiation_control_enters_and_keeps_contrast():
    temp, f, cons, rad = _dn(pv=0.01)
    b, c = ct.day_night_response(cons, temp, f, 22.0, years=YEARS, by_year=True,
                                 extra=ct.radiation_regressors(rad))
    assert "rad" in b.index and "rad_2024" in b.index
    d, se, z = ct.day_night_difference(b, c, 2021, 2024)
    assert abs(d - 4.0) < 3 * se + 0.3


def test_weekday_subset():
    temp, f, cons, _ = _dn()
    b, c = ct.day_night_response(cons, temp, f, 22.0, years=YEARS, by_year=True, weekdays=range(5))
    s = ct.day_night_summary(b, c, True, 2021, 2024)
    assert abs(s["canvi_nit"] - 4.0) < 3 * s["se_canvi_nit"] + 0.4


def test_resample_weeks_keeps_whole_weeks_and_size():
    temp = _temp()
    cons = synthetic.consumption(temp, seed=3)
    cons = cons[cons["data"].dt.month.isin([6, 7, 8, 9])].reset_index(drop=True)
    s = ct.resample_weeks(cons, np.random.default_rng(0))
    assert abs(len(s) - len(cons)) / len(cons) < 0.1
    # every resampled ISO week is complete (same days as in the original)
    iso = lambda d: (d["data"].dt.isocalendar().year.astype(int) * 100 + d["data"].dt.isocalendar().week.astype(int)).values
    orig = cons.groupby(iso(cons)).size()
    for w, n in s.drop_duplicates("data").groupby(iso(s.drop_duplicates("data"))).size().items():
        assert n == orig[w]


def test_block_bootstrap_covers_true_growth():
    temp = _temp()
    chi = {2021: 4.0, 2022: 5.0, 2023: 6.0, 2024: 7.0, 2025: 8.0}
    cons = synthetic.consumption(temp, tc=22.0, chi_by_year=chi, seed=11)
    cons = cons[cons["data"].dt.month.isin([6, 7, 8, 9])].reset_index(drop=True)

    def stat(s):
        _, b, c = ct.response_by_year(s, temp, 22.0, years=YEARS)
        return {"d": ct.growth(b, c, 2021, 2024)[0]}
    bt = ct.block_bootstrap(cons, stat, n=40, seed=1)
    lo, hi = ct.percentile_interval(bt["d"])
    assert len(bt) == 40 and lo < 3.0 < hi and hi - lo < 3


def test_summer_coverage_weights_hot_days():
    temp = _temp()
    summer = temp[temp["data"].dt.month.isin([6, 7, 8, 9]) & (temp["data"].dt.year == 2024)]
    hot = summer.nlargest(15, "tmean")["data"]
    good = set(temp["data"]) - set(hot)
    cov = ct.summer_coverage(good, temp, 22.0, YEARS)
    assert cov.loc[2024, "frac_dies"] > 0.85 and cov.loc[2024, "frac_cdd"] < 0.7
    assert cov.loc[2021, "frac_cdd"] == 1.0
    assert ct.quality_rule(cov) == [2021, 2022, 2023, 2025]


def test_station_temperature_idw():
    days = pd.date_range("2024-07-01", periods=3)
    st = pd.DataFrame([(d, e, v, v + 5) for d in days for e, v in [("X4", 26.0), ("X8", 24.0), ("WU", 25.0)]],
                      columns=["data", "estacio", "tmean", "tmax"])
    st = st[~((st["data"] == days[2]))]                               # last day: no station
    fb = pd.DataFrame({"data": days, "tmean": [25.0, 25.0, 20.0], "tmax": [30.0, 30.0, 25.0]})
    lat, lon = ct.XEMA_STATIONS["X4"][1:3]                            # at the Raval station
    out, w = ct.station_temperature(st, lat, lon, fallback=fb)
    assert w[0] > 0.9 and abs(out["tmean"].iloc[0] - 26.0) < 0.2
    # gap filled with fallback + mean offset
    off = out["tmean"].iloc[0] - 25.0
    assert abs(out["tmean"].iloc[2] - (20.0 + off)) < 1e-9


def test_xema_daily_pivot():
    raw = pd.DataFrame({"codi_estacio": ["X4", "X4"], "data_lectura": ["2024-07-01T00:00:00"] * 2,
                        "codi_variable": [1000, 1001], "valor": ["25.1", "30.2"]})
    d = ct.xema_daily(raw)
    assert d.loc[0, "tmean"] == 25.1 and d.loc[0, "tmax"] == 30.2 and d.loc[0, "estacio"] == "X4"


def test_threshold_factor_ignores_missing_cells():
    g = pd.Series([1.0, 2.0, 3.0, 4.0], index=[24, 25, 26, 27])
    lam = {2021: 1.0, 2022: 1.5, 2023: 2.0}
    Y = pd.DataFrame({a: g * l for a, l in lam.items()})
    S = pd.DataFrame(0.1, index=Y.index, columns=Y.columns)
    Y.loc[27, 2021] = np.nan
    S.loc[26, 2022] = np.nan
    est = ct.threshold_factor(Y, S, ref=2021)[0]
    assert np.allclose(est.values, [1.0, 1.5, 2.0], atol=1e-6)


def test_response_curves_raise_without_reference_days():
    temp = _temp()
    cons = synthetic.consumption(temp, seed=4)
    hot = temp.copy(); hot["tmean"] = hot["tmean"].where(hot["data"].dt.year != 2022, 30.0)
    try:
        ct.response_curves(cons, hot, [2021, 2022], min_ref=1)
        assert False, "should raise"
    except ValueError:
        pass
