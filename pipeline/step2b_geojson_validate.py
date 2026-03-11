"""
step2b_geojson_validate.py
─────────────────────────────────────────────────────────────────────────────
Validates step02 output using district boundary GeoJSON (point-in-polygon).
Uses local dists11.geojson for fast validation — no external API calls.

For each record with lat/long:
  - Find which district polygon contains the point
  - Compare polygon's ST_NM (state) and DISTRICT with our state_original, major_city
  - is_valid=True if match, False if mismatch or point outside India

Records without lat/long → is_valid=None (cannot validate).
Invalid records (is_valid=False) are REMOVED to eliminate duplicate/invalid matches.
"""
import json
import os
import pandas as pd
from shapely.geometry import shape, Point
from shapely.strtree import STRtree
from utils import normalize_name, normalize_state, print_step_header, coverage_report, print_value_counts, save_checkpoint


# State name aliases: GeoJSON uses different spellings than our config
GEOJSON_STATE_ALIASES = {
    "arunanchal pradesh": "arunachal pradesh",
    "nct of delhi": "delhi",
    "andaman & nicobar island": "andaman and nicobar islands",
    "andaman and nicobar island": "andaman and nicobar islands",
    "dadara & nagar havelli": "dadra and nagar haveli",
    "dadra & nagar haveli": "dadra and nagar haveli",
    "lakshadweep ": "lakshadweep",
    "chandigarh ": "chandigarh",
    "nct of delhi ": "delhi",
}


def _normalize_geojson_state(name: str) -> str:
    """Normalize state name from GeoJSON to match our config."""
    n = normalize_state(name) if name else ""
    return GEOJSON_STATE_ALIASES.get(n, n)


def _load_district_index(geojson_path: str) -> tuple[STRtree, list[tuple]]:
    """
    Load GeoJSON and build STRtree spatial index.
    Returns (tree, list of (district, state_norm) per geometry index).
    GeoJSON coordinates are [lon, lat].
    """
    if not os.path.exists(geojson_path):
        raise FileNotFoundError(f"District GeoJSON not found: {geojson_path}")

    with open(geojson_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    geoms = []
    props_list = []

    for feat in data.get("features", []):
        geom = shape(feat["geometry"])
        props = feat.get("properties", {})
        district = (props.get("DISTRICT") or "").strip()
        state_raw = (props.get("ST_NM") or "").strip()
        state_norm = _normalize_geojson_state(state_raw)

        geoms.append(geom)
        props_list.append((district, state_norm))

    tree = STRtree(geoms)
    return tree, props_list


def _point_in_district(lon: float, lat: float, tree: STRtree, props_list: list) -> tuple[str | None, str | None]:
    """
    Find district and state for point (lon, lat). Returns (district, state_norm) or (None, None).
    Uses predicate='within' so point is within polygon (contains check).
    """
    pt = Point(lon, lat)
    idx = tree.query(pt, predicate="within")
    if idx is None or len(idx) == 0:
        return (None, None)
    # Take first match (districts shouldn't overlap)
    i = int(idx[0]) if hasattr(idx, '__getitem__') else int(idx)
    return props_list[i]


def _expected_major_city(district: str, state_norm: str, district_to_city: dict) -> str:
    """
    Get expected major_city from district. Uses DISTRICT_TO_MAJOR_CITY for metro areas.
    """
    d_norm = normalize_name(district)
    # Delhi districts: "Central" -> "central delhi" etc.
    if state_norm == "delhi" and d_norm:
        key = f"{d_norm} delhi"
        if key in district_to_city:
            return district_to_city[key]
    if d_norm in district_to_city:
        return district_to_city[d_norm]
    return district


def _values_match(ours: str | None, theirs: str | None) -> bool:
    """Compare our value with GeoJSON value (normalized)."""
    if not ours or not str(ours).strip():
        return not (theirs and str(theirs).strip())
    if not theirs or not str(theirs).strip():
        return False
    o = normalize_name(str(ours))
    t = normalize_name(str(theirs))
    if o == t:
        return True
    # Lenient: "Bangalore Urban" matches "Bangalore" district
    if o in t or t in o:
        return True
    return False


def run(df: pd.DataFrame, config: dict) -> pd.DataFrame:
    print_step_header(3, "GeoJSON Validate — is_valid (district boundaries)")

    geojson_path = config["PATHS"].get("dists_geojson")
    if not geojson_path:
        print("\n  [WARN] PATHS['dists_geojson'] not set. Add to config.py")
        df = df.copy()
        df["is_valid"] = None
        save_checkpoint(df, config["PATHS"]["checkpoints"], step=3)
        return df

    district_to_city = {normalize_name(k): v for k, v in config.get("DISTRICT_TO_MAJOR_CITY", {}).items()}

    print(f"\n  Loading district boundaries: {geojson_path}")
    tree, props_list = _load_district_index(geojson_path)
    print(f"  Loaded {len(props_list):,} district polygons")

    df = df.copy()
    df["is_valid"] = None

    lat_col = df["latitude"] if "latitude" in df.columns else None
    lon_col = df["longitude"] if "longitude" in df.columns else None

    if lat_col is None or lon_col is None:
        print("\n  [WARN] No latitude/longitude columns. Skipping validation.")
        save_checkpoint(df, config["PATHS"]["checkpoints"], step=3)
        return df

    lat_vals = pd.to_numeric(df["latitude"], errors="coerce")
    lon_vals = pd.to_numeric(df["longitude"], errors="coerce")
    has_coords = lat_vals.notna() & lon_vals.notna()
    to_validate = has_coords.sum()
    no_coords = (~has_coords).sum()

    print(f"\n  Records with lat/long  : {to_validate:,}")
    print(f"  Records without coords : {no_coords:,}  (is_valid=None, kept)")

    is_valid_list = [None] * len(df)
    coord_cache = {}  # (lat, lon) rounded -> (district, state)

    for i in range(len(df)):
        if not has_coords.iloc[i]:
            is_valid_list[i] = None
            continue

        lat = float(lat_vals.iloc[i])
        lon = float(lon_vals.iloc[i])
        key = (round(lat, 5), round(lon, 5))
        if key not in coord_cache:
            coord_cache[key] = _point_in_district(lon, lat, tree, props_list)
        district_geo, state_geo = coord_cache[key]

        ours_state = df.iloc[i].get("state_original")
        ours_city = df.iloc[i].get("major_city")

        if district_geo is None and state_geo is None:
            is_valid_list[i] = False  # Point outside all districts
        else:
            state_ok = _values_match(ours_state, state_geo)
            expected_city = _expected_major_city(district_geo or "", state_geo or "", district_to_city)
            city_ok = _values_match(ours_city, expected_city) or _values_match(ours_city, district_geo)
            is_valid_list[i] = state_ok and city_ok

        if (i + 1) % 50000 == 0:
            print(f"  Progress: {i + 1:,} / {len(df):,}")

    df["is_valid"] = is_valid_list

    valid_count = sum(1 for v in is_valid_list if v is True)
    invalid_count = sum(1 for v in is_valid_list if v is False)
    none_count = sum(1 for v in is_valid_list if v is None)

    print(f"\n  Validation results:")
    print(f"    is_valid=True   : {valid_count:>8,}")
    print(f"    is_valid=False  : {invalid_count:>8,}  (will be REMOVED)")
    print(f"    is_valid=None   : {none_count:>8,}  (no coords, kept)")

    # Remove invalid duplicates
    before = len(df)
    df = df[df["is_valid"] != False].copy()
    removed = before - len(df)

    print(f"\n  Removed invalid records: {removed:,}  (kept {len(df):,} rows)")

    print_value_counts(df, "is_valid", top_n=5)
    coverage_report(df, ["is_valid"])

    save_checkpoint(df, config["PATHS"]["checkpoints"], step=3)
    return df
