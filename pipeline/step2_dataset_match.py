"""
step2_dataset_match.py
─────────────────────────────────────────────────────────────────────────────
Matches input cities against multiple sources to resolve state_original,
major_city, latitude, longitude for maximum coverage.

Sources (merged into unified lookup):
  1. GeoNames IN.txt: name + alternatenames, admin1/admin2 for state/district
  2. final_cities.csv: State, District, City, Latitude, Longitude
  3. Indian Cities Database.csv: City, Lat, Long, State

Strategy: exact match first, then fuzzy (threshold 85) across all sources.
DISTRICT_TO_MAJOR_CITY for metro districts (e.g. Mumbai Suburban → Mumbai).

Multiple matches → create multiple output rows (one per match).
Unmatched rows → saved to OutputData/unmatched_cities.csv
"""
import os
import pandas as pd
from rapidfuzz import process, fuzz
from utils import (
    normalize_name,
    print_step_header,
    coverage_report,
    print_value_counts,
    save_checkpoint,
)


# ──────────────────────────────────────────────────────────────────────────────
# GeoNames dump loader
# ──────────────────────────────────────────────────────────────────────────────

def _parse_float(val):
    """Parse to float or return None."""
    if val is None or (isinstance(val, str) and not val.strip()):
        return None
    try:
        return float(val)
    except (ValueError, TypeError):
        return None


def _load_geonames(path: str, admin1_path: str, admin2_path: str, district_map: dict) -> tuple:
    """
    Load IN.txt, admin1, admin2. Returns:
    - name_to_records: dict normalized_name -> list of (state, major_city, lat, long)
    - all_keys: list of normalized names for fuzzy search
    """
    # admin1: IN.XX -> state name
    admin1 = {}
    with open(admin1_path, encoding="utf-8") as f:
        for line in f:
            parts = line.strip().split("\t")
            if len(parts) >= 2 and parts[0].startswith("IN."):
                admin1[parts[0]] = parts[1].strip()

    # admin2: IN.XX.YYY -> district name
    admin2 = {}
    with open(admin2_path, encoding="utf-8") as f:
        for line in f:
            parts = line.strip().split("\t")
            if len(parts) >= 2 and parts[0].startswith("IN."):
                admin2[parts[0]] = parts[1].strip()

    def _district_to_city(admin1_code: str, admin2_code: str, district_name: str) -> str:
        key = district_name.lower().strip() if district_name else ""
        if key in district_map:
            return district_map[key]
        return district_name or ""

    name_to_records = {}
    all_keys = set()

    # Only P (populated) and A (admin) - skip rivers, etc.
    feature_classes = {"P", "A"}
    with open(path, encoding="utf-8", errors="replace") as f:
        for line in f:
            parts = line.strip().split("\t")
            if len(parts) < 12:
                continue
            name, asciiname = parts[1], parts[2]
            alternames = parts[3] if len(parts) > 3 else ""
            lat = _parse_float(parts[4]) if len(parts) > 4 else None
            lon = _parse_float(parts[5]) if len(parts) > 5 else None
            fclass = parts[6] if len(parts) > 6 else ""
            country = parts[8] if len(parts) > 8 else ""
            if country != "IN" or fclass not in feature_classes:
                continue
            adm1 = parts[10].strip() if len(parts) > 10 else ""
            adm2 = parts[11].strip() if len(parts) > 11 else ""

            adm1_key = f"IN.{adm1}" if adm1 else ""
            adm2_key = f"IN.{adm1}.{adm2}" if adm1 and adm2 else ""
            state = admin1.get(adm1_key, "") if adm1_key else ""
            district = admin2.get(adm2_key, "") if adm2_key else ""
            if district:
                major_city = _district_to_city(adm1, adm2, district)
            else:
                major_city = name.strip()

            rec = (state, major_city, lat, lon)
            names_to_index = [name, asciiname] + alternames.split(",")[:30]  # limit alts
            for n in names_to_index:
                n = n.strip()
                if not n or len(n) < 2:
                    continue
                key = normalize_name(n)
                if not key:
                    continue
                all_keys.add(key)
                if key not in name_to_records:
                    name_to_records[key] = []
                if rec not in name_to_records[key]:
                    name_to_records[key].append(rec)

    # Build first-letter index for faster fuzzy (search only same first letter)
    keys_by_first = {}
    for k in all_keys:
        fc = k[0] if k else ""
        if fc not in keys_by_first:
            keys_by_first[fc] = []
        keys_by_first[fc].append(k)
    return name_to_records, list(all_keys), keys_by_first


def _build_keys_by_first(all_keys: set) -> dict:
    """Build first-letter index for fuzzy search."""
    keys_by_first = {}
    for k in all_keys:
        fc = k[0] if k else ""
        if fc not in keys_by_first:
            keys_by_first[fc] = []
        keys_by_first[fc].append(k)
    return keys_by_first


def _load_final_cities(path: str) -> tuple:
    """
    Load final_cities.csv. Returns same format as _load_geonames:
    - name_to_records: dict normalized_name -> list of (state, major_city, lat, lon)
    - all_keys: set of normalized names
    - keys_by_first: dict for fuzzy search
    """
    if not path or not os.path.exists(path):
        return {}, set(), {}
    df = pd.read_csv(path, encoding="utf-8", dtype=str)
    name_to_records = {}
    all_keys = set()
    for _, row in df.iterrows():
        state = str(row.get("State", "")).strip()
        city = str(row.get("City", "")).strip()
        lat = _parse_float(row.get("Latitude"))
        lon = _parse_float(row.get("Longitude"))
        if not city or len(city) < 2:
            continue
        rec = (state, city, lat, lon)
        key = normalize_name(city)
        if not key:
            continue
        all_keys.add(key)
        if key not in name_to_records:
            name_to_records[key] = []
        if rec not in name_to_records[key]:
            name_to_records[key].append(rec)
    return name_to_records, all_keys, _build_keys_by_first(all_keys)


def _load_icd(path: str) -> tuple:
    """
    Load Indian Cities Database.csv. Returns same format as _load_geonames.
    Filters to India (iso2=IN or country=India).
    """
    if not path or not os.path.exists(path):
        return {}, set(), {}
    df = pd.read_csv(path, encoding="utf-8", dtype=str)
    name_to_records = {}
    all_keys = set()
    for _, row in df.iterrows():
        iso2 = str(row.get("iso2", "")).strip().upper()
        country = str(row.get("country", "")).strip()
        if iso2 != "IN" and "india" not in country.lower():
            continue
        state = str(row.get("State", "")).strip()
        city = str(row.get("City", "")).strip()
        lat = _parse_float(row.get("Lat"))
        lon = _parse_float(row.get("Long"))
        if not city or len(city) < 2:
            continue
        rec = (state, city, lat, lon)
        key = normalize_name(city)
        if not key:
            continue
        all_keys.add(key)
        if key not in name_to_records:
            name_to_records[key] = []
        if rec not in name_to_records[key]:
            name_to_records[key].append(rec)
    return name_to_records, all_keys, _build_keys_by_first(all_keys)


def _merge_lookups(sources: list) -> tuple:
    """
    Merge multiple (name_to_records, all_keys, keys_by_first) into one.
    sources: list of (name_to_records, all_keys, keys_by_first) tuples.
    """
    merged_records = {}
    merged_keys = set()
    for name_to_records, all_keys, _ in sources:
        merged_keys.update(all_keys)
        for key, recs in name_to_records.items():
            if key not in merged_records:
                merged_records[key] = []
            for r in recs:
                if r not in merged_records[key]:
                    merged_records[key].append(r)
    return merged_records, merged_keys, _build_keys_by_first(merged_keys)


# ──────────────────────────────────────────────────────────────────────────────
# Main step
# ──────────────────────────────────────────────────────────────────────────────

def run(df: pd.DataFrame, config: dict) -> pd.DataFrame:
    print_step_header(2, "Dataset Match — state, major_city, lat/long (GeoNames + final_cities + Indian Cities DB)")

    threshold = config.get("FUZZY_THRESHOLD", 85)
    district_map = {k.lower(): v for k, v in config.get("DISTRICT_TO_MAJOR_CITY", {}).items()}
    paths = config.get("PATHS", {})

    # ── Load all sources ───────────────────────────────────────────────────
    sources = []

    # 1. GeoNames
    gn_path = paths.get("geonames_dump")
    gn_admin1 = paths.get("geonames_admin1")
    gn_admin2 = paths.get("geonames_admin2")
    if gn_path and gn_admin1 and gn_admin2 and os.path.exists(gn_path):
        gn_data, gn_keys, gn_keys_first = _load_geonames(gn_path, gn_admin1, gn_admin2, district_map)
        sources.append((gn_data, gn_keys, gn_keys_first))
        print(f"\n  GeoNames IN.txt: {len(gn_data):,} unique names")
    else:
        print("\n  GeoNames dump not found, skipping")

    # 2. final_cities.csv
    fc_path = paths.get("src_final_cities")
    if fc_path and os.path.exists(fc_path):
        fc_data, fc_keys, fc_keys_first = _load_final_cities(fc_path)
        sources.append((fc_data, fc_keys, fc_keys_first))
        print(f"  final_cities.csv: {len(fc_data):,} unique names")
    else:
        print("  final_cities.csv not found, skipping")

    # 3. Indian Cities Database.csv
    icd_path = paths.get("src_icd")
    if icd_path and os.path.exists(icd_path):
        icd_data, icd_keys, icd_keys_first = _load_icd(icd_path)
        sources.append((icd_data, icd_keys, icd_keys_first))
        print(f"  Indian Cities Database.csv: {len(icd_data):,} unique names")
    else:
        print("  Indian Cities Database.csv not found, skipping")

    # Merge into unified lookup
    match_data, match_keys, match_keys_by_first = _merge_lookups(sources)
    print(f"\n  Merged: {len(match_data):,} unique names across all sources")

    # ── Add new columns ───────────────────────────────────────────────────
    for col in ["major_city", "latitude", "longitude"]:
        if col not in df.columns:
            df[col] = None

    matched_rows = []
    unmatched_rows = []

    def _add_match(base_row, state, major_city, lat, lon, source: str):
        r = base_row.copy()
        r["state_original"] = state if state else None
        r["major_city"] = major_city if major_city else None
        r["latitude"] = lat
        r["longitude"] = lon
        r["match_source"] = source
        matched_rows.append(r)

    def _try_match(city_key: str, base_row: dict) -> bool:
        if not match_data:
            return False
        if city_key in match_data:
            for state, city, lat, lon in match_data[city_key]:
                _add_match(base_row, state, city, lat, lon, "merged:exact")
            return True
        # Fuzzy: search only keys with same first letter (faster)
        fc = city_key[0] if city_key else ""
        candidates = match_keys_by_first.get(fc, [])
        if not candidates:
            return False
        matches = process.extract(city_key, candidates, scorer=fuzz.token_sort_ratio, score_cutoff=threshold, limit=5)
        if matches:
            seen = set()
            for m, _, _ in matches:
                for state, city, lat, lon in match_data.get(m, []):
                    t = (state, city, lat, lon)
                    if t not in seen:
                        seen.add(t)
                        _add_match(base_row, state, city, lat, lon, "merged:fuzzy")
            return True
        return False

    # ── Process each row ──────────────────────────────────────────────────
    print(f"\n  Matching {len(df):,} rows (threshold={threshold})...")

    for _, row in df.iterrows():
        base = row.to_dict()
        city_key = str(base.get("city_normalized", "")).strip()
        if not city_key:
            unmatched_rows.append(base)
            continue

        if _try_match(city_key, base):
            continue

        base["match_source"] = "unresolved"
        unmatched_rows.append(base)

    # ── Build output ─────────────────────────────────────────────────────
    out_df = pd.DataFrame(matched_rows) if matched_rows else df.head(0).copy()
    if unmatched_rows:
        unmatched_df = pd.DataFrame(unmatched_rows)
    else:
        unmatched_df = pd.DataFrame()

    # Ensure column order
    base_cols = [c for c in df.columns if c in out_df.columns]
    extra = [c for c in out_df.columns if c not in base_cols]
    out_df = out_df[base_cols + extra]

    # ── Stats ─────────────────────────────────────────────────────────────
    total_in = len(df)
    total_out = len(out_df)
    total_unmatched = len(unmatched_df)

    print(f"\n  Match results:")
    print(f"    Input rows              : {total_in:>8,}")
    print(f"    Output rows (matched)    : {total_out:>8,}  (multiple matches → multiple rows)")
    print(f"    Unmatched               : {total_unmatched:>8,}")

    coverage_report(out_df, ["state_original", "major_city", "latitude", "longitude", "match_source"])
    print_value_counts(out_df, "match_source", top_n=10)

    # ── Save unmatched ────────────────────────────────────────────────────
    if total_unmatched > 0:
        um_path = config["PATHS"].get("unmatched")
        if um_path:
            os.makedirs(os.path.dirname(um_path), exist_ok=True)
            unmatched_df.to_csv(um_path, index=False)
            print(f"\n  [OK] Unmatched saved -> {um_path}  ({total_unmatched:,} rows)")

    save_checkpoint(out_df, config["PATHS"]["checkpoints"], step=2)
    return out_df
