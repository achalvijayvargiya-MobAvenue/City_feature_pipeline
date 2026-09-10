import requests
from typing import Dict, Any, List
from .base import SourceAdapter, SourceRequest, SourceResponse, RawArtifact
from ..storage.cache import LocalCache

class BTSAdapter(SourceAdapter):
    source_name = "bts"

    def __init__(self, cache: LocalCache):
        self.cache = cache
        self.base_url = "https://data.bts.gov/resource/ntad-transit.json"

    def fetch(self, request: SourceRequest) -> SourceResponse:
        cached_data = self.cache.get(self.source_name, request.dataset, request.version, request.params)
        if cached_data:
            return SourceResponse(data=cached_data, metadata={"cached": True})

        response = requests.get(self.base_url, params=request.params)
        response.raise_for_status()
        
        data = response.json()
        
        self.cache.set(self.source_name, request.dataset, request.version, request.params, data)
        
        return SourceResponse(data=data, metadata={"cached": False})

    def validate(self, response: SourceResponse) -> None:
        if not isinstance(response.data, list):
            raise ValueError("Invalid BTS API response format")

    def save_raw(self, response: SourceResponse) -> RawArtifact:
        pass
