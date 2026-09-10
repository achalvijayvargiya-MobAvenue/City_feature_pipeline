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
