# Water data for the LiveBetter water module

All figures are copied from the official sources below; nothing is estimated. Keep this file in the repo.

| File | What it holds | Source |
|---|---|---|
| `cwa_domestic_tariff_2012.csv` | CWA domestic tariff, rising blocks per m³ per month (potable + wastewater). Minimum monthly charge: Rs 45 potable, Rs 55 wastewater. In force since 1 Jan 2012 and not revised since (Le Mauricien, 1 Jul 2026). | V. Proag, *La tarification d'eau potable à l'île Maurice et à Rodrigues* (2014), Tableau 3: https://bdd.pseau.org/outils/ouvrages/unim_la_tarification_de_l_eau_potable_a_l_ile_de_maurice_et_a_rodrigues_2014.pdf · Le Mauricien, 20 Oct 2011: https://www.lemauricien.com/actualites/societe/eau-potable-et-eaux-us%C3%A9es-hausse-des-tarifs-35/136009/ · Le Mauricien, 1 Jul 2026: https://www.lemauricien.com/actualites/societe/revision-des-tarifs-a-letude-patrick-assirvaden-pas-question-dalourdir-la-charge-des-menages/711464/ · Official page (not reachable from our tools): https://cwa.govmu.org/cwa/?page_id=794 |
| `mu_water_indicators_2018_2025.csv` | Potable water produced/used and litres per person per day (all users; domestic tariff: 198.9 L in 2025). | Statistics Mauritius, ESI No 1929 *Energy and Water Statistics 2025*, Table 1 |
| `mu_water_sales_by_tariff_2024_2025.csv` | Subscribers, volume, amount, average consumption and average price per tariff (domestic 2025: 387,256 subscribers, 225 m³/year, Rs 9.97/m³). | Same report, Table 16 |
| `mu_reservoir_levels_monthly_2024_2025.csv` | Monthly mean/min/max % level for 7 reservoirs + all reservoirs, 2024 and 2025, and the 1990–1999 normal where printed. | Same report, Table 14 (Water Resources Commission) |
| `mu_reservoir_capacity.csv` | Capacity of each reservoir (Mm³). | Same report, Table 14 |
| `mu_rainfall_monthly_by_region_2024_2025.csv` | Monthly rainfall (mm) for North, South, East, West, Centre, the whole island and Rodrigues, with the 1991–2020 long-term mean. | Same report, Table 13 (Mauritius Meteorological Services) |

Statistics Mauritius report (PDF, published 5 Jun 2026; 2025 figures provisional):
https://statsmauritius.govmu.org/Documents/Statistics/ESI/2026/EI1929/Energy_Water_Yr25_050626.pdf

Notes
- Tariff blocks are monthly; meters are read every 25–35 days. Each rate applies to the m³ inside its block ("next 10 m³", "next 30 m³").
- Not found in any source: the meter rent amount and whether VAT applies. Check a real CWA bill.
- Wastewater is charged only to homes connected to the public sewer.
- In Table 14 the 1990–1999 normal for Mare aux Vacoas looks unusual (10–77%); use it with care.
- Empty cells = "-" (no data) in the source.

## Electricity (added)
| File | What it holds | Source |
|---|---|---|
| `ceb_domestic_tariff_2026.csv` | CEB domestic tariff 2026, 12 rising blocks per kWh per month | CEB 2026 tariff as published by Expat Mauritius (28 Jul 2026), citing ceb.mu: https://expat-mauritius.com/en/blog/electricity-mauritius-connection-ceb-meter-price-2026/ · official page: https://ceb.mu/customer-corner/tariff/domestic-tariff · **Verified on our real CEB bill: 145 kWh -> Rs 828.** |
| `ceb_minimum_charge_2026.csv` | Minimum monthly charge by tariff code (110 / 120 / 140) | Same page |
| `mu_household_benchmarks_2025.csv` | National averages used for "you vs Mauritius" | Statistics Mauritius ESI 1929, Tables 1, 11 and 16 |

Fixed charges from our bills: CWA meter rent Rs 10 (12 mm), postal Rs 14, no VAT; CEB meter rental Rs 20, TV licence Rs 150, VAT 0.
