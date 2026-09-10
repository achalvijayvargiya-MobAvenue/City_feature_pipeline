# USA City Features — Data Dictionary

## Output schema

The final compatibility dataset contains exactly 36 columns.

| # | Column | Type | Unit | Null allowed | Definition |
|---:|---|---|---|---|---|
| 1 | `#` | int | — | No | Sequential record ID |
| 2 | `pincode` | string | 5-digit | No | USA Census ZCTA |
| 3 | `state_original` | string | USPS code | No | Two-letter state code |
| 4 | `major_city` | string | — | Yes | Census Place assigned by spatial join |
| 5 | `latitude` | float | degrees | No | Representative latitude |
| 6 | `longitude` | float | degrees | No | Representative longitude |
| 7 | `region` | string | — | No | Census region |
| 8 | `coastal_city` | bool | — | Yes | Coastal rule result |
| 9 | `distance_to_state_capital` | float | km | Yes | Haversine distance |
| 10 | `city_tier` | string | — | Yes | Configurable population tier |
| 11 | `is_metro_city` | bool | — | Yes | Inside an MSA |
| 12 | `is_smart_city` | bool | — | Yes | Derived smart-city score |
| 13 | `is_state_capital` | bool | — | No | State capital indicator |
| 14 | `is_union_territory_capital` | bool | — | No | Territory capital indicator |
| 15 | `literacy_rate` | float | % | Yes | Education-attainment proxy |
| 16 | `median_age_estimate` | float | years | Yes | ACS median age |
| 17 | `consumer_price_index` | float | index | Yes | BLS CPI |
| 18 | `income_bucket` | string | — | Yes | Derived from median household income |
| 19 | `has_airport` | bool | — | Yes | Qualifying airport nearby |
| 20 | `has_international_airport` | bool | — | Yes | Qualifying international airport |
| 21 | `has_metro_rail` | bool | — | Yes | Qualifying rail transit |
| 22 | `has_seaport` | bool | — | Yes | Qualifying seaport |
| 23 | `major_railway_station` | bool | — | Yes | Qualifying passenger rail station |
| 24 | `internet_penetration_state` | float | % | Yes | Household Internet subscription rate |
| 25 | `smartphone_penetration_state` | float | % | Yes | Household smartphone rate |
| 26 | `digital_payment_index` | float | 0-100 | Yes | Derived digital-adoption index |
| 27 | `is_it_hub` | bool | — | Yes | Industry concentration rule |
| 28 | `is_manufacturing_hub` | bool | — | Yes | Manufacturing concentration rule |
| 29 | `is_financial_center` | bool | — | Yes | Finance concentration rule |
| 30 | `is_textile_hub` | bool | — | Yes | Textile concentration rule |
| 31 | `is_education_hub` | bool | — | Yes | Education employment concentration |
| 32 | `is_tourist_city` | bool | — | Yes | Tourism score |
| 33 | `is_coastal` | bool | — | Yes | Coast distance rule |
| 34 | `district_population_numeric` | int | people | Yes | County population for compatibility |
| 35 | `district_population` | string | — | Yes | County population bucket |
| 36 | `sex_ratio` | float | per 100 females | Yes | Male / female * 100 |

## Core formulas

### Sex ratio

`male_population / female_population * 100`

### Internet penetration

`households_with_internet / total_households * 100`

### Smartphone penetration

`households_with_smartphone / total_households * 100`

### Industry share

`industry_employment / total_employment`

### Digital payment index

Weighted normalized score from configured inputs. It is a derived proxy, not an observed government statistic.

### Distance

Haversine distance in kilometers.

## USA-specific semantic notes

- `pincode` is a compatibility name; use a 5-digit Census ZCTA internally.
- `district_population_numeric` is a compatibility name; use county population internally.
- `literacy_rate` is a compatibility name; use a documented education-attainment proxy.
- `consumer_price_index` must record its geographic scope because U.S. CPI is not available for every city.
- Boolean `null` means unknown, not false.
