# Water module: data sources

Every number is copied from the source named; nothing is estimated. Keep this file in the repo.

| File / value | What it holds | Source |
|---|---|---|
| `cwa_domestic_tariff_2012.csv` | CWA domestic tariff, rising blocks per m³ per month: 0–10 Rs 6, 10–20 Rs 8, 20–50 Rs 17, 50+ Rs 32 (wastewater 7.5 / 9 / 20 / 45). Minimum monthly charge Rs 45 (wastewater Rs 55). In force since 1 Jan 2012. | V. Proag (2014), *La tarification d'eau potable à l'île Maurice et à Rodrigues*, Tableau 3: https://bdd.pseau.org/outils/ouvrages/unim_la_tarification_de_l_eau_potable_a_l_ile_de_maurice_et_a_rodrigues_2014.pdf · Le Mauricien, 20 Oct 2011 (2012 increase): https://www.lemauricien.com/actualites/societe/eau-potable-et-eaux-us%C3%A9es-hausse-des-tarifs-35/136009/ · Le Mauricien, 1 Jul 2026 (not revised since 2012): https://www.lemauricien.com/actualites/societe/revision-des-tarifs-a-letude-patrick-assirvaden-pas-question-dalourdir-la-charge-des-menages/711464/ · Official page: https://cwa.govmu.org/cwa/?page_id=794 |
| Meter rent Rs 10, postal Rs 14, no VAT, minimum Rs 45 | Fixed lines of the bill | Our team's real CWA bill (0 m³ → Rs 69). Numbers only; the bill photo is not in the repo. |
| `mu_water_indicators_2018_2025.csv` | Litres per person per day (domestic tariff 2025: **198.9 L**) | Statistics Mauritius, *Energy and Water Statistics 2025* (ESI 1929), Table 1: https://statsmauritius.govmu.org/Documents/Statistics/ESI/2026/EI1929/Energy_Water_Yr25_050626.pdf |
| `mu_water_sales_by_tariff_2024_2025.csv` | Domestic 2025: 387,256 subscribers, 225 m³/year each, Rs 9.97/m³ average | Same report, Table 16 |
| `mu_reservoir_levels_monthly_2024_2025.csv`, `mu_reservoir_capacity.csv` | Monthly reservoir levels (%) 2024–2025 and the 1990–1999 normal; capacities | Same report, Table 14 (Water Resources Commission) |
| `mu_rainfall_monthly_by_region_2024_2025.csv` | Monthly rain (mm) by region with the 1991–2020 long-term mean | Same report, Table 13 (Mauritius Meteorological Services) |
| Shower 7.9 L/min (2.1 gpm), 7.7 min; flush 9.8 L (2.6 gal); washing machine 111 L/load | Default values for water-saving actions (user can change them) | *Residential End Uses of Water, Version 2* (Water Research Foundation, 2016), as summarised at https://en.wikipedia.org/wiki/Residential_water_use_in_the_U.S._and_Canada · data: https://hydroshare.org/resource/6cbedaad1c19414d9015ed10c88fb761/ |
| Dripping tap 31 L/day | "One drip per second wastes more than 3,000 gallons per year" (= 11,356 L / 365) | US EPA WaterSense, Fix a Leak Week: https://www.epa.gov/watersense/fix-leak-week |
| `household_day_variation_percentiles.csv` | Real day-to-day spread of household water use (101 percentiles; 5th–95th: 0.50×–1.60×) and the weekend factor ×1.12 | *Smart Meter Water Consumption Measurements*, 17 households in Mauth, Germany, Sep 2020–Sep 2022, CC BY 4.0: https://zenodo.org/records/7506076 (processed with `data_prep/`) |
| `mu_monthly_temperature_2016_2025.csv` | Mean temperature per month, central plateau and Port Louis, 2016–2025 | ERA5 reanalysis via Open-Meteo archive API: https://open-meteo.com/en/docs/historical-weather-api |
| +2.6% water per °C (homes mostly without AC), +0.7% per °C (all homes) | How much more water households use when it is hotter, in a tropical city | A. Salvo (2018), *Electrical appliances moderate households' water demand response to heat*, Nature Communications 9, 5408 — 121,480 Singapore households, bills 2012–2015: https://pmc.ncbi.nlm.nih.gov/articles/PMC6302094 |
| `mu_potable_production_monthly_2024_2025.csv` | CWA potable water production per month (Mm³), Island of Mauritius | Statistics Mauritius ESI 1929, Table 15 (supply side: shows reservoirs/cuts, not household demand) |
| Summer = Nov–Apr | Mauritian seasons | Mauritius Meteorological Services climate description: http://metservice.intnet.mu |

Notes
- Rising blocks: each price applies only to the m³ inside its block, per monthly bill.
- The block rule above 10 m³ is from the published tariff; our only real CWA bill was 0 m³. **Add a real bill above 10 m³ and check it.**
- Wastewater is charged only to homes on the public sewer.
- Reservoir and rainfall figures are past years (2024–2025), used as season context, not live levels.
- Mare aux Vacoas 1990–1999 normal in Table 14 looks unusual (10–77%); use with care.
- Shower, flush and washer values are North-American averages; Mauritian fixtures may differ.
- The German households use slightly more water in winter (cool climate), so they are used only for the weekend
  factor and day-to-day spread. The summer increase comes from the tropical Singapore study.
