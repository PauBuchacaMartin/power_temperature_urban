# consum-temperatura-urbana

**How does a city's electricity consumption respond to heat?**
Code for article 1 of the PhD thesis *"The city observed through its responses"*
(Pau Buchaca, ETSAB – Universitat Politècnica de Catalunya).

Using hourly electricity consumption by postcode in Barcelona (Datadis, via Open Data BCN)
and ERA5 temperature, we measure the city's **susceptibility to heat**: how much consumption
rises per degree above a comfort temperature, with memory of previous days. The response
has grown strongly since 2021, mostly at night, and only part of that growth comes from
more air conditioners.

## The model

For each spatial unit (city or postcode) and summer day *d*:

$$\ln E(d) = \sum_{k=0}^{L} \chi_k\,\mathrm{CDD}(d-k) + \text{fixed effects (year, ISO week, weekday, holiday)} + \varepsilon(d)$$

with $\mathrm{CDD}(d) = \max(T(d) - T_c, 0)$. The static susceptibility
$\chi^0 = 100\sum_k \chi_k$ is the % change in consumption per degree-day.
Standard errors are cluster-robust by ISO week.

This is the simplest case of the thesis framework:
$Y_i(t) = \mu_i + \sum_k \int \chi_{ik}(\tau) F_k(t-\tau)\,d\tau + \rho \sum_j W_{ij} Y_j(t) + \eta_i(t)$.

## Install

```bash
pip install git+https://github.com/PauBuchacaMartin/consum-temperatura-urbana.git
```

In Google Colab, put `!` before the line.

## Quick start

```python
import consum_temperatura as ct
from consum_temperatura import synthetic

temp = synthetic.summer_temperature()                       # or ct.era5_daily(41.39, 2.17, "2021-01-01", "2025-12-31")
cons = synthetic.consumption(temp, tc=22.0, chi_by_year={2021: 2.0, 2022: 2.5, 2023: 3.0, 2024: 3.5, 2025: 3.5})

tc, profile = ct.choose_tc(cons, temp)                      # comfort temperature
table, beta, cov = ct.response_by_year(cons, temp, tc)      # chi0 for each summer
print(table)
print(ct.growth(beta, cov, 2021, 2024))                     # growth with its standard error
```

See `notebooks/exemple_dades_sintetiques.ipynb` (opens in Colab).

## Contents

| Path | What it is |
|---|---|
| `src/consum_temperatura/forcings.py` | Degree days with lags, heatwaves, day/night temperature bands |
| `src/consum_temperatura/response.py` | Design matrix, cluster-robust OLS, chi0, per-year response, threshold model, extensive margin |
| `src/consum_temperatura/data.py` | Cached downloads (ERA5 via Open-Meteo), Open Data BCN consumption reader |
| `src/consum_temperatura/alerts.py` | Data-quality alerts: time-band regime change, complete days, level jumps |
| `src/consum_temperatura/synthetic.py` | Synthetic data with known response, used by the tests |
| `src/consum_temperatura/quality.py` | City series, temperature-conditioned anomalies (single days, coverage gaps), sector audit |
| `src/consum_temperatura/daynight.py` | Day-heat and night-heat forcings, response of each time band and its change |
| `src/consum_temperatura/seasonal.py` | Cold branch (heating degree days, symmetry of the V) and the hysteresis (fronts) test |
| `src/consum_temperatura/figstyle.py` | One validated colour style for every article figure |
| `tests/` | Every estimator must recover known parameters on synthetic data |
| `notebooks/` | The article notebook (v0.14, answer to the external review; v0.13 lean version), the full exploratory archive (v0.12) and v0.11, the energy-certificate pilot (v0.2) and an example |
| `docs/article1.md` | State of article 1: results, data alerts, what is and is not established |

## Rules of this repository

1. No method is applied to real data before it recovers known parameters on synthetic data.
2. Every data source is downloaded through a cache, so analyses are reproducible offline.
3. No private data in the repository: only code, open data and synthetic data.

## En català

Aquest repositori conté el codi del primer article de la tesi: la resposta del consum elèctric
de Barcelona a la calor. El notebook de l'article és `notebooks/resposta_calor_bcn_v14.ipynb` (la predicció registrada del 2026 és a `docs/prediccio_2026.md`; l'arxiu complet, `resposta_calor_bcn_v12.ipynb`) i
l'estat de l'article, a `docs/article1.md`. Les funcions del paquet són les mateixes del
notebook, netes i amb proves.

## License

MIT. Data sources keep their own licences (Open Data BCN, Copernicus ERA5, Generalitat de Catalunya).
