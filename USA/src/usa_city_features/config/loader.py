import os
import yaml
from pathlib import Path
from pydantic import BaseModel
from typing import Dict, Any

class CensusConfig(BaseModel):
    acs_dataset: str = "acs/acs5"
    acs_year: int = 2024
    zcta_year: int = 2025
    place_year: int = 2025
    cbsa_year: int = 2025

class BLSConfig(BaseModel):
    cpi_series: str = "CUUR0000SA0"

class SourceConfig(BaseModel):
    census: CensusConfig = CensusConfig()
    bls: BLSConfig = BLSConfig()
    faa: Dict[str, Any] = {"enabled": True}
    bts: Dict[str, Any] = {"enabled": True}
    fra: Dict[str, Any] = {"enabled": True}
    marad: Dict[str, Any] = {"enabled": True}
    noaa: Dict[str, Any] = {"enabled": True}

class GeographyThresholds(BaseModel):
    coastal_radius_km: float = 25.0

class CityTierThresholds(BaseModel):
    t1_min_population: int = 1000000
    t2_min_population: int = 250000

class IndustryHubThresholds(BaseModel):
    minimum_employment: int = 5000
    minimum_share: float = 0.05

class ThresholdsConfig(BaseModel):
    geography: GeographyThresholds = GeographyThresholds()
    city_tier: CityTierThresholds = CityTierThresholds()
    industry_hub: IndustryHubThresholds = IndustryHubThresholds()

class Config(BaseModel):
    sources: SourceConfig
    thresholds: ThresholdsConfig

def load_yaml(path: str) -> dict:
    if not os.path.exists(path):
        return {}
    with open(path, 'r') as f:
        return yaml.safe_load(f) or {}

def load_config(configs_dir: str = "configs") -> Config:
    sources_path = os.path.join(configs_dir, "sources.yaml")
    thresholds_path = os.path.join(configs_dir, "thresholds.yaml")
    
    sources_data = load_yaml(sources_path)
    thresholds_data = load_yaml(thresholds_path)
    
    return Config(
        sources=SourceConfig(**sources_data),
        thresholds=ThresholdsConfig(**thresholds_data)
    )
