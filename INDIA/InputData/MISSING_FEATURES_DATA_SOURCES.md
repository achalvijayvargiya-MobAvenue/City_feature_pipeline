# Data Sources & Collection Methods for Missing Pipeline Features

**Your pipeline identifiers:** `city_original`, `city_normalized`, `major_city` (district), `state`, `latitude`, `longitude`

---

## 1. city_population

| Source | Granularity | Match Key | Access |
|--------|-------------|-----------|--------|
| **Census 2011 – Town Amenities** | Town-level | Town name + District + State | [data.gov.in](https://www.data.gov.in/catalog/town-amenities-census-2011) – CSV/Zip |
| **Complete Towns Directory** | Town-level | Town name + Sub-district | [data.gov.in](https://www.data.gov.in/catalog/complete-towns-directory-indiastatedistrictsub-district-level-census-2011) |
| **IndianCities (GitHub)** | Major cities | City name | [github.com/recurze/IndianCities](https://github.com/recurze/IndianCities) |
| **census_population.csv** (existing) | District/Sub-district | District name | Already in `true_source/` – use district-level population as fallback |

**Suggested approach:**
- Primary: Download Town Amenities CSV, fuzzy-match `city_normalized` + `major_city` + `state` to Town Name + District + State.
- Fallback: Use district-level population from `census_population.csv` where `major_city` = District.
- For metros: Use `Indian Cities Database.csv` or IndianCities repo for major cities.

---

## 2. literacy_rate & literacy_source

| Source | Granularity | Match Key | Access |
|--------|-------------|-----------|--------|
| **dists.csv** (existing) | District | `major_city` → dist | Already in `true_source/` – has `litrate` |
| **config.STATE_LITERACY_RATES** | State | `state` | Already in pipeline – fallback |
| **Primary Census Abstract 2011** | Town-level | Town + District | [data.gov.in](https://www.data.gov.in/resource/primary-census-abstract-2011-india) |

**Suggested approach:**
- `step5b_district_census.py` already loads `dists.csv` for `sex_ratio` and `population_density` but **does not use `litrate`**. Add `litrate` → `literacy_rate` mapping in that step.
- Use `literacy_source = "district_census"` when from dists, `"state_average"` when from config.

---

## 3. internet_penetration_state & smartphone_penetration_state

| Source | Granularity | Match Key | Access |
|--------|-------------|-----------|--------|
| **IAMAI Kantar Report** | State | `state` | [iamai.in/research/internet-india-2024](https://www.iamai.in/research/internet-india-2024-kantariamai-report) – PDF |
| **TRAI** | State/Telecom circle | State | [trai.gov.in](https://www.trai.gov.in) – reports |
| **GSMA** | State (estimated) | State | Industry reports |

**Suggested approach:**
- Manually extract state-wise % from IAMAI/TRAI PDFs into a CSV (e.g. `state_internet_penetration.csv`).
- Map `state` → penetration %.
- Same for smartphone penetration if available in same reports.
- Update annually.

---

## 5. digital_payment_index

| Source | Granularity | Match Key | Access |
|--------|-------------|-----------|--------|
| **NPCI UPI Statistics** | State (volume) | `state` | [npci.org.in/statistics/monthly-metrics](https://www.npci.org.in/statistics/monthly-metrics) |
| **Media/ET articles** | State per-capita | State | Scraped or manual from reports |
| **Dataful / Medianama** | State analysis | State | Articles with state-wise UPI data |

**Suggested approach:**
- Create index from NPCI state-wise UPI volume ÷ state population.
- Or use per-capita UPI transactions as proxy (e.g. Telangana 274, Bihar ~40).
- Store as `state_digital_payment_index.csv` with columns: state, index_value.

---

## 6. median_age_estimate

| Source | Granularity | Match Key | Access |
|--------|-------------|-----------|--------|
| **Census age distribution** | State | `state` | [data.gov.in – 5-year age groups](https://www.data.gov.in/catalog/population-five-year-age-group-residence-and-sex-india-and-states) |
| **Statista / Data For India** | State | State | [dataforindia.com](https://www.dataforindia.com/age-distribution-states/) |
| **UN Population Prospects** | National | N/A | Use India median as fallback |

**Suggested approach:**
- Download state-wise age distribution, compute median age per state.
- Or use published state estimates (e.g. Kerala ~33, Bihar ~20).
- Map `state` → median_age. District-level is rare; state is best available.

---

## 7. consumer_price_index

| Source | Granularity | Match Key | Access |
|--------|-------------|-----------|--------|
| **MoSPI** | State (rural/urban) | `state` | [mospi.gov.in](https://www.mospi.gov.in) – CPI state-wise |
| **Labour Bureau** | City (CPI-IW) | City name | [labourbureau.gov.in/centre-wise-general-index](https://labourbureau.gov.in/centre-wise-general-index) |
| **IndiaAI portal** | State | State | [aikosh.indiaai.gov.in](https://aikosh.indiaai.gov.in/home/datasets/details/state_level_consumer_price_index_rural_urban_upto_may_2023.html) |

**Suggested approach:**
- Primary: State-level CPI from MoSPI (base 2012=100).
- City-level: Labour Bureau centre-wise index for major cities; map `major_city` or `city_normalized` where possible.
- Store as `state_cpi.csv` or `city_cpi.csv`.

---

## 8. income_bucket

| Source | Granularity | Match Key | Access |
|--------|-------------|-----------|--------|
| **NSSO Household Survey** | State/rural-urban | State + urban/rural | MOSPI/NSSO reports |
| **PLFS (Periodic Labour Force)** | State | State | Labour Bureau |
| **Tax data (CBDT)** | State | State | Indirect – income tax filers |
| **Derived** | District | `major_city` | Use city_tier + literacy + CPI as proxy |

**Suggested approach:**
- State-level income buckets from NSSO/PLFS (Low/Medium/High).
- Or derive: `city_tier` + `literacy_rate` + `avg_property_price` → ordinal bucket.
- LLM enrichment: ask model to assign bucket from city name + tier.

---

## 9. avg_property_price

| Source | Granularity | Match Key | Access |
|--------|-------------|-----------|--------|
| **NHB Residex** | City | City name | [residex.nhbonline.org.in](https://residex.nhbonline.org.in/2017-18/NHB_Residex.aspx) |
| **Magicbricks PropIndex** | City | City name | [property.magicbricks.com](https://property.magicbricks.com/mb-microsite/propindex/all-india-overview.html) |
| **99acres / PropTiger** | City | City name | Web scraping or paid APIs |
| **realdataapi.com** | City | City name | Paid Magicbricks dataset |

**Suggested approach:**
- NHB Residex: official index; map to cities where available.
- Magicbricks PropIndex: city-wise reports; manual extraction or scraping.
- Fallback: district-level from `major_city` if only district data exists.
- Store as `city_property_price.csv` (city, price_per_sqft or index).

---

## Implementation Priority

| Priority | Feature | Effort | Data Availability |
|----------|---------|--------|-------------------|
| 1 | literacy_rate | Low | Already in dists.csv – wire it up |
| 2 | city_population | Medium | Census Town Amenities + district fallback |
| 4 | internet_penetration_state | Low | **Created:** `true_source/state_lookups/state_internet_penetration.csv` |
| 5 | consumer_price_index | Low | **Created:** `true_source/state_lookups/state_cpi.csv` |
| 6 | median_age_estimate | Low | **Created:** `true_source/state_lookups/state_median_age.csv` |
| 7 | digital_payment_index | Medium | NPCI + manual state index |
| 8 | smartphone_penetration_state | Low | **Created:** `true_source/state_lookups/state_smartphone_penetration.csv` |
| 9 | income_bucket | Medium | NSSO or derived proxy |
| 10 | avg_property_price | High | NHB/Magicbricks – limited cities |

---

## Quick Wins (No New Data)

1. **literacy_rate**: Use `litrate` from `dists.csv` in `step5b_district_census.py` (already loaded).
2. **literacy_source**: Set to `"district_census"` when from dists.
3. **city_population**: Use district-level population from `census_population.csv` as fallback where town-level match fails.
