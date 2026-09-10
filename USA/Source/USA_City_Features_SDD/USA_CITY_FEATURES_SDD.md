# USA City Features — Spec-Driven Development Specification

**Document:** `USA_CITY_FEATURES_SDD.md`  
**Version:** 1.0  
**Status:** Development-ready specification  
**Target:** IDE / coding agent  
**Primary objective:** Build a modular, testable, reproducible pipeline that creates a USA city/location feature dataset matching the 36-column schema in `cityy.xlsx`.

---

## 1. Development instruction

Implement this project as a **spec-driven, modular data-engineering pipeline**.

Do not build one large scraper.

Use independent source adapters, normalization modules, spatial-join modules, feature calculators, validation modules, and an orchestration layer.

Every source must be replaceable without changing downstream feature logic.

Every derived feature must have:
- an explicit formula/rule,
- source provenance,
- version/date,
- confidence/status,
- unit where applicable,
- validation tests.

Do not scrape commercial websites when a free authoritative dataset/API exists.

The pipeline must be deterministic for a fixed source snapshot and configuration.

---

# 2. Original input schema

The source Excel contains exactly these 36 columns:

1. `#`
2. `pincode`
3. `state_original`
4. `major_city`
5. `latitude`
6. `longitude`
7. `region`
8. `coastal_city`
9. `distance_to_state_capital`
10. `city_tier`
11. `is_metro_city`
12. `is_smart_city`
13. `is_state_capital`
14. `is_union_territory_capital`
15. `literacy_rate`
16. `median_age_estimate`
17. `consumer_price_index`
18. `income_bucket`
19. `has_airport`
20. `has_international_airport`
21. `has_metro_rail`
22. `has_seaport`
23. `major_railway_station`
24. `internet_penetration_state`
25. `smartphone_penetration_state`
26. `digital_payment_index`
27. `is_it_hub`
28. `is_manufacturing_hub`
29. `is_financial_center`
30. `is_textile_hub`
31. `is_education_hub`
32. `is_tourist_city`
33. `is_coastal`
34. `district_population_numeric`
35. `district_population`
36. `sex_ratio`

The final USA dataset must preserve these exact column names and order for backward compatibility.

---

# 3. Important USA geography decision

The source dataset is Indian PIN-code oriented.

For USA, use this logical grain:

`ZCTA/ZIP -> Place/City -> County -> State -> Region`

Primary location key:

`zcta5`

Important:
- A Census ZCTA is not exactly the same thing as a USPS ZIP Code.
- Treat ZCTA as the analytical geographic unit.
- Preserve a future `zip_source_type` field internally.
- Do not assume one ZIP belongs to exactly one city.
- Use spatial joins to assign city/place, county and CBSA.

The public output can retain `pincode` for compatibility, but its USA value is the 5-digit ZCTA.

---

# 4. Architecture

```text
                    +----------------------+
                    |   CLI / Orchestrator |
                    +----------+-----------+
                               |
              +----------------+----------------+
              |                |                |
              v                v                v
       Census Adapter     BLS Adapter      FAA Adapter
              |                |                |
              v                v                v
       Census Raw Data     BLS Raw Data    FAA Raw Data
              |                |                |
              +----------------+----------------+
                               |
              +----------------+----------------+
              |                |                |
              v                v                v
        BTS/FRA Adapter   MARAD/NOAA        Industry Adapter
              |                |                |
              +----------------+----------------+
                               |
                               v
                     Normalization Layer
                               |
                               v
                     Geography Resolver
                               |
                               v
                     Feature Calculators
                               |
                               v
                     Feature Validation
                               |
                               v
                 Final 36-column Dataset
                               |
                    +----------+----------+
                    |                     |
                    v                     v
                CSV/Parquet          Data Quality
```

---

# 5. Recommended repository structure

```text
usa_city_features/
│
├── README.md
├── pyproject.toml
├── .env.example
├── .gitignore
│
├── configs/
│   ├── default.yaml
│   ├── sources.yaml
│   ├── thresholds.yaml
│   └── schema.yaml
│
├── src/
│   └── usa_city_features/
│       ├── __init__.py
│       │
│       ├── cli.py
│       ├── orchestrator.py
│       │
│       ├── config/
│       │   ├── loader.py
│       │   └── models.py
│       │
│       ├── models/
│       │   ├── location.py
│       │   ├── source_record.py
│       │   ├── feature_record.py
│       │   └── provenance.py
│       │
│       ├── sources/
│       │   ├── base.py
│       │   ├── census.py
│       │   ├── bls.py
│       │   ├── faa.py
│       │   ├── bts.py
│       │   ├── fra.py
│       │   ├── marad.py
│       │   ├── noaa.py
│       │   └── state_capitals.py
│       │
│       ├── geography/
│       │   ├── zcta.py
│       │   ├── places.py
│       │   ├── counties.py
│       │   ├── cbsa.py
│       │   ├── regions.py
│       │   └── spatial_join.py
│       │
│       ├── features/
│       │   ├── geography_features.py
│       │   ├── demographic_features.py
│       │   ├── infrastructure_features.py
│       │   ├── connectivity_features.py
│       │   ├── industry_features.py
│       │   ├── tourism_features.py
│       │   ├── derived_features.py
│       │   └── feature_registry.py
│       │
│       ├── transforms/
│       │   ├── normalize.py
│       │   ├── type_cast.py
│       │   ├── bucketize.py
│       │   └── distance.py
│       │
│       ├── validation/
│       │   ├── schema_validator.py
│       │   ├── range_validator.py
│       │   ├── geography_validator.py
│       │   ├── source_validator.py
│       │   └── report.py
│       │
│       ├── storage/
│       │   ├── cache.py
│       │   ├── raw_store.py
│       │   └── output.py
│       │
│       └── utils/
│           ├── http.py
│           ├── logging.py
│           ├── hashing.py
│           └── retry.py
│
├── data/
│   ├── raw/
│   ├── intermediate/
│   ├── processed/
│   └── reference/
│
├── tests/
│   ├── unit/
│   ├── integration/
│   ├── contract/
│   └── fixtures/
│
├── docs/
│   ├── DATA_DICTIONARY.md
│   ├── SOURCE_CATALOG.md
│   └── DERIVATION_RULES.md
│
└── scripts/
    ├── download_sources.py
    ├── build_features.py
    └── validate_output.py
```

---

# 6. Module responsibilities

## 6.1 `sources/base.py`

Define a common interface:

```python
class SourceAdapter(Protocol):
    source_name: str

    def fetch(self, request: SourceRequest) -> SourceResponse:
        ...

    def validate(self, response: SourceResponse) -> None:
        ...

    def save_raw(self, response: SourceResponse) -> RawArtifact:
        ...
```

Requirements:
- retry transient HTTP failures,
- timeout,
- logging,
- response checksum,
- source timestamp,
- raw artifact caching,
- no silent failures.

---

# 7. Source modules

## 7.1 Census Adapter

Primary source for:
- ZCTA
- states
- places
- counties
- CBSA
- population
- median age
- income
- education
- internet
- smartphone
- sex ratio

Use Census API and TIGER/Line/Gazetteer downloads.

Default ACS dataset:

`2024 ACS 5-Year`

Make ACS year configurable.

Core variables:

```text
B01003_001E  total population
B01002_001E  median age
B01001_002E  male population
B01001_026E  female population
B19013_001E  median household income
B28002       internet subscription
B28001       computer/device ownership
```

Do not hard-code variable descriptions in feature logic. Put source-variable mappings in `configs/sources.yaml`.

---

# 8. Smartphone variable requirement

Do not blindly assume a single variable index.

At startup, the Census adapter must retrieve the selected ACS group's variable metadata and resolve the variable by its Census label/ concept.

This prevents breakage if the exact variable code changes between releases.

Required semantic target:

`households with smartphone / total households * 100`

The adapter should expose:

```python
get_variable_by_label(
    group="B28001",
    semantic_label="smartphone"
)
```

and fail loudly if the expected semantic variable cannot be found.

---

# 9. BLS Adapter

Primary use:

`consumer_price_index`

Default BLS series:

```text
CUUR0000SA0
```

Meaning:

`All items in U.S. city average, all urban consumers, not seasonally adjusted`

Important:

This is NOT a CPI value for every individual U.S. city.

Therefore:

- default feature = latest configured U.S.-city-average CPI;
- optionally support BLS area-specific series where available;
- record `cpi_scope` in provenance;
- never imply city-level precision when source is national.

Configuration:

```yaml
cpi:
  mode: us_city_average
  series_id: CUUR0000SA0
```

---

# 10. FAA Adapter

Source:
`FAA Airport Master Record / aviation facility datasets`

Required normalized fields:

```text
airport_id
airport_name
latitude
longitude
airport_type
facility_type
scheduled_service
international_indicator
```

Features:

```text
has_airport
has_international_airport
```

Spatial rule:

A location gets `has_airport=1` when at least one qualifying airport is within the configured radius or intersects the assigned geography.

Do not use airport name matching as the primary method.

---

# 11. BTS / transit Adapter

Source:
`BTS National Transit Map / GTFS-derived transit data`

Required fields:

```text
agency
route
stop
mode
latitude
longitude
```

Rail modes must be configurable.

Default qualifying modes:

```text
subway
heavy rail
light rail
streetcar
commuter rail
```

Feature:

`has_metro_rail`

Do not classify a city as metro rail based only on the existence of a bus route.

---

# 12. FRA / Amtrak Adapter

Source:

`BTS/FRA Amtrak Stations dataset`

Required fields:

```text
station_name
latitude
longitude
city
state
```

Feature:

`major_railway_station`

Default definition:

`1` when a qualifying Amtrak/intercity passenger rail station is spatially associated with the location.

Make a future option available for all FRA passenger rail stations.

---

# 13. MARAD / NOAA Adapter

Sources:
- MARAD U.S. port data
- NOAA coastline/geospatial data
- World Port Index where appropriate

Features:

```text
has_seaport
coastal_city
is_coastal
```

Important:
`coastal_city` and `is_coastal` should not be independently guessed.

Use one canonical coastline calculation and derive both fields from it.

Example:

```python
is_coastal = distance_to_coast_km <= COASTAL_RADIUS_KM
coastal_city = is_coastal
```

Default radius must be configurable.

---

# 14. State capital module

Maintain a version-controlled reference table:

```text
state_code
state_name
capital_name
capital_latitude
capital_longitude
```

This is a small static reference dataset.

Features:

```text
is_state_capital
distance_to_state_capital
```

Distance:

Use Haversine distance in kilometers.

Formula:

```text
a = sin²((lat2-lat1)/2)
    + cos(lat1) * cos(lat2) * sin²((lon2-lon1)/2)

c = 2 * atan2(sqrt(a), sqrt(1-a))

distance_km = earth_radius_km * c
```

---

# 15. Geography module

## 15.1 ZCTA

Download Census ZCTA geometry.

Normalize:

```text
zcta5 = zero-padded 5 digit string
```

Never store ZIP/ZCTA as integer internally because leading zeroes are meaningful.

Example:

```text
02108
```

must remain:

```text
"02108"
```

---

## 15.2 Place / city

Use Census Places geometry.

Spatially associate ZCTA representative point to Place.

If multiple Places intersect a ZCTA:
- choose the Place containing the ZCTA representative point;
- if no Place contains it, use nearest Place within configured radius;
- otherwise set city unresolved and flag the record.

Never silently guess.

---

## 15.3 County

Assign county using spatial containment.

Store internally:

```text
county_fips
county_name
```

Use county as the USA analogue for the source dataset's district population concept.

---

## 15.4 CBSA

Use Census CBSA geometry.

Feature:

```text
is_metro_city
```

Default:

```text
1 = inside Metropolitan Statistical Area
0 = otherwise
```

Do not classify Micropolitan Statistical Areas as metro unless configuration explicitly says so.

---

# 16. Region mapping

Use official Census regions:

```text
Northeast
Midwest
South
West
```

Recommended output values:

```text
NE
MW
S
W
```

This is different from the Indian source's regional semantics.

The mapping must be stored in configuration, not embedded in code.

---

# 17. City tier

There is no single official U.S. city-tier field.

Implement a configurable derived feature.

Default:

```yaml
city_tier:
  T1:
    min_population: 1000000
  T2:
    min_population: 250000
    max_population: 999999
  T3:
    max_population: 249999
```

Use Census population for the selected Place.

If the assigned geography is not a Census Place, fall back to county/city population only when explicitly enabled.

---

# 18. Literacy rate

Do not invent a U.S. literacy rate.

The Census ACS does not provide a directly comparable universal city-level literacy percentage.

Default implementation:

Use a documented education proxy.

Recommended:

```text
education_rate =
population age 25+ with high school diploma or higher
/
population age 25+
* 100
```

Store internally:

```text
literacy_rate
literacy_rate_definition = education_attainment_proxy
```

The public 36-column output keeps `literacy_rate` for compatibility.

---

# 19. Income bucket

Source:

`B19013_001E`

Default buckets:

```text
L  < 50,000
M  50,000 - 99,999
H  100,000 - 199,999
VH >= 200,000
```

All thresholds configurable.

---

# 20. Digital payment index

There is no single authoritative free U.S. city-level digital-payment index.

Do not scrape arbitrary websites.

Implement a reproducible derived index.

Default inputs:

```text
internet_penetration_state
smartphone_penetration_state
income_normalized
metro_score
```

Example:

```text
digital_payment_index =
    0.40 * internet_score
  + 0.35 * smartphone_score
  + 0.15 * income_score
  + 0.10 * metro_score
```

Normalize to `0..100`.

All weights must live in `thresholds.yaml`.

This feature is explicitly labeled `derived`, not `observed`.

---

# 21. Smart city

There is no authoritative national binary field.

Implement a configurable derived score.

Suggested inputs:

```text
has_metro_rail
has_airport
internet penetration
smartphone penetration
digital_payment_index
IT hub status
```

Do not use subjective web search.

Default:

```text
smart_city_score >= configured threshold
=> is_smart_city = true
```

Keep the score internally even though the final schema only contains the boolean.

---

# 22. Industry hub features

Use employment concentration rather than subjective lists.

Recommended industry definitions:

```text
IT:
  NAICS 51 + relevant NAICS 54 sectors

Manufacturing:
  NAICS 31-33

Financial:
  NAICS 52

Textile:
  NAICS 313-314

Education:
  NAICS 61
```

Primary source:
- Census ACS industry tables
- BLS QCEW for more detailed industry employment

Generic formula:

```text
industry_share =
industry_employment / total_employment
```

Hub classification:

```text
industry_share >= configured threshold
AND
industry_employment >= configured minimum
```

This avoids declaring a small city a hub from a tiny denominator.

---

# 23. Tourist city

No universal official binary flag.

Implement a derived score.

Possible free inputs:

```text
NPS visitation
BTS tourism/travel indicators where available
arts/entertainment employment
accommodation/food employment
airport presence
coastal status
```

Default rule should be configuration-driven.

Example:

```text
tourism_score =
  weighted standardized indicators

is_tourist_city = tourism_score >= threshold
```

Never use a hard-coded city list in feature logic.

---

# 24. Population fields

## `district_population_numeric`

For USA compatibility:

Use assigned county population.

Source:

```text
ACS B01003_001E
```

Internal canonical field:

```text
county_population
```

Final compatibility output:

```text
district_population_numeric
```

---

## `district_population`

Bucket `district_population_numeric`.

Example default:

```yaml
district_population:
  VS: < 250000
  S: 250000 - 499999
  M: 500000 - 999999
  L: 1000000 - 4999999
  VL: >= 5000000
```

Thresholds configurable.

---

# 25. Sex ratio

Use:

```text
male_population = B01001_002E
female_population = B01001_026E
```

Formula:

```text
sex_ratio =
male_population / female_population * 100
```

Handle zero denominator as null + validation error.

---

# 26. Exact 36-column output contract

Output order must be exactly:

```text
#
pincode
state_original
major_city
latitude
longitude
region
coastal_city
distance_to_state_capital
city_tier
is_metro_city
is_smart_city
is_state_capital
is_union_territory_capital
literacy_rate
median_age_estimate
consumer_price_index
income_bucket
has_airport
has_international_airport
has_metro_rail
has_seaport
major_railway_station
internet_penetration_state
smartphone_penetration_state
digital_payment_index
is_it_hub
is_manufacturing_hub
is_financial_center
is_textile_hub
is_education_hub
is_tourist_city
is_coastal
district_population_numeric
district_population
sex_ratio
```

---

# 27. Internal canonical schema

Do NOT perform all processing directly against the 36-column compatibility schema.

Maintain an internal richer schema.

Recommended:

```text
location_id
zcta5
place_geoid
place_name
county_fips
county_name
state_fips
state_code
state_name
cbsa_code
cbsa_name
latitude
longitude
region
population
county_population
median_age
median_household_income
male_population
female_population
internet_households
smartphone_households
airport_count
international_airport_count
rail_station_count
metro_rail_count
seaport_count
distance_to_state_capital_km
distance_to_coast_km
industry_employment_*
education_rate
cpi_value
cpi_scope
...
```

Then map this internal schema to the final 36-column schema.

This is critical for maintainability.

---

# 28. Provenance

Every source-derived field must be traceable.

Maintain a provenance table:

```text
feature_name
source_name
source_dataset
source_version
source_year
source_variable
retrieved_at
raw_artifact_hash
transformation
confidence
```

Example:

```text
median_age_estimate
Census
ACS5
2024
B01002_001E
2026-09-10T...
...
```

Derived fields must include:

```text
derivation_rule
rule_version
input_features
```

---

# 29. Caching

Never repeatedly download the same public dataset.

Raw cache path:

```text
data/raw/{source}/{dataset}/{version}/
```

Example:

```text
data/raw/census/acs5/2024/
data/raw/census/zcta/2025/
data/raw/faa/2026/
```

Cache key:

```text
source + dataset + version + request parameters
```

Store SHA-256 checksum.

---

# 30. Configuration

`configs/sources.yaml`

Example:

```yaml
census:
  acs_dataset: acs/acs5
  acs_year: 2024
  zcta_year: 2025
  place_year: 2025
  cbsa_year: 2025

bls:
  cpi_series: CUUR0000SA0

faa:
  enabled: true

bts:
  enabled: true

fra:
  enabled: true

marad:
  enabled: true

noaa:
  enabled: true
```

`configs/thresholds.yaml`

```yaml
geography:
  coastal_radius_km: 25

city_tier:
  t1_min_population: 1000000
  t2_min_population: 250000

industry_hub:
  minimum_employment: 5000
  minimum_share: 0.05
```

All business rules must be configurable.

---

# 31. CLI

Required commands:

```bash
python -m usa_city_features.cli download
python -m usa_city_features.cli build-geography
python -m usa_city_features.cli build-features
python -m usa_city_features.cli validate
python -m usa_city_features.cli export
python -m usa_city_features.cli run
```

Recommended options:

```bash
--config configs/default.yaml
--year 2024
--state CA
--zcta 90210
--force-refresh
--no-cache
--output data/processed/usa_city_features.csv
```

A single-location debug command is required:

```bash
python -m usa_city_features.cli inspect --zcta 90210
```

It must print:
- geography mapping,
- source records,
- feature calculations,
- validation results,
- provenance.

---

# 32. Logging

Use structured logging.

Every module should log:

```text
source
dataset
request
records_fetched
records_written
records_failed
duration_ms
cache_hit
```

Never log API keys or secrets.

---

# 33. Error handling

Classify errors:

```text
SourceUnavailable
SourceSchemaChanged
SourceRateLimited
InvalidSourceRecord
SpatialJoinFailure
FeatureCalculationError
ValidationError
ConfigurationError
```

Rules:
- transient HTTP errors -> retry;
- rate limit -> exponential backoff;
- source schema change -> fail loudly;
- missing optional source -> configurable degraded mode;
- missing required source -> fail pipeline;
- feature-specific missing data -> null + quality flag.

Never silently replace missing data with zero.

---

# 34. Null policy

Do not convert unknown to `0`.

For binary features:

```text
true
false
null
```

where:
- true = positively observed,
- false = positively determined absent,
- null = insufficient evidence.

For final compatibility with the source dataset, allow an explicit export option:

```yaml
boolean_output:
  format: "true_false"
```

Do not use `f/t` unless explicitly requested.

---

# 35. Validation

## Schema checks

- exactly 36 output columns;
- exact names;
- exact order;
- no duplicate columns;
- expected data types.

## Geography checks

```text
latitude between -90 and 90
longitude between -180 and 180
pincode exactly 5 digits
state_original valid USPS state code
```

## Numeric checks

```text
median_age > 0
income >= 0
CPI > 0
internet 0..100
smartphone 0..100
digital_payment_index 0..100
sex_ratio >= 0
distance >= 0
```

## Boolean checks

Allowed:

```text
true
false
null
```

## Referential checks

- every ZCTA must map to a valid state;
- every assigned county must exist in Census reference;
- every state capital must be in the correct state;
- metro status must agree with CBSA spatial membership.

---

# 36. Quality report

Generate:

```text
data/processed/quality_report.json
data/processed/quality_report.csv
```

Include:

```text
total_records
valid_records
invalid_records
null_count_by_column
range_errors_by_column
source_failure_count
spatial_join_failure_count
```

Also include coverage:

```text
airport_coverage_pct
rail_coverage_pct
port_coverage_pct
census_coverage_pct
industry_coverage_pct
```

---

# 37. Unit tests

Required tests:

```text
test_zcta_zero_padding
test_haversine_distance
test_state_capital_mapping
test_city_tier_boundaries
test_income_bucket_boundaries
test_population_bucket_boundaries
test_sex_ratio_formula
test_internet_penetration_formula
test_smartphone_penetration_formula
test_boolean_null_handling
test_schema_column_order
test_cpi_scope
test_industry_hub_threshold
test_coastal_radius
```

---

# 38. Contract tests

Mock source responses.

Test that each adapter produces the expected normalized structure.

Examples:

```text
CensusAdapter -> CensusRecord
BLSAdapter -> CPIRecord
FAAAdapter -> AirportRecord
BTSAdapter -> TransitRecord
FRAAdapter -> RailStationRecord
MARADAdapter -> PortRecord
NOAAAdapter -> CoastlineRecord
```

Contract tests must not require network access.

---

# 39. Integration tests

Create a fixture for one known ZCTA, for example:

```text
90210
```

Test complete flow:

```text
ZCTA
 -> place
 -> county
 -> state
 -> CBSA
 -> Census features
 -> airport
 -> transit
 -> railway
 -> coast
 -> derived features
 -> final 36 columns
```

The fixture must be stored locally so CI does not depend on external APIs.

---

# 40. Reproducibility

Every generated dataset must have:

```text
run_id
generated_at
config_hash
source_versions
code_version
```

Create:

```text
data/processed/run_metadata.json
```

Example:

```json
{
  "run_id": "20260910T130000Z",
  "code_version": "git-sha",
  "config_hash": "sha256...",
  "census_acs_year": 2024,
  "geography_year": 2025
}
```

---

# 41. Performance

The pipeline must support full-USA execution without one API request per ZCTA where a bulk dataset is available.

Preferred:

```text
bulk download
    >
cache
    >
local processing
    >
spatial join
```

Avoid:

```text
40,000 ZCTAs
    >
40,000 individual HTTP requests
```

For Census API calls:
- batch variables;
- batch geography where supported;
- cache results.

Use GeoPandas/Shapely or an equivalent spatial engine.

---

# 42. Offline/debug mode

Required:

```bash
python -m usa_city_features.cli run --offline
```

Offline mode uses:

```text
data/raw/
data/reference/
tests/fixtures/
```

No network calls.

This allows debugging transformations independently from source availability.

---

# 43. Source priority

Priority order:

### Tier 1 — authoritative government

```text
US Census
BLS
FAA
BTS
FRA
MARAD
NOAA
```

### Tier 2 — government-maintained reference data

```text
state government reference tables
```

### Tier 3 — derived

```text
city tier
smart city
digital payment
IT hub
manufacturing hub
financial center
textile hub
education hub
tourist city
```

Never use Tier 3 data as if it were directly observed.

---

# 44. 36-column feature mapping

| Output | Type | Source | Transformation |
|---|---|---|---|
| `#` | int | pipeline | sequential |
| `pincode` | string | Census ZCTA | 5-digit ZCTA |
| `state_original` | string | Census | USPS state code |
| `major_city` | string | Census Places | spatial join |
| `latitude` | float | Census | representative point |
| `longitude` | float | Census | representative point |
| `region` | string | Census | region mapping |
| `coastal_city` | bool | NOAA/Census | coastline rule |
| `distance_to_state_capital` | float | Census + reference | Haversine km |
| `city_tier` | string | Census | population rule |
| `is_metro_city` | bool | Census CBSA | spatial join |
| `is_smart_city` | bool | derived | smart-city score |
| `is_state_capital` | bool | reference | exact state capital match |
| `is_union_territory_capital` | bool | reference | false for 50-state dataset |
| `literacy_rate` | float | Census ACS | education proxy |
| `median_age_estimate` | float | Census ACS | B01002_001E |
| `consumer_price_index` | float | BLS | configured CPI series |
| `income_bucket` | string | Census ACS | B19013_001E bucket |
| `has_airport` | bool | FAA | spatial join |
| `has_international_airport` | bool | FAA | classification + spatial join |
| `has_metro_rail` | bool | BTS | transit mode + spatial join |
| `has_seaport` | bool | MARAD/NOAA | port spatial join |
| `major_railway_station` | bool | FRA/BTS | station spatial join |
| `internet_penetration_state` | float | Census ACS | subscription % |
| `smartphone_penetration_state` | float | Census ACS | smartphone household % |
| `digital_payment_index` | float | derived | weighted normalized score |
| `is_it_hub` | bool | Census/BLS | employment concentration |
| `is_manufacturing_hub` | bool | Census/BLS | employment concentration |
| `is_financial_center` | bool | Census/BLS | employment concentration |
| `is_textile_hub` | bool | BLS/Census | employment concentration |
| `is_education_hub` | bool | Census/BLS | employment concentration |
| `is_tourist_city` | bool | derived | tourism score |
| `is_coastal` | bool | NOAA | coastline rule |
| `district_population_numeric` | int | Census ACS | county population |
| `district_population` | string | Census ACS | population bucket |
| `sex_ratio` | float | Census ACS | male/female * 100 |

---

# 45. Non-functional requirements

The implementation must be:

- modular,
- testable,
- deterministic,
- idempotent,
- cache-aware,
- observable,
- configuration-driven,
- source-versioned,
- safe against schema changes,
- capable of offline development,
- suitable for scheduled production execution.

No business rule should be hidden inside a source adapter.

No source adapter should calculate final business features.

No feature calculator should perform HTTP requests.

No CLI command should contain business logic.

---

# 46. Definition of Done

The project is complete only when:

1. Full USA ZCTA geography can be loaded.
2. Census demographic features are populated.
3. FAA airport features are populated.
4. BTS/FRA transportation features are populated.
5. MARAD/NOAA coastal/port features are populated.
6. Industry features are calculated from documented rules.
7. All derived features are explicitly marked and reproducible.
8. Final output contains exactly the 36 required columns.
9. Validation report is generated.
10. Provenance is generated.
11. Unit tests pass.
12. Contract tests pass.
13. Offline mode works.
14. A single-ZCTA inspection command works.
15. Raw source data is cached.
16. No credentials are hard-coded.
17. No commercial web scraping is required for the baseline pipeline.
18. README contains setup and execution instructions.

---

# 47. Recommended implementation order

Do NOT implement everything at once.

### Phase 1 — Foundation

Implement:

```text
config
models
logging
cache
CLI
schema validator
```

### Phase 2 — Geography

Implement:

```text
ZCTA
Place
County
State
CBSA
Region
State capital
distance
```

### Phase 3 — Census features

Implement:

```text
population
median age
income
education
internet
smartphone
sex ratio
```

### Phase 4 — Infrastructure

Implement:

```text
FAA
BTS
FRA
MARAD
NOAA
```

### Phase 5 — Derived features

Implement:

```text
city tier
smart city
digital payment index
industry hubs
tourist city
population buckets
```

### Phase 6 — Validation

Implement:

```text
schema validation
range validation
coverage validation
source validation
quality report
```

### Phase 7 — Production hardening

Implement:

```text
retries
rate limiting
incremental refresh
source versioning
run metadata
offline mode
CI
```

---

# 48. IDE agent instructions

When implementing this specification:

1. First inspect the repository.
2. Create the directory structure.
3. Implement configuration and data models first.
4. Implement source adapters independently.
5. Write tests before integrating each adapter.
6. Never mix HTTP/network code with feature calculation.
7. Never hard-code source URLs or thresholds in feature functions.
8. Never silently fill missing data with zero.
9. Never make undocumented assumptions about geography.
10. Keep the original 36-column output schema unchanged.
11. Add internal columns freely for provenance and debugging.
12. Use type hints.
13. Use small functions with single responsibility.
14. Prefer dependency injection for source adapters.
15. Make all network calls mockable.
16. Add structured logging.
17. Add unit tests for every formula.
18. Add one end-to-end test using a local fixture.
19. Do not require network access for unit tests.
20. Update `DATA_DICTIONARY.md`, `SOURCE_CATALOG.md`, and `DERIVATION_RULES.md` whenever a feature rule changes.

---

# 49. Final deliverables

The implementation should produce:

```text
data/processed/usa_city_features.csv
data/processed/usa_city_features.parquet
data/processed/quality_report.csv
data/processed/quality_report.json
data/processed/run_metadata.json
```

Documentation:

```text
README.md
docs/DATA_DICTIONARY.md
docs/SOURCE_CATALOG.md
docs/DERIVATION_RULES.md
docs/ARCHITECTURE.md
```

Tests:

```text
tests/unit/
tests/contract/
tests/integration/
```

The resulting project must be maintainable so that replacing one source (for example FAA with another airport dataset) does not require rewriting the rest of the pipeline.
