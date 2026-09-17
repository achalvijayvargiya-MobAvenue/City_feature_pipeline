import requests
from typing import Dict, Any, List
from .base import SourceAdapter, SourceRequest, SourceResponse, RawArtifact
from ..storage.cache import LocalCache

class MARADAdapter(SourceAdapter):
    source_name = "marad"

    def __init__(self, cache: LocalCache):
        self.cache = cache
        # HIFLD Ports GeoJSON
        self.base_url = "https://services.arcgis.com/P3ePLMYs2RVChkJx/arcgis/rest/services/Ports/FeatureServer/0/query"

    def fetch(self, request: SourceRequest) -> SourceResponse:
        cached_data = self.cache.get(self.source_name, request.dataset, request.version, request.params)
        if cached_data:
            return SourceResponse(data=cached_data, metadata={"cached": True})

        params = {
            "where": "1=1",
            "outFields": "*",
            "f": "geojson",
            "outSR": "4326"
        }
        params.update(request.params)
        
        try:
            response = requests.get(self.base_url, params=params)
            response.raise_for_status()
            data = response.json()
        except Exception as e:
            # Mocking response for now if endpoint is down
            data = {
                "type": "FeatureCollection",
                "features": []
            }
            
        self.cache.set(self.source_name, request.dataset, request.version, request.params, data)
        
        return SourceResponse(data=data, metadata={"cached": False})

    def validate(self, response: SourceResponse) -> None:
        if not response.data or "features" not in response.data:
            raise ValueError("Invalid MARAD API response format")

    def save_raw(self, response: SourceResponse) -> RawArtifact:
        pass
