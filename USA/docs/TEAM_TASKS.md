# Team Delegation & Task Breakdown

Welcome to the USA City Features Pipeline! The foundational skeleton (directory structure, base classes, CLI stubs, and configuration loaders) has been set up. 

To ensure everyone gets hands-on experience with the new architecture, the remaining implementation has been broken down into modular tasks. 

**Prerequisite for everyone:** Read `USA/Source/USA_City_Features_SDD/USA_CITY_FEATURES_SDD.md` to understand the architecture and rules.

---

## 🛠️ Task 1: Orchestration & CLI Wiring
**Assignee:** _________________

**Objective:** The CLI (`src/usa_city_features/cli.py`) currently has empty commands. You need to build the `Orchestrator` class that glues the adapters, geography, and feature calculators together.

**Step-by-Step:**
1. [ ] Create `src/usa_city_features/orchestrator.py`.
2. [ ] Implement a `PipelineOrchestrator` class that takes the `Config` object.
3. [ ] Write the `run()` method to execute the pipeline sequentially: 
   - Load ZCTAs -> Fetch Census Data -> Fetch Infra Data -> Run Spatial Joins -> Calculate Features -> Validate -> Export.
4. [ ] Update `cli.py` to instantiate `PipelineOrchestrator` and call its methods for the `download`, `build-features`, and `run` commands.
5. [ ] **Test:** Run `usa_city_features run --offline` and ensure it executes the pipeline flow (even if the data is mocked/empty).

---

## 🗺️ Task 2: Geospatial Engine (ZCTA → Place → County)
**Assignee:** _________________

**Objective:** The core of the USA pipeline is mapping Zip Code Tabulation Areas (ZCTAs) to Census Places (Cities) and Counties using spatial joins.

**Step-by-Step:**
1. [ ] Create a download script (`scripts/download_sources.py`) to fetch Census TIGER/Line shapefiles for ZCTAs, Places, Counties, and CBSAs.
2. [ ] Update `src/usa_city_features/geography/spatial_join.py` to load these shapefiles into `geopandas.GeoDataFrame`s.
3. [ ] Implement the logic: For a given ZCTA centroid (Point), find which Place (Polygon) and County (Polygon) it intersects with.
4. [ ] Handle edge cases: What if a ZCTA crosses multiple places? (Rule: Use the Place containing the ZCTA representative point).
5. [ ] **Test:** Create a test in `tests/integration/test_geography.py` using ZCTA `90210` (Beverly Hills). Assert that it correctly maps to Los Angeles County and the Place of Beverly Hills.

---

## 📊 Task 3: Census API & Demographic Features
**Assignee:** _________________

**Objective:** Fetch real demographic data from the US Census API (ACS 5-Year) and map it to our internal data model.

**Step-by-Step:**
1. [ ] Update `src/usa_city_features/sources/census.py`. Implement the exact API call to fetch variables defined in the SDD (e.g., `B01003_001E` for population, `B01002_001E` for median age).
2. [ ] Handle API pagination or batching if requesting data for all ~33,000 ZCTAs.
3. [ ] Ensure the `LocalCache` is saving the raw JSON responses to `data/raw/census/`.
4. [ ] In `src/usa_city_features/features/demographic_features.py`, wire up the formulas to calculate `literacy_rate` (education proxy), `internet_penetration`, and `smartphone_penetration`.
5. [ ] **Test:** Write `tests/unit/test_census.py` to mock the Census API response and ensure the parser correctly extracts the population and age.

---

## ✈️ Task 4: Infrastructure Adapters (FAA, BTS, FRA)
**Assignee:** _________________

**Objective:** Determine if a city has an airport, metro rail, or major railway station.

**Step-by-Step:**
1. [ ] Update `src/usa_city_features/sources/faa.py`, `bts.py`, and `fra.py` to fetch the respective geospatial datasets.
2. [ ] In `src/usa_city_features/features/infrastructure_features.py`, refine the `has_infrastructure` function. 
3. [ ] Implement the spatial buffer rule: A ZCTA gets `has_airport=True` if an airport intersects a 25km buffer around the ZCTA.
4. [ ] Filter BTS transit data to only include rail modes (subway, light rail, commuter rail) for the `has_metro_rail` feature.
5. [ ] **Test:** Write `tests/unit/test_infrastructure.py`. Create a dummy ZCTA point and a dummy Airport point 10km away. Assert `has_airport` returns `True`.

---

## 🏭 Task 5: Derived Features & Economic Data (BLS)
**Assignee:** _________________

**Objective:** Calculate complex derived scores (Smart City, Digital Payment Index, Industry Hubs) and fetch CPI data.

**Step-by-Step:**
1. [ ] Update `src/usa_city_features/sources/bls.py` to fetch the National CPI (`CUUR0000SA0`) and QCEW industry employment data.
2. [ ] In `src/usa_city_features/features/derived_features.py`, implement the logic for `is_it_hub`, `is_manufacturing_hub`, etc., using the employment concentration thresholds from `configs/thresholds.yaml`.
3. [ ] Finalize the `calculate_digital_payment_index` and `calculate_smart_city_score` functions, ensuring they handle `None` (null) inputs gracefully.
4. [ ] **Test:** Write `tests/unit/test_derived_features.py`. Pass in mock employment numbers and assert that `is_it_hub` correctly flips to `True` when the 5% threshold is crossed.

---

## 🛡️ Task 6: Validation, Quality Report, & Export
**Assignee:** _________________

**Objective:** Ensure the final output strictly adheres to the 36-column contract and generate data quality reports.

**Step-by-Step:**
1. [ ] In `src/usa_city_features/validation/schema_validator.py`, implement strict type checking (e.g., `pincode` must be a string, `latitude` must be a float).
2. [ ] Update `src/usa_city_features/storage/output.py` to map the rich internal dataset to the exact 36 columns. Ensure missing data is represented as `None` (or empty string in CSV), NOT as `0`.
3. [ ] Generate the `data/processed/quality_report.json` containing null counts, range errors, and coverage percentages.
4. [ ] **Test:** Create a dummy dataframe with 35 columns and assert that `validate_schema` fails. Create a dataframe with a latitude of `150.0` and assert that `validate_ranges` catches the error.

---

## 🚀 Final Integration (Whole Team)
Once all tasks are complete, the team will convene to run:
```bash
usa_city_features run
```
We will review the generated `usa_city_features.csv` and `quality_report.json` together to ensure the USA pipeline matches the high standards of the spec!
