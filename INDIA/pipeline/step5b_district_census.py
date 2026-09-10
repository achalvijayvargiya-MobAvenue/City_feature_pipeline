"""
step5b_district_census.py
─────────────────────────────────────────────────────────────────────────────
Enriches with district-level Census data from dists.csv (maps-master) and
census_population.csv. Matches by major_city (district name) + state.

Fills:
  sex_ratio          — female per 1000 males (Census)
  population_density  — persons per sq km
  literacy_rate      — district literacy % (from dists litrate)
  literacy_source    — "district_census" when from dists
  city_population    — district-level population (from census_population)
"""
import json
import os
import pandas as pd
from utils import normalize_name, normalize_state, print_step_header, coverage_report, save_checkpoint, save_step_lost


def _load_dists_with_state(geojson_path: str, dists_csv_path: str) -> dict:
    """
    Build (district_norm, state_norm) -> {sexratio, popdensity, litrate} from
    dists11.geojson (district+state) + dists.csv (district -> litrate, sexratio, etc).
    """
    lookup = {}
    if not os.path.exists(dists_csv_path):
        return lookup

    # Load dists.csv: dist, litrate, sexratio, area, popdensity, workpoprate
    dists_df = pd.read_csv(dists_csv_path, dtype=str)
    dists_df.columns = [c.strip().lower() for c in dists_df.columns]
    dists_df["dist_norm"] = dists_df["dist"].str.strip().apply(normalize_name)

    # Build district -> first row (dists.csv may have dup district names)
    dist_to_row = {}
    for _, r in dists_df.iterrows():
        d = r["dist_norm"]
        if d and d not in dist_to_row:
            dist_to_row[d] = {
                "sexratio": pd.to_numeric(r.get("sexratio"), errors="coerce"),
                "popdensity": pd.to_numeric(r.get("popdensity"), errors="coerce"),
                "litrate": pd.to_numeric(r.get("litrate"), errors="coerce"),
            }

    # Load geojson to get (district, state) pairs
    if not os.path.exists(geojson_path):
        return lookup

    with open(geojson_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    for feat in data.get("features", []):
        props = feat.get("properties", {})
        district = (props.get("DISTRICT") or "").strip()
        state_raw = (props.get("ST_NM") or "").strip()
        state_norm = normalize_state(state_raw)
        district_norm = normalize_name(district)
        if not district_norm:
            continue
        row = dist_to_row.get(district_norm)
        if row:
            key = (district_norm, state_norm)
            lookup[key] = row

    return lookup


def _load_census_district_population(census_path: str) -> dict:
    """
    Build (district_norm, state_norm) -> population from census_population.csv.
    Uses DISTRICT rows with Residence=Total. State name from STATE rows.
    """
    lookup = {}
    if not census_path or not os.path.exists(census_path):
        return lookup

    census_df = pd.read_csv(census_path, dtype=str)
    census_df.columns = [c.strip() for c in census_df.columns]

    # Build state_code -> state_name from STATE rows (Residence=Total)
    state_code_to_name = {}
    for _, r in census_df.iterrows():
        if (r.get("Category") == "STATE" and
                str(r.get("Residence", "")).strip() == "Total"):
            code = str(r.get("State Code", "")).strip()
            name = (r.get("Name") or "").strip()
            if code and name:
                state_code_to_name[code] = name

    # Build (district_norm, state_norm) -> population from DISTRICT rows
    for _, r in census_df.iterrows():
        if (r.get("Category") != "DISTRICT" or
                str(r.get("Residence", "")).strip() != "Total"):
            continue
        state_code = str(r.get("State Code", "")).strip()
        district_name = (r.get("Name") or "").strip()
        pop_str = (r.get("Population (Person)") or "").strip()
        if not district_name or not pop_str:
            continue
        state_name = state_code_to_name.get(state_code)
        if not state_name:
            continue
        try:
            pop = int(float(pop_str))
        except (ValueError, TypeError):
            continue
        key = (normalize_name(district_name), normalize_state(state_name))
        lookup[key] = pop

    return lookup


def run(df: pd.DataFrame, config: dict) -> pd.DataFrame:
    print_step_header(6, "District Census — sex_ratio, population_density, literacy_rate, city_population")

    geojson_path = config["PATHS"].get("dists_geojson")
    dists_path = config["PATHS"].get("dists_csv")
    census_path = config["PATHS"].get("src_census")

    # Ensure columns exist
    for col in ["sex_ratio", "population_density", "literacy_rate", "literacy_source", "city_population"]:
        if col not in df.columns:
            df[col] = None

    if not geojson_path or not dists_path:
        print("\n  [WARN] dists_geojson or dists_csv not configured. Skipping.")
        save_checkpoint(df, config["PATHS"]["checkpoints"], step=6)
        return df

    lookup = _load_dists_with_state(geojson_path, dists_path)
    print(f"  Loaded {len(lookup):,} district census records (dists)")

    pop_lookup = _load_census_district_population(census_path)
    print(f"  Loaded {len(pop_lookup):,} district population records (census)")

    sex_ratio_col = []
    pop_density_col = []
    literacy_rate_col = []
    literacy_source_col = []
    city_pop_col = []

    for _, row in df.iterrows():
        mc = row.get("major_city")
        so = row.get("state_original")
        district = "" if (mc is None or (isinstance(mc, float) and pd.isna(mc))) else str(mc).strip()
        state = "" if (so is None or (isinstance(so, float) and pd.isna(so))) else str(so).strip()
        d_norm = normalize_name(district)
        s_norm = normalize_state(state)
        key = (d_norm, s_norm)

        rec = lookup.get(key)
        if rec:
            sex_ratio_col.append(rec["sexratio"] if pd.notna(rec["sexratio"]) else None)
            pop_density_col.append(rec["popdensity"] if pd.notna(rec["popdensity"]) else None)
            lit = rec.get("litrate")
            if pd.notna(lit) and lit is not None:
                literacy_rate_col.append(float(lit))
                literacy_source_col.append("district_census")
            else:
                literacy_rate_col.append(None)
                literacy_source_col.append(None)
        else:
            sex_ratio_col.append(None)
            pop_density_col.append(None)
            literacy_rate_col.append(None)
            literacy_source_col.append(None)

        pop_val = pop_lookup.get(key)
        city_pop_col.append(pop_val if pop_val is not None else None)

    df["sex_ratio"] = sex_ratio_col
    df["population_density"] = pop_density_col
    df["literacy_rate"] = literacy_rate_col
    df["literacy_source"] = literacy_source_col
    df["city_population"] = city_pop_col

    filled_sex = df["sex_ratio"].notna().sum()
    filled_pop = df["population_density"].notna().sum()
    filled_lit = df["literacy_rate"].notna().sum()
    filled_city_pop = df["city_population"].notna().sum()
    print(f"\n  sex_ratio filled          : {filled_sex:,} / {len(df):,}")
    print(f"  population_density filled : {filled_pop:,} / {len(df):,}")
    print(f"  literacy_rate filled      : {filled_lit:,} / {len(df):,} (district_census)")
    print(f"  city_population filled    : {filled_city_pop:,} / {len(df):,} (district fallback)")

    coverage_report(df, ["sex_ratio", "population_density", "literacy_rate", "literacy_source", "city_population"])
    save_step_lost(6, [], config)
    save_checkpoint(df, config["PATHS"]["checkpoints"], step=6)
    return df
