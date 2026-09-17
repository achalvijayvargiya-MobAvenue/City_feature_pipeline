import pandas as pd
from typing import List, Dict, Any, Tuple
import numpy as np

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

# USA has no union territories; this column is always False and excluded from completeness.
EXCLUDED_FROM_COMPLETENESS = {"is_union_territory_capital"}

# Values treated as missing / incomplete for final production data
MISSING_STRING_TOKENS = {
    "", "nan", "none", "null", "unknown", "n/a", "na", "<na>", "nat"
}


def _is_missing_value(value: Any) -> bool:
    if value is None:
        return True
    try:
        if pd.isna(value):
            return True
    except (TypeError, ValueError):
        pass
    if isinstance(value, str):
        return value.strip().lower() in MISSING_STRING_TOKENS
    return False


def completeness_columns(df: pd.DataFrame) -> List[str]:
    """Columns that must be populated for a USA record to be final/valid."""
    return [
        c for c in df.columns
        if c != "#" and c not in EXCLUDED_FROM_COMPLETENESS
    ]


def missing_columns_for_row(row: pd.Series, columns: List[str]) -> List[str]:
    return [c for c in columns if _is_missing_value(row.get(c))]


def split_complete_records(df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame, Dict[str, Any]]:
    """
    Split into:
      - valid: every required field populated (except is_union_territory_capital)
      - invalid: any blank/unknown field; includes missing_columns for enrichment
    """
    work = df.copy()
    cols = completeness_columns(work)

    missing_matrix = pd.DataFrame(False, index=work.index, columns=cols)
    for col in cols:
        series = work[col]
        miss = series.isna()
        if series.dtype == object or pd.api.types.is_string_dtype(series):
            normalized = series.astype(str).str.strip().str.lower()
            miss = miss | normalized.isin(MISSING_STRING_TOKENS)
        missing_matrix[col] = miss

    missing_lists = missing_matrix.apply(
        lambda row: ";".join(missing_matrix.columns[row.values]),
        axis=1,
    )
    valid_mask = ~missing_matrix.any(axis=1)

    valid_df = work.loc[valid_mask].copy()
    invalid_df = work.loc[~valid_mask].copy()
    invalid_df["missing_columns"] = missing_lists.loc[~valid_mask].values

    if "#" in valid_df.columns:
        valid_df["#"] = range(1, len(valid_df) + 1)
    if "#" in invalid_df.columns:
        invalid_df["#"] = range(1, len(invalid_df) + 1)

    missing_freq: Dict[str, int] = {
        col: int(missing_matrix.loc[~valid_mask, col].sum())
        for col in cols
        if int(missing_matrix.loc[~valid_mask, col].sum()) > 0
    }
    missing_freq = dict(sorted(missing_freq.items(), key=lambda x: (-x[1], x[0])))

    summary = {
        "total_records": int(len(work)),
        "valid_complete_records": int(len(valid_df)),
        "invalid_incomplete_records": int(len(invalid_df)),
        "excluded_from_completeness": sorted(EXCLUDED_FROM_COMPLETENESS),
        "required_columns": cols,
        "invalid_missing_field_frequency": missing_freq,
    }
    return valid_df, invalid_df, summary


def generate_quality_report(df: pd.DataFrame) -> Dict[str, Any]:
    """Generate a quality report for the dataset."""
    total_records = len(df)

    null_counts = {}
    for col in df.columns:
        series = df[col]
        miss = series.isna()
        if series.dtype == object or pd.api.types.is_string_dtype(series):
            normalized = series.astype(str).str.strip().str.lower()
            miss = miss | normalized.isin(MISSING_STRING_TOKENS)
        null_counts[col] = int(miss.sum())

    range_errors = validate_ranges(df)

    coverage_percentages = {}
    if total_records > 0:
        for col, nulls in null_counts.items():
            coverage_percentages[col] = round(((total_records - nulls) / total_records) * 100, 2)

    _, _, split_summary = split_complete_records(df)

    return {
        "total_records": total_records,
        "valid_records": split_summary["valid_complete_records"],
        "invalid_records": split_summary["invalid_incomplete_records"],
        "null_count_by_column": {k: int(v) for k, v in null_counts.items()},
        "coverage_percentages": coverage_percentages,
        "range_errors_by_column": range_errors,
        "completeness_split": {
            "excluded_from_completeness": split_summary["excluded_from_completeness"],
            "invalid_missing_field_frequency": split_summary["invalid_missing_field_frequency"],
        },
    }
