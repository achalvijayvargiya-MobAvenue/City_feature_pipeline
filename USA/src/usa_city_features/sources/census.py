import requests
from typing import Dict, Any, List
from .base import SourceAdapter, SourceRequest, SourceResponse, RawArtifact
from ..storage.cache import LocalCache

class CensusAdapter(SourceAdapter):
    source_name = "census"

    def __init__(self, cache: LocalCache):
        self.cache = cache
        self.base_url = "https://api.census.gov/data"

    def get_variable_by_label(self, dataset: str, version: str, group: str, semantic_label: str) -> str:
        """Fetch variable metadata and find the correct variable code by semantic label."""
        params = {}
        cached_vars = self.cache.get(self.source_name, f"{dataset}_variables", version, params)
        
        if not cached_vars:
            url = f"{self.base_url}/{version}/{dataset}/variables.json"
            response = requests.get(url)
            response.raise_for_status()
            cached_vars = response.json()
            self.cache.set(self.source_name, f"{dataset}_variables", version, params, cached_vars)
            
        variables = cached_vars.get("variables", {})
        
        semantic_lower = semantic_label.lower()
        for var_name, var_info in variables.items():
            if not var_name.startswith(group):
                continue
            
            label = var_info.get("label", "").lower()
            concept = var_info.get("concept", "").lower()
            
            if semantic_lower in label or semantic_lower in concept:
                return var_name
                
        raise ValueError(f"Could not find variable in group {group} matching label '{semantic_label}'")

    def fetch(self, request: SourceRequest) -> SourceResponse:
        cached_data = self.cache.get(self.source_name, request.dataset, request.version, request.params)
        if cached_data:
            return SourceResponse(data=cached_data, metadata={"cached": True})

        url = f"{self.base_url}/{request.version}/{request.dataset}"
        
        # Note: API pagination or batching could be implemented here if requesting 
        # > 50 variables at once. For demographic features, we only request ~7.
        # Requesting ZCTA:* works in one single batch for < 50 variables.
        response = requests.get(url, params=request.params)
        response.raise_for_status()
        
        data = response.json()
        
        # LocalCache saves raw json
        self.cache.set(self.source_name, request.dataset, request.version, request.params, data)
        
        return SourceResponse(data=data, metadata={"cached": False})

    def validate(self, response: SourceResponse) -> None:
        if not response.data or not isinstance(response.data, list) or len(response.data) < 2:
            raise ValueError("Invalid Census API response format")

    def save_raw(self, response: SourceResponse) -> RawArtifact:
        # Saved by cache during fetch
        return RawArtifact(path="handled_by_cache", hash="")

    def parse_response(self, response: SourceResponse) -> List[Dict[str, Any]]:
        self.validate(response)
        headers = response.data[0]
        rows = response.data[1:]
        
        parsed = []
        for row in rows:
            parsed.append(dict(zip(headers, row)))
        return parsed
