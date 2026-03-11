"""
step4_derived_fields.py
─────────────────────────────────────────────────────────────────────────────
Derives geographic and distance-based features from state and coordinates.
Aligned with InputData/feature_list.txt.

Fills:
  region (geographic_region), coastal_city (is_coastal), state (alias)
  distance_to_state_capital — Haversine distance to state/UT capital
"""
import math
import pandas as pd
from utils import normalize_state, print_step_header, coverage_report, print_value_counts, save_checkpoint


# State/UT capital coordinates (lat, lon) for distance calculation
CAPITAL_COORDS = {
    "jammu and kashmir": (34.08, 74.80), "jammu & kashmir": (34.08, 74.80),
    "ladakh": (34.15, 77.58),
    "himachal pradesh": (31.10, 77.17),
    "punjab": (30.73, 76.78), "chandigarh": (30.73, 76.78),
    "haryana": (30.73, 76.78),
    "uttarakhand": (30.32, 78.03),
    "uttar pradesh": (26.85, 80.95),
    "delhi": (28.61, 77.21), "national capital territory of delhi": (28.61, 77.21),
    "rajasthan": (26.91, 75.79),
    "bihar": (25.60, 85.12),
    "jharkhand": (23.35, 85.33),
    "west bengal": (22.57, 88.36),
    "odisha": (20.30, 85.82), "orissa": (20.30, 85.82),
    "sikkim": (27.34, 88.61),
    "assam": (26.14, 91.74),
    "meghalaya": (25.58, 91.88),
    "manipur": (24.82, 93.95),
    "mizoram": (23.73, 92.72),
    "nagaland": (25.67, 94.11),
    "tripura": (23.83, 91.28),
    "arunachal pradesh": (27.10, 93.69),
    "madhya pradesh": (23.26, 77.41),
    "chhattisgarh": (21.25, 81.63),
    "gujarat": (23.02, 72.57),
    "maharashtra": (19.08, 72.88),
    "goa": (15.50, 73.83),
    "dadra and nagar haveli": (20.18, 73.01), "dadra & nagar haveli": (20.18, 73.01),
    "daman and diu": (20.42, 72.83), "daman & diu": (20.42, 72.83),
    "dadra and nagar haveli and daman and diu": (20.18, 73.01),
    "karnataka": (12.97, 77.59),
    "tamil nadu": (13.08, 80.27),
    "andhra pradesh": (16.51, 80.52),
    "telangana": (17.38, 78.47),
    "kerala": (8.52, 76.94),
    "puducherry": (11.94, 79.81), "pondicherry": (11.94, 79.81),
    "lakshadweep": (10.57, 72.64),
    "andaman and nicobar islands": (11.67, 92.74), "andaman & nicobar": (11.67, 92.74),
}


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Haversine distance in km."""
    R = 6371  # Earth radius km
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
    c = 2 * math.asin(math.sqrt(a))
    return R * c


def run(df: pd.DataFrame, config: dict) -> pd.DataFrame:
    print_step_header(5, "Derived Fields — region, coastal_city, distance_to_state_capital")

    state_to_region = config["STATE_TO_REGION"]
    coastal_states = {s.lower() for s in config["COASTAL_STATES"]}

    regions = []
    coastals = []
    distances = []
    state_vals = []

    lat_vals = pd.to_numeric(df["latitude"], errors="coerce")
    lon_vals = pd.to_numeric(df["longitude"], errors="coerce")

    for i, state in enumerate(df["state_original"]):
        if not isinstance(state, str) or not state.strip():
            regions.append(None)
            coastals.append(None)
            distances.append(None)
            state_vals.append(None)
            continue

        state_n = normalize_state(state)
        state_vals.append(state)
        regions.append(state_to_region.get(state_n))
        coastals.append(state_n in coastal_states)

        # Distance to state capital
        cap_coords = CAPITAL_COORDS.get(state_n)
        lat, lon = lat_vals.iloc[i], lon_vals.iloc[i]
        if cap_coords and pd.notna(lat) and pd.notna(lon):
            dist = _haversine_km(float(lat), float(lon), cap_coords[0], cap_coords[1])
            distances.append(round(dist, 2))
        else:
            distances.append(None)

    df["state"] = state_vals
    df["region"] = regions
    df["geographic_region"] = regions
    df["coastal_city"] = coastals
    df["distance_to_state_capital"] = distances

    # Backward compat
    df["is_coastal"] = coastals

    total = len(df)
    region_resolved = df["geographic_region"].notna().sum()
    coastal_true = (df["coastal_city"] == True).sum()
    dist_filled = df["distance_to_state_capital"].notna().sum()

    print(f"\n  geographic_region resolved : {region_resolved:,} / {total:,}")
    print(f"  coastal_city=True          : {coastal_true:,}")
    print(f"  distance_to_state_capital : {dist_filled:,} (with lat/lon)")

    print_value_counts(df, "geographic_region")
    coverage_report(df, ["geographic_region", "coastal_city", "distance_to_state_capital"])
    save_checkpoint(df, config["PATHS"]["checkpoints"], step=5)
    return df
