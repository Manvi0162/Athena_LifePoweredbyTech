# How the seasonal data files were made
Run once during the hackathon (13 Nov 2026); the app only reads the small CSVs in `../data`.

| Output file | Made from | Result |
|---|---|---|
| `household_day_variation_percentiles.csv` | 17 German households, 4,219 metered days (Zenodo 7506076, CC BY 4.0) | Day-to-day spread: 5th–95th percentile 0.50×–1.60× of a usual day. Weekend ×1.12. |
| `mu_monthly_temperature_2016_2025.csv` | ERA5 daily temperature 2016–2025 (Open-Meteo), central plateau and Port Louis | Coast: Feb 26.9 °C, Jul 22.1 °C. Plateau: Feb 23.1 °C, Jul 17.8 °C. |
| `mu_potable_production_monthly_2024_2025.csv` | Statistics Mauritius ESI 1929, Table 15 (typed from the PDF) | CWA production per month (supply context only) |

Finding: the German households use slightly MORE water in winter (cool climate, no extra showers in summer),
so the summer effect comes from the tropical Singapore study (Salvo 2018): +2.6%/°C without AC, +0.7%/°C overall.
Scripts: `german_daily.py` (meter readings → daily m³), `build_seasonal_data.py` (factors and percentiles).
The raw downloads (~200 MB) are not in the repo.
