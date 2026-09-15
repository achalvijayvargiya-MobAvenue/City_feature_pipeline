import pytest
from unittest.mock import patch, MagicMock
from usa_city_features.sources.base import SourceRequest
from usa_city_features.sources.census import CensusAdapter
from usa_city_features.storage.cache import LocalCache
from usa_city_features.features.demographic_features import extract_demographic_features

@pytest.fixture
def cache(tmp_path):
    return LocalCache(base_dir=str(tmp_path))

@pytest.fixture
def census_adapter(cache):
    return CensusAdapter(cache=cache)

@patch('requests.get')
def test_get_variable_by_label(mock_get, census_adapter):
    # Mock the variables.json response
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "variables": {
            "B28001_001E": {"label": "Estimate!!Total", "concept": "TYPES OF COMPUTERS AND INTERNET SUBSCRIPTIONS"},
            "B28001_005E": {"label": "Estimate!!Total!!Has a smartphone", "concept": "TYPES OF COMPUTERS AND INTERNET SUBSCRIPTIONS"}
        }
    }
    mock_get.return_value = mock_response

    # Test exact semantic search
    var_code = census_adapter.get_variable_by_label("acs/acs5", "2024", "B28001", "smartphone")
    assert var_code == "B28001_005E"

    # Test missing semantic
    with pytest.raises(ValueError, match="Could not find variable"):
        census_adapter.get_variable_by_label("acs/acs5", "2024", "B28001", "tablet")

@patch('requests.get')
def test_fetch_and_parse(mock_get, census_adapter):
    # Mock the data response
    mock_response = MagicMock()
    mock_response.json.return_value = [
        ["NAME", "B01003_001E", "zip code tabulation area"],
        ["ZCTA5 90210", "33941", "90210"]
    ]
    mock_get.return_value = mock_response

    request = SourceRequest(
        dataset="acs/acs5",
        version="2024",
        params={"get": "NAME,B01003_001E", "for": "zip code tabulation area:*"}
    )
    
    response = census_adapter.fetch(request)
    assert response.metadata["cached"] is False
    
    parsed = census_adapter.parse_response(response)
    assert len(parsed) == 1
    assert parsed[0]["B01003_001E"] == "33941"
    assert parsed[0]["zip code tabulation area"] == "90210"
    
    # Test caching works
    response_cached = census_adapter.fetch(request)
    assert response_cached.metadata["cached"] is True

def test_extract_demographic_features():
    raw_row = {
        "B01003_001E": "100000",
        "B01002_001E": "35.5",
        "B01001_002E": "49000",
        "B01001_026E": "51000",
        "B19013_001E": "85000",
        "B15003_001E": "70000",
        "B15003_022E": "60000",
        "B28001_001E": "30000",
        "B28001_005E": "25000",
        "B28002_002E": "28000"
    }
    
    vars_map = {
        "population": "B01003_001E",
        "median_age": "B01002_001E",
        "male_population": "B01001_002E",
        "female_population": "B01001_026E",
        "median_income": "B19013_001E",
        "population_25_plus": "B15003_001E",
        "population_hs_plus": "B15003_022E",
        "total_households": "B28001_001E",
        "smartphone_households": "B28001_005E",
        "internet_households": "B28002_002E"
    }
    
    features = extract_demographic_features(raw_row, vars_map)
    
    assert features["district_population_numeric"] == 100000
    assert features["median_age_estimate"] == 35.5
    assert round(features["sex_ratio"], 2) == 96.08 # 49000/51000 * 100
    assert features["income_bucket"] == "M"
    assert round(features["literacy_rate"], 2) == 85.71 # 60000/70000 * 100
    assert round(features["internet_penetration_state"], 2) == 93.33 # 28000/30000 * 100
    assert round(features["smartphone_penetration_state"], 2) == 83.33 # 25000/30000 * 100
