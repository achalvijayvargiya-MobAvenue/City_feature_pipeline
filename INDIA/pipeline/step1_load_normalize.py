"""
step1_load_normalize.py
─────────────────────────────────────────────────────────────────────────────
Loads pincode input, joins with Pincode_mapping.csv to get district, state,
latitude, longitude. Builds the working DataFrame for downstream steps.

Adds columns:
  pincode          — input pincode (6 digits)
  city_original    — same as pincode (for compatibility with lost/discarded)
  city_normalized  — district name normalized (for tier/metro/city lookups)
  state_original   — state from mapping
  major_city       — district with DISTRICT_TO_MAJOR_CITY override (metro areas)
  latitude         — from mapping (NA allowed)
  longitude        — from mapping
  match_source     — "pincode_mapping"

Discards: blank/null pincodes, pincodes not found in mapping.
Saves discarded rows to OutputData/discarded_cities.csv.
"""
import os
import pandas as pd
from utils import (
    normalize_name,
    print_step_header,
    coverage_report,
    save_checkpoint,
    save_step_lost,
)


# All feature columns (from InputData/feature_list.txt)
TARGET_COLUMNS = [
    "pincode",
    "city_original",
    "city_normalized",
    "state_original",
    "major_city",
    "match_source",
    "latitude",
    "longitude",
    "state",
    "region",
    "geographic_region",
    "is_valid",
    "coastal_city",
    "distance_to_state_capital",
    "city_tier",
    "is_metro_city",
    "is_smart_city",
    "is_state_capital",
    "is_union_territory_capital",
    "city_population",
    "population_density",
    "literacy_rate",
    "sex_ratio",
    "literacy_source",
    "median_age_estimate",
    "consumer_price_index",
    "income_bucket",
    "avg_property_price",
    "has_airport",
    "has_international_airport",
    "has_metro_rail",
    "has_seaport",
    "major_railway_station",
    "internet_penetration_state",
    "smartphone_penetration_state",
    "digital_payment_index",
    "is_it_hub",
    "is_manufacturing_hub",
    "is_financial_center",
    "is_textile_hub",
    "is_education_hub",
    "is_tourist_city",
]


def _parse_float(val):
    """Parse to float or return None. Handles 'NA' string."""
    if val is None or (isinstance(val, str) and (not val.strip() or val.strip().upper() == "NA")):
        return None
    try:
        return float(val)
    except (ValueError, TypeError):
        return None


def _add_discarded(discarded_list: list, pincodes: list, reason: str):
    """Append rows to discarded list with reason."""
    for p in pincodes:
        discarded_list.append({"city_original": str(p), "discard_reason": reason})


def run(config: dict) -> pd.DataFrame:
    print_step_header(1, "Load & Normalize — Pincode Input + Pincode Mapping")

    discarded_rows: list[dict] = []

    paths = config["PATHS"]
    input_path = paths.get("input")
    mapping_path = paths.get("pincode_mapping")

    if not input_path or not os.path.exists(input_path):
        raise FileNotFoundError(f"Input file not found: {input_path}")

    if not mapping_path or not os.path.exists(mapping_path):
        raise FileNotFoundError(f"Pincode mapping not found: {mapping_path}")

    district_to_major = {normalize_name(k): v for k, v in config.get("DISTRICT_TO_MAJOR_CITY", {}).items()}

    # ── Load pincode input ─────────────────────────────────────────────────
    print(f"\n  Loading input: {input_path}")
    df_in = pd.read_csv(input_path, dtype=str)
    print(f"  Raw rows loaded: {len(df_in):,}")
    print(f"  Columns found:   {list(df_in.columns)}")

    # Standardize pincode column
    pincode_col = "pincode" if "pincode" in df_in.columns else df_in.columns[0]
    df_in = df_in.rename(columns={pincode_col: "pincode"})
    df_in["pincode"] = df_in["pincode"].astype(str).str.strip()

    # ── Drop blanks / nulls ───────────────────────────────────────────────
    valid_mask = (
        df_in["pincode"].notna()
        & (df_in["pincode"] != "")
        & (df_in["pincode"].str.lower() != "nan")
    )
    _add_discarded(discarded_rows, df_in.loc[~valid_mask, "pincode"].tolist(), "blank_or_null")
    df_in = df_in[valid_mask].copy()
    print(f"  Rows after dropping blanks: {len(df_in):,}  (removed {len(discarded_rows):,})")

    # ── Keep valid 6-digit pincodes ────────────────────────────────────────
    pincode_valid = df_in["pincode"].str.match(r"^\d{6}$", na=False)
    _add_discarded(discarded_rows, df_in.loc[~pincode_valid, "pincode"].tolist(), "invalid_pincode_format")
    df_in = df_in[pincode_valid].copy()
    if (~pincode_valid).sum():
        print(f"  Rows after pincode format check: {len(df_in):,}")

    # ── Load Pincode_mapping ───────────────────────────────────────────────
    print(f"\n  Loading mapping: {mapping_path}")
    mapping_df = pd.read_csv(mapping_path, dtype=str)
    mapping_df["pincode"] = mapping_df["pincode"].astype(str).str.strip()
    # Drop duplicates per pincode: prefer rows with valid lat/lon
    mapping_df["_lat"] = mapping_df["latitude"].apply(_parse_float)
    mapping_df["_lon"] = mapping_df["longitude"].apply(_parse_float)
    mapping_df["_has_coords"] = mapping_df["_lat"].notna() & mapping_df["_lon"].notna()
    # Sort: has_coords first, then take first per pincode
    mapping_df = mapping_df.sort_values("_has_coords", ascending=False)
    mapping_one = mapping_df.drop_duplicates(subset=["pincode"], keep="first")
    mapping_one = mapping_one.drop(columns=["_lat", "_lon", "_has_coords"], errors="ignore")
    print(f"  Unique pincodes in mapping: {mapping_one['pincode'].nunique():,}")

    # ── Join input with mapping ────────────────────────────────────────────
    before_join = len(df_in)
    df = df_in.merge(mapping_one, on="pincode", how="inner", suffixes=("", "_map"))
    after_join = len(df)
    unmatched = set(df_in["pincode"].unique()) - set(df["pincode"].unique())
    if unmatched:
        _add_discarded(discarded_rows, list(unmatched), "pincode_not_in_mapping")
        print(f"  Rows after join: {after_join:,}  (unmatched: {len(unmatched):,})")
    else:
        print(f"  Rows after join: {after_join:,}")

    if df.empty:
        raise ValueError("No pincodes matched the mapping. Check input and mapping files.")

    # ── Derive columns ─────────────────────────────────────────────────────
    df["city_original"] = df["pincode"].astype(str)  # compatibility

    if "district" not in df.columns:
        raise ValueError("Pincode_mapping must have a 'district' column")
    district_raw = df["district"].fillna("").astype(str).str.strip()

    statename_col = "statename" if "statename" in df.columns else ("state" if "state" in df.columns else None)
    if statename_col is None:
        raise ValueError("Pincode_mapping must have 'statename' or 'state' column")
    state_raw = df[statename_col].fillna("").astype(str).str.strip()

    # major_city: district with DISTRICT_TO_MAJOR_CITY override
    major_city_list = []
    for d in district_raw:
        d_norm = normalize_name(d)
        major_city_list.append(district_to_major.get(d_norm, d) if d else None)
    df["major_city"] = major_city_list
    df["city_normalized"] = df["major_city"].apply(lambda x: normalize_name(str(x)) if pd.notna(x) else "")
    df["state_original"] = state_raw

    # latitude, longitude
    df["latitude"] = df["latitude"].apply(_parse_float)
    df["longitude"] = df["longitude"].apply(_parse_float)
    df["match_source"] = "pincode_mapping"

    # Drop extra columns from mapping (circlename, regionname, etc.)
    keep_cols = [
        "pincode", "city_original", "city_normalized", "state_original", "major_city",
        "match_source", "latitude", "longitude"
    ]
    df = df[[c for c in keep_cols if c in df.columns]].copy()

    # ── De-duplicate on pincode (keep first) ───────────────────────────────
    dup_mask = df.duplicated(subset=["pincode"], keep="first")
    if dup_mask.any():
        _add_discarded(discarded_rows, df.loc[dup_mask, "pincode"].tolist(), "duplicate")
        df = df[~dup_mask].reset_index(drop=True)
        print(f"  Rows after de-duplication: {len(df):,}")

    # ── Add empty target columns ───────────────────────────────────────────
    for col in TARGET_COLUMNS:
        if col not in df.columns:
            df[col] = None

    # ── Quick sample ─────────────────────────────────────────────────────
    print(f"\n  Sample rows (first 5):")
    sample_cols = ["pincode", "city_original", "city_normalized", "state_original", "major_city"]
    print(df[[c for c in sample_cols if c in df.columns]].head(5).to_string(index=False))

    coverage_report(df, TARGET_COLUMNS)
    save_checkpoint(df, config["PATHS"]["checkpoints"], step=1)

    # ── Save discarded ────────────────────────────────────────────────────
    if discarded_rows:
        discarded_path = config["PATHS"]["discarded"]
        os.makedirs(os.path.dirname(discarded_path), exist_ok=True)
        discarded_df = pd.DataFrame(discarded_rows)
        discarded_df.to_csv(discarded_path, index=False)
        print(f"\n  [OK] Discarded pincodes saved -> {discarded_path}  ({len(discarded_df):,} rows)")

    lost_pincodes = [r["city_original"] for r in discarded_rows]
    save_step_lost(1, lost_pincodes, config)

    return df
