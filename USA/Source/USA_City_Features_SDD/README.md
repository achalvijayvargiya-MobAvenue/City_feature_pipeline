# USA City Features

A modular spec-driven pipeline for generating a USA location feature dataset compatible with the 36-column `cityy.xlsx` schema.

## Development

Read:

1. `USA_CITY_FEATURES_SDD.md`
2. `DATA_DICTIONARY.md`
3. `SOURCE_CATALOG.md`
4. `DERIVATION_RULES.md`

The implementation should proceed in phases:

1. Foundation
2. Geography
3. Census
4. Infrastructure
5. Derived features
6. Validation
7. Production hardening

## Principle

Separate:

- source ingestion
- normalization
- geography
- feature calculation
- validation
- output

This makes source changes and debugging localized.

## Output

```text
data/processed/usa_city_features.csv
data/processed/usa_city_features.parquet
```
