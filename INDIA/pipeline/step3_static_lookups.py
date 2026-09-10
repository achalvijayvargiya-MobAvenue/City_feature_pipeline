"""
step3_static_lookups.py
─────────────────────────────────────────────────────────────────────────────
Applies hardcoded, authoritative lookups for classification fields.
Aligned with InputData/feature_list.txt — all binary/categorical features
from predefined lists.

Fills:
  city_tier, is_metro_city, is_smart_city, is_state_capital, is_union_territory_capital
  has_airport, has_international_airport, has_metro_rail, has_seaport
  major_railway_station, is_it_hub, is_manufacturing_hub, is_financial_center
  is_textile_hub, is_education_hub, is_tourist_city
  internet_penetration_state, smartphone_penetration_state, consumer_price_index, median_age_estimate
  income_bucket, digital_payment_index, avg_property_price
"""
import os
import pandas as pd
from utils import normalize_name, normalize_state, print_step_header, coverage_report, print_value_counts, save_checkpoint, save_step_lost

# State name aliases for lookup (normalized form -> canonical key in CSV)
STATE_ALIASES = {
    "jammu kashmir": "jammu and kashmir",
    "orissa": "odisha",
    "pondicherry": "puducherry",
    "andaman nicobar": "andaman and nicobar islands",
    "andaman and nicobar": "andaman and nicobar islands",
    "nct delhi": "delhi",
    "national capital territory of delhi": "delhi",
    "dadra nagar haveli": "dadra and nagar haveli and daman and diu",
    "dadra and nagar haveli": "dadra and nagar haveli and daman and diu",
    "daman and diu": "dadra and nagar haveli and daman and diu",
    "daman diu": "dadra and nagar haveli and daman and diu",
}


def _to_set(items) -> set:
    """Convert config list/set to normalized set."""
    return {normalize_name(str(x)) for x in items}


def _resolve_state(state_norm: str) -> str:
    """Resolve state alias to canonical key for lookup."""
    return STATE_ALIASES.get(state_norm, state_norm)


def _load_state_lookups(paths: dict) -> dict:
    """Load state-level CSVs into {state_norm -> value} lookups."""
    result = {
        "internet": {},
        "smartphone": {},
        "cpi": {},
        "median_age": {},
        "income_bucket": {},
        "digital_payment": {},
    }
    # Internet penetration
    p = paths.get("state_internet")
    if p and os.path.exists(p):
        df = pd.read_csv(p, dtype=str)
        for _, r in df.iterrows():
            s = (r.get("state") or "").strip()
            if s:
                k = normalize_state(s)
                v = pd.to_numeric(r.get("internet_penetration_pct"), errors="coerce")
                if pd.notna(v):
                    result["internet"][k] = float(v)
    # Smartphone penetration
    p = paths.get("state_smartphone")
    if p and os.path.exists(p):
        df = pd.read_csv(p, dtype=str)
        for _, r in df.iterrows():
            s = (r.get("state") or "").strip()
            if s:
                k = normalize_state(s)
                v = pd.to_numeric(r.get("smartphone_penetration_pct"), errors="coerce")
                if pd.notna(v):
                    result["smartphone"][k] = float(v)
    # CPI
    p = paths.get("state_cpi")
    if p and os.path.exists(p):
        df = pd.read_csv(p, dtype=str)
        for _, r in df.iterrows():
            s = (r.get("state") or "").strip()
            if s:
                k = normalize_state(s)
                v = pd.to_numeric(r.get("cpi_combined"), errors="coerce")
                if pd.notna(v):
                    result["cpi"][k] = float(v)
    # Median age
    p = paths.get("state_median_age")
    if p and os.path.exists(p):
        df = pd.read_csv(p, dtype=str)
        for _, r in df.iterrows():
            s = (r.get("state") or "").strip()
            if s:
                k = normalize_state(s)
                v = pd.to_numeric(r.get("median_age_years"), errors="coerce")
                if pd.notna(v):
                    result["median_age"][k] = float(v)
    # Income bucket
    p = paths.get("state_income")
    if p and os.path.exists(p):
        df = pd.read_csv(p, dtype=str)
        for _, r in df.iterrows():
            s = (r.get("state") or "").strip()
            if s:
                k = normalize_state(s)
                v = (r.get("income_bucket") or "").strip()
                if v:
                    result["income_bucket"][k] = v
    # Digital payment index
    p = paths.get("state_digital")
    if p and os.path.exists(p):
        df = pd.read_csv(p, dtype=str)
        for _, r in df.iterrows():
            s = (r.get("state") or "").strip()
            if s:
                k = normalize_state(s)
                v = pd.to_numeric(r.get("digital_payment_index"), errors="coerce")
                if pd.notna(v):
                    result["digital_payment"][k] = float(v)
    return result


def _load_city_property_lookup(path: str) -> dict:
    """Load city -> price_per_sqft lookup. Keys are normalized city names."""
    lookup = {}
    if not path or not os.path.exists(path):
        return lookup
    df = pd.read_csv(path, dtype=str)
    for _, r in df.iterrows():
        city = (r.get("city") or "").strip()
        if not city:
            continue
        # Use price_per_sqft_approx for avg_property_price
        v = pd.to_numeric(r.get("price_per_sqft_approx"), errors="coerce")
        if pd.notna(v):
            k = normalize_name(city)
            lookup[k] = float(v)
    return lookup


def run(df: pd.DataFrame, config: dict) -> pd.DataFrame:
    print_step_header(4, "Static Lookups — all binary/categorical features")

    metro_set = _to_set(config.get("METRO_CITIES", []))
    tier2_set = config.get("TIER2_CITIES", set())
    if not isinstance(tier2_set, set):
        tier2_set = set(tier2_set) if tier2_set else set()
    tier2_set = _to_set(tier2_set)

    smart_set = _to_set(config.get("SMART_CITIES", []))
    state_cap_set = _to_set(config.get("STATE_CAPITALS", []))
    ut_cap_set = _to_set(config.get("UT_CAPITALS", []))

    airport_set = _to_set(config.get("CITIES_WITH_AIRPORT", []))
    intl_airport_set = _to_set(config.get("CITIES_WITH_INTERNATIONAL_AIRPORT", []))
    metro_rail_set = _to_set(config.get("CITIES_WITH_METRO_RAIL", []))
    seaport_set = _to_set(config.get("CITIES_WITH_SEAPORT", []))
    railway_set = _to_set(config.get("MAJOR_RAILWAY_STATION", []))
    it_hub_set = _to_set(config.get("IT_HUB_CITIES", []))
    mfg_hub_set = _to_set(config.get("MANUFACTURING_HUB_CITIES", []))
    fin_center_set = _to_set(config.get("FINANCIAL_CENTER_CITIES", []))
    textile_set = _to_set(config.get("TEXTILE_HUB_CITIES", []))
    edu_hub_set = _to_set(config.get("EDUCATION_HUB_CITIES", []))
    tourist_set = _to_set(config.get("TOURIST_CITIES", []))

    cities = df["city_normalized"].fillna("").tolist()
    n = len(cities)

    city_tier = []
    is_metro_city = []
    is_smart_city = []
    is_state_capital = []
    is_union_territory_capital = []
    has_airport = []
    has_international_airport = []
    has_metro_rail = []
    has_seaport = []
    major_railway_station = []
    is_it_hub = []
    is_manufacturing_hub = []
    is_financial_center = []
    is_textile_hub = []
    is_education_hub = []
    is_tourist_city = []

    for i in range(n):
        city_n = normalize_name(cities[i]) if cities[i] else ""

        # city_tier: Tier 1 (metro) | Tier 2 | Tier 3
        if city_n in metro_set:
            city_tier.append("Tier 1")
        elif city_n in tier2_set:
            city_tier.append("Tier 2")
        else:
            city_tier.append("Tier 3")

        is_metro_city.append(city_n in metro_set)
        is_smart_city.append(city_n in smart_set)
        is_state_capital.append(city_n in state_cap_set)
        is_union_territory_capital.append(city_n in ut_cap_set)
        has_airport.append(city_n in airport_set)
        has_international_airport.append(city_n in intl_airport_set)
        has_metro_rail.append(city_n in metro_rail_set)
        has_seaport.append(city_n in seaport_set)
        major_railway_station.append(city_n in railway_set)
        is_it_hub.append(city_n in it_hub_set)
        is_manufacturing_hub.append(city_n in mfg_hub_set)
        is_financial_center.append(city_n in fin_center_set)
        is_textile_hub.append(city_n in textile_set)
        is_education_hub.append(city_n in edu_hub_set)
        is_tourist_city.append(city_n in tourist_set)

    df["city_tier"] = city_tier
    df["is_metro_city"] = is_metro_city
    df["is_smart_city"] = is_smart_city
    df["is_state_capital"] = is_state_capital
    df["is_union_territory_capital"] = is_union_territory_capital
    df["has_airport"] = has_airport
    df["has_international_airport"] = has_international_airport
    df["has_metro_rail"] = has_metro_rail
    df["has_seaport"] = has_seaport
    df["major_railway_station"] = major_railway_station
    df["is_it_hub"] = is_it_hub
    df["is_manufacturing_hub"] = is_manufacturing_hub
    df["is_financial_center"] = is_financial_center
    df["is_textile_hub"] = is_textile_hub
    df["is_education_hub"] = is_education_hub
    df["is_tourist_city"] = is_tourist_city

    # State-level lookups (internet, smartphone, CPI, median age, income, digital payment)
    paths = config.get("PATHS", {})
    state_lookups = _load_state_lookups(paths)
    city_property = _load_city_property_lookup(paths.get("city_property"))

    internet_col = []
    smartphone_col = []
    cpi_col = []
    median_age_col = []
    income_col = []
    digital_col = []
    property_col = []

    for i in range(len(df)):
        row = df.iloc[i]
        state_raw = (row.get("state_original") or "").strip()
        state_key = _resolve_state(normalize_state(state_raw)) if state_raw else ""
        internet_col.append(state_lookups["internet"].get(state_key))
        smartphone_col.append(state_lookups["smartphone"].get(state_key))
        cpi_col.append(state_lookups["cpi"].get(state_key))
        median_age_col.append(state_lookups["median_age"].get(state_key))
        income_col.append(state_lookups["income_bucket"].get(state_key))
        digital_col.append(state_lookups["digital_payment"].get(state_key))

        # City-level property: try city_normalized, then major_city
        city_n = normalize_name(row.get("city_normalized") or "")
        major_n = normalize_name(row.get("major_city") or "")
        prop_val = city_property.get(city_n) or city_property.get(major_n)
        property_col.append(prop_val)

    df["internet_penetration_state"] = internet_col
    df["smartphone_penetration_state"] = smartphone_col
    df["consumer_price_index"] = cpi_col
    df["median_age_estimate"] = median_age_col
    df["income_bucket"] = income_col
    df["digital_payment_index"] = digital_col
    df["avg_property_price"] = property_col

    # Placeholder columns (no data source yet)
    for col in ["city_population"]:
        if col not in df.columns:
            df[col] = None

    # Summary
    print(f"\n  is_metro_city=True        : {sum(is_metro_city):,}")
    print(f"  is_smart_city=True        : {sum(is_smart_city):,}")
    print(f"  is_state_capital=True     : {sum(is_state_capital):,}")
    print(f"  is_union_territory_capital: {sum(is_union_territory_capital):,}")
    print(f"  has_airport=True          : {sum(has_airport):,}")
    print(f"  has_international_airport : {sum(has_international_airport):,}")
    print(f"  has_metro_rail=True       : {sum(has_metro_rail):,}")
    print(f"  has_seaport=True          : {sum(has_seaport):,}")
    print(f"  major_railway_station=True : {sum(major_railway_station):,}")
    print(f"  is_it_hub=True            : {sum(is_it_hub):,}")
    print(f"  is_tourist_city=True      : {sum(is_tourist_city):,}")

    # State/city lookup summary
    filled_internet = df["internet_penetration_state"].notna().sum()
    filled_smartphone = df["smartphone_penetration_state"].notna().sum()
    filled_cpi = df["consumer_price_index"].notna().sum()
    filled_median_age = df["median_age_estimate"].notna().sum()
    filled_income = df["income_bucket"].notna().sum()
    filled_digital = df["digital_payment_index"].notna().sum()
    filled_property = df["avg_property_price"].notna().sum()
    print(f"\n  internet_penetration_state filled : {filled_internet:,} / {len(df):,}")
    print(f"  smartphone_penetration_state filled: {filled_smartphone:,} / {len(df):,}")
    print(f"  consumer_price_index filled  : {filled_cpi:,} / {len(df):,}")
    print(f"  median_age_estimate filled  : {filled_median_age:,} / {len(df):,}")
    print(f"  income_bucket filled        : {filled_income:,} / {len(df):,}")
    print(f"  digital_payment_index filled: {filled_digital:,} / {len(df):,}")
    print(f"  avg_property_price filled   : {filled_property:,} / {len(df):,} (city-level)")

    print_value_counts(df, "city_tier")
    print_value_counts(df, "income_bucket")
    coverage_report(df, ["city_tier", "is_metro_city", "is_smart_city", "is_state_capital",
                        "has_airport", "has_metro_rail", "is_it_hub",
                        "internet_penetration_state", "smartphone_penetration_state",
                        "consumer_price_index", "median_age_estimate",
                        "income_bucket", "digital_payment_index", "avg_property_price"])

    # No rows removed at this step
    save_step_lost(4, [], config)

    save_checkpoint(df, config["PATHS"]["checkpoints"], step=4)
    return df
