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
"""
import pandas as pd
from utils import normalize_name, print_step_header, coverage_report, print_value_counts, save_checkpoint


def _to_set(items) -> set:
    """Convert config list/set to normalized set."""
    return {normalize_name(str(x)) for x in items}


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

    # Placeholder columns (no data source yet)
    for col in ["national_highway_access", "internet_penetration_state", "smartphone_penetration_state",
                "digital_payment_index", "median_age_estimate", "consumer_price_index",
                "income_bucket", "avg_property_price", "city_population"]:
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

    print_value_counts(df, "city_tier")
    coverage_report(df, ["city_tier", "is_metro_city", "is_smart_city", "is_state_capital",
                        "has_airport", "has_metro_rail", "is_it_hub"])

    save_checkpoint(df, config["PATHS"]["checkpoints"], step=4)
    return df
