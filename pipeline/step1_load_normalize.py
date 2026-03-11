"""
step1_load_normalize.py
─────────────────────────────────────────────────────────────────────────────
Loads the input city list, normalizes names, and builds the working DataFrame.

Adds columns:
  city_original   — raw value from CSV (unchanged)
  city_normalized — cleaned, lowercased, ascii-only name for matching

Discards: blank/null, "nan", mojibake, invalid chars (non alphanumeric), pure numeric, empty normalized, duplicate originals.
Saves discarded rows to OutputData/discarded_cities.csv for manual validation.
"""
import os
import pandas as pd
from utils import (
    normalize_name,
    contains_mojibake,
    contains_invalid_chars,
    print_step_header,
    coverage_report,
    save_checkpoint,
)


# All feature columns (from InputData/feature_list.txt)
TARGET_COLUMNS = [
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
    "national_highway_access",
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


def _add_discarded(discarded_list: list, df_slice: pd.DataFrame, reason: str):
    """Append rows to discarded list with reason."""
    if df_slice.empty:
        return
    for _, row in df_slice.iterrows():
        discarded_list.append({"city_original": row["city_original"], "discard_reason": reason})


def run(config: dict) -> pd.DataFrame:
    print_step_header(1, "Load & Normalize Input Cities")

    discarded_rows: list[dict] = []

    # ── Load ──────────────────────────────────────────────────────────────
    print(f"\n  Loading: {config['PATHS']['input']}")
    df = pd.read_csv(config["PATHS"]["input"], dtype=str)
    print(f"  Raw rows loaded: {len(df):,}")
    print(f"  Columns found:   {list(df.columns)}")

    # ── Standardise the city column name ──────────────────────────────────
    col = df.columns[0]
    df = df.rename(columns={col: "city_original"})
    df["city_original"] = df["city_original"].astype(str).str.strip()

    # ── Drop blanks / nulls ───────────────────────────────────────────────
    valid_mask = (
        df["city_original"].notna()
        & (df["city_original"] != "")
        & (df["city_original"].str.lower() != "nan")
    )
    _add_discarded(discarded_rows, df[~valid_mask], "blank_or_null")
    df = df[valid_mask].copy()
    print(f"  Rows after dropping blanks: {len(df):,}  (removed {len(discarded_rows):,})")

    # ── Drop mojibake / invalid encoding ──────────────────────────────────
    mojibake_mask = df["city_original"].apply(contains_mojibake)
    _add_discarded(discarded_rows, df[mojibake_mask], "invalid_encoding")
    df = df[~mojibake_mask].copy()
    if mojibake_mask.sum():
        print(f"  Rows after dropping mojibake: {len(df):,}  (removed {mojibake_mask.sum():,})")

    # ── Drop rows with invalid chars (only letters, digits, space, parens allowed) ─
    # Discards "2337722-2-1" (hyphen), "1400ØŒØŒ" (Arabic), etc.
    invalid_mask = df["city_original"].apply(contains_invalid_chars)
    _add_discarded(discarded_rows, df[invalid_mask], "invalid_chars")
    df = df[~invalid_mask].copy()
    if invalid_mask.sum():
        print(f"  Rows after dropping invalid chars: {len(df):,}  (removed {invalid_mask.sum():,})")

    # ── Drop pure numeric values only (e.g. "123", "5025905") ─────────────
    # Keeps "faridabad (sector 11)" etc. — only discards when entire value is digits
    pure_numeric_mask = df["city_original"].str.strip().str.match(r"^\d+$", na=False)
    _add_discarded(discarded_rows, df[pure_numeric_mask], "pure_numeric")
    df = df[~pure_numeric_mask].copy()
    if pure_numeric_mask.sum():
        print(f"  Rows after dropping pure numeric: {len(df):,}  (removed {pure_numeric_mask.sum():,})")

    # ── Strip bracket content before normalizing ──────────────────────────
    # e.g. "MUMBAI (KURLA WEST)" → "MUMBAI", "[OLD] DELHI" → "DELHI"
    df["city_normalized"] = (
        df["city_original"]
        .str.replace(r"\(.*?\)", "", regex=True)   # remove (...) blocks
        .str.replace(r"\[.*?\]", "", regex=True)   # remove [...] blocks
        .str.strip()
        .apply(normalize_name)
    )

    # Show examples where brackets were found and stripped
    bracket_mask = df["city_original"].str.contains(r"[\(\[\{]", regex=True, na=False)
    bracket_count = bracket_mask.sum()
    print(f"  Bracket content stripped: {bracket_count:,} rows")
    if bracket_count:
        sample = df[bracket_mask][["city_original", "city_normalized"]].head(5)
        print(f"\n  Sample bracket stripping:")
        print(sample.to_string(index=False))

    # ── Drop empty or too-short normalized ───────────────────────────────
    short_mask = df["city_normalized"].str.len() < 2
    _add_discarded(discarded_rows, df[short_mask], "empty_normalized")
    df = df[~short_mask].copy()
    if short_mask.sum():
        print(f"  Rows after dropping empty normalized: {len(df):,}  (removed {short_mask.sum():,})")

    # ── De-duplicate on original city name only (keep first occurrence) ─────
    # "delhi (sector 6)" and "delhi" are both kept — different originals
    dup_mask = df.duplicated(subset=["city_original"], keep="first")
    _add_discarded(discarded_rows, df[dup_mask], "duplicate")
    df = df[~dup_mask].reset_index(drop=True)
    print(f"  Rows after de-duplication:  {len(df):,}  (removed {dup_mask.sum():,} duplicates)")

    # ── Add empty target columns ──────────────────────────────────────────
    for col in TARGET_COLUMNS:
        if col not in df.columns:
            df[col] = None

    # ── Quick sample ─────────────────────────────────────────────────────
    print(f"\n  Sample rows (first 5):")
    print(df[["city_original", "city_normalized"]].head(5).to_string(index=False))

    # ── Coverage snapshot ────────────────────────────────────────────────
    coverage_report(df, TARGET_COLUMNS)

    # ── Save checkpoint ───────────────────────────────────────────────────
    save_checkpoint(df, config["PATHS"]["checkpoints"], step=1)

    # ── Save discarded cities for manual validation ───────────────────────
    if discarded_rows:
        discarded_path = config["PATHS"]["discarded"]
        os.makedirs(os.path.dirname(discarded_path), exist_ok=True)
        discarded_df = pd.DataFrame(discarded_rows)
        discarded_df.to_csv(discarded_path, index=False)
        print(f"\n  [OK] Discarded cities saved -> {discarded_path}  ({len(discarded_df):,} rows)")

    return df
