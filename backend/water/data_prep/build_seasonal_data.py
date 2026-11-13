"""Rebuild the seasonal data files in ../data from the raw downloads (run once, not at app runtime).

Inputs (download first):
  1. Zenodo 7506076 (CC BY 4.0), 17 German households: https://zenodo.org/records/7506076
     unzip hh-01.zip ... hh-17.zip into RAW/ ; then: python german_daily.py RAW german_daily.csv
  2. Mauth (Germany) daily temperature 2020-09-01..2022-09-30, Open-Meteo archive (ERA5):
     https://archive-api.open-meteo.com/v1/archive?latitude=48.86&longitude=13.58&start_date=2020-09-01&end_date=2022-09-30&daily=temperature_2m_mean&timezone=Europe%2FBerlin
  3. Mauritius daily temperature 2016-2025, Open-Meteo archive (ERA5), two points:
     central plateau  latitude=-20.30&longitude=57.52    coast (Port Louis) latitude=-20.16&longitude=57.50
Usage: python build_seasonal_data.py german_daily.csv mauth.json plateau.json portlouis.json
"""
import json
import sys

import numpy as np
import pandas as pd

daily, mauth, plateau, coast = sys.argv[1:5]
d = pd.read_csv(daily, parse_dates=["date"])
d = d[d["m3"] > 0.005]                                        # drop empty-house days (holidays)
t = json.load(open(mauth))["daily"]
d = d.merge(pd.DataFrame({"date": pd.to_datetime(t["time"]), "temp": t["temperature_2m_mean"]}), on="date")
d["weekend"] = d["date"].dt.dayofweek >= 5
d["month"] = d["date"].dt.month
wk = d.groupby(["household", "weekend"])["m3"].mean().unstack()
print("weekend factor (median of households):", round((wk[True] / wk[False]).median(), 3))     # -> 1.12
d["rel"] = d["m3"] / d.groupby(["household", "month", "weekend"])["m3"].transform("mean")
pd.DataFrame({"percentile": np.arange(101), "relative_to_mean": np.round(np.percentile(d["rel"], np.arange(101)), 4)}) \
    .to_csv("../data/household_day_variation_percentiles.csv", index=False)
d["tbin"] = pd.cut(d["temp"], [-20, 0, 5, 10, 15, 20, 30])
d["rel_hh"] = d["m3"] / d.groupby("household")["m3"].transform("mean")
print(d.groupby("tbin", observed=True)["rel_hh"].agg(["mean", "count"]).round(3))   # no summer rise in Germany
rows = {}
for name, f in (("central_plateau_c", plateau), ("coast_port_louis_c", coast)):
    x = pd.DataFrame(json.load(open(f))["daily"]).dropna(subset=["temperature_2m_mean"])
    rows[name] = x.groupby(pd.to_datetime(x["time"]).dt.month)["temperature_2m_mean"].mean()
m = pd.DataFrame(rows)
m["average_c"] = m.mean(axis=1)
m.index.name = "month"
m.round(2).to_csv("../data/mu_monthly_temperature_2016_2025.csv")
