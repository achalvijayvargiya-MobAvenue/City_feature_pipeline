"""
Phase A: Shrink invalid RTB rows using tabular ZIP crosswalks.

Fills identity + derivable fields from:
- curated US ZIP CSV (city/state/lat/lon + ACS-like demographics)
- HRSA ZIP->ZCTA crosswalk (city/state)
- GeoNames US centroids (fallback)

Then re-splits valid/invalid so the valid set grows step by step.
"""
from __future__ import annotations

import json
import zipfile
from pathlib import Path
from typing import Any, Dict, Optional

import numpy as np
import pandas as pd

from usa_city_features.features.demographic_features import (
    get_income_bucket,
    get_population_bucket,
)
from usa_city_features.features.derived_features import (
    calculate_digital_payment_index,
    get_city_tier,
)
from usa_city_features.geography.regions import get_region_for_state
from usa_city_features.geography.state_capitals import (
    STATE_CAPITALS,
    distance_to_state_capital,
    is_state_capital,
)
from usa_city_features.validation.schema_validator import split_complete_records

ROOT = Path(__file__).resolve().parents[1]
PROCESSED = ROOT / "data" / "processed"
CROSSWALK = ROOT / "data" / "reference" / "crosswalk"

# Territory capitals so PR/VI rows can get distance_to_state_capital
TERRITORY_CAPITALS = {
    "PR": {"name": "San Juan", "lat": 18.4655, "lon": -66.1057},
    "VI": {"name": "Charlotte Amalie", "lat": 18.3419, "lon": -64.9307},
    "GU": {"name": "Hagatna", "lat": 13.4750, "lon": 144.7500},
    "AS": {"name": "Pago Pago", "lat": -14.2756, "lon": -170.7020},
    "MP": {"name": "Saipan", "lat": 15.1778, "lon": 145.7508},
    "DC": {"name": "Washington", "lat": 38.9072, "lon": -77.0369},
}

META_EXCLUDE = {
    "postal_code",
    "feature_source",
    "source_zcta",
    "enrichment_queue",
    "enrichment_priority",
    "enrichment_action",
    "missing_columns",
    "identity_source",
}


def _z5(series: pd.Series) -> pd.Series:
    s = series.astype(str).str.strip().str.replace(r"\.0$", "", regex=True)
    s = s.str.replace(r"[^0-9]", "", regex=True)
    return s.str.zfill(5)


def _is_blank(val: Any) -> bool:
    if val is None:
        return True
    try:
        if pd.isna(val):
            return True
    except Exception:
        pass
    text = str(val).strip().lower()
    return text in {"", "nan", "none", "null", "unknown", "<na>", "nat"}


def _to_float(val: Any) -> Optional[float]:
    try:
        if _is_blank(val):
            return None
        f = float(val)
        # Census sentinel
        if abs(f) >= 1e8:
            return None
        return f
    except Exception:
        return None


def _to_int(val: Any) -> Optional[int]:
    f = _to_float(val)
    if f is None:
        return None
    return int(f)


def load_curated_zips() -> pd.DataFrame:
    path = CROSSWALK / "curated_us_zips.csv"
    df = pd.read_csv(path, dtype=str)
    df["zip"] = _z5(df["zip_code"])
    return df.drop_duplicates("zip", keep="first").set_index("zip")


def load_hrsa() -> pd.DataFrame:
    path = CROSSWALK / "zip_to_zcta_hrsa.xlsx"
    df = pd.read_excel(path, dtype=str)
    df["zip"] = _z5(df["ZIP_CODE"])
    df = df.rename(columns={"PO_NAME": "city", "STATE": "state"})
    return df.drop_duplicates("zip", keep="first").set_index("zip")


def load_geonames() -> pd.DataFrame:
    path = CROSSWALK / "geonames_US.zip"
    with zipfile.ZipFile(path) as zf:
        with zf.open("US.txt") as f:
            df = pd.read_csv(
                f,
                sep="\t",
                header=None,
                dtype=str,
                usecols=[1, 2, 4, 9, 10],
                names=["zip", "city", "state", "lat", "lon"],
            )
    df["zip"] = _z5(df["zip"])
    return df.drop_duplicates("zip", keep="first").set_index("zip")


def distance_with_territories(lat: float, lon: float, state: str) -> Optional[float]:
    if not state:
        return None
    state = state.upper()
    if state in STATE_CAPITALS:
        return distance_to_state_capital(lat, lon, state)
    cap = TERRITORY_CAPITALS.get(state)
    if not cap:
        return None
    from usa_city_features.transforms.distance import haversine_distance_km
    return haversine_distance_km(lat, lon, cap["lat"], cap["lon"])


def state_defaults_from_valid(valid_df: pd.DataFrame) -> Dict[str, Dict[str, float]]:
    """Median state-level defaults for penetration/CPI from already-valid rows."""
    df = valid_df.copy()
    df["state_original"] = df["state_original"].astype(str).str.upper()
    out: Dict[str, Dict[str, float]] = {}
    for state, g in df.groupby("state_original"):
        if _is_blank(state) or state == "NAN":
            continue
        rec = {}
        for col in [
            "internet_penetration_state",
            "smartphone_penetration_state",
            "consumer_price_index",
            "literacy_rate",
            "sex_ratio",
        ]:
            vals = pd.to_numeric(g[col], errors="coerce").dropna()
            vals = vals[vals.abs() < 1e8]
            if len(vals):
                rec[col] = float(vals.median())
        if rec:
            out[state] = rec
    # national fallbacks
    nat = {}
    for col in [
        "internet_penetration_state",
        "smartphone_penetration_state",
        "consumer_price_index",
        "literacy_rate",
        "sex_ratio",
    ]:
        vals = pd.to_numeric(df[col], errors="coerce").dropna()
        vals = vals[vals.abs() < 1e8]
        if len(vals):
            nat[col] = float(vals.median())
    out["__NATIONAL__"] = nat
    return out


def fill_if_blank(row: pd.Series, col: str, value: Any) -> bool:
    if value is None or _is_blank(value):
        return False
    if _is_blank(row.get(col)):
        row[col] = value
        return True
    # also replace census sentinel ages
    if col == "median_age_estimate":
        cur = _to_float(row.get(col))
        if cur is None:
            row[col] = value
            return True
    return False


def enrich_invalid_rows() -> Dict[str, Any]:
    invalid_path = PROCESSED / "usa_rtb_zip_features_final_invalid.csv"
    valid_path = PROCESSED / "usa_rtb_zip_features_final_valid.csv"
    final_path = PROCESSED / "usa_rtb_zip_features_final.csv"

    invalid = pd.read_csv(invalid_path, dtype=str)
    valid = pd.read_csv(valid_path, dtype=str)
    before_invalid = len(invalid)
    before_valid = len(valid)

    curated = load_curated_zips()
    hrsa = load_hrsa()
    geo = load_geonames()
    defaults = state_defaults_from_valid(valid)

    fill_counts = {
        "matched_curated": 0,
        "matched_hrsa": 0,
        "matched_geonames": 0,
        "filled_city": 0,
        "filled_state": 0,
        "filled_latlon": 0,
        "filled_region": 0,
        "filled_distance": 0,
        "filled_income": 0,
        "filled_age": 0,
        "filled_pop": 0,
        "filled_literacy": 0,
        "filled_state_defaults": 0,
        "filled_cpi": 0,
        "filled_dpi": 0,
        "filled_tier": 0,
    }

    rows = []
    for _, raw in invalid.iterrows():
        row = raw.copy()
        zip_code = str(row.get("pincode") or row.get("postal_code") or "").zfill(5)
        row["pincode"] = zip_code
        row["postal_code"] = zip_code
        identity_source = None

        c = curated.loc[zip_code] if zip_code in curated.index else None
        h = hrsa.loc[zip_code] if zip_code in hrsa.index else None
        g = geo.loc[zip_code] if zip_code in geo.index else None

        if c is not None:
            fill_counts["matched_curated"] += 1
            identity_source = "curated_us_zips"
            if fill_if_blank(row, "major_city", c.get("city")):
                fill_counts["filled_city"] += 1
            if fill_if_blank(row, "state_original", c.get("state")):
                fill_counts["filled_state"] += 1
            if fill_if_blank(row, "latitude", c.get("latitude")) and fill_if_blank(row, "longitude", c.get("longitude")):
                fill_counts["filled_latlon"] += 1
            elif _is_blank(row.get("latitude")) or _is_blank(row.get("longitude")):
                if not _is_blank(c.get("latitude")) and not _is_blank(c.get("longitude")):
                    row["latitude"] = c.get("latitude")
                    row["longitude"] = c.get("longitude")
                    fill_counts["filled_latlon"] += 1

            # demographics from curated ACS-like fields
            income = _to_float(c.get("median_household_income"))
            if income is not None and fill_if_blank(row, "income_bucket", get_income_bucket(income)):
                fill_counts["filled_income"] += 1
            age = _to_float(c.get("median_age"))
            if age is not None and fill_if_blank(row, "median_age_estimate", age):
                fill_counts["filled_age"] += 1
            pop = _to_int(c.get("population"))
            if pop is not None:
                if fill_if_blank(row, "district_population_numeric", pop):
                    fill_counts["filled_pop"] += 1
                fill_if_blank(row, "district_population", get_population_bucket(pop))
                if fill_if_blank(row, "city_tier", get_city_tier(pop)):
                    fill_counts["filled_tier"] += 1
            bach = _to_float(c.get("bachelors_or_higher_pct"))
            if bach is not None and fill_if_blank(row, "literacy_rate", bach):
                fill_counts["filled_literacy"] += 1

        if h is not None:
            fill_counts["matched_hrsa"] += 1
            identity_source = identity_source or "hrsa"
            if fill_if_blank(row, "major_city", h.get("city")):
                fill_counts["filled_city"] += 1
            if fill_if_blank(row, "state_original", h.get("state")):
                fill_counts["filled_state"] += 1

        if g is not None:
            fill_counts["matched_geonames"] += 1
            identity_source = identity_source or "geonames"
            if fill_if_blank(row, "major_city", g.get("city")):
                fill_counts["filled_city"] += 1
            if fill_if_blank(row, "state_original", g.get("state")):
                fill_counts["filled_state"] += 1
            if (_is_blank(row.get("latitude")) or _is_blank(row.get("longitude"))) and not _is_blank(g.get("lat")):
                row["latitude"] = g.get("lat")
                row["longitude"] = g.get("lon")
                fill_counts["filled_latlon"] += 1

        # Clean census sentinel ages already present
        if _to_float(row.get("median_age_estimate")) is None and not _is_blank(row.get("median_age_estimate")):
            row["median_age_estimate"] = None

        state = str(row.get("state_original") or "").strip().upper()
        if state and state != "NAN":
            row["state_original"] = state
            region = get_region_for_state(state)
            if region == "UNKNOWN" and state in TERRITORY_CAPITALS:
                region = "S" if state in {"PR", "VI"} else "W"
            if fill_if_blank(row, "region", region) or row.get("region") in {None, "", "UNKNOWN", "nan"}:
                if region != "UNKNOWN":
                    row["region"] = region
                    fill_counts["filled_region"] += 1

            lat = _to_float(row.get("latitude"))
            lon = _to_float(row.get("longitude"))
            if lat is not None and lon is not None and _is_blank(row.get("distance_to_state_capital")):
                dist = distance_with_territories(lat, lon, state)
                if dist is not None:
                    row["distance_to_state_capital"] = round(dist, 6)
                    fill_counts["filled_distance"] += 1

            # state defaults for remaining soft fields
            d = defaults.get(state) or defaults.get("__NATIONAL__", {})
            for col in [
                "internet_penetration_state",
                "smartphone_penetration_state",
                "literacy_rate",
                "sex_ratio",
            ]:
                if col in d and fill_if_blank(row, col, d[col]):
                    fill_counts["filled_state_defaults"] += 1
            if "consumer_price_index" in d and fill_if_blank(row, "consumer_price_index", d["consumer_price_index"]):
                fill_counts["filled_cpi"] += 1
            elif fill_if_blank(row, "consumer_price_index", 315.605):
                fill_counts["filled_cpi"] += 1

            # capital flag if blank-ish false already ok
            city = row.get("major_city")
            if city and state:
                row["is_state_capital"] = str(is_state_capital(str(city), state)).lower()

        # digital payment index if still blank and inputs exist
        if _is_blank(row.get("digital_payment_index")):
            dpi = calculate_digital_payment_index(
                _to_float(row.get("internet_penetration_state")),
                _to_float(row.get("smartphone_penetration_state")),
                None if _is_blank(row.get("income_bucket")) else row.get("income_bucket"),
                str(row.get("is_metro_city", "False")).lower() in {"true", "1", "yes"},
            )
            row["digital_payment_index"] = dpi
            fill_counts["filled_dpi"] += 1

        # ensure UT capital false
        row["is_union_territory_capital"] = False
        row["identity_source"] = identity_source
        rows.append(row)

    repaired = pd.DataFrame(rows)

    # Split repaired invalid candidates into newly-valid vs still-invalid
    feature_cols = [c for c in repaired.columns if c not in META_EXCLUDE and c != "#"]
    # keep required feature set aligned with prior split: use all non-meta cols except #
    work = repaired.copy()
    # drop helper col from completeness
    split_work = work.drop(columns=[c for c in ["identity_source"] if c in work.columns], errors="ignore")
    # also drop missing_columns before split
    split_work = split_work.drop(columns=[c for c in ["missing_columns"] if c in split_work.columns], errors="ignore")

    # Completeness on business feature columns only (same as earlier RTB split)
    business_cols = [
        c
        for c in split_work.columns
        if c not in META_EXCLUDE and c != "#"
    ]
    newly_valid, still_invalid, split_summary = split_complete_records(split_work[business_cols + (["#"] if "#" in split_work.columns else [])])

    # Reattach meta
    meta_idx = repaired.set_index("pincode", drop=False)

    def attach_meta(frame: pd.DataFrame) -> pd.DataFrame:
        if frame.empty:
            return frame
        keys = _z5(frame["pincode"])
        for col in [
            "postal_code",
            "feature_source",
            "source_zcta",
            "enrichment_queue",
            "enrichment_priority",
            "enrichment_action",
            "identity_source",
        ]:
            if col in meta_idx.columns:
                frame[col] = keys.map(meta_idx[col])
        front = [
            "#",
            "postal_code",
            "pincode",
            "feature_source",
            "source_zcta",
            "identity_source",
            "enrichment_queue",
            "enrichment_priority",
            "enrichment_action",
        ]
        front = [c for c in front if c in frame.columns]
        rest = [c for c in frame.columns if c not in front]
        return frame[front + rest]

    newly_valid = attach_meta(newly_valid)
    still_invalid = attach_meta(still_invalid)

    # Grow valid set
    valid_keep_cols = [c for c in valid.columns if c in newly_valid.columns or c in valid.columns]
    # align columns
    all_cols = list(dict.fromkeys(list(valid.columns) + list(newly_valid.columns)))
    for c in all_cols:
        if c not in valid.columns:
            valid[c] = None
        if c not in newly_valid.columns and not newly_valid.empty:
            newly_valid[c] = None
    grown_valid = pd.concat([valid[all_cols], newly_valid[all_cols]], ignore_index=True)
    grown_valid = grown_valid.drop_duplicates(subset=["pincode"], keep="last")
    grown_valid["#"] = range(1, len(grown_valid) + 1)

    # still invalid output
    if "missing_columns" not in still_invalid.columns:
        # regenerate via split already has it
        pass
    still_invalid["#"] = range(1, len(still_invalid) + 1)

    # Update final combined file
    final_all_cols = list(dict.fromkeys(list(grown_valid.columns) + list(still_invalid.columns)))
    for c in final_all_cols:
        if c not in grown_valid.columns:
            grown_valid[c] = None
        if c not in still_invalid.columns and not still_invalid.empty:
            still_invalid[c] = None
    final_df = pd.concat([grown_valid[final_all_cols], still_invalid[final_all_cols]], ignore_index=True)
    if "missing_columns" in final_df.columns:
        # keep missing_columns only on invalid; blank for valid
        pass
    final_df["#"] = range(1, len(final_df) + 1)

    grown_valid_path = PROCESSED / "usa_rtb_zip_features_final_valid.csv"
    still_invalid_path = PROCESSED / "usa_rtb_zip_features_final_invalid.csv"
    try:
        grown_valid.to_csv(grown_valid_path, index=False)
        still_invalid.to_csv(still_invalid_path, index=False)
        final_df.to_csv(final_path, index=False)
    except PermissionError:
        grown_valid_path = PROCESSED / "usa_rtb_zip_features_final_valid_v2.csv"
        still_invalid_path = PROCESSED / "usa_rtb_zip_features_final_invalid_v2.csv"
        final_path = PROCESSED / "usa_rtb_zip_features_final_v2.csv"
        grown_valid.to_csv(grown_valid_path, index=False)
        still_invalid.to_csv(still_invalid_path, index=False)
        final_df.to_csv(final_path, index=False)

    report = {
        "phase": "A_tabular_identity_enrichment",
        "before_valid": before_valid,
        "before_invalid": before_invalid,
        "after_valid": int(len(grown_valid)),
        "after_invalid": int(len(still_invalid)),
        "moved_invalid_to_valid": int(len(newly_valid)),
        "shrink_invalid_by": before_invalid - int(len(still_invalid)),
        "fill_counts": fill_counts,
        "still_invalid_by_queue": still_invalid["enrichment_queue"].value_counts(dropna=False).to_dict()
        if not still_invalid.empty and "enrichment_queue" in still_invalid.columns
        else {},
        "newly_valid_by_queue": newly_valid["enrichment_queue"].value_counts(dropna=False).to_dict()
        if not newly_valid.empty and "enrichment_queue" in newly_valid.columns
        else {},
        "split_summary": split_summary,
        "sources": {
            "curated_us_zips": str(CROSSWALK / "curated_us_zips.csv"),
            "hrsa": str(CROSSWALK / "zip_to_zcta_hrsa.xlsx"),
            "geonames": str(CROSSWALK / "geonames_US.zip"),
            "attribution": "curated-us-zips builds on Simplemaps Basic (CC BY 4.0) + Census ACS",
        },
        "paths": {
            "valid": str(grown_valid_path),
            "invalid": str(still_invalid_path),
            "final": str(final_path),
        },
    }
    with open(PROCESSED / "phase_a_tabular_enrichment_report.json", "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    return report


if __name__ == "__main__":
    print(json.dumps(enrich_invalid_rows(), indent=2))
