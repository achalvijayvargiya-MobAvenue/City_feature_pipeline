# State & City Lookup Data Sources

This folder contains curated CSV files for pipeline features. Data is compiled from published government and industry reports.

## Files

| File | Feature | Columns | Source |
|------|---------|---------|--------|
| `state_internet_penetration.csv` | internet_penetration_state | state, internet_penetration_pct | IAMAI Kantar 2024 |
| `state_smartphone_penetration.csv` | smartphone_penetration_state | state, smartphone_penetration_pct | IAMAI / TRAI |
| `state_cpi.csv` | consumer_price_index | state, cpi_combined | MoSPI |
| `state_median_age.csv` | median_age_estimate | state, median_age_years | Census 2011 projections |
| `state_income_bucket.csv` | income_bucket | state, per_capita_nsdp, income_bucket | RBI / Wikipedia NSDP |
| `state_digital_payment_index.csv` | digital_payment_index | state, upi_per_capita_annual, digital_payment_index | NPCI / Dataful / ET |
| `city_property_price.csv` | avg_property_price | city, price_index, price_per_sqft_approx | NHB Residex / Magicbricks |

## Official Download URLs

### Internet, CPI, Median age, Smartphone
- data.gov.in, MoSPI, IAMAI, TRAI (see `download_state_sources.py`)

### Income (income_bucket)
- RBI Handbook of Statistics: https://www.rbi.org.in/Scripts/PublicationsView.aspx?id=22089
- Wikipedia NSDP list: https://en.wikipedia.org/wiki/List_of_Indian_states_and_union_territories_by_GDP_per_capita
- PIB state-wise per capita: https://pib.gov.in/Pressreleaseshare.aspx?PRID=1942055

### Digital payment (digital_payment_index)
- NPCI monthly metrics: https://www.npci.org.in/statistics/monthly-metrics
- Dataful state-wise UPI: https://dataful.in/datasets/21563/
- ET / Moneycontrol articles for per-capita by state

### Property price (avg_property_price)
- NHB Residex: https://residex.nhbonline.org.in/
- Magicbricks PropIndex: https://property.magicbricks.com/microsite/research-insights/prop-index/
