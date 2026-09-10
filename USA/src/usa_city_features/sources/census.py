import requests
from typing import Dict, Any, List
from .base import SourceAdapter, SourceRequest, SourceResponse, RawArtifact
from ..storage.cache import LocalCache

class CensusAdapter(SourceAdapter):
    source_name = "census"

    def __init__(self, cache: LocalCache):
        self.cache = cache
        self.base_url = "https://api.census.gov/data"

    def fetch(self, request: SourceRequest) -> SourceResponse:
        cached_data = self.cache.get(self.source_name, request.dataset, request.version, request.params)
        if cached_data:
            return SourceResponse(data=cached_data, metadata={"cached": True})

        # Construct URL
        # e.g. https://api.census.gov/data/2024/acs/acs5
        url = f"{self.base_url}/{request.version}/{request.dataset}"
        
        response = requests.get(url, params=request.params)
        response.raise_for_status()
        
        data = response.json()
        
        self.cache.set(self.source_name, request.dataset, request.version, request.params, data)
        
        return SourceResponse(data=data, metadata={"cached": False})

    def validate(self, response: SourceResponse) -> None:
        if not response.data or not isinstance(response.data, list) or len(response.data) < 2:
            raise ValueError("Invalid Census API response format")

    def save_raw(self, response: SourceResponse) -> RawArtifact:
        # Handled by cache in fetch
        pass

    def parse_response(self, response: SourceResponse) -> List[Dict[str, Any]]:
        self.validate(response)
        headers = response.data[0]
        rows = response.data[1:]
        
        parsed = []
        for row in rows:
            parsed.append(dict(zip(headers, row)))
        return parsed
