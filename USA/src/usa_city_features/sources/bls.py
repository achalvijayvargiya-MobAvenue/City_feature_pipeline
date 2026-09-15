import requests
import json
from typing import Dict, Any, List, Optional
from .base import SourceAdapter, SourceRequest, SourceResponse, RawArtifact
from ..storage.cache import LocalCache

class BLSAdapter(SourceAdapter):
    source_name = "bls"

    def __init__(self, cache: LocalCache):
        self.cache = cache
        self.base_url = "https://api.bls.gov/publicAPI/v2/timeseries/data/"

    def fetch(self, request: SourceRequest) -> SourceResponse:
        cached_data = self.cache.get(self.source_name, request.dataset, request.version, request.params)
        if cached_data:
            return SourceResponse(data=cached_data, metadata={"cached": True})

        headers = {'Content-type': 'application/json'}
        data = json.dumps({
            "seriesid": request.params.get("series_id", []), 
            "startyear": request.params.get("startyear"), 
            "endyear": request.params.get("endyear")
        })
        
        response = requests.post(self.base_url, data=data, headers=headers)
        response.raise_for_status()
        
        data = response.json()
        
        self.cache.set(self.source_name, request.dataset, request.version, request.params, data)
        
        return SourceResponse(data=data, metadata={"cached": False})

    def fetch_cpi(self, start_year: str, end_year: str) -> SourceResponse:
        """Fetches the National CPI (CUUR0000SA0)."""
        request = SourceRequest(
            dataset="cpi",
            version="v2",
            params={
                "series_id": ["CUUR0000SA0"],
                "startyear": start_year,
                "endyear": end_year
            }
        )
        return self.fetch(request)

    def fetch_qcew_employment(self, area_code: str, industry_code: str, start_year: str, end_year: str) -> SourceResponse:
        """
        Fetches QCEW industry employment data.
        Mock series ID generation: ENU + area_code + 105 + industry_code
        (Actual QCEW series IDs have a specific format, this is an approximation)
        """
        series_id = f"ENU{area_code}105{industry_code}"
        request = SourceRequest(
            dataset="qcew",
            version="v2",
            params={
                "series_id": [series_id],
                "startyear": start_year,
                "endyear": end_year
            }
        )
        return self.fetch(request)

    def validate(self, response: SourceResponse) -> None:
        if not response.data or "Results" not in response.data:
            raise ValueError("Invalid BLS API response format")

    def save_raw(self, response: SourceResponse) -> RawArtifact:
        pass

