import pandas as pd
from typing import Dict, Any
import json
from pathlib import Path
from .schema_validator import REQUIRED_COLUMNS, generate_quality_report

def map_to_36_columns(internal_df: pd.DataFrame) -> pd.DataFrame:
    """Map the internal rich dataframe to the exact 36-column schema."""
    out_df = pd.DataFrame()
    
    # 1. #
    out_df["#"] = range(1, len(internal_df) + 1)
    
    # 2. pincode
    out_df["pincode"] = internal_df.get("zcta5", None)
    
    # 3. state_original
    out_df["state_original"] = internal_df.get("state_code", None)
    
    # 4. major_city
    out_df["major_city"] = internal_df.get("place_name", None)
    
    # 5. latitude
    out_df["latitude"] = internal_df.get("latitude", None)
    
    # 6. longitude
    out_df["longitude"] = internal_df.get("longitude", None)
    
    # 7. region
    out_df["region"] = internal_df.get("region", None)
    
    # 8. coastal_city
    out_df["coastal_city"] = internal_df.get("is_coastal", False)
    
    # 9. distance_to_state_capital
    out_df["distance_to_state_capital"] = internal_df.get("distance_to_state_capital_km", None)
    
    # 10. city_tier
    out_df["city_tier"] = internal_df.get("city_tier", "Unknown")
    
    # 11. is_metro_city
    out_df["is_metro_city"] = internal_df.get("is_metro_city", False)
    
    # 12. is_smart_city
    out_df["is_smart_city"] = internal_df.get("is_smart_city", False)
    
    # 13. is_state_capital
    out_df["is_state_capital"] = internal_df.get("is_state_capital", False)
    
    # 14. is_union_territory_capital (always false for USA)
    out_df["is_union_territory_capital"] = False
    
    # 15. literacy_rate
    out_df["literacy_rate"] = internal_df.get("education_rate", None)
    
    # 16. median_age_estimate
    out_df["median_age_estimate"] = internal_df.get("median_age", None)
    
    # 17. consumer_price_index
    out_df["consumer_price_index"] = internal_df.get("cpi_value", None)
    
    # 18. income_bucket
    out_df["income_bucket"] = internal_df.get("income_bucket", None)
    
    # 19. has_airport
    out_df["has_airport"] = internal_df.get("has_airport", False)
    
    # 20. has_international_airport
    out_df["has_international_airport"] = internal_df.get("has_international_airport", False)
    
    # 21. has_metro_rail
    out_df["has_metro_rail"] = internal_df.get("has_metro_rail", False)
    
    # 22. has_seaport
    out_df["has_seaport"] = internal_df.get("has_seaport", False)
    
    # 23. major_railway_station
    out_df["major_railway_station"] = internal_df.get("major_railway_station", False)
    
    # 24. internet_penetration_state
    out_df["internet_penetration_state"] = internal_df.get("internet_penetration", None)
    
    # 25. smartphone_penetration_state
    out_df["smartphone_penetration_state"] = internal_df.get("smartphone_penetration", None)
    
    # 26. digital_payment_index
    out_df["digital_payment_index"] = internal_df.get("digital_payment_index", None)
    
    # 27. is_it_hub
    out_df["is_it_hub"] = internal_df.get("is_it_hub", False)
    
    # 28. is_manufacturing_hub
    out_df["is_manufacturing_hub"] = internal_df.get("is_manufacturing_hub", False)
    
    # 29. is_financial_center
    out_df["is_financial_center"] = internal_df.get("is_financial_center", False)
    
    # 30. is_textile_hub
    out_df["is_textile_hub"] = internal_df.get("is_textile_hub", False)
    
    # 31. is_education_hub
    out_df["is_education_hub"] = internal_df.get("is_education_hub", False)
    
    # 32. is_tourist_city
    out_df["is_tourist_city"] = internal_df.get("is_tourist_city", False)
    
    # 33. is_coastal
    out_df["is_coastal"] = internal_df.get("is_coastal", False)
    
    # 34. district_population_numeric
    out_df["district_population_numeric"] = internal_df.get("county_population", None)
    
    # 35. district_population
    out_df["district_population"] = internal_df.get("population_bucket", None)
    
    # 36. sex_ratio
    out_df["sex_ratio"] = internal_df.get("sex_ratio", None)
    
    # Ensure columns are exactly in order and any missing columns from internal_df are added as None
    for col in REQUIRED_COLUMNS:
        if col not in out_df.columns:
            out_df[col] = None
            
    return out_df[REQUIRED_COLUMNS]

def export_dataset(df: pd.DataFrame, output_path: str, report_path: str) -> None:
    """Export the mapped dataframe and generate quality report."""
    # Ensure directory exists
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    Path(report_path).parent.mkdir(parents=True, exist_ok=True)
    
    # Export CSV
    df.to_csv(output_path, index=False)
    
    # Generate and export report
    report = generate_quality_report(df)
    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2)
