import pytest
import pandas as pd
from usa_city_features.validation.schema_validator import (
    REQUIRED_COLUMNS,
    validate_schema,
    validate_ranges,
    generate_quality_report
)

def get_valid_36_col_df():
    # Build a 1-row valid dataframe
    data = {}
    for col in REQUIRED_COLUMNS:
        data[col] = [None]
        
    df = pd.DataFrame(data)
    
    # Fill in valid mock data
    df["#"] = [1]
    df["pincode"] = ["90210"]
    df["state_original"] = ["CA"]
    df["major_city"] = ["Beverly Hills"]
    df["latitude"] = [34.07]
    df["longitude"] = [-118.40]
    df["region"] = ["West"]
    df["coastal_city"] = [True]
    df["distance_to_state_capital"] = [500.0]
    df["city_tier"] = ["T2"]
    df["is_metro_city"] = [True]
    df["is_smart_city"] = [False]
    df["is_state_capital"] = [False]
    df["is_union_territory_capital"] = [False]
    df["literacy_rate"] = [95.5]
    df["median_age_estimate"] = [45.0]
    df["consumer_price_index"] = [250.0]
    df["income_bucket"] = ["VH"]
    df["has_airport"] = [True]
    df["has_international_airport"] = [True]
    df["has_metro_rail"] = [False]
    df["has_seaport"] = [False]
    df["major_railway_station"] = [False]
    df["internet_penetration_state"] = [85.0]
    df["smartphone_penetration_state"] = [90.0]
    df["digital_payment_index"] = [80.0]
    df["is_it_hub"] = [False]
    df["is_manufacturing_hub"] = [False]
    df["is_financial_center"] = [False]
    df["is_textile_hub"] = [False]
    df["is_education_hub"] = [False]
    df["is_tourist_city"] = [True]
    df["is_coastal"] = [True]
    df["district_population_numeric"] = [10000000.0]
    df["district_population"] = [">10M"]
    df["sex_ratio"] = [105.0]
    
    return df

def test_validate_schema_valid():
    df = get_valid_36_col_df()
    assert validate_schema(df) == True

def test_validate_schema_fails_35_cols():
    df = get_valid_36_col_df()
    df = df.drop(columns=["sex_ratio"])
    assert len(df.columns) == 35
    assert validate_schema(df) == False

def test_validate_schema_fails_wrong_type():
    df = get_valid_36_col_df()
    # Pincode must be string, let's make it int
    df["pincode"] = [90210]
    assert validate_schema(df) == False

def test_validate_ranges_catches_latitude():
    df = get_valid_36_col_df()
    df["latitude"] = [150.0]  # Invalid latitude
    errors = validate_ranges(df)
    
    assert "latitude" in errors
    assert errors["latitude"] == 1
    assert "longitude" not in errors

def test_generate_quality_report():
    df = get_valid_36_col_df()
    # Introduce a null
    df.loc[0, "literacy_rate"] = None
    
    report = generate_quality_report(df)
    assert report["total_records"] == 1
    assert report["null_count_by_column"]["literacy_rate"] == 1
    assert report["coverage_percentages"]["literacy_rate"] == 0.0
    assert report["coverage_percentages"]["latitude"] == 100.0
