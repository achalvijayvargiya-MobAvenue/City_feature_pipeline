import pytest
import geopandas as gpd
import pandas as pd
from shapely.geometry import Point, Polygon
from usa_city_features.geography.spatial_join import SpatialJoiner

def test_spatial_join_beverly_hills():
    # 1. Mock ZCTA (90210 - Beverly Hills)
    # Beverly Hills centroid is roughly: -118.4004, 34.0736
    zcta_df = pd.DataFrame({
        'zcta': ['90210'],
        'geometry': [Point(-118.4004, 34.0736)]
    })
    zcta_gdf = gpd.GeoDataFrame(zcta_df, geometry='geometry', crs="EPSG:4326")
    
    # 2. Mock Place (Beverly Hills)
    # A polygon enclosing the point
    bh_poly = Polygon([
        (-118.42, 34.05),
        (-118.38, 34.05),
        (-118.38, 34.09),
        (-118.42, 34.09)
    ])
    places_df = pd.DataFrame({
        'place_name': ['Beverly Hills'],
        'geometry': [bh_poly]
    })
    places_gdf = gpd.GeoDataFrame(places_df, geometry='geometry', crs="EPSG:4326")
    
    # 3. Mock County (Los Angeles)
    # A larger polygon enclosing the point
    la_poly = Polygon([
        (-119.0, 33.5),
        (-117.5, 33.5),
        (-117.5, 34.5),
        (-119.0, 34.5)
    ])
    counties_df = pd.DataFrame({
        'county_name': ['Los Angeles County'],
        'geometry': [la_poly]
    })
    counties_gdf = gpd.GeoDataFrame(counties_df, geometry='geometry', crs="EPSG:4326")
    
    # Run the spatial join
    joiner = SpatialJoiner(places_gdf=places_gdf, counties_gdf=counties_gdf)
    
    # Test Place assignment
    zcta_with_place = joiner.assign_place(zcta_gdf)
    assert len(zcta_with_place) == 1
    assert zcta_with_place.iloc[0]['place_name'] == 'Beverly Hills'
    
    # Test County assignment
    zcta_with_county = joiner.assign_county(zcta_gdf)
    assert len(zcta_with_county) == 1
    assert zcta_with_county.iloc[0]['county_name'] == 'Los Angeles County'

def test_spatial_join_drops_duplicates():
    # Test edge case where a point intersects multiple overlapping polygons
    zcta_df = pd.DataFrame({
        'zcta': ['90210'],
        'geometry': [Point(-118.4004, 34.0736)]
    })
    zcta_gdf = gpd.GeoDataFrame(zcta_df, geometry='geometry', crs="EPSG:4326")
    
    # Two overlapping places
    poly1 = Polygon([(-118.5, 34.0), (-118.3, 34.0), (-118.3, 34.2), (-118.5, 34.2)])
    poly2 = Polygon([(-118.45, 34.0), (-118.35, 34.0), (-118.35, 34.1), (-118.45, 34.1)])
    
    places_df = pd.DataFrame({
        'place_name': ['Place1', 'Place2'],
        'geometry': [poly1, poly2]
    })
    places_gdf = gpd.GeoDataFrame(places_df, geometry='geometry', crs="EPSG:4326")
    
    joiner = SpatialJoiner(places_gdf=places_gdf)
    result = joiner.assign_place(zcta_gdf)
    
    # Should only return one record due to ~joined.index.duplicated
    assert len(result) == 1
