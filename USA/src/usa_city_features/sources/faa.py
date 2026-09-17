import requests
from typing import Dict, Any, List
from .base import SourceAdapter, SourceRequest, SourceResponse, RawArtifact
from ..storage.cache import LocalCache

class FAAAdapter(SourceAdapter):
    source_name = "faa"

    def __init__(self, cache: LocalCache):
        self.cache = cache
        # Using HIFLD Open Data GeoJSON endpoint for US Airports
        self.base_url = "https://opendata.arcgis.com/api/v3/datasets/e747ab91a11045e8b3f8a3efd093d3b5_0/downloads/data"

    def fetch(self, request: SourceRequest) -> SourceResponse:
        cached_data = self.cache.get(self.source_name, request.dataset, request.version, request.params)
        if cached_data:
            return SourceResponse(data=cached_data, metadata={"cached": True})

        params = {
            "where": "1=1",
            "format": "geojson",
            "spatialRefId": "4326"
        }
        params.update(request.params)
        
        response = requests.get(self.base_url, params=params)
        response.raise_for_status()
        
        data = response.json()
        
        self.cache.set(self.source_name, request.dataset, request.version, request.params, data)
        
        return SourceResponse(data=data, metadata={"cached": False})

    def validate(self, response: SourceResponse) -> None:
        if not response.data or "features" not in response.data:
            raise ValueError("Invalid FAA API response format")

    def save_raw(self, response: SourceResponse) -> RawArtifact:
        pass
