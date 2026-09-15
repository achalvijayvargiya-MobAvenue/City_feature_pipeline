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

STRING_COLS = ["pincode", "state_original", "major_city", "region", "city_tier", "income_bucket", "district_population"]
FLOAT_COLS = ["latitude", "longitude", "distance_to_state_capital", "literacy_rate", "median_age_estimate", 
                "consumer_price_index", "internet_penetration_state", "smartphone_penetration_state", 
                "digital_payment_index", "sex_ratio", "district_population_numeric"]
BOOL_COLS = ["coastal_city", "is_metro_city", "is_smart_city", "is_state_capital", "is_union_territory_capital", 
                "has_airport", "has_international_airport", "has_metro_rail", "has_seaport", "major_railway_station",
                "is_it_hub", "is_manufacturing_hub", "is_financial_center", "is_textile_hub", "is_education_hub", 
                "is_tourist_city", "is_coastal"]

def validate_schema(df: pd.DataFrame) -> bool:
    """Check if dataframe has exactly the required 36 columns in order, and strictly check types."""
    if len(df.columns) != 36:
        return False
    
    for i, col in enumerate(REQUIRED_COLUMNS):
        if df.columns[i] != col:
            return False
            
    # Strict type checking
    for col in STRING_COLS:
        non_nulls = df[col].dropna()
        if len(non_nulls) > 0 and not all(isinstance(x, str) for x in non_nulls):
            return False
            
    for col in FLOAT_COLS:
        non_nulls = df[col].dropna()
        if len(non_nulls) > 0 and not all(isinstance(x, (float, int)) for x in non_nulls):
            return False
            
    for col in BOOL_COLS:
        non_nulls = df[col].dropna()
        if len(non_nulls) > 0 and not all(isinstance(x, bool) for x in non_nulls):
            return False
            
    return True

def validate_ranges(df: pd.DataFrame) -> Dict[str, int]:
    """Check numeric ranges and return count of errors per column."""
    errors = {}
    
    # We must drop nulls before checking range to avoid False errors with pandas NA/None
    if "latitude" in df.columns:
        valid_mask = df["latitude"].dropna().between(-90, 90)
        errors["latitude"] = (~valid_mask).sum()
        
    if "longitude" in df.columns:
        valid_mask = df["longitude"].dropna().between(-180, 180)
        errors["longitude"] = (~valid_mask).sum()
        
    if "median_age_estimate" in df.columns:
        valid_mask = (df["median_age_estimate"].dropna() > 0)
        errors["median_age_estimate"] = (~valid_mask).sum()
        
    if "internet_penetration_state" in df.columns:
        valid_mask = df["internet_penetration_state"].dropna().between(0, 100)
        errors["internet_penetration_state"] = (~valid_mask).sum()
        
    if "smartphone_penetration_state" in df.columns:
        valid_mask = df["smartphone_penetration_state"].dropna().between(0, 100)
        errors["smartphone_penetration_state"] = (~valid_mask).sum()
        
    if "digital_payment_index" in df.columns:
        valid_mask = df["digital_payment_index"].dropna().between(0, 100)
        errors["digital_payment_index"] = (~valid_mask).sum()
        
    if "sex_ratio" in df.columns:
        valid_mask = (df["sex_ratio"].dropna() >= 0)
        errors["sex_ratio"] = (~valid_mask).sum()
        
    if "distance_to_state_capital" in df.columns:
        valid_mask = (df["distance_to_state_capital"].dropna() >= 0)
        errors["distance_to_state_capital"] = (~valid_mask).sum()
        
    return {k: int(v) for k, v in errors.items() if v > 0}

def generate_quality_report(df: pd.DataFrame) -> Dict[str, Any]:
    """Generate a quality report for the dataset."""
    total_records = len(df)
    
    null_counts = df.isnull().sum().to_dict()
    range_errors = validate_ranges(df)
    
    coverage_percentages = {}
    if total_records > 0:
        for col, nulls in null_counts.items():
            coverage_percentages[col] = round(((total_records - nulls) / total_records) * 100, 2)
    
    # A record is valid if it has no nulls in critical fields and no range errors
    valid_records = df.dropna(subset=["pincode", "latitude", "longitude"]).shape[0]
    
    return {
        "total_records": total_records,
        "valid_records": valid_records,
        "invalid_records": total_records - valid_records,
        "null_count_by_column": {k: int(v) for k, v in null_counts.items()},
        "coverage_percentages": coverage_percentages,
        "range_errors_by_column": range_errors
    }
