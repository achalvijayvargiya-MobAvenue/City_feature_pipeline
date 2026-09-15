import pytest
from usa_city_features.features.derived_features import (
    is_it_hub,
    is_manufacturing_hub,
    calculate_digital_payment_index,
    calculate_smart_city_score
)

def test_is_it_hub_true():
    # 6000 IT jobs, 100000 total jobs. 
    # 6000 >= 5000 (min_employment)
    # 6000 / 100000 = 0.06 >= 0.05 (min_share)
    assert is_it_hub(6000, 100000) == True

def test_is_it_hub_fails_min_employment():
    # 4000 IT jobs, 40000 total jobs.
    # 4000 < 5000 (fails min_employment)
    # 4000 / 40000 = 0.10 >= 0.05
    assert is_it_hub(4000, 40000) == False

def test_is_it_hub_fails_min_share():
    # 6000 IT jobs, 200000 total jobs.
    # 6000 >= 5000
    # 6000 / 200000 = 0.03 < 0.05 (fails min_share)
    assert is_it_hub(6000, 200000) == False

def test_is_it_hub_none_inputs():
    assert is_it_hub(None, 100000) == False
    assert is_it_hub(6000, None) == False

def test_calculate_digital_payment_index_with_none():
    # internet_pen=None, smartphone_pen=None, income_bucket="M", is_metro=True
    # Formula: (0.4 * 0) + (0.35 * 0) + (0.15 * 50) + (0.10 * 100) = 0 + 0 + 7.5 + 10 = 17.5
    score = calculate_digital_payment_index(None, None, "M", True)
    assert score == 17.5

def test_calculate_digital_payment_index_full_values():
    # internet_pen=100, smartphone_pen=100, income_bucket="VH", is_metro=True
    # Formula: 40 + 35 + 15 + 10 = 100
    score = calculate_digital_payment_index(100.0, 100.0, "VH", True)
    assert score == 100.0

def test_calculate_smart_city_score_with_none():
    # has_metro=False, has_airport=False, internet=None, smartphone=None, dpi=None, is_it_hub=False
    score = calculate_smart_city_score(False, False, None, None, None, False)
    assert score == 0.0

def test_calculate_smart_city_score_partial_none():
    # has_metro=True (20), airport=False, internet=50 (10), smartphone=None (0), dpi=50 (10), it_hub=True (10)
    # Total = 20 + 10 + 0 + 10 + 10 = 50.0
    score = calculate_smart_city_score(True, False, 50.0, None, 50.0, True)
    assert score == 50.0
