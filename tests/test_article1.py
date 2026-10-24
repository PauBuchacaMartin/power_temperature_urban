"""Tests of the v0.13 functions: data quality, absolute response, heatwave residuals,
response curves, correlation check and day–night response. All on synthetic data
with a known answer."""
import numpy as np
import pandas as pd

import consum_temperatura as ct
from consum_temperatura import synthetic
from consum_temperatura.data import daily_consumption

YEARS = [2021, 2022, 2023, 2024, 2025]


def _temp():
    t = synthetic.summer_temperature(seed=0)
    t["tmax"] = t["tmean"] + 5
    return t


# ---------- qualitat de dades ----------

def test_daily_consumption_drops_duplicates():
    raw = pd.DataFrame({"Data": ["2024-01-01"] * 3, "Codi_Postal": ["08001"] * 3,
                        "Sector_Economic": ["Residencial"] * 3, "Tram_Horari": ["De 00:00:00 a 05:59:59 h"] * 3,
                        "Valor": [10, 10, 5]})
    raw.loc[2, "Tram_Horari"] = "De 06:00:00 a 11:59:59 h"
    d = daily_consumption(raw)
    assert len(d) == 2 and d["kwh"].sum() == 15


def test_daily_consumption_numeric_postcode():
    # el CSV del portal llegit amb pandas dona el CP com a número (8001)
    raw = pd.DataFrame({"Data": ["2024-01-01"], "Codi_Postal": [8001], "Sector_Economic": ["Residencial"],
                        "Tram_Horari": ["De 00:00:00 a 05:59:59 h"], "Valor": [3.5]})
    d = daily_consumption(raw)
    assert d["cp"].iloc[0] == "08001" and d["kwh"].iloc[0] == 3.5


def test_anomalies_find_gap_but_not_heat():
    temp = _temp()
    cons = synthetic.annual_consumption(temp, chi_c_by_year={a: 6.0 for a in YEARS}, seed=3)
    gap = (cons["data"] >= "2023-01-10") & (cons["data"] <= "2023-03-20")
    cons.loc[gap, "kwh"] *= 0.70                                    # forat de cobertura: −30 %
    cons.loc[cons["data"] == "2022-05-04", "kwh"] *= 2.0            # un dia dolent
    hot = temp.nlargest(15, "tmean")["data"]                        # els dies més calents
    an = ct.anomalies(cons, temp, protect=ct.extreme_days(temp))
    flagged = set(an.index[an["single"] | an["block"]])
    gap_days = set(cons.loc[gap, "data"])
    assert len(gap_days & flagged) / len(gap_days) > 0.8
    assert pd.Timestamp("2022-05-04") in flagged
    assert not (set(hot) & flagged)


def test_positive_block_is_not_excluded():
    temp = _temp()
    cons = synthetic.annual_consumption(temp, seed=4)
    m = (cons["data"] >= "2024-08-01") & (cons["data"] <= "2024-08-20")
    cons.loc[m, "kwh"] *= 1.20                                      # dues setmanes de consum alt (calor persistent)
    an = ct.anomalies(cons, temp)
    assert not an.loc[an.index.isin(cons.loc[m, "data"]), "block"].any()
    assert an.loc[an.index.isin(cons.loc[m, "data"]), "block_pos"].any()


def test_city_series_sums_sectors():
    d = pd.DataFrame({"data": pd.to_datetime(["2024-01-01"] * 3), "cp": ["08001", "08002", "08001"],
                      "sector": ["Residencial", "Residencial", "Serveis"], "tram": ["a", "a", "a"], "kwh": [1., 2., 4.]})
    assert ct.city_series(d, "Residencial")["kwh"].iloc[0] == 3
    assert ct.city_series(d)["kwh"].iloc[0] == 7


# ---------- resposta ----------

def test_absolute_response_constant_while_relative_grows():
    # el consum base baixa i la resposta absoluta és constant: la relativa ha de créixer, l'absoluta no
    temp = _temp()
    t = temp.sort_values("data").reset_index(drop=True)
    cdd = np.maximum(t["tmean"] - 22, 0)
    base = 1e5 * (1 - 0.05 * (t["data"].dt.year - 2021))
    rng = np.random.default_rng(1)
    kwh = base + 3000 * cdd + rng.normal(0, 300, len(t))
    cons = pd.DataFrame({"data": t["data"], "kwh": kwh})
    ab = ct.absolute_response_by_year(cons, temp, 22.0, lags=0, years=YEARS)
    assert np.allclose(ab["resp"].values, 3.0, atol=0.3)            # 3000 kWh = 3 MWh per K
    tab, _, _ = ct.response_by_year(cons, temp, 22.0, lags=0, years=YEARS)
    assert tab.loc[2025, "chi0"] > tab.loc[2021, "chi0"]


def test_heatwave_residuals_zero_for_linear_system():
    temp = _temp()
    waves = ct.heatwaves(temp)
    chi = {2021: 4.0, 2022: 5.0, 2023: 5.5, 2024: 7.0, 2025: 7.0}
    cons = synthetic.consumption(temp, tc=22.0, chi_by_year=chi, seed=5)
    hot, summ, sd = ct.heatwave_residuals(cons, temp, 22.0, temp.loc[waves, "data"], years=YEARS)
    assert len(hot) > 10
    assert abs(hot["residu_pct"].mean()) < 3 * sd / np.sqrt(len(hot)) + 0.5


def test_response_curves_and_threshold_factor():
    # corbes amb la mateixa forma i amplitud ×1, ×1,5, ×2: el model de llindars ho ha de recuperar
    temp = _temp()
    amp = {2021: 1.0, 2022: 1.5, 2023: 2.0}
    t = temp.sort_values("data").reset_index(drop=True)
    tm3 = t["tmean"].rolling(3).mean().fillna(t["tmean"])
    shape = np.maximum(tm3 - 20, 0) ** 1.5 / 100
    rng = np.random.default_rng(2)
    a = t["data"].dt.year.map(amp).fillna(1.0).values
    cons = pd.DataFrame({"data": t["data"], "kwh": np.exp(11 + a * shape + rng.normal(0, 0.01, len(t)))})
    Y, S = ct.response_curves(cons, temp, years=list(amp), bins=range(21, 27), floor=20)
    hi = [b for b in Y.index if b >= 23]
    lam, se, g, chi2, dof = ct.threshold_factor(Y.loc[hi], S.loc[hi], ref=2021)
    assert abs(lam[2022] - 1.5) < 0.15 and abs(lam[2023] - 2.0) < 0.2


def test_curves_equal():
    Y = pd.DataFrame({2021: [1.0, 2.0], 2022: [1.0, 2.0]}, index=[21, 22])
    S = pd.DataFrame(0.5, index=Y.index, columns=Y.columns)
    chi2, dof = ct.curves_equal(Y, S)
    assert chi2 < 1e-12 and dof == 2


def test_correlation_check_matches_regression():
    temp = _temp()
    cons = synthetic.consumption(temp, tc=22.0, chi_by_year={a: 5.0 for a in YEARS}, seed=6)
    reg, cor = ct.correlation_check(cons, temp, 22.0, years=YEARS)
    assert abs(reg.sum() - cor.sum()) < 0.5


def test_slope_over_years():
    temp = _temp()
    chi = {2021: 4.0, 2022: 5.0, 2023: 6.0, 2024: 7.0, 2025: 8.0}
    cons = synthetic.consumption(temp, tc=22.0, chi_by_year=chi, seed=7)
    tab, b, c = ct.response_by_year(cons, temp, 22.0, years=YEARS)
    s, se = ct.slope_over_years(b, c, YEARS)
    assert abs(s - 1.0) < 3 * se + 0.1


# ---------- dia–nit ----------

def _day_night_data(grow_night=True, seed=8):
    temp = _temp()
    t = temp.sort_values("data").reset_index(drop=True)
    rng = np.random.default_rng(seed)
    bands = pd.DataFrame({"data": t["data"],
                          "t_nit": t["tmean"] - 3 + rng.normal(0, 1.2, len(t)),
                          "t_dia": t["tmean"] + 4 + rng.normal(0, 1.2, len(t))})
    f = ct.day_night_forcings(bands, tc_day=27, tc_night=20).fillna(0)
    yr = t["data"].dt.year.values
    night = np.where(yr >= 2024, 0.08, 0.04) if grow_night else 0.04
    ln_e = 11 + night * f["cdd_nit0"].values + 0.01 * f["cdd_dia0"].values + rng.normal(0, 0.01, len(t))
    return temp, bands, f, pd.DataFrame({"data": t["data"], "kwh": np.exp(ln_e)})


def test_day_night_recovers_night_response():
    temp, bands, f, cons = _day_night_data(grow_night=False)
    b, c = ct.day_night_response(cons, temp, f, 22.0, years=YEARS)
    s = ct.day_night_summary(b, c)
    assert abs(s["nit"] - 4.0) < 3 * s["se_nit"] + 0.3
    assert abs(s["dia"] - 1.0) < 3 * s["se_dia"] + 0.3


def test_day_night_growth_of_night_only():
    temp, bands, f, cons = _day_night_data(grow_night=True)
    b, c = ct.day_night_response(cons, temp, f, 22.0, years=YEARS, by_year=True)
    s = ct.day_night_summary(b, c, by_year=True, y0=2021, y1=2024)
    assert abs(s["canvi_nit"] - 4.0) < 3 * s["se_canvi_nit"] + 0.3
    assert abs(s["canvi_dia"]) < 3 * s["se_canvi_dia"] + 0.3


def test_response_by_year_with_extra_control():
    # un control que no hi té res a veure no ha de moure el creixement
    temp = _temp()
    chi = {2021: 4.0, 2022: 5.0, 2023: 6.0, 2024: 7.0, 2025: 8.0}
    cons = synthetic.consumption(temp, tc=22.0, chi_by_year=chi, seed=9)
    rng = np.random.default_rng(0)
    tab, b, c = ct.response_by_year(cons, temp, 22.0, years=YEARS,
                                    extra=lambda t: pd.DataFrame({"soroll": rng.normal(size=len(t))}))
    d, se = ct.growth(b, c, 2021, 2024)
    assert "soroll" in b.index and abs(d - 3.0) < 3 * se + 0.2


def test_year_colors_are_ordered():
    cols = ct.figstyle.year_colors([2021, 2022, 2023, 2024, 2025])
    assert cols[2021] == ct.figstyle.YEARS_RAMP[0] and cols[2025] == ct.figstyle.YEARS_RAMP[-1]
