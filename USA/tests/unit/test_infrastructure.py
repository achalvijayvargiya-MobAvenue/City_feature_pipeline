import pytest
import geopandas as gpd
from shapely.geometry import Point
from usa_city_features.features.infrastructure_features import (
    has_infrastructure,
    calculate_has_airport,
    calculate_has_metro_rail,
    calculate_has_major_railway
)

@pytest.fixture
def dummy_zcta_gdf():
    # A point in the central US (Kansas)
    return gpd.GeoDataFrame({
        'zcta': ['12345'],
        'geometry': [Point(-95.0, 40.0)]
    }, crs="EPSG:4326")

def test_has_infrastructure_10km_away(dummy_zcta_gdf):
    # 0.09 degrees of latitude is roughly 10km
    infra_gdf = gpd.GeoDataFrame({
        'name': ['Test Airport'],
        'geometry': [Point(-95.0, 40.09)]
    }, crs="EPSG:4326")
    
    result = has_infrastructure(dummy_zcta_gdf, infra_gdf, radius_km=25.0, col_name='has_infra')
    assert result.iloc[0]['has_infra'] == True

def test_has_infrastructure_30km_away(dummy_zcta_gdf):
    # 0.28 degrees of latitude is roughly 31km
    infra_gdf = gpd.GeoDataFrame({
        'name': ['Far Airport'],
        'geometry': [Point(-95.0, 40.28)]
    }, crs="EPSG:4326")
    
    result = has_infrastructure(dummy_zcta_gdf, infra_gdf, radius_km=25.0, col_name='has_infra')
    assert result.iloc[0]['has_infra'] == False

def test_calculate_has_airport(dummy_zcta_gdf):
    faa_data = {
        "features": [
            {
                "type": "Feature",
                "properties": {"name": "Test Airport"},
                "geometry": {"type": "Point", "coordinates": [-95.0, 40.09]}
            }
        ]
    }
    result = calculate_has_airport(dummy_zcta_gdf.copy(), faa_data)
    assert result.iloc[0]['has_airport'] == True

def test_calculate_has_metro_rail(dummy_zcta_gdf):
    bts_data = {
        "features": [
            {
                "type": "Feature",
                "properties": {"mode": "subway"},
                "geometry": {"type": "Point", "coordinates": [-95.0, 40.05]}
            },
            {
                "type": "Feature",
                "properties": {"mode": "bus"}, # Should be filtered out
                "geometry": {"type": "Point", "coordinates": [-95.0, 40.05]}
            }
        ]
    }
    result = calculate_has_metro_rail(dummy_zcta_gdf.copy(), bts_data)
    assert result.iloc[0]['has_metro_rail'] == True

def test_calculate_has_metro_rail_filtered_out(dummy_zcta_gdf):
    bts_data = {
        "features": [
            {
                "type": "Feature",
                "properties": {"mode": "bus"}, # Only bus nearby
                "geometry": {"type": "Point", "coordinates": [-95.0, 40.05]}
            }
        ]
    }
    result = calculate_has_metro_rail(dummy_zcta_gdf.copy(), bts_data)
    assert result.iloc[0]['has_metro_rail'] == False
