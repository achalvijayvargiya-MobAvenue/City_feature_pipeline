STATE_TO_REGION = {
    "CT": "NE", "ME": "NE", "MA": "NE", "NH": "NE", "RI": "NE", "VT": "NE",
    "NJ": "NE", "NY": "NE", "PA": "NE",
    "IL": "MW", "IN": "MW", "MI": "MW", "OH": "MW", "WI": "MW",
    "IA": "MW", "KS": "MW", "MN": "MW", "MO": "MW", "NE": "MW", "ND": "MW", "SD": "MW",
    "DE": "S", "FL": "S", "GA": "S", "MD": "S", "NC": "S", "SC": "S", "VA": "S", "DC": "S", "WV": "S",
    "AL": "S", "KY": "S", "MS": "S", "TN": "S",
    "AR": "S", "LA": "S", "OK": "S", "TX": "S",
    "AZ": "W", "CO": "W", "ID": "W", "MT": "W", "NV": "W", "NM": "W", "UT": "W", "WY": "W",
    "AK": "W", "CA": "W", "HI": "W", "OR": "W", "WA": "W"
}

def get_region_for_state(state_code: str) -> str:
    return STATE_TO_REGION.get(state_code.upper(), "UNKNOWN")
