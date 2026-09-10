# USA City Features — Source Catalog

## Primary free sources

| Source | Role | Dataset/API | Usage |
|---|---|---|---|
| US Census Bureau | Geography + demographics | ACS 5-Year API | Population, age, income, education, Internet, devices, sex |
| US Census Bureau | Geography | TIGER/Line | ZCTA, Place, County, CBSA geometries |
| US Census Bureau | Geography | Gazetteer files | Representative coordinates |
| Bureau of Labor Statistics | CPI | BLS Public Data API / CPI series | CPI |
| Federal Aviation Administration | Airports | Airport Master Record / aviation facility data | Airports |
| Bureau of Transportation Statistics | Transit | National Transit Map | Metro/rail |
| BTS/FRA | Passenger rail | Amtrak Stations dataset | Railway station |
| MARAD | Ports | U.S. port data | Seaport |
| NOAA | Coast | Coastal/geospatial data | Coastline |
| BLS QCEW | Industry | County/industry employment | Hub detection |
| Census ACS | Industry | Industry employment tables | Hub detection |

## Key Census variables

```text
B01003_001E  total population
B01002_001E  median age
B01001_002E  male population
B01001_026E  female population
B19013_001E  median household income
B28002        Internet subscription
B28001        household computer/device categories
```

The implementation must resolve device variables by metadata/label instead of assuming a variable index across releases.

## BLS

Default CPI series:

```text
CUUR0000SA0
```

Scope:

`U.S. city average, all items, CPI-U, not seasonally adjusted`

## Important source policy

Prefer bulk government datasets.

Do not use Google Maps or commercial city-data providers for the baseline implementation.

Do not scrape arbitrary websites for:
- smart city
- digital payment
- tourist city
- IT hub
- financial center

Those must be reproducible derived features unless a specific authoritative dataset is added later.
