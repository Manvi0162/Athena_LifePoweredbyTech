"""Seasons and day-to-day patterns, all taken from datasets (see data/SOURCES.md).

1. Temperature effect (hot months -> more water):
     factor(month) = 1 + b x (temperature of the month - yearly average temperature)
   b comes from a tropical study of 121,480 Singapore households (Salvo 2018, Nature Communications):
     +2.6% per degC for homes that mostly have no air conditioning, +0.7% per degC across all homes
     (air conditioning replaces some cooling showers). Most Mauritian homes have no AC -> 2.6% by default.
   Monthly temperatures: Mauritius 2016-2025, ERA5 reanalysis via Open-Meteo, central plateau
   (Curepipe area, for region Centre) or coast (Port Louis, other regions).
   Example, no AC, coast: Feb 26.9 degC vs year 24.4 -> x1.065; Jul 22.1 degC -> x0.94.
2. Weekends: x1.12. Measured in 17 German households (4,219 metered days, Zenodo 7506076); same value
   as our earlier assumption.
3. Day-to-day variation: drawn from the real spread of 4,219 household-days (5th-95th percentile:
   0.50x to 1.60x of the household's usual day), not a made-up bell curve.
Habit changes (guests, extra showers, garden) are NOT hidden in the forecast: they are what-if scenarios.
The German data itself shows NO summer increase (cool climate: showers do not go up in summer), which is
why the temperature effect comes from the tropical study and not from Germany.
"""
import bisect
import csv
import os

DATA = os.path.join(os.path.dirname(__file__), "data")
WEEKEND_FACTOR = 1.12
PCT_PER_DEGC = {"no_ac": 0.026, "ac": 0.007}
SUMMER_MONTHS = {11, 12, 1, 2, 3, 4}          # Mauritius Meteorological Services: summer Nov-Apr


def _rows(name):
    with open(os.path.join(DATA, name)) as fh:
        return list(csv.DictReader(fh))


_T = _rows("mu_monthly_temperature_2016_2025.csv")
TEMPS = {"Centre": {int(r["month"]): float(r["central_plateau_c"]) for r in _T},
         "coast": {int(r["month"]): float(r["coast_port_louis_c"]) for r in _T}}
_P = _rows("household_day_variation_percentiles.csv")
_PCT = [float(r["percentile"]) / 100 for r in _P]
_REL = [float(r["relative_to_mean"]) for r in _P]


def _temps(profile):
    return TEMPS["Centre"] if profile.get("region") == "Centre" else TEMPS["coast"]


def slope(profile):
    return PCT_PER_DEGC["ac"] if profile.get("has_air_conditioning") else PCT_PER_DEGC["no_ac"]


def season_factor(day, profile):
    t = _temps(profile)
    return 1 + slope(profile) * (t[day.month] - sum(t.values()) / 12)


def weekday_factor(day):
    return WEEKEND_FACTOR if day.weekday() >= 5 else 1.0


def random_day(rnd):
    """A realistic day-to-day multiplier, drawn from the measured percentiles (mean about 1)."""
    u = rnd.random()
    i = min(bisect.bisect_left(_PCT, u), len(_PCT) - 1)
    if i == 0:
        return _REL[0]
    a, b = _PCT[i - 1], _PCT[i]
    return _REL[i - 1] + (_REL[i] - _REL[i - 1]) * (u - a) / (b - a)


def explain(profile, months):
    t = _temps(profile)
    year = sum(t.values()) / 12
    return {
        "months": [{"month": m, "temperature_c": round(t[m], 1), "factor": round(1 + slope(profile) * (t[m] - year), 3),
                    "summer": m in SUMMER_MONTHS} for m in months],
        "yearly_average_temperature_c": round(year, 1),
        "pct_per_degc": round(slope(profile) * 100, 1),
        "air_conditioning": bool(profile.get("has_air_conditioning")),
        "weekend_factor": WEEKEND_FACTOR,
        "temperatures_from": "central plateau" if profile.get("region") == "Centre" else "coast (Port Louis)",
        "sources": ["Salvo (2018) Nature Communications: Singapore household water use vs temperature",
                    "ERA5 daily temperature 2016-2025 for Mauritius (Open-Meteo)",
                    "Zenodo 7506076: 17 German households, smart-meter readings 2020-2022 (weekend factor, daily spread)"],
    }
