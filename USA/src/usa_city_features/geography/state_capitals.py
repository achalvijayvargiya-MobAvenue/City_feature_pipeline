from typing import Optional, Tuple
from ..transforms.distance import haversine_distance_km

STATE_CAPITALS = {
    "AL": {"name": "Montgomery", "lat": 32.3668, "lon": -86.3000},
    "AK": {"name": "Juneau", "lat": 58.3019, "lon": -134.4197},
    "AZ": {"name": "Phoenix", "lat": 33.4484, "lon": -112.0740},
    "AR": {"name": "Little Rock", "lat": 34.7465, "lon": -92.2896},
    "CA": {"name": "Sacramento", "lat": 38.5816, "lon": -121.4944},
    "CO": {"name": "Denver", "lat": 39.7392, "lon": -104.9903},
    "CT": {"name": "Hartford", "lat": 41.7658, "lon": -72.6734},
    "DE": {"name": "Dover", "lat": 39.1582, "lon": -75.5244},
    "FL": {"name": "Tallahassee", "lat": 30.4383, "lon": -84.2807},
    "GA": {"name": "Atlanta", "lat": 33.7490, "lon": -84.3880},
    "HI": {"name": "Honolulu", "lat": 21.3069, "lon": -157.8583},
    "ID": {"name": "Boise", "lat": 43.6150, "lon": -116.2023},
    "IL": {"name": "Springfield", "lat": 39.7817, "lon": -89.6501},
    "IN": {"name": "Indianapolis", "lat": 39.7684, "lon": -86.1581},
    "IA": {"name": "Des Moines", "lat": 41.5868, "lon": -93.6250},
    "KS": {"name": "Topeka", "lat": 39.0473, "lon": -95.6752},
    "KY": {"name": "Frankfort", "lat": 38.2009, "lon": -84.8733},
    "LA": {"name": "Baton Rouge", "lat": 30.4515, "lon": -91.1871},
    "ME": {"name": "Augusta", "lat": 44.3106, "lon": -69.7795},
    "MD": {"name": "Annapolis", "lat": 38.9784, "lon": -76.4922},
    "MA": {"name": "Boston", "lat": 42.3601, "lon": -71.0589},
    "MI": {"name": "Lansing", "lat": 42.7325, "lon": -84.5555},
    "MN": {"name": "St. Paul", "lat": 44.9537, "lon": -93.0900},
    "MS": {"name": "Jackson", "lat": 32.2988, "lon": -90.1848},
    "MO": {"name": "Jefferson City", "lat": 38.5767, "lon": -92.1735},
    "MT": {"name": "Helena", "lat": 46.5891, "lon": -112.0391},
    "NE": {"name": "Lincoln", "lat": 40.8136, "lon": -96.7026},
    "NV": {"name": "Carson City", "lat": 39.1638, "lon": -119.7674},
    "NH": {"name": "Concord", "lat": 43.2081, "lon": -71.5326},
    "NJ": {"name": "Trenton", "lat": 40.2171, "lon": -74.7429},
    "NM": {"name": "Santa Fe", "lat": 35.6870, "lon": -105.9378},
    "NY": {"name": "Albany", "lat": 42.6526, "lon": -73.7562},
    "NC": {"name": "Raleigh", "lat": 35.7796, "lon": -78.6382},
    "ND": {"name": "Bismarck", "lat": 46.8083, "lon": -100.7837},
    "OH": {"name": "Columbus", "lat": 39.9612, "lon": -83.0007},
    "OK": {"name": "Oklahoma City", "lat": 35.4676, "lon": -97.5164},
    "OR": {"name": "Salem", "lat": 44.9429, "lon": -123.0351},
    "PA": {"name": "Harrisburg", "lat": 40.2732, "lon": -76.8867},
    "RI": {"name": "Providence", "lat": 41.8240, "lon": -71.4128},
    "SC": {"name": "Columbia", "lat": 34.0007, "lon": -81.0348},
    "SD": {"name": "Pierre", "lat": 44.3683, "lon": -100.3510},
    "TN": {"name": "Nashville", "lat": 36.1627, "lon": -86.7816},
    "TX": {"name": "Austin", "lat": 30.2672, "lon": -97.7431},
    "UT": {"name": "Salt Lake City", "lat": 40.7608, "lon": -111.8910},
    "VT": {"name": "Montpelier", "lat": 44.2601, "lon": -72.5754},
    "VA": {"name": "Richmond", "lat": 35.5424, "lon": -77.4603},
    "WA": {"name": "Olympia", "lat": 47.0379, "lon": -122.9007},
    "WV": {"name": "Charleston", "lat": 38.3498, "lon": -81.6326},
    "WI": {"name": "Madison", "lat": 43.0731, "lon": -89.4012},
    "WY": {"name": "Cheyenne", "lat": 41.1400, "lon": -104.8202}
}

def get_state_capital(state_code: str) -> Optional[dict]:
    return STATE_CAPITALS.get(state_code.upper())

def is_state_capital(city_name: str, state_code: str) -> bool:
    capital = get_state_capital(state_code)
    if not capital:
        return False
    return capital["name"].lower() == city_name.lower()

def distance_to_state_capital(lat: float, lon: float, state_code: str) -> Optional[float]:
    capital = get_state_capital(state_code)
    if not capital:
        return None
    return haversine_distance_km(lat, lon, capital["lat"], capital["lon"])
