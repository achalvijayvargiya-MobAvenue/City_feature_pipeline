# USA City Features — Derivation Rules

## City tier

Default:

```text
T1 >= 1,000,000
T2 250,000 - 999,999
T3 < 250,000
```

Population source: Census Place population.

## Income bucket

```text
L  < 50,000
M  50,000 - 99,999
H  100,000 - 199,999
VH >= 200,000
```

## County population bucket

```text
VS < 250,000
S 250,000 - 499,999
M 500,000 - 999,999
L 1,000,000 - 4,999,999
VL >= 5,000,000
```

## Coastal

Default:

```text
distance_to_coast_km <= 25
```

Make radius configurable.

## Metro

`is_metro_city = true` when the location is inside a Census Metropolitan Statistical Area.

Micropolitan areas are false unless explicitly enabled.

## State capital

Exact match against the maintained state-capital reference table.

## Distance to state capital

Haversine distance from ZCTA representative point to capital coordinates.

## Education proxy

Use:

```text
population age 25+ with high school diploma or higher
/
population age 25+
* 100
```

Keep output column name `literacy_rate` only for compatibility.

## Digital payment index

Default:

```text
0.40 * internet_score
+ 0.35 * smartphone_score
+ 0.15 * income_score
+ 0.10 * metro_score
```

Normalize to 0-100.

Weights are configuration.

## Smart city

Derived from:

```text
metro rail
airport
internet
smartphone
digital payment index
IT hub
```

Use configurable threshold.

## Industry hubs

Use:

```text
industry_share = industry_employment / total_employment
```

and require both:

```text
industry_share >= minimum_share
industry_employment >= minimum_employment
```

Recommended industries:

```text
IT: Information + selected Professional/Scientific/Technical sectors
Manufacturing: NAICS 31-33
Finance: NAICS 52
Textile: NAICS 313-314
Education: NAICS 61
```

## Tourist city

Build a score from available free indicators.

Recommended components:

```text
NPS visitation
arts/entertainment employment
accommodation/food employment
airport presence
coastal status
```

Use standardized inputs and configurable weights.

Do not maintain a manually curated list of tourist cities.
