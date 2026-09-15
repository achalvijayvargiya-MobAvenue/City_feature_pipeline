import geopandas as gpd
from typing import Optional
from shapely.geometry import Point

def has_infrastructure(zcta_gdf: gpd.GeoDataFrame, infra_gdf: gpd.GeoDataFrame, radius_km: float = 25.0, col_name: str = 'has_infra') -> gpd.GeoDataFrame:
    """
    Check if infrastructure exists within a certain radius of a ZCTA.
    """
    if infra_gdf is None or infra_gdf.empty:
        zcta_gdf[col_name] = False
        return zcta_gdf

    # Ensure both are in EPSG:4326 before starting (if they have a CRS)
    if zcta_gdf.crs is None:
        zcta_gdf.set_crs(epsg=4326, inplace=True)
    if infra_gdf.crs is None:
        infra_gdf.set_crs(epsg=4326, inplace=True)
    
    # Project to EPSG:5070 (CONUS Albers) for accurate buffering in meters
    zcta_proj = zcta_gdf.to_crs(epsg=5070)
    infra_proj = infra_gdf.to_crs(epsg=5070)

    # Buffer ZCTAs
    buffer_meters = radius_km * 1000.0
    zcta_buffered = zcta_proj.copy()
    zcta_buffered.geometry = zcta_buffered.geometry.buffer(buffer_meters)

    # Spatial join
    joined = gpd.sjoin(zcta_buffered, infra_proj, how="left", predicate="intersects")
    
    # If index_right is not null, there is an intersection
    zcta_gdf[col_name] = joined['index_right'].notna()
    
    # Deduplicate in case a ZCTA intersects multiple infra points
    zcta_gdf = zcta_gdf[~zcta_gdf.index.duplicated(keep='first')]
    
    return zcta_gdf

def calculate_has_airport(zcta_gdf: gpd.GeoDataFrame, faa_data: dict) -> gpd.GeoDataFrame:
    if not faa_data or "features" not in faa_data:
        zcta_gdf['has_airport'] = False
        return zcta_gdf
    
    # Create GeoDataFrame from GeoJSON
    faa_gdf = gpd.GeoDataFrame.from_features(faa_data["features"])
    return has_infrastructure(zcta_gdf, faa_gdf, radius_km=25.0, col_name='has_airport')

def calculate_has_metro_rail(zcta_gdf: gpd.GeoDataFrame, bts_data: dict) -> gpd.GeoDataFrame:
    if not bts_data or "features" not in bts_data:
        zcta_gdf['has_metro_rail'] = False
        return zcta_gdf
    
    bts_gdf = gpd.GeoDataFrame.from_features(bts_data["features"])
    if not bts_gdf.empty:
        # Filter for rail modes. Common terms: 'subway', 'light rail', 'commuter rail', or GTFS route_type (0, 1, 2)
        rail_keywords = ['subway', 'light rail', 'commuter rail', 'rail']
        
        if 'mode' in bts_gdf.columns:
            # handle cases where mode could be nan
            mode_str = bts_gdf['mode'].astype(str).str.lower()
            bts_gdf = bts_gdf[mode_str.isin(rail_keywords) | mode_str.str.contains('rail')]
        elif 'route_type' in bts_gdf.columns:
             # GTFS: 0=Tram/Light Rail, 1=Subway/Metro, 2=Rail
             bts_gdf = bts_gdf[bts_gdf['route_type'].astype(str).isin(['0', '1', '2'])]
             
    return has_infrastructure(zcta_gdf, bts_gdf, radius_km=10.0, col_name='has_metro_rail')

def calculate_has_major_railway(zcta_gdf: gpd.GeoDataFrame, fra_data: dict) -> gpd.GeoDataFrame:
    if not fra_data or "features" not in fra_data:
        zcta_gdf['has_major_railway'] = False
        return zcta_gdf
    
    fra_gdf = gpd.GeoDataFrame.from_features(fra_data["features"])
    return has_infrastructure(zcta_gdf, fra_gdf, radius_km=10.0, col_name='has_major_railway')
