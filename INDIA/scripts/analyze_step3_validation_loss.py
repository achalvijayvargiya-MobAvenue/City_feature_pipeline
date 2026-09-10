"""
analyze_step3_validation_loss.py
─────────────────────────────────────────────────────────────────────────────
Diagnose why Step 3 (GeoJSON Validate) removes records.

Two failure modes:
  A) Point outside India — lat/lon falls outside all district polygons
  B) Name mismatch — point is inside a polygon, but our (state, district) don't
     match the polygon's (ST_NM, DISTRICT)

Run after step 2: python scripts/analyze_step3_validation_loss.py
"""
import json
import os
import sys

import pandas as pd
from shapely.geometry import shape, Point
from shapely.strtree import STRtree

# Add pipeline to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "pipeline"))
from utils import normalize_name, normalize_state

# GeoJSON aliases (same as step2b)
GEOJSON_STATE_ALIASES = {
    "arunanchal pradesh": "arunachal pradesh",
    "nct of delhi": "delhi",
    "andaman & nicobar island": "andaman and nicobar islands",
    "andaman and nicobar islands": "andaman and nicobar islands",
    "dadara & nagar havelli": "dadra and nagar haveli",
    "dadra & nagar haveli": "dadra and nagar haveli",
}

BASE = os.path.join(os.path.dirname(__file__), "..")


def load_geojson_index(geojson_path):
    geoms, props_list = [], []
    with open(geojson_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    for feat in data.get("features", []):
        geoms.append(shape(feat["geometry"]))
        p = feat.get("properties", {})
        state_raw = (p.get("ST_NM") or "").strip()
        state_norm = normalize_state(state_raw)
        state_norm = GEOJSON_STATE_ALIASES.get(state_norm, state_norm)
        props_list.append(((p.get("DISTRICT") or "").strip(), state_norm))
    tree = STRtree(geoms)
    return tree, props_list


def point_in_district(lon, lat, tree, props_list):
    pt = Point(lon, lat)
    idx = tree.query(pt, predicate="within")
    if idx is None or len(idx) == 0:
        return (None, None)
    i = int(idx[0]) if hasattr(idx, "__getitem__") else int(idx)
    return props_list[i]


def main():
    geojson_path = os.path.join(BASE, "true_source", "dists11.geojson")
    cp_path = os.path.join(BASE, "checkpoints", "step02_output.csv")

    if not os.path.exists(cp_path):
        print("Run pipeline through step 2 first (checkpoints/step02_output.csv)")
        return

    df = pd.read_csv(cp_path)
    tree, props_list = load_geojson_index(geojson_path)

    lat = pd.to_numeric(df["latitude"], errors="coerce")
    lon = pd.to_numeric(df["longitude"], errors="coerce")
    has_coords = lat.notna() & lon.notna()

    outside = []   # Point outside India
    state_mismatch = []
    district_mismatch = []
    valid_count = 0

    for i in range(len(df)):
        if not has_coords.iloc[i]:
            continue
        la, lo = float(lat.iloc[i]), float(lon.iloc[i])
        d_geo, s_geo = point_in_district(lo, la, tree, props_list)
        ours_d = str(df.iloc[i].get("major_city") or "").strip()
        ours_s = str(df.iloc[i].get("state_original") or "").strip()

        if d_geo is None and s_geo is None:
            outside.append({
                "pincode": df.iloc[i].get("city_original"),
                "ours_state": ours_s,
                "ours_district": ours_d,
                "lat": la,
                "lon": lo,
            })
        else:
            d_geo_n = normalize_name(d_geo or "")
            s_geo_n = normalize_state(s_geo or "")
            ours_d_n = normalize_name(ours_d)
            ours_s_n = normalize_state(ours_s)

            state_ok = s_geo_n == ours_s_n or ours_s_n in s_geo_n or s_geo_n in ours_s_n
            city_ok = d_geo_n == ours_d_n or ours_d_n in d_geo_n or d_geo_n in ours_d_n

            if state_ok and city_ok:
                valid_count += 1
            else:
                rec = {
                    "pincode": df.iloc[i].get("city_original"),
                    "ours_state": ours_s,
                    "ours_district": ours_d,
                    "geo_state": s_geo,
                    "geo_district": d_geo,
                    "lat": la,
                    "lon": lo,
                }
                if not state_ok:
                    state_mismatch.append(rec)
                else:
                    district_mismatch.append(rec)

    print("=" * 70)
    print("  STEP 3 VALIDATION LOSS ANALYSIS")
    print("=" * 70)
    print(f"\n  Records with coords  : {has_coords.sum():,}")
    print(f"  Would PASS (valid)   : {valid_count:,}")
    print(f"\n  FAILURE BREAKDOWN:")
    print(f"    A) Point OUTSIDE India (not in any polygon) : {len(outside):,}")
    print(f"    B) State mismatch (inside polygon, wrong state) : {len(state_mismatch):,}")
    print(f"    C) District mismatch (state ok, district differs) : {len(district_mismatch):,}")
    print(f"\n  Total failures: {len(outside) + len(state_mismatch) + len(district_mismatch):,}")

    if outside:
        print("\n  --- Sample OUTSIDE India (likely bad lat/lon in Pincode_mapping) ---")
        for r in outside[:5]:
            print(f"    pincode={r['pincode']} state={r['ours_state']} district={r['ours_district']} lat={r['lat']:.4f} lon={r['lon']:.4f}")

    if state_mismatch:
        print("\n  --- Sample STATE mismatch (e.g. Telangana vs Andhra Pradesh) ---")
        for r in state_mismatch[:8]:
            print(f"    pincode={r['pincode']} | ours: {r['ours_state']}/{r['ours_district']} | geo: {r['geo_state']}/{r['geo_district']}")

    if district_mismatch:
        print("\n  --- Sample DISTRICT mismatch (new vs old district names) ---")
        for r in district_mismatch[:8]:
            print(f"    pincode={r['pincode']} | ours: {r['ours_district']} | geo: {r['geo_district']}")

    print("\n" + "=" * 70)
    print("  LIKELY CAUSE:")
    print("  dists11.geojson uses 2011 Census boundaries. Many districts were")
    print("  reorganized after 2011 (Telangana 2014, new districts carved).")
    print("  Pincode_mapping uses CURRENT postal district names.")
    print("  GeoJSON polygon says 'Adilabad, Andhra Pradesh' but Pincode says")
    print("  'KUMURAM BHEEM ASIFABAD, TELANGANA' -> mismatch -> removed.")
    print("=" * 70)


if __name__ == "__main__":
    main()
