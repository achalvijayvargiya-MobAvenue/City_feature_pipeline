import yaml
from pathlib import Path
from typing import Optional, Dict, Any

# Load thresholds from config
config_path = Path(__file__).resolve().parents[3] / "configs" / "thresholds.yaml"
try:
    with open(config_path, "r") as f:
        THRESHOLDS = yaml.safe_load(f)
except Exception:
    THRESHOLDS = {}

HUB_MIN_EMP = THRESHOLDS.get("industry_hub", {}).get("minimum_employment", 5000)
HUB_MIN_SHARE = THRESHOLDS.get("industry_hub", {}).get("minimum_share", 0.05)
T1_MIN_POP = THRESHOLDS.get("city_tier", {}).get("t1_min_population", 1000000)
T2_MIN_POP = THRESHOLDS.get("city_tier", {}).get("t2_min_population", 250000)

def get_city_tier(population: Optional[int]) -> str:
    if population is None:
        return "Unknown"
    
    if population >= T1_MIN_POP:
        return "T1"
    elif population >= T2_MIN_POP:
        return "T2"
    else:
        return "T3"

def calculate_digital_payment_index(internet_pen: Optional[float], smartphone_pen: Optional[float], income_bucket: Optional[str], is_metro: bool) -> float:
    # Handle None gracefully by defaulting to 0.0
    internet_pen = internet_pen or 0.0
    smartphone_pen = smartphone_pen or 0.0
    
    # Simple scoring mechanism
    income_score = {"VH": 100, "H": 80, "M": 50, "L": 20}.get(income_bucket, 0)
    metro_score = 100 if is_metro else 0
    
    dpi = (0.40 * internet_pen) + (0.35 * smartphone_pen) + (0.15 * income_score) + (0.10 * metro_score)
    return min(max(dpi, 0.0), 100.0)

def calculate_smart_city_score(has_metro: bool, has_airport: bool, internet_pen: Optional[float], smartphone_pen: Optional[float], dpi: Optional[float], is_it_hub: bool) -> float:
    score = 0.0
    if has_metro: score += 20.0
    if has_airport: score += 10.0
    score += (internet_pen or 0.0) * 0.2
    score += (smartphone_pen or 0.0) * 0.2
    score += (dpi or 0.0) * 0.2
    if is_it_hub: score += 10.0
    
    return score

def is_smart_city(score: float, threshold: float = 60.0) -> bool:
    return score >= threshold

def is_industry_hub(industry_employment: Optional[int], total_employment: Optional[int], min_employment: int = HUB_MIN_EMP, min_share: float = HUB_MIN_SHARE) -> bool:
    if industry_employment is None or total_employment is None or total_employment == 0:
        return False
    
    share = industry_employment / total_employment
    return industry_employment >= min_employment and share >= min_share

def is_it_hub(it_employment: Optional[int], total_employment: Optional[int]) -> bool:
    return is_industry_hub(it_employment, total_employment)

def is_manufacturing_hub(mfg_employment: Optional[int], total_employment: Optional[int]) -> bool:
    return is_industry_hub(mfg_employment, total_employment)

def calculate_tourism_score(has_airport: bool, is_coastal: bool, arts_employment: Optional[int], food_employment: Optional[int], total_employment: Optional[int]) -> float:
    score = 0.0
    if has_airport: score += 20.0
    if is_coastal: score += 20.0
    
    if arts_employment and total_employment and total_employment > 0:
        arts_share = arts_employment / total_employment
        if arts_share > 0.02: score += 30.0
        
    if food_employment and total_employment and total_employment > 0:
        food_share = food_employment / total_employment
        if food_share > 0.10: score += 30.0
        
    return score

def is_tourist_city(score: float, threshold: float = 50.0) -> bool:
    return score >= threshold
