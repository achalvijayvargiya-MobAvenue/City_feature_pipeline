"""
Build a new RTB feature universe keyed on usps_listofzip_base.csv (~41.5k).

- Keep features from usa_rtb_zip_features_final_valid_v2.csv where ZIP exists in base
- Enrich remaining base ZIPs from available pipeline sources
- Emit new valid + invalid completeness splits
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
from usa_city_features.geography.manual_flags import (
    load_coastal_county_fips,
    load_manual_flags,
    normalize_place_name,
    place_in_flag,
)
from usa_city_features.geography.regions import get_region_for_state
from usa_city_features.geography.state_capitals import (
    STATE_CAPITALS,
    distance_to_state_capital,
    is_state_capital,
)
from usa_city_features.transforms.distance import haversine_distance_km
from usa_city_features.validation.schema_validator import (
    REQUIRED_COLUMNS,
    split_complete_records,
)

ROOT = Path(__file__).resolve().parents[1]
PROCESSED = ROOT / "data" / "processed"
CROSSWALK = ROOT / "data" / "reference" / "crosswalk"

TERRITORY_CAPITALS = {
    "PR": {"name": "San Juan", "lat": 18.4655, "lon": -66.1057},
    "VI": {"name": "Charlotte Amalie", "lat": 18.3419, "lon": -64.9307},
    "GU": {"name": "Hagatna", "lat": 13.4750, "lon": 144.7500},
    "AS": {"name": "Pago Pago", "lat": -14.2756, "lon": -170.7020},
    "MP": {"name": "Saipan", "lat": 15.1778, "lon": 145.7508},
    "DC": {"name": "Washington", "lat": 38.9072, "lon": -77.0369},
}

BOOL_FALSE_DEFAULTS = [
    "coastal_city",
    "is_metro_city",
    "is_smart_city",
    "is_state_capital",
    "is_union_territory_capital",
    "has_airport",
    "has_international_airport",
    "has_metro_rail",
    "has_seaport",
    "major_railway_station",
    "is_it_hub",
    "is_manufacturing_hub",
    "is_financial_center",
    "is_textile_hub",
    "is_education_hub",
    "is_tourist_city",
    "is_coastal",
]

META_COLS = {
    "feature_source",
    "source_zcta",
    "enrichment_queue",
    "enrichment_priority",
    "enrichment_action",
    "identity_source",
    "missing_columns",
    "base_name",
}


def _z5(s: pd.Series) -> pd.Series:
    return (
        s.astype(str)
        .str.strip()
        .str.replace(r"\.0$", "", regex=True)
        .str.replace(r"[^0-9]", "", regex=True)
        .str.zfill(5)
    )


def _blank(v: Any) -> bool:
    if v is None:
        return True
    try:
        if pd.isna(v):
            return True
    except Exception:
        pass
    t = str(v).strip().lower()
    return t in {"", "nan", "none", "null", "unknown", "<na>", "nat"}


def _f(v: Any) -> Optional[float]:
    try:
        if _blank(v):
            return None
        x = float(v)
        if abs(x) >= 1e8:
            return None
        return x
    except Exception:
        return None


def _i(v: Any) -> Optional[int]:
    x = _f(v)
    return None if x is None else int(x)


def distance_any(lat: float, lon: float, state: str) -> Optional[float]:
    state = (state or "").upper()
    if state in STATE_CAPITALS:
        return distance_to_state_capital(lat, lon, state)
    cap = TERRITORY_CAPITALS.get(state)
    if not cap:
        return None
    return haversine_distance_km(lat, lon, cap["lat"], cap["lon"])


def load_sources():
    curated = pd.read_csv(CROSSWALK / "curated_us_zips.csv", dtype=str)
    curated["zip"] = _z5(curated["zip_code"])
    curated = curated.drop_duplicates("zip").set_index("zip")

    hrsa = pd.read_excel(CROSSWALK / "zip_to_zcta_hrsa.xlsx", dtype=str)
    hrsa["zip"] = _z5(hrsa["ZIP_CODE"])
    hrsa = hrsa.rename(columns={"PO_NAME": "city", "STATE": "state"})
    hrsa = hrsa.drop_duplicates("zip").set_index("zip")

    with zipfile.ZipFile(CROSSWALK / "geonames_US.zip") as zf:
        with zf.open("US.txt") as f:
            geo = pd.read_csv(
                f,
                sep="\t",
                header=None,
                dtype=str,
                usecols=[1, 2, 4, 9, 10],
                names=["zip", "city", "state", "lat", "lon"],
            )
    geo["zip"] = _z5(geo["zip"])
    geo = geo.drop_duplicates("zip").set_index("zip")

    return curated, hrsa, geo


def state_defaults(valid: pd.DataFrame) -> Dict[str, Dict[str, Any]]:
    df = valid.copy()
    df["state_original"] = df["state_original"].astype(str).str.upper()
    out: Dict[str, Dict[str, Any]] = {}
    for state, g in df.groupby("state_original"):
        if _blank(state) or state == "NAN":
            continue
        rec: Dict[str, Any] = {}
        for col in [
            "internet_penetration_state",
            "smartphone_penetration_state",
            "consumer_price_index",
            "literacy_rate",
            "sex_ratio",
            "median_age_estimate",
        ]:
            vals = pd.to_numeric(g[col], errors="coerce").dropna()
            vals = vals[vals.abs() < 1e8]
            if len(vals):
                rec[col] = float(vals.median())
        mode_inc = g["income_bucket"].dropna()
        mode_inc = mode_inc[~mode_inc.astype(str).str.lower().isin(["nan", "none", ""])]
        if len(mode_inc):
            rec["income_bucket"] = mode_inc.mode().iloc[0]
        pop = pd.to_numeric(g["district_population_numeric"], errors="coerce").dropna()
        if len(pop):
            rec["district_population_numeric"] = float(pop.median())
        if rec:
            out[state] = rec
    # national
    nat: Dict[str, Any] = {}
    for col in [
        "internet_penetration_state",
        "smartphone_penetration_state",
        "consumer_price_index",
        "literacy_rate",
        "sex_ratio",
        "median_age_estimate",
    ]:
        vals = pd.to_numeric(df[col], errors="coerce").dropna()
        vals = vals[vals.abs() < 1e8]
        if len(vals):
            nat[col] = float(vals.median())
    mode_inc = df["income_bucket"].dropna()
    mode_inc = mode_inc[~mode_inc.astype(str).str.lower().isin(["nan", "none", ""])]
    if len(mode_inc):
        nat["income_bucket"] = mode_inc.mode().iloc[0]
    pop = pd.to_numeric(df["district_population_numeric"], errors="coerce").dropna()
    if len(pop):
        nat["district_population_numeric"] = float(pop.median())
    nat["consumer_price_index"] = nat.get("consumer_price_index", 315.605)
    out["__NATIONAL__"] = nat
    return out


def nearest_valid_zip(lat: float, lon: float, coords: np.ndarray, codes: np.ndarray) -> Optional[str]:
    if coords.size == 0:
        return None
    dlat = np.radians(coords[:, 0] - lat)
    dlon = np.radians(coords[:, 1] - lon)
    mean_lat = np.radians((coords[:, 0] + lat) / 2.0)
    dist2 = dlat * dlat + (dlon * np.cos(mean_lat)) ** 2
    return str(codes[int(np.argmin(dist2))])


def apply_manual_flags(row: Dict[str, Any]) -> None:
    city = row.get("major_city")
    for flag in [
        "has_airport",
        "has_international_airport",
        "has_metro_rail",
        "has_seaport",
        "major_railway_station",
        "is_it_hub",
        "is_manufacturing_hub",
        "is_financial_center",
        "is_textile_hub",
        "is_education_hub",
        "is_tourist_city",
    ]:
        if place_in_flag(city, flag):
            row[flag] = True
    # coastal by county fips if available from curated
    # also coastal_city mirrors is_coastal
    if row.get("is_coastal") is True:
        row["coastal_city"] = True


def empty_feature_row(zip_code: str, base_name: str) -> Dict[str, Any]:
    row = {c: None for c in REQUIRED_COLUMNS if c != "#"}
    row["pincode"] = zip_code
    row["postal_code"] = zip_code
    for b in BOOL_FALSE_DEFAULTS:
        row[b] = False
    row["base_name"] = base_name
    row["feature_source"] = "base_pending"
    row["source_zcta"] = None
    row["identity_source"] = None
    return row


def build() -> Dict[str, Any]:
    base = pd.read_csv(PROCESSED / "usps_listofzip_base.csv", dtype=str)
    base["postal_code"] = _z5(base["postal_code"])
    base = base.drop_duplicates("postal_code", keep="first")

    valid = pd.read_csv(PROCESSED / "usa_rtb_zip_features_final_valid_v2.csv", dtype=str)
    valid["pincode"] = _z5(valid["pincode"])
    valid["postal_code"] = _z5(valid.get("postal_code", valid["pincode"]))
    valid = valid.drop_duplicates("pincode", keep="first")

    curated, hrsa, geo = load_sources()
    defaults = state_defaults(valid)
    manual_flags = load_manual_flags()
    coastal_fips = load_coastal_county_fips()

    # nearest search matrix from existing valid
    coords_df = valid[["pincode", "latitude", "longitude"]].copy()
    coords_df["latitude"] = pd.to_numeric(coords_df["latitude"], errors="coerce")
    coords_df["longitude"] = pd.to_numeric(coords_df["longitude"], errors="coerce")
    coords_df = coords_df.dropna()
    zcta_coords = coords_df[["latitude", "longitude"]].to_numpy(dtype=float)
    zcta_codes = coords_df["pincode"].to_numpy()
    valid_by_zip = valid.set_index("pincode", drop=False)

    base_z = set(base["postal_code"])
    valid_in_base = valid[valid["pincode"].isin(base_z)].copy()
    missing_z = sorted(base_z - set(valid_in_base["pincode"]))
    valid_not_in_base = sorted(set(valid["pincode"]) - base_z)

    stats = {
        "base_zips": int(len(base_z)),
        "existing_valid_total": int(len(valid)),
        "existing_valid_in_base": int(len(valid_in_base)),
        "existing_valid_not_in_base": int(len(valid_not_in_base)),
        "base_missing_to_enrich": int(len(missing_z)),
        "matched_curated": 0,
        "matched_hrsa": 0,
        "matched_geonames": 0,
        "inherited_nearest": 0,
        "manual_flags_applied": 0,
    }

    enriched_rows = []
    base_name_map = dict(zip(base["postal_code"], base["name"]))

    for zip_code in missing_z:
        row = empty_feature_row(zip_code, base_name_map.get(zip_code, ""))
        sources = []

        if zip_code in curated.index:
            stats["matched_curated"] += 1
            sources.append("curated")
            c = curated.loc[zip_code]
            row["major_city"] = c.get("city")
            row["state_original"] = c.get("state")
            row["latitude"] = c.get("latitude")
            row["longitude"] = c.get("longitude")
            income = _f(c.get("median_household_income"))
            if income is not None:
                row["income_bucket"] = get_income_bucket(income)
            age = _f(c.get("median_age"))
            if age is not None:
                row["median_age_estimate"] = age
            pop = _i(c.get("population"))
            if pop is not None:
                row["district_population_numeric"] = pop
                row["district_population"] = get_population_bucket(pop)
                row["city_tier"] = get_city_tier(pop)
            bach = _f(c.get("bachelors_or_higher_pct"))
            if bach is not None:
                row["literacy_rate"] = bach
            # coastal via county fips if present
            cf = str(c.get("county_fips") or "").zfill(5)
            if cf in coastal_fips:
                row["is_coastal"] = True
                row["coastal_city"] = True

        if zip_code in hrsa.index:
            stats["matched_hrsa"] += 1
            sources.append("hrsa")
            h = hrsa.loc[zip_code]
            if _blank(row.get("major_city")):
                row["major_city"] = h.get("city")
            if _blank(row.get("state_original")):
                row["state_original"] = h.get("state")

        if zip_code in geo.index:
            stats["matched_geonames"] += 1
            sources.append("geonames")
            g = geo.loc[zip_code]
            if _blank(row.get("major_city")):
                row["major_city"] = g.get("city")
            if _blank(row.get("state_original")):
                row["state_original"] = g.get("state")
            if _blank(row.get("latitude")) or _blank(row.get("longitude")):
                row["latitude"] = g.get("lat")
                row["longitude"] = g.get("lon")

        # nearest valid inheritance for remaining demographic gaps
        lat = _f(row.get("latitude"))
        lon = _f(row.get("longitude"))
        nearest = None
        if lat is not None and lon is not None:
            nearest = nearest_valid_zip(lat, lon, zcta_coords, zcta_codes)
            if nearest and nearest in valid_by_zip.index:
                stats["inherited_nearest"] += 1
                sources.append(f"nearest:{nearest}")
                donor = valid_by_zip.loc[nearest]
                for col in [
                    "literacy_rate",
                    "median_age_estimate",
                    "income_bucket",
                    "internet_penetration_state",
                    "smartphone_penetration_state",
                    "digital_payment_index",
                    "sex_ratio",
                    "district_population_numeric",
                    "district_population",
                    "city_tier",
                    "consumer_price_index",
                    "is_metro_city",
                ]:
                    if _blank(row.get(col)) and not _blank(donor.get(col)):
                        row[col] = donor.get(col)
                row["source_zcta"] = nearest

        state = str(row.get("state_original") or "").strip().upper()
        if state and state != "NAN":
            row["state_original"] = state
            region = get_region_for_state(state)
            if region == "UNKNOWN" and state in TERRITORY_CAPITALS:
                region = "S" if state in {"PR", "VI"} else "W"
            if region != "UNKNOWN":
                row["region"] = region
            if lat is not None and lon is not None:
                dist = distance_any(lat, lon, state)
                if dist is not None:
                    row["distance_to_state_capital"] = round(dist, 6)
            if row.get("major_city"):
                row["is_state_capital"] = is_state_capital(str(row["major_city"]), state)

            d = defaults.get(state) or defaults.get("__NATIONAL__", {})
            for col, val in d.items():
                if _blank(row.get(col)):
                    row[col] = val
            if _blank(row.get("district_population")) and not _blank(row.get("district_population_numeric")):
                pop = _i(row.get("district_population_numeric"))
                if pop is not None:
                    row["district_population"] = get_population_bucket(pop)
                    if _blank(row.get("city_tier")):
                        row["city_tier"] = get_city_tier(pop)

        # manual city flags
        before_flags = {k: row.get(k) for k in BOOL_FALSE_DEFAULTS}
        apply_manual_flags(row)
        if any(row.get(k) != before_flags.get(k) for k in BOOL_FALSE_DEFAULTS):
            stats["manual_flags_applied"] += 1

        if _blank(row.get("consumer_price_index")):
            row["consumer_price_index"] = defaults.get("__NATIONAL__", {}).get("consumer_price_index", 315.605)

        if _blank(row.get("digital_payment_index")):
            row["digital_payment_index"] = calculate_digital_payment_index(
                _f(row.get("internet_penetration_state")),
                _f(row.get("smartphone_penetration_state")),
                None if _blank(row.get("income_bucket")) else row.get("income_bucket"),
                str(row.get("is_metro_city", False)).lower() in {"true", "1", "yes"},
            )

        row["identity_source"] = "|".join(sources) if sources else None
        row["feature_source"] = "base_enriched" if sources else "base_stub"
        row["enrichment_queue"] = "queue_base_expansion"
        row["enrichment_priority"] = 2
        row["enrichment_action"] = "tabular_plus_nearest_defaults"
        enriched_rows.append(row)

    enriched_df = pd.DataFrame(enriched_rows)

    # Align existing valid-in-base rows
    keep_cols = list(
        dict.fromkeys(
            ["postal_code", "pincode", "base_name"]
            + [c for c in REQUIRED_COLUMNS if c != "#"]
            + [
                "feature_source",
                "source_zcta",
                "identity_source",
                "enrichment_queue",
                "enrichment_priority",
                "enrichment_action",
            ]
        )
    )

    valid_in_base = valid_in_base.copy()
    valid_in_base["base_name"] = valid_in_base["pincode"].map(base_name_map)
    valid_in_base["feature_source"] = valid_in_base.get("feature_source", "exact_or_prior_valid")
    for c in keep_cols:
        if c not in valid_in_base.columns:
            valid_in_base[c] = None
        if c not in enriched_df.columns and not enriched_df.empty:
            enriched_df[c] = None

    universe = pd.concat([valid_in_base[keep_cols], enriched_df[keep_cols]], ignore_index=True)
    universe = universe.drop_duplicates(subset=["pincode"], keep="first")
    # ensure every base zip exists
    missing_after = sorted(base_z - set(universe["pincode"]))
    if missing_after:
        extras = [empty_feature_row(z, base_name_map.get(z, "")) for z in missing_after]
        universe = pd.concat([universe, pd.DataFrame(extras)], ignore_index=True)

    universe["postal_code"] = universe["pincode"]
    universe["#"] = range(1, len(universe) + 1)

    # Completeness split on business columns
    business_cols = [c for c in REQUIRED_COLUMNS if c != "#"]
    for c in business_cols:
        if c not in universe.columns:
            universe[c] = None
    # map pincode already present; REQUIRED uses pincode
    split_df = universe[business_cols + ["#"]].copy()
    # REQUIRED has pincode not postal_code
    valid_df, invalid_df, split_summary = split_complete_records(split_df)

    meta = universe.set_index("pincode", drop=False)

    def attach(frame: pd.DataFrame) -> pd.DataFrame:
        if frame.empty:
            return frame
        keys = _z5(frame["pincode"])
        for c in [
            "postal_code",
            "base_name",
            "feature_source",
            "source_zcta",
            "identity_source",
            "enrichment_queue",
            "enrichment_priority",
            "enrichment_action",
        ]:
            if c in meta.columns:
                frame[c] = keys.map(meta[c])
        front = [
            "#",
            "postal_code",
            "pincode",
            "base_name",
            "feature_source",
            "source_zcta",
            "identity_source",
            "enrichment_queue",
            "enrichment_priority",
            "enrichment_action",
        ]
        front = [c for c in front if c in frame.columns]
        rest = [c for c in frame.columns if c not in front]
        out = frame[front + rest]
        out["#"] = range(1, len(out) + 1)
        return out

    valid_df = attach(valid_df)
    invalid_df = attach(invalid_df)

    out_valid = PROCESSED / "usa_rtb_base41k_features_valid.csv"
    out_invalid = PROCESSED / "usa_rtb_base41k_features_invalid.csv"
    out_all = PROCESSED / "usa_rtb_base41k_features_all.csv"
    out_side = PROCESSED / "usa_rtb_valid_not_in_base41k.csv"

    universe.to_csv(out_all, index=False)
    valid_df.to_csv(out_valid, index=False)
    invalid_df.to_csv(out_invalid, index=False)
    if valid_not_in_base:
        valid[valid["pincode"].isin(valid_not_in_base)].to_csv(out_side, index=False)
    else:
        pd.DataFrame(columns=valid.columns).to_csv(out_side, index=False)

    report = {
        **stats,
        "after_valid": int(len(valid_df)),
        "after_invalid": int(len(invalid_df)),
        "universe_rows": int(len(universe)),
        "split_summary": split_summary,
        "paths": {
            "all": str(out_all),
            "valid": str(out_valid),
            "invalid": str(out_invalid),
            "valid_not_in_base": str(out_side),
            "report": str(PROCESSED / "usa_rtb_base41k_build_report.json"),
        },
    }
    with open(PROCESSED / "usa_rtb_base41k_build_report.json", "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    return report


if __name__ == "__main__":
    print(json.dumps(build(), indent=2))
