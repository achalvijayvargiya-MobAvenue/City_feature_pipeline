from typing import Optional, Dict, Any

def calculate_sex_ratio(male_pop: Optional[int], female_pop: Optional[int]) -> Optional[float]:
    if male_pop is None or female_pop is None or female_pop == 0:
        return None
    return (male_pop / female_pop) * 100.0

def calculate_education_rate(pop_25_plus: Optional[int], pop_25_plus_hs_or_higher: Optional[int]) -> Optional[float]:
    if pop_25_plus is None or pop_25_plus_hs_or_higher is None or pop_25_plus == 0:
        return None
    return (pop_25_plus_hs_or_higher / pop_25_plus) * 100.0

def calculate_penetration_rate(total_households: Optional[int], target_households: Optional[int]) -> Optional[float]:
    if total_households is None or target_households is None or total_households == 0:
        return None
    return (target_households / total_households) * 100.0

def get_income_bucket(median_income: Optional[float]) -> Optional[str]:
    if median_income is None or median_income < 0:
        return None
    
    if median_income < 50000:
        return "L"
    elif median_income < 100000:
        return "M"
    elif median_income < 200000:
        return "H"
    else:
        return "VH"

def get_population_bucket(population: Optional[int]) -> Optional[str]:
    if population is None or population < 0:
        return None
    
    if population < 250000:
        return "VS"
    elif population < 500000:
        return "S"
    elif population < 1000000:
        return "M"
    elif population < 5000000:
        return "L"
    else:
        return "VL"

def extract_demographic_features(raw_row: Dict[str, Any], vars_map: Dict[str, str]) -> Dict[str, Any]:
    """
    Extracts and calculates features from a raw Census row using a provided
    variable mapping (e.g. {'population': 'B01003_001E', ...}).
    """
    def safe_int(val):
        try:
            return int(val)
        except (ValueError, TypeError):
            return None
            
    def safe_float(val):
        try:
            return float(val)
        except (ValueError, TypeError):
            return None

    # Get mapped keys
    pop_key = vars_map.get("population")
    age_key = vars_map.get("median_age")
    male_key = vars_map.get("male_population")
    female_key = vars_map.get("female_population")
    income_key = vars_map.get("median_income")
    
    # Education
    pop_25_key = vars_map.get("population_25_plus")
    hs_plus_key = vars_map.get("population_hs_plus")
    
    # Penetration
    total_hh_key = vars_map.get("total_households")
    internet_key = vars_map.get("internet_households")
    smartphone_key = vars_map.get("smartphone_households")

    features = {}
    
    features["district_population_numeric"] = safe_int(raw_row.get(pop_key)) if pop_key else None
    features["median_age_estimate"] = safe_float(raw_row.get(age_key)) if age_key else None
    
    male_pop = safe_int(raw_row.get(male_key)) if male_key else None
    female_pop = safe_int(raw_row.get(female_key)) if female_key else None
    features["sex_ratio"] = calculate_sex_ratio(male_pop, female_pop)
    
    median_income = safe_float(raw_row.get(income_key)) if income_key else None
    features["income_bucket"] = get_income_bucket(median_income)
    
    pop_25 = safe_int(raw_row.get(pop_25_key)) if pop_25_key else None
    hs_plus = safe_int(raw_row.get(hs_plus_key)) if hs_plus_key else None
    features["literacy_rate"] = calculate_education_rate(pop_25, hs_plus)
    
    total_hh = safe_int(raw_row.get(total_hh_key)) if total_hh_key else None
    internet_hh = safe_int(raw_row.get(internet_key)) if internet_key else None
    smartphone_hh = safe_int(raw_row.get(smartphone_key)) if smartphone_key else None
    
    features["internet_penetration_state"] = calculate_penetration_rate(total_hh, internet_hh)
    features["smartphone_penetration_state"] = calculate_penetration_rate(total_hh, smartphone_hh)
    
    return features
