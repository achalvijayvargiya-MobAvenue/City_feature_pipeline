import geopandas as gpd
from typing import Optional
from shapely.geometry import Point

def has_infrastructure(zcta_gdf: gpd.GeoDataFrame, infra_gdf: gpd.GeoDataFrame, radius_km: float = 25.0) -> gpd.GeoDataFrame:
    """
    Check if infrastructure (airports, transit, etc.) exists within a certain radius of a ZCTA.
    This assumes geometries are in a suitable projected CRS for distance calculations (or we buffer in degrees roughly).
    For a robust implementation, we should project to a local CRS, buffer, and then spatial join.
    """
    if infra_gdf is None or infra_gdf.empty:
        zcta_gdf['has_infra'] = False
        return zcta_gdf

    # Rough approximation: 1 degree ~ 111 km
    buffer_degrees = radius_km / 111.0
    
    # Create buffered geometries for ZCTAs
    zcta_buffered = zcta_gdf.copy()
    zcta_buffered.geometry = zcta_buffered.geometry.buffer(buffer_degrees)
    
    # Spatial join
    joined = gpd.sjoin(zcta_buffered, infra_gdf, how="left", predicate="intersects")
    
    # If index_right is not null, it means there's an intersection
    zcta_gdf['has_infra'] = joined['index_right'].notna()
    
    # Deduplicate in case a ZCTA intersects multiple infra points
    zcta_gdf = zcta_gdf[~zcta_gdf.index.duplicated(keep='first')]
    
    return zcta_gdf
