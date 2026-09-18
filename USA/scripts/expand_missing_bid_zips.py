"""
Option A: Expand ZCTA feature table with missing bid-request ZIP codes.

Steps:
1. Build ZIP master = existing ZCTAs ∪ cleaned missing bid ZIPs
2. Map missing ZIPs -> ZCTA via HRSA crosswalk (fallback: CensusReporter)
3. For still-unmapped ZIPs with GeoNames centroids, inherit from nearest ZCTA
4. Export expanded RTB feature table + coverage report
"""
from __future__ import annotations

import json
import zipfile
from pathlib import Path
from typing import Dict, Optional, Tuple

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
PROCESSED = ROOT / "data" / "processed"
CROSSWALK = ROOT / "data" / "reference" / "crosswalk"


def _z5(series: pd.Series) -> pd.Series:
    s = series.astype(str).str.strip().str.replace(r"\.0$", "", regex=True)
    s = s.str.replace(r"[^0-9]", "", regex=True)
    return s.str.zfill(5)


def load_base_features() -> pd.DataFrame:
    frames = []
    for name in ("usa_city_features_valid.csv", "usa_city_features_invalid.csv"):
        path = PROCESSED / name
        if not path.exists():
            continue
        df = pd.read_csv(path, dtype=str)
        if "missing_columns" in df.columns:
            df = df.drop(columns=["missing_columns"])
        frames.append(df)
    if not frames:
        raise FileNotFoundError("No valid/invalid feature CSVs found in data/processed")

    base = pd.concat(frames, ignore_index=True)
    base["pincode"] = _z5(base["pincode"])
    base = base.drop_duplicates(subset=["pincode"], keep="first")
    base["feature_source"] = "exact_zcta"
    base["source_zcta"] = base["pincode"]
    return base


def load_hrsa_crosswalk() -> pd.DataFrame:
    path = CROSSWALK / "zip_to_zcta_hrsa.xlsx"
    df = pd.read_excel(path, dtype=str)
    df = df.rename(columns={"ZIP_CODE": "zip", "zcta": "zcta", "STATE": "state", "PO_NAME": "po_name"})
    df["zip"] = _z5(df["zip"])
    df["zcta"] = _z5(df["zcta"])
    # one primary ZCTA per ZIP
    return df.drop_duplicates(subset=["zip"], keep="first")[["zip", "zcta", "state", "po_name"]]


def load_censusreporter_crosswalk() -> pd.DataFrame:
    path = CROSSWALK / "zip_zcta_xref_censusreporter.csv"
    df = pd.read_csv(path, dtype=str)
    df = df.rename(columns={"zip_code": "zip"})
    df["zip"] = _z5(df["zip"])
    df["zcta"] = _z5(df["zcta"])
    return df.drop_duplicates(subset=["zip"], keep="first")[["zip", "zcta"]]


def load_geonames_centroids() -> pd.DataFrame:
    path = CROSSWALK / "geonames_US.zip"
    with zipfile.ZipFile(path) as zf:
        with zf.open("US.txt") as f:
            # country, postal, place, admin1 name, admin1 code, admin2 name, admin2 code,
            # admin3 name, admin3 code, lat, lon, accuracy
            df = pd.read_csv(
                f,
                sep="\t",
                header=None,
                dtype=str,
                usecols=[1, 2, 4, 9, 10],
                names=["zip", "place", "state", "lat", "lon"],
            )
    df["zip"] = _z5(df["zip"])
    df["lat"] = pd.to_numeric(df["lat"], errors="coerce")
    df["lon"] = pd.to_numeric(df["lon"], errors="coerce")
    df = df.dropna(subset=["lat", "lon"]).drop_duplicates(subset=["zip"], keep="first")
    return df


def nearest_zcta(
    lat: float,
    lon: float,
    zcta_coords: np.ndarray,
    zcta_codes: np.ndarray,
) -> Optional[str]:
    if pd.isna(lat) or pd.isna(lon):
        return None
    # equirectangular approximation good enough for nearest US ZIP
    dlat = np.radians(zcta_coords[:, 0] - lat)
    dlon = np.radians(zcta_coords[:, 1] - lon)
    mean_lat = np.radians((zcta_coords[:, 0] + lat) / 2.0)
    dx = dlon * np.cos(mean_lat)
    dist2 = dlat * dlat + dx * dx
    idx = int(np.argmin(dist2))
    return str(zcta_codes[idx])


def inherit_row(base_row: pd.Series, zip_code: str, source: str, source_zcta: str, overrides: Optional[Dict] = None) -> Dict:
    row = base_row.to_dict()
    row["pincode"] = zip_code
    row["feature_source"] = source
    row["source_zcta"] = source_zcta
    if overrides:
        row.update(overrides)
    return row


def build_option_a() -> Dict:
    CROSSWALK.mkdir(parents=True, exist_ok=True)
    base = load_base_features()
    base_by_zip = base.set_index("pincode", drop=False)

    missing = pd.read_csv(PROCESSED / "bid_zips_missing_from_zcta.csv", dtype=str)
    missing["postal_code"] = _z5(missing["postal_code"])
    missing_zips = sorted(set(missing["postal_code"]) - set(base_by_zip.index))

    hrsa = load_hrsa_crosswalk()
    hrsa_map = dict(zip(hrsa["zip"], hrsa["zcta"]))
    hrsa_meta = hrsa.set_index("zip")

    cr = load_censusreporter_crosswalk()
    cr_map = dict(zip(cr["zip"], cr["zcta"]))

    geo = load_geonames_centroids()
    geo_map = geo.set_index("zip")

    # ZCTA coordinate matrix for nearest search
    coords = base[["pincode", "latitude", "longitude"]].copy()
    coords["latitude"] = pd.to_numeric(coords["latitude"], errors="coerce")
    coords["longitude"] = pd.to_numeric(coords["longitude"], errors="coerce")
    coords = coords.dropna(subset=["latitude", "longitude"])
    zcta_coords = coords[["latitude", "longitude"]].to_numpy(dtype=float)
    zcta_codes = coords["pincode"].to_numpy()

    inherited_rows = []
    stats = {
        "missing_input": len(missing_zips),
        "mapped_hrsa": 0,
        "mapped_censusreporter": 0,
        "mapped_nearest": 0,
        "unmapped": 0,
    }
    unmapped = []

    for zip_code in missing_zips:
        mapped_zcta = None
        source = None
        overrides = {}

        zcta = hrsa_map.get(zip_code)
        if zcta and zcta in base_by_zip.index:
            mapped_zcta = zcta
            source = "inherited_hrsa"
            stats["mapped_hrsa"] += 1
            if zip_code in hrsa_meta.index:
                meta = hrsa_meta.loc[zip_code]
                if pd.notna(meta.get("state")) and str(meta.get("state")).strip():
                    overrides["state_original"] = str(meta.get("state")).strip()
                if pd.notna(meta.get("po_name")) and str(meta.get("po_name")).strip():
                    overrides["major_city"] = str(meta.get("po_name")).strip()
        else:
            zcta = cr_map.get(zip_code)
            if zcta and zcta in base_by_zip.index:
                mapped_zcta = zcta
                source = "inherited_censusreporter"
                stats["mapped_censusreporter"] += 1

        if mapped_zcta is None and zip_code in geo_map.index:
            g = geo_map.loc[zip_code]
            nearest = nearest_zcta(float(g["lat"]), float(g["lon"]), zcta_coords, zcta_codes)
            if nearest and nearest in base_by_zip.index:
                mapped_zcta = nearest
                source = "inherited_nearest_zcta"
                stats["mapped_nearest"] += 1
                overrides["latitude"] = g["lat"]
                overrides["longitude"] = g["lon"]
                if pd.notna(g.get("state")) and str(g.get("state")).strip():
                    overrides["state_original"] = str(g.get("state")).strip()
                if pd.notna(g.get("place")) and str(g.get("place")).strip():
                    overrides["major_city"] = str(g.get("place")).strip()

        if mapped_zcta is None:
            stats["unmapped"] += 1
            unmapped.append(zip_code)
            # still add a stub row so RTB join does not fail
            stub = {c: None for c in base.columns}
            stub["pincode"] = zip_code
            stub["feature_source"] = "unmapped_stub"
            stub["source_zcta"] = None
            stub["is_union_territory_capital"] = False
            for b in [
                "coastal_city", "is_metro_city", "is_smart_city", "is_state_capital",
                "has_airport", "has_international_airport", "has_metro_rail", "has_seaport",
                "major_railway_station", "is_it_hub", "is_manufacturing_hub",
                "is_financial_center", "is_textile_hub", "is_education_hub",
                "is_tourist_city", "is_coastal",
            ]:
                if b in stub:
                    stub[b] = False
            if zip_code in geo_map.index:
                g = geo_map.loc[zip_code]
                stub["latitude"] = g["lat"]
                stub["longitude"] = g["lon"]
                stub["state_original"] = g.get("state")
                stub["major_city"] = g.get("place")
            if zip_code in hrsa_meta.index:
                meta = hrsa_meta.loc[zip_code]
                stub["state_original"] = meta.get("state") or stub.get("state_original")
                stub["major_city"] = meta.get("po_name") or stub.get("major_city")
            inherited_rows.append(stub)
            continue

        inherited_rows.append(
            inherit_row(base_by_zip.loc[mapped_zcta], zip_code, source, mapped_zcta, overrides)
        )

    inherited_df = pd.DataFrame(inherited_rows)
    expanded = pd.concat([base, inherited_df], ignore_index=True)
    expanded["pincode"] = _z5(expanded["pincode"])
    expanded = expanded.drop_duplicates(subset=["pincode"], keep="first")
    expanded["#"] = range(1, len(expanded) + 1)

    # ZIP master
    master = expanded[["pincode", "feature_source", "source_zcta", "state_original", "major_city"]].copy()
    master = master.rename(columns={"pincode": "postal_code"})

    # Coverage vs cleaned bid ZIPs
    bid_clean = pd.read_csv(PROCESSED / "bid_zips_cleaned.csv", dtype=str)
    bid_z = set(_z5(bid_clean["postal_code"]))
    our_z = set(expanded["pincode"])
    covered = bid_z & our_z
    still_missing = sorted(bid_z - our_z)

    report = {
        "option": "A_traffic_first_zip_expansion",
        "base_zcta_rows": int(len(base)),
        "missing_bid_zips_input": int(stats["missing_input"]),
        "inheritance_stats": stats,
        "expanded_rows": int(len(expanded)),
        "zip_master_rows": int(len(master)),
        "bid_cleaned_distinct": int(len(bid_z)),
        "bid_covered_after": int(len(covered)),
        "bid_coverage_pct_after": round(100.0 * len(covered) / len(bid_z), 2) if bid_z else 0.0,
        "bid_still_missing_after": int(len(still_missing)),
        "unmapped_stub_zips_sample": unmapped[:30],
        "paths": {
            "expanded_features": str(PROCESSED / "usa_city_features_rtb_expanded.csv"),
            "zip_master": str(PROCESSED / "zip_master.csv"),
            "inherited_only": str(PROCESSED / "usa_city_features_inherited_zips.csv"),
            "still_missing_bid_zips": str(PROCESSED / "bid_zips_still_missing_after_option_a.csv"),
            "report": str(PROCESSED / "option_a_coverage_report.json"),
        },
    }

    expanded.to_csv(PROCESSED / "usa_city_features_rtb_expanded.csv", index=False)
    master.to_csv(PROCESSED / "zip_master.csv", index=False)
    inherited_df.to_csv(PROCESSED / "usa_city_features_inherited_zips.csv", index=False)
    pd.DataFrame({"postal_code": still_missing}).to_csv(
        PROCESSED / "bid_zips_still_missing_after_option_a.csv", index=False
    )
    pd.DataFrame({"postal_code": unmapped}).to_csv(
        PROCESSED / "option_a_unmapped_stub_zips.csv", index=False
    )
    with open(PROCESSED / "option_a_coverage_report.json", "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    return report


if __name__ == "__main__":
    result = build_option_a()
    print(json.dumps(result, indent=2))
