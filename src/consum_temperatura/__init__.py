"""consum_temperatura: response of urban electricity consumption to temperature.

Code of article 1 of Pau Buchaca's PhD thesis (ETSAB-UPC): how Barcelona's
electricity consumption responds to heat, why the response grows mostly at night,
and how much of the growth comes from more air conditioners versus more use.
"""
from .forcings import cooling_degree_days, heating_degree_days, heatwaves, band_temperatures
from .response import (design_matrix, fit_cluster, prepare, static_susceptibility, fit_city,
                       choose_tc, response_by_year, growth, threshold_factor, extensive_share)
from .data import from_cache, era5_daily, era5_hourly, daily_consumption
from .alerts import band_regime, complete_days, level_jumps
from . import synthetic

__version__ = "0.1.0"
