from typing import Optional, Dict, Any

def get_city_tier(population: Optional[int], t1_threshold: int = 1000000, t2_threshold: int = 250000) -> str:
    if population is None:
        return "Unknown"
    
    if population >= t1_threshold:
        return "T1"
    elif population >= t2_threshold:
        return "T2"
    else:
        return "T3"

def calculate_digital_payment_index(internet_pen: Optional[float], smartphone_pen: Optional[float], income_bucket: Optional[str], is_metro: bool) -> Optional[float]:
    if internet_pen is None or smartphone_pen is None:
        return None
    
    # Simple scoring mechanism
    income_score = {"VH": 100, "H": 80, "M": 50, "L": 20}.get(income_bucket, 0)
    metro_score = 100 if is_metro else 0
    
    dpi = (0.40 * internet_pen) + (0.35 * smartphone_pen) + (0.15 * income_score) + (0.10 * metro_score)
    return min(max(dpi, 0.0), 100.0)

def calculate_smart_city_score(has_metro: bool, has_airport: bool, internet_pen: Optional[float], smartphone_pen: Optional[float], dpi: Optional[float], is_it_hub: bool) -> float:
    score = 0.0
    if has_metro: score += 20
    if has_airport: score += 10
    if internet_pen: score += (internet_pen * 0.2)
    if smartphone_pen: score += (smartphone_pen * 0.2)
    if dpi: score += (dpi * 0.2)
    if is_it_hub: score += 10
    
    return score

def is_smart_city(score: float, threshold: float = 60.0) -> bool:
    return score >= threshold

def is_industry_hub(industry_employment: Optional[int], total_employment: Optional[int], min_employment: int = 5000, min_share: float = 0.05) -> bool:
    if industry_employment is None or total_employment is None or total_employment == 0:
        return False
    
    share = industry_employment / total_employment
    return industry_employment >= min_employment and share >= min_share

def calculate_tourism_score(has_airport: bool, is_coastal: bool, arts_employment: Optional[int], food_employment: Optional[int], total_employment: Optional[int]) -> float:
    score = 0.0
    if has_airport: score += 20
    if is_coastal: score += 20
    
    if arts_employment and total_employment and total_employment > 0:
        arts_share = arts_employment / total_employment
        if arts_share > 0.02: score += 30
        
    if food_employment and total_employment and total_employment > 0:
        food_share = food_employment / total_employment
        if food_share > 0.10: score += 30
        
    return score

def is_tourist_city(score: float, threshold: float = 50.0) -> bool:
    return score >= threshold
