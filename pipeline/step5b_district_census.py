"""
step5b_district_census.py
─────────────────────────────────────────────────────────────────────────────
Enriches with district-level Census data from dists.csv (maps-master).
Matches by major_city (district name) to get sex_ratio, population_density.
Also uses district-level literacy (litrate) when available, supplementing
state-level literacy from step6.

Fills:
  sex_ratio          — female per 1000 males (Census)
  population_density  — persons per sq km
"""
import json
import os
import pandas as pd
from utils import normalize_name, normalize_state, print_step_header, coverage_report, save_checkpoint


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


def run(df: pd.DataFrame, config: dict) -> pd.DataFrame:
    print_step_header(6, "District Census — sex_ratio, population_density")

    geojson_path = config["PATHS"].get("dists_geojson")
    dists_path = config["PATHS"].get("dists_csv")
    if not geojson_path or not dists_path:
        print("\n  [WARN] dists_geojson or dists_csv not configured. Skipping.")
        for col in ["sex_ratio", "population_density"]:
            if col not in df.columns:
                df[col] = None
        save_checkpoint(df, config["PATHS"]["checkpoints"], step=6)
        return df

    lookup = _load_dists_with_state(geojson_path, dists_path)
    print(f"  Loaded {len(lookup):,} district census records")

    sex_ratio_col = []
    pop_density_col = []

    for _, row in df.iterrows():
        district = (row.get("major_city") or "").strip()
        state = (row.get("state_original") or "").strip()
        d_norm = normalize_name(district)
        s_norm = normalize_state(state)
        key = (d_norm, s_norm)
        rec = lookup.get(key)
        if rec:
            sex_ratio_col.append(rec["sexratio"] if pd.notna(rec["sexratio"]) else None)
            pop_density_col.append(rec["popdensity"] if pd.notna(rec["popdensity"]) else None)
        else:
            sex_ratio_col.append(None)
            pop_density_col.append(None)

    df["sex_ratio"] = sex_ratio_col
    df["population_density"] = pop_density_col

    filled_sex = df["sex_ratio"].notna().sum()
    filled_pop = df["population_density"].notna().sum()
    print(f"\n  sex_ratio filled          : {filled_sex:,} / {len(df):,}")
    print(f"  population_density filled : {filled_pop:,} / {len(df):,}")

    coverage_report(df, ["sex_ratio", "population_density"])
    save_checkpoint(df, config["PATHS"]["checkpoints"], step=6)
    return df
