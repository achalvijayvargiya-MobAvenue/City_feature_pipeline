from pydantic import BaseModel
from typing import Optional

class ZCTAModel(BaseModel):
    zcta5: str
    latitude: float
    longitude: float

class PlaceModel(BaseModel):
    place_geoid: str
    place_name: str
    state_fips: str

class CountyModel(BaseModel):
    county_fips: str
    county_name: str
    state_fips: str

class CBSAModel(BaseModel):
    cbsa_code: str
    cbsa_name: str
    is_metro: bool

class LocationModel(BaseModel):
    zcta5: str
    latitude: float
    longitude: float
    place_geoid: Optional[str] = None
    place_name: Optional[str] = None
    county_fips: Optional[str] = None
    county_name: Optional[str] = None
    state_fips: Optional[str] = None
    state_code: Optional[str] = None
    state_name: Optional[str] = None
    cbsa_code: Optional[str] = None
    cbsa_name: Optional[str] = None
    region: Optional[str] = None
    is_metro_city: bool = False
