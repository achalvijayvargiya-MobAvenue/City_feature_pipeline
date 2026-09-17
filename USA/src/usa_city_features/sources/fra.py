import requests
from typing import Dict, Any, List
from .base import SourceAdapter, SourceRequest, SourceResponse, RawArtifact
from ..storage.cache import LocalCache

class FRAAdapter(SourceAdapter):
    source_name = "fra"

    def __init__(self, cache: LocalCache):
        self.cache = cache
        # Use the official Bureau of Transportation Statistics API endpoint for Amtrak Stations
        self.base_url = "https://data.bts.gov/resource/f39y-jbrv.geojson"

    def fetch(self, request: SourceRequest) -> SourceResponse:
        cached_data = self.cache.get(self.source_name, request.dataset, request.version, request.params)
        if cached_data:
            return SourceResponse(data=cached_data, metadata={"cached": True})

        # Mocking FRA response for now since the endpoint is down
        data = {
            "type": "FeatureCollection",
            "features": []
        }
        
        self.cache.set(self.source_name, request.dataset, request.version, request.params, data)
        
        return SourceResponse(data=data, metadata={"cached": False})

    def validate(self, response: SourceResponse) -> None:
        if not response.data or "features" not in response.data:
            raise ValueError("Invalid FRA API response format")

    def save_raw(self, response: SourceResponse) -> RawArtifact:
        pass
