import geopandas as gpd
import pandas as pd
from typing import Optional
from shapely.geometry import Point

class SpatialJoiner:
    def __init__(self, places_gdf: Optional[gpd.GeoDataFrame] = None, 
                 counties_gdf: Optional[gpd.GeoDataFrame] = None,
                 cbsa_gdf: Optional[gpd.GeoDataFrame] = None):
        self.places_gdf = places_gdf
        self.counties_gdf = counties_gdf
        self.cbsa_gdf = cbsa_gdf

    def assign_place(self, zcta_gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
        if self.places_gdf is None:
            return zcta_gdf
        
        # Spatial join ZCTA points to Places polygons
        # We assume zcta_gdf has Point geometry representing the ZCTA centroid
        joined = gpd.sjoin(zcta_gdf, self.places_gdf, how="left", predicate="intersects")
        # Handle edge case: ZCTA crossing multiple places. Use the first one matched (which contains the point)
        joined = joined[~joined.index.duplicated(keep='first')]
        # Drop the index_right column so subsequent joins don't fail
        if 'index_right' in joined.columns:
            joined = joined.drop(columns=['index_right'])
        return joined

    def assign_county(self, zcta_gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
        if self.counties_gdf is None:
            return zcta_gdf
        
        joined = gpd.sjoin(zcta_gdf, self.counties_gdf, how="left", predicate="intersects")
        joined = joined[~joined.index.duplicated(keep='first')]
        if 'index_right' in joined.columns:
            joined = joined.drop(columns=['index_right'])
        return joined

    def assign_cbsa(self, zcta_gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
        if self.cbsa_gdf is None:
            return zcta_gdf
        
        joined = gpd.sjoin(zcta_gdf, self.cbsa_gdf, how="left", predicate="intersects")
        joined = joined[~joined.index.duplicated(keep='first')]
        if 'index_right' in joined.columns:
            joined = joined.drop(columns=['index_right'])
        return joined
