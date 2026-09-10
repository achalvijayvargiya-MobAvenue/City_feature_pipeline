import pandas as pd
from typing import List, Dict, Any

REQUIRED_COLUMNS = [
    "#",
    "pincode",
    "state_original",
    "major_city",
    "latitude",
    "longitude",
    "region",
    "coastal_city",
    "distance_to_state_capital",
    "city_tier",
    "is_metro_city",
    "is_smart_city",
    "is_state_capital",
    "is_union_territory_capital",
    "literacy_rate",
    "median_age_estimate",
    "consumer_price_index",
    "income_bucket",
    "has_airport",
    "has_international_airport",
    "has_metro_rail",
    "has_seaport",
    "major_railway_station",
    "internet_penetration_state",
    "smartphone_penetration_state",
    "digital_payment_index",
    "is_it_hub",
    "is_manufacturing_hub",
    "is_financial_center",
    "is_textile_hub",
    "is_education_hub",
    "is_tourist_city",
    "is_coastal",
    "district_population_numeric",
    "district_population",
    "sex_ratio"
]

def validate_schema(df: pd.DataFrame) -> bool:
    """Check if dataframe has exactly the required 36 columns in order."""
    if len(df.columns) != 36:
        return False
    
    for i, col in enumerate(REQUIRED_COLUMNS):
        if df.columns[i] != col:
            return False
            
    return True

def validate_ranges(df: pd.DataFrame) -> Dict[str, int]:
    """Check numeric ranges and return count of errors per column."""
    errors = {}
    
    if "latitude" in df.columns:
        errors["latitude"] = (~df["latitude"].between(-90, 90)).sum()
        
    if "longitude" in df.columns:
        errors["longitude"] = (~df["longitude"].between(-180, 180)).sum()
        
    if "median_age_estimate" in df.columns:
        errors["median_age_estimate"] = (df["median_age_estimate"] <= 0).sum()
        
    if "internet_penetration_state" in df.columns:
        errors["internet_penetration_state"] = (~df["internet_penetration_state"].between(0, 100)).sum()
        
    if "smartphone_penetration_state" in df.columns:
        errors["smartphone_penetration_state"] = (~df["smartphone_penetration_state"].between(0, 100)).sum()
        
    if "digital_payment_index" in df.columns:
        errors["digital_payment_index"] = (~df["digital_payment_index"].between(0, 100)).sum()
        
    if "sex_ratio" in df.columns:
        errors["sex_ratio"] = (df["sex_ratio"] < 0).sum()
        
    if "distance_to_state_capital" in df.columns:
        errors["distance_to_state_capital"] = (df["distance_to_state_capital"] < 0).sum()
        
    return {k: int(v) for k, v in errors.items() if v > 0}

def generate_quality_report(df: pd.DataFrame) -> Dict[str, Any]:
    """Generate a quality report for the dataset."""
    total_records = len(df)
    
    null_counts = df.isnull().sum().to_dict()
    range_errors = validate_ranges(df)
    
    # A record is valid if it has no nulls in critical fields and no range errors
    # For simplicity, we'll just count records without nulls in pincode, lat, lon
    valid_records = df.dropna(subset=["pincode", "latitude", "longitude"]).shape[0]
    
    return {
        "total_records": total_records,
        "valid_records": valid_records,
        "invalid_records": total_records - valid_records,
        "null_count_by_column": {k: int(v) for k, v in null_counts.items()},
        "range_errors_by_column": range_errors
    }
