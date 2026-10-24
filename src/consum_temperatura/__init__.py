"""consum_temperatura: response of urban electricity consumption to temperature.

Code of article 1 of Pau Buchaca's PhD thesis (ETSAB-UPC): how Barcelona's
electricity consumption responds to heat, why the response grows mostly at night,
and how much of the growth comes from more air conditioners versus more use.
"""
from .forcings import cooling_degree_days, heating_degree_days, heatwaves, band_temperatures
from .response import (design_matrix, fit_cluster, prepare, static_susceptibility, fit_city,
                       choose_tc, response_by_year, growth, threshold_factor, extensive_share,
                       absolute_response_by_year, heatwave_residuals, response_curves, curves_equal,
                       correlation_check, slope_over_years)
from .quality import (city_series, temperature_residuals, anomalies, extreme_days, clean_days,
                      anomaly_blocks, sector_shares)
from .daynight import day_night_forcings, day_night_response, day_night_summary
from .data import from_cache, era5_daily, era5_hourly, daily_consumption
from .alerts import band_regime, complete_days, level_jumps
from .seasonal import (winter_label, christmas, prepare_winter, winter_design, fit_winter, choose_th,
                       response_by_winter, asymmetry, falling_days, flexible_memory, hysteresis_test, summer_phase,
                       response_by_phase)
from . import synthetic, figstyle

__version__ = "0.3.0"
