"""Static curated lookups for USA infrastructure and industry flags.

Mirrors INDIA/pipeline/step3_static_lookups.py: when live geospatial APIs
are empty or incomplete, apply authoritative city/county config lists.
"""
from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Iterable, Optional, Set

import yaml

CONFIG_DIR = Path(__file__).resolve().parents[3] / "configs"

_SUFFIX_RE = re.compile(
    r"\b(city|town|village|borough|municipality|cdp|urban county|consolidated government)\b",
    re.IGNORECASE,
)
_NON_ALNUM_RE = re.compile(r"[^a-z0-9\s]+")
_WS_RE = re.compile(r"\s+")


def normalize_place_name(name: Any) -> str:
    if name is None:
        return ""
    text = str(name).strip().lower()
    if not text or text == "nan":
        return ""
    text = _SUFFIX_RE.sub(" ", text)
    text = _NON_ALNUM_RE.sub(" ", text)
    text = _WS_RE.sub(" ", text).strip()
    # Common Census / alias normalizations
    aliases = {
        "st louis": "st louis",
        "saint louis": "st louis",
        "st paul": "st paul",
        "saint paul": "st paul",
        "st petersburg": "st petersburg",
        "saint petersburg": "st petersburg",
        "winston salem": "winston salem",
        "new york city": "new york",
        "washington dc": "washington",
        "district of columbia": "washington",
    }
    return aliases.get(text, text)


def _to_norm_set(items: Optional[Iterable[Any]]) -> Set[str]:
    if not items:
        return set()
    return {normalize_place_name(x) for x in items if normalize_place_name(x)}


@lru_cache(maxsize=1)
def load_manual_flags(configs_dir: Optional[str] = None) -> Dict[str, Set[str]]:
    path = Path(configs_dir) / "manual_flags.yaml" if configs_dir else CONFIG_DIR / "manual_flags.yaml"
    data: Dict[str, Any] = {}
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}

    return {
        "has_airport": _to_norm_set(data.get("cities_with_airport")),
        "has_international_airport": _to_norm_set(data.get("cities_with_international_airport")),
        "has_metro_rail": _to_norm_set(data.get("cities_with_metro_rail")),
        "has_seaport": _to_norm_set(data.get("cities_with_seaport")),
        "major_railway_station": _to_norm_set(data.get("major_railway_station")),
        "is_it_hub": _to_norm_set(data.get("it_hub_cities")),
        "is_manufacturing_hub": _to_norm_set(data.get("manufacturing_hub_cities")),
        "is_financial_center": _to_norm_set(data.get("financial_center_cities")),
        "is_textile_hub": _to_norm_set(data.get("textile_hub_cities")),
        "is_education_hub": _to_norm_set(data.get("education_hub_cities")),
        "is_tourist_city": _to_norm_set(data.get("tourist_cities")),
    }


@lru_cache(maxsize=1)
def load_coastal_county_fips(configs_dir: Optional[str] = None) -> Set[str]:
    path = Path(configs_dir) / "coastal_counties.yaml" if configs_dir else CONFIG_DIR / "coastal_counties.yaml"
    if not path.exists():
        return set()
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    fips = data.get("county_fips") or []
    return {str(x).zfill(5) for x in fips}


def county_fips_key(state_fips: Any, county_fips: Any) -> str:
    if state_fips is None or county_fips is None:
        return ""
    try:
        if str(state_fips) in ("nan", "") or str(county_fips) in ("nan", ""):
            return ""
        return f"{int(state_fips):02d}{int(county_fips):03d}"
    except (TypeError, ValueError):
        s = str(state_fips).strip()
        c = str(county_fips).strip()
        if not s or not c:
            return ""
        return (s + c).zfill(5)[-5:]


def is_coastal_county(state_fips: Any, county_fips: Any, configs_dir: Optional[str] = None) -> bool:
    key = county_fips_key(state_fips, county_fips)
    if not key:
        return False
    return key in load_coastal_county_fips(configs_dir)


def place_in_flag(place_name: Any, flag_name: str, configs_dir: Optional[str] = None) -> bool:
    city = normalize_place_name(place_name)
    if not city:
        return False
    flags = load_manual_flags(configs_dir)
    return city in flags.get(flag_name, set())


def resolve_boolean_flags(
    place_name: Any,
    state_fips: Any = None,
    county_fips: Any = None,
    existing: Optional[Dict[str, Any]] = None,
    configs_dir: Optional[str] = None,
) -> Dict[str, bool]:
    """Apply curated city/county config as the authoritative source for these flags.

    Live geospatial APIs remain useful for diagnostics, but for one-time USA
    production generation we follow the India pipeline pattern: static lists win.
    """
    existing = existing or {}
    city_flags = [
        "has_airport",
        "has_international_airport",
        "has_metro_rail",
        "has_seaport",
        "major_railway_station",
        "is_it_hub",
        "is_manufacturing_hub",
        "is_financial_center",
        "is_textile_hub",
        "is_education_hub",
        "is_tourist_city",
    ]
    out: Dict[str, bool] = {}
    for name in city_flags:
        out[name] = place_in_flag(place_name, name, configs_dir)

    # Coastal uses NOAA shoreline county FIPS (not city name)
    out["is_coastal"] = is_coastal_county(state_fips, county_fips, configs_dir)
    return out
