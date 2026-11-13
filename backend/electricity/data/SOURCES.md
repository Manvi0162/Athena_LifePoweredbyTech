# Electricity module: data sources

| File / value | What it holds | Source |
|---|---|---|
| `ceb_domestic_tariff_2026.csv` | CEB domestic tariff 2026, 12 rising blocks per kWh per month (from Rs 3.63) | Expat Mauritius, 28 Jul 2026, citing ceb.mu: https://expat-mauritius.com/en/blog/electricity-mauritius-connection-ceb-meter-price-2026/ · official page: https://ceb.mu/customer-corner/tariff/domestic-tariff |
| `ceb_minimum_charge_2026.csv` | Minimum monthly charge by tariff code: 110 → Rs 50.60, 120 → Rs 211.60, 140 → Rs 424.35 | Same pages |
| Meter rental Rs 20, TV licence Rs 150, VAT 0 | Fixed lines | Our team's real CEB bill (numbers only, no photo in the repo) |
| 201.5 kWh per month | Domestic average: 1,172,239 MWh / 484,680 consumers / 12 | Statistics Mauritius, *Energy and Water Statistics 2025*, Table 11: https://statsmauritius.govmu.org/Documents/Statistics/ESI/2026/EI1929/Energy_Water_Yr25_050626.pdf |
| Appliance kW (air conditioner 1.2, water heater 3.0, iron 1.0, ...) | Typical power ratings, user can enter the label value | Assumptions: replace with a sourced list if you have one |

Verified: real bill 145 kWh (tariff 140, 31 days) → consumption Rs 828, total Rs 998, with blocks NOT scaled to 31 days.
"Last 3 consumptions" on the bill (130 / 143 / 116) assumed most recent first.
