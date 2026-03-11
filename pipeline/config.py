"""
config.py — All paths, constants, and static lookup dictionaries.
Edit this file to change data sources, API keys, or classification logic.
"""
import os

# ─────────────────────────────────────────────
# PATHS
# ─────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

PATHS = {
    "input":            os.path.join(BASE_DIR, "InputData",    "city_name_20260310.csv"),
    "src_final_cities": os.path.join(BASE_DIR, "true_source",  "final_cities.csv"),
    "src_icd":          os.path.join(BASE_DIR, "true_source",  "Indian Cities Database.csv"),
    "src_census":       os.path.join(BASE_DIR, "true_source",  "census_population.csv"),
    "checkpoints":      os.path.join(BASE_DIR, "checkpoints"),
    "output":           os.path.join(BASE_DIR, "OutputData",   "city_features.csv"),
    "discarded":        os.path.join(BASE_DIR, "OutputData",   "discarded_cities.csv"),
    "unmatched":        os.path.join(BASE_DIR, "OutputData",   "unmatched_cities.csv"),
    "geonames_dump":    os.path.join(BASE_DIR, "dumps",        "IN.txt"),
    "geonames_admin1":  os.path.join(BASE_DIR, "dumps",        "admin1CodesASCII.txt"),
    "geonames_admin2":  os.path.join(BASE_DIR, "dumps",        "admin2Codes.txt"),
    # District boundaries for GeoJSON-based validation (replaces geopy)
    "dists_geojson":    os.path.join(BASE_DIR, "true_source",  "maps-master", "maps-master", "website", "docs", "data", "geojson", "dists11.geojson"),
    # District-level census data (literacy, sex_ratio, population_density)
    "dists_csv":       os.path.join(BASE_DIR, "true_source",  "maps-master", "maps-master", "website", "docs", "data", "csv", "dists.csv"),
}

# ─────────────────────────────────────────────
# LLM CONFIG  (OpenAI-compatible)
# ─────────────────────────────────────────────
LLM_PROVIDER   = "openai"          # "openai" | "anthropic"
LLM_MODEL      = "gpt-4o-mini"    # cheap + fast for bulk
LLM_API_KEY    = os.getenv("OPENAI_API_KEY", "")
LLM_BATCH_SIZE = 50               # cities per API call
LLM_ENABLED    = False            # set True to run LLM step

# ─────────────────────────────────────────────
# FUZZY MATCH THRESHOLD
# ─────────────────────────────────────────────
FUZZY_THRESHOLD = 85   # 0–100; lower = more matches but noisier

# Geopy validation: max rows to validate (None = all). Use e.g. 100 for quick testing.
GEOPY_MAX_ROWS = None  # Set to 100 for quick test; None for full run (~50+ hours with 185k unique coords)

# ─────────────────────────────────────────────
# GEOGRAPHIC: District → Major City (for localities in metro districts)
# Default: district name = city. Override here for metro areas.
# ─────────────────────────────────────────────
DISTRICT_TO_MAJOR_CITY = {
    "mumbai suburban": "Mumbai",
    "mumbai": "Mumbai",
    "central delhi": "Delhi",
    "north delhi": "Delhi",
    "south delhi": "Delhi",
    "east delhi": "Delhi",
    "north east delhi": "Delhi",
    "south west delhi": "Delhi",
    "north west delhi": "Delhi",
    "west delhi": "Delhi",
    "new delhi": "Delhi",
    "south east": "Delhi",  # Delhi district
    "shahdara": "Delhi",
}

# ─────────────────────────────────────────────
# STATIC LOOKUPS
# ─────────────────────────────────────────────

# Official HRA Tier-1 (X) cities — 7th Central Pay Commission
# Plus aspiration metros with significant metro areas
METRO_CITIES = {
    "delhi","new delhi",
    "mumbai","bombay",
    "chennai","madras",
    "kolkata","calcutta",
    "bengaluru","bangalore",
    "hyderabad",
    "ahmedabad",
    "pune",
    "surat",                # Major metro area, textile + manufacturing hub
    "jaipur",               # State capital, major tourist + retail hub
    "lucknow",              # State capital, major commercial center
    "kochi","cochin"        # Metro area, IT + tourism
}

# All state/UT capitals (both spellings where relevant)
CAPITAL_CITIES = {
    # States
    "srinagar", "jammu",          # J&K (summer/winter)
    "shimla",                      # Himachal Pradesh
    "chandigarh",                  # Punjab & Haryana
    "dehradun",                    # Uttarakhand
    "delhi", "new delhi",          # Delhi
    "jaipur",                      # Rajasthan
    "lucknow",                     # Uttar Pradesh
    "patna",                       # Bihar
    "ranchi",                      # Jharkhand
    "kolkata",                     # West Bengal
    "bhubaneswar",                 # Odisha
    "raipur",                      # Chhattisgarh
    "bhopal",                      # Madhya Pradesh
    "gandhinagar",                 # Gujarat
    "mumbai",                      # Maharashtra
    "panaji",                      # Goa
    "bengaluru", "bangalore",      # Karnataka
    "Chennai",                     # Tamil Nadu
    "amaravati",                   # Andhra Pradesh (new capital)
    "hyderabad",                   # Telangana
    "thiruvananthapuram",          # Kerala
    "gangtok",                     # Sikkim
    "itanagar",                    # Arunachal Pradesh
    "kohima",                      # Nagaland
    "imphal",                      # Manipur
    "aizawl",                      # Mizoram
    "agartala",                    # Tripura
    "shillong",                    # Meghalaya
    "dispur",                      # Assam (within Guwahati)
    "guwahati",                    # Assam (commonly cited)
    # UTs
    "leh",                         # Ladakh
    "daman",                       # Daman & Diu
    "puducherry", "pondicherry",   # Puducherry
    "kavaratti",                   # Lakshadweep
    "port blair",                  # Andaman & Nicobar
    "silvassa",                    # Dadra & NH
}

# HRA Tier-2 (Y) cities — 7th CPC gazette list (97 cities)
TIER2_CITIES = {
"agra","ajmer","aligarh","prayagraj","allahabad",
"amravati","amritsar","asansol","aurangabad","bareilly",
"belagavi","belgaum","bhavnagar","bhiwandi","bhopal",
"bhubaneswar","bikaner","bokaro","chandigarh","coimbatore",
"cuttack","dehradun","dhanbad","bhilai","durgapur",
"erode","faridabad","firozabad","ghaziabad","gorakhpur",
"gulbarga","kalaburagi","guntur","gurugram","gurgaon",
"guwahati","hubli","hubballi","dharwad","indore",
"jabalpur","jaipur","jalandhar","jammu","jamnagar",
"jamshedpur","jhansi","jodhpur","kakinada","kanpur",
"kochi","kolhapur","kollam","kozhikode","calicut",
"kurnool","lucknow","ludhiana","madurai","meerut",
"moradabad","mysuru","mysore","nagpur","nashik",
"nellore","noida","patna","puducherry","pondicherry",
"raipur","rajkot","rajahmundry","ranchi","rourkela",
"saharanpur","salem","sangli","shimla","siliguri",
"solapur","srinagar","surat","thiruvananthapuram",
"thrissur","tiruchirappalli","trichy","tirunelveli",
"tiruppur","tirupati","ujjain","vadodara","baroda",
"varanasi","banaras","vijayawada","visakhapatnam",
"vizag","warangal","mira bhayandar","vasai virar",
"navi mumbai","greater noida",
"alwar","udaipur","bhilwara","gaya","muzaffarpur",
"bilaspur","korba","gwalior","satna","ratlam"
}

# ─────────────────────────────────────────────
# SMART CITIES MISSION (100 cities)
# ─────────────────────────────────────────────
SMART_CITIES = {
    "ahmedabad", "ajmer", "allahabad", "prayagraj", "amritsar", "aurangabad",
    "belgaum", "belagavi", "bhopal", "bhubaneswar", "chandigarh", "chennai",
    "coimbatore", "davangere", "dhanbad", "dharamsala", "dholera", "greater warangal",
    "guwahati", "hubli", "hubballi", "indore", "jaipur", "jabalpur", "jalandhar",
    "kakinada", "karnal", "kochi", "kohima", "kota", "lucknow", "ludhiana",
    "madurai", "mangaluru", "mangalore", "mumbai", "nagpur", "nashik", "naya raipur",
    "new delhi", "delhi", "pimpri chinchwad", "port blair", "puducherry", "pondicherry",
    "raipur", "rajkot", "ranchi", "rewa", "sagar", "salem", "shimoga", "shivamogga",
    "silvassa", "solapur", "srinagar", "surat", "thane", "thiruvananthapuram",
    "tiruchirappalli", "trichy", "tirunelveli", "tiruppur", "ujjain", "vadodara",
    "varanasi", "vijayawada", "visakhapatnam", "vizag", "warangal", "pasighat",
    "itanagar", "imphal", "shillong", "aizawl", "kohima", "agartala", "gangtok",
    "namchi", "pasighat", "itagar", "imphal", "shillong", "aizawl", "agartala",
}

# State capitals (states only, not UTs)
STATE_CAPITALS = {
    "srinagar", "jammu", "shimla", "dehradun", "jaipur", "lucknow", "patna",
    "ranchi", "kolkata", "bhubaneswar", "raipur", "bhopal", "gandhinagar",
    "mumbai", "panaji", "bengaluru", "bangalore", "chennai", "amaravati",
    "hyderabad", "thiruvananthapuram", "gangtok", "itanagar", "kohima",
    "imphal", "aizawl", "agartala", "shillong", "dispur", "guwahati",
}

# Union Territory capitals
UT_CAPITALS = {
    "leh", "daman", "puducherry", "pondicherry", "kavaratti", "port blair",
    "silvassa", "chandigarh", "delhi", "new delhi",
}

# Cities with airports (major domestic/commercial airports)
CITIES_WITH_AIRPORT = {
    "agra", "ahmedabad", "amritsar", "aurangabad", "bengaluru", "bangalore",
    "bhopal", "bhubaneswar", "chandigarh", "chennai", "coimbatore", "dehradun",
    "delhi", "new delhi", "goa", "panaji", "guwahati", "hyderabad", "imphal",
    "indore", "jaipur", "jammu", "kolkata", "kochi", "cochin", "leh", "lucknow",
    "madurai", "mumbai", "nagpur", "patna", "pune", "raipur", "rajkot",
    "ranchi", "srinagar", "surat", "thiruvananthapuram", "trivandrum", 
    "tiruchirappalli", "trichy", "vadodara", "varanasi", "vijayawada", 
    "visakhapatnam", "vizag", "erode", "salem",
}

# Cities with international airports
CITIES_WITH_INTERNATIONAL_AIRPORT = {
    "ahmedabad", "amritsar", "bengaluru", "bangalore", "chennai", "cochin",
    "kochi", "delhi", "new delhi", "goa", "hyderabad", "kolkata", "mumbai",
    "trivandrum", "thiruvananthapuram", "guwahati", "srinagar", "jaipur",
    "lucknow", "mangaluru", "mangalore", "nagpur", "pune", "tiruchirappalli",
    "trichy", "visakhapatnam", "vizag", "gaya", "varanasi", "imphal",
    "surat", "vadodara", "coimbatore", "bhopal", "patna",
}

# Cities with metro rail (rapid transit/MRTS/metro under construction or operational)
CITIES_WITH_METRO_RAIL = {
    "delhi", "new delhi", "mumbai", "bengaluru", "bangalore", "chennai",
    "kolkata", "hyderabad", "jaipur", "kochi", "cochin", "lucknow", "nagpur", 
    "pune", "ahmedabad", "kanpur", "bhopal", "indore", "kozhikode", "calicut",
    "surat", "visakhapatnam", "vizag", "guwahati",
}

# Cities with seaports
CITIES_WITH_SEAPORT = {
    "mumbai", "chennai", "kolkata", "visakhapatnam", "vizag", "kochi",
    "mangaluru", "mangalore", "tuticorin", "paradip", "kandla", "mormugao",
    "ennore", "tuticorin", "port blair", "puducherry", "pondicherry",
}

# Major railway junction cities
MAJOR_RAILWAY_STATION = {
    "delhi", "mumbai", "chennai", "kolkata", "bangalore", "bengaluru",
    "hyderabad", "ahmedabad", "pune", "jaipur", "lucknow", "kanpur",
    "nagpur", "indore", "bhopal", "patna", "ranchi", "guwahati",
    "thiruvananthapuram", "kochi", "coimbatore", "madurai", "varanasi",
}

# IT hub cities (major software/IT hubs and BPOs)
IT_HUB_CITIES = {
    "bengaluru", "bangalore", "hyderabad", "chennai", "pune", "mumbai",
    "delhi", "noida", "gurugram", "gurgaon", "kolkata", "ahmedabad",
    "jaipur", "chandigarh", "kochi", "cochin", "thiruvananthapuram", "indore",
    "vadodara", "visakhapatnam", "vizag", "mysore", "mysuru", "kota", "lucknow",
}

# Manufacturing hub cities (auto, engineering, textiles, chemicals)
MANUFACTURING_HUB_CITIES = {
    "pune", "chennai", "bangalore", "bengaluru", "ahmedabad", "mumbai",
    "delhi", "gurugram", "gurgaon", "faridabad", "jaipur", "coimbatore",
    "ludhiana", "tiruppur", "surat", "vadodara", "nashik", "nagpur",
    "visakhapatnam", "vizag", "indore", "bhopal", "guwahati", "sangli",
    "belgaum", "belagavi", "kolhapur", "vapi", "aurangabad", "solapur",
}

# Financial center cities
FINANCIAL_CENTER_CITIES = {
    "mumbai", "delhi", "bangalore", "bengaluru", "chennai", "hyderabad",
    "kolkata", "pune", "ahmedabad", "gurugram", "gurgaon", "noida",
}

# Textile hub cities
TEXTILE_HUB_CITIES = {
    "surat", "ahmedabad", "tiruppur", "coimbatore", "ludhiana", "bhilwara",
    "kanpur", "indore", "jaipur", "mumbai", "erode", "salem",
}

# Education hub cities (universities, skill training, coaching hubs)
EDUCATION_HUB_CITIES = {
    "bangalore", "bengaluru", "pune", "chennai", "hyderabad", "delhi",
    "mumbai", "kolkata", "chandigarh", "jaipur", "bhopal", "allahabad",
    "prayagraj", "mysore", "mysuru", "coimbatore", "thiruvananthapuram",
    "kota", "indore", "lucknow", "patna", "varanasi", "banaras",
    "dehradun", "guwahati", "chandigarh", "shimla",
}

# Major tourist cities (heritage, nature, religious, wellness)
TOURIST_CITIES = {
    # Rajasthan
    "jaipur", "udaipur", "jodhpur", "jaisalmer", "ajmer", "pushkar",
    "bikaner", "khimsar", "mandawa", "palanpur", "bhilwara",
    # North India
    "agra", "varanasi", "banaras", "mathura", "vrindavan", "rishikesh",
    "haridwar", "dehradun", "shimla", "manali", "kasol", "palampur",
    "dharamshala", "mcleodganj", "amritsar", "chandigarh",
    # South India
    "kochi", "cochin", "munnar", "thekkady", "alleppey", "kottayam",
    "kumarakom", "thiruvananthapuram", "trivandrum",
    "mysore", "mysuru", "ooty", "coorg", "hampi", "hassan", "chikmagalur",
    "mahabalipuram", "pondicherry", "puducherry", "tirupati", "tiruvannamalai",
    "madurai", "thanjavur", "rameswaram",
    # East India
    "darjeeling", "kalimpong", "shillong", "guwahati", "assam",
    "kolkata",
    # West
    "goa", "panaji", "mumbai", "aurangabad", "ellora", "ajanta",
    "khajuraho", "indore", "mandu", "bhopal",
    # Ladakh
    "leh", "srinagar", "kashmir", "pahalgam", "gulmarg",
    # Specialized
    "nainital", "almora", "auli", "rishikesh",
}

# ─────────────────────────────────────────────
# STATE → GEOGRAPHIC REGION MAPPING
# ─────────────────────────────────────────────
STATE_TO_REGION = {
    # North
    "jammu & kashmir": "North",  "jammu and kashmir": "North",
    "ladakh": "North",
    "himachal pradesh": "North",
    "punjab": "North",
    "haryana": "North",
    "uttarakhand": "North",
    "uttar pradesh": "North",
    "delhi": "North",            "national capital territory of delhi": "North",
    "rajasthan": "North",
    "chandigarh": "North",

    # South
    "tamil nadu": "South",
    "kerala": "South",
    "karnataka": "South",
    "andhra pradesh": "South",
    "telangana": "South",
    "puducherry": "South",       "pondicherry": "South",
    "lakshadweep": "South",

    # East
    "west bengal": "East",
    "odisha": "East",            "orissa": "East",
    "bihar": "East",
    "jharkhand": "East",
    "sikkim": "East",
    "andaman and nicobar islands": "East",
    "andaman & nicobar": "East",

    # West
    "gujarat": "West",
    "maharashtra": "West",
    "goa": "West",
    "dadra and nagar haveli and daman and diu": "West",
    "dadra & nagar haveli": "West",
    "daman and diu": "West",     "daman & diu": "West",

    # Central
    "madhya pradesh": "Central",
    "chhattisgarh": "Central",

    # Northeast
    "assam": "Northeast",
    "meghalaya": "Northeast",
    "manipur": "Northeast",
    "mizoram": "Northeast",
    "nagaland": "Northeast",
    "tripura": "Northeast",
    "arunachal pradesh": "Northeast",
}

# ─────────────────────────────────────────────
# COASTAL DISTRICTS
# ─────────────────────────────────────────────
COASTAL_DISTRICTS = [
    # Gujarat
    "kutch", "jamnagar", "porbandar", "dwarka", "devbhoomi dwarka",
    "junagadh", "gir somnath", "bhavnagar", "amreli", "botad",
    "ahmedabad", "anand",

    # Maharashtra
    "mumbai", "mumbai suburban", "thane", "raigad", "ratnagiri", "sindhudurg",

    # Goa
    "north goa", "south goa",

    # Karnataka
    "uttara kannada", "dakshina kannada", "udupi",

    # Kerala
    "thiruvananthapuram", "trivandrum", "kollam", "pathanamthitta",
    "alappuzha", "kottayam", "ernakulam", "kochi", "cochin",
    "thrissur", "malappuram", "kozhikode", "calicut", "kannur", "kasaragod",

    # Tamil Nadu
    "kanyakumari", "tirunelveli", "tuticorin", "thoothukudi",
    "ramanathapuram", "puducherry", "villupuram", "chengalpattu",
    "kanchipuram", "tiruvallur", "ranipet", "vellore", "chennai", "madras",

    # Andhra Pradesh
    "nellore", "tirupati", "chittoor", "bapatla", "guntur", "krishna",
    "west godavari", "east godavari", "visakhapatnam", "vizag",
    "vizianagaram", "srikakulam",

    # Odisha
    "balasore", "baleswar", "bhadrak", "kendrapara", "jagatsinghpur",
    "cuttack", "khordha", "puri", "ganjam", "gajapati",

    # West Bengal
    "north 24 parganas", "south 24 parganas", "hooghly",
    "east medinipur", "west medinipur",

    # Puducherry (UT)
    "puducherry", "pondicherry", "karaikal", "mahe", "yanam",

    # Lakshadweep (UT)
    "lakshadweep", "kavaratti", "agatti", "amini", "androth", "minicoy",

    # Andaman & Nicobar (UT)
    "north and middle andaman", "south andaman", "nicobar", "port blair",

    # Daman & Diu (UT)
    "daman", "diu",
]

# ─────────────────────────────────────────────
# STATE-LEVEL LITERACY RATES (Census 2011 fallback)
# ─────────────────────────────────────────────
STATE_LITERACY_RATES = {
    "kerala": 93.91,
    "lakshadweep": 92.28,
    "mizoram": 91.58,
    "tripura": 87.22,
    "goa": 88.70,
    "daman and diu": 87.07,  "daman & diu": 87.07,
    "puducherry": 86.55,     "pondicherry": 86.55,
    "chandigarh": 86.43,
    "delhi": 86.34,          "national capital territory of delhi": 86.34,
    "andaman and nicobar islands": 86.27, "andaman & nicobar": 86.27,
    "himachal pradesh": 83.78,
    "maharashtra": 82.91,
    "sikkim": 82.20,
    "nagaland": 80.11,
    "tamil nadu": 80.33,
    "manipur": 79.85,
    "gujarat": 79.31,
    "uttarakhand": 79.63,
    "punjab": 76.68,
    "haryana": 76.64,
    "west bengal": 77.08,
    "dadra and nagar haveli and daman and diu": 77.65,
    "dadra & nagar haveli": 77.65,
    "karnataka": 75.60,
    "meghalaya": 75.48,
    "assam": 73.18,
    "odisha": 73.45,          "orissa": 73.45,
    "chhattisgarh": 71.04,
    "madhya pradesh": 70.63,
    "telangana": 66.54,
    "andhra pradesh": 67.41,
    "uttar pradesh": 67.70,
    "arunachal pradesh": 66.95,
    "jharkhand": 66.41,
    "rajasthan": 66.11,
    "jammu & kashmir": 68.74, "jammu and kashmir": 68.74,
    "ladakh": 58.00,
    "bihar": 63.82,
}

# ─────────────────────────────────────────────
# OUTPUT COLUMN ORDER (aligned with InputData/feature_list.txt)
# ─────────────────────────────────────────────
OUTPUT_COLUMNS = [
    # Core identifiers
    "city_original",
    "city_normalized",
    "state_original",
    "major_city",
    "match_source",
    # Geographic
    "latitude",
    "longitude",
    "state",
    "region",
    "geographic_region",
    "is_valid",
    "coastal_city",
    "distance_to_state_capital",
    # Classification
    "city_tier",
    "is_metro_city",
    "is_smart_city",
    "is_state_capital",
    "is_union_territory_capital",
    # Demographics (Census)
    "city_population",
    "population_density",
    "literacy_rate",
    "sex_ratio",
    "literacy_source",
    # Demographics (projected/estimated)
    "median_age_estimate",
    # Economic
    "consumer_price_index",
    "income_bucket",
    "avg_property_price",
    # Infrastructure
    "has_airport",
    "has_international_airport",
    "has_metro_rail",
    "has_seaport",
    "major_railway_station",
    "national_highway_access",
    # Digital
    "internet_penetration_state",
    "smartphone_penetration_state",
    "digital_payment_index",
    # Industry
    "is_it_hub",
    "is_manufacturing_hub",
    "is_financial_center",
    "is_textile_hub",
    "is_education_hub",
    "is_tourist_city",
]

# ─────────────────────────────────────────────
# FEATURE GENERATION MAPPING
# ─────────────────────────────────────────────
# Maps hardcoded variable names to output columns that will be generated
FEATURE_MAPPING = {
    "METRO_CITIES":                        "is_metro_city",
    "CAPITAL_CITIES/STATE_CAPITALS":       "is_state_capital",
    "UT_CAPITALS":                         "is_union_territory_capital",
    "TIER2_CITIES":                        "city_tier",  # Tier 1 vs Tier 2 classification
    "SMART_CITIES":                        "is_smart_city",
    "CITIES_WITH_AIRPORT":                 "has_airport",
    "CITIES_WITH_INTERNATIONAL_AIRPORT":   "has_international_airport",
    "CITIES_WITH_METRO_RAIL":              "has_metro_rail",
    "CITIES_WITH_SEAPORT":                 "has_seaport",
    "MAJOR_RAILWAY_STATION":               "major_railway_station",
    "IT_HUB_CITIES":                       "is_it_hub",
    "MANUFACTURING_HUB_CITIES":            "is_manufacturing_hub",
    "FINANCIAL_CENTER_CITIES":             "is_financial_center",
    "TEXTILE_HUB_CITIES":                  "is_textile_hub",
    "EDUCATION_HUB_CITIES":                "is_education_hub",
    "TOURIST_CITIES":                      "is_tourist_city",
    "STATE_TO_REGION":                     "geographic_region",
    "COASTAL_DISTRICTS":                   "coastal_city",  # District-level mapping
    "STATE_LITERACY_RATES":                "literacy_rate",
}

# ─────────────────────────────────────────────
# FEATURE COMPUTATION NOTES
# ─────────────────────────────────────────────
"""
FEATURES COMPUTED FROM HARDCODED LISTS:

1. **City Tier Classification**:
   - if city in METRO_CITIES → city_tier = "Tier 1 Metro"
   - elif city in TIER2_CITIES → city_tier = "Tier 2"
   - else → city_tier = "Tier 3 / Smaller"

2. **Boolean Infrastructure Flags** (all direct lookup):
   - is_metro_city ← METRO_CITIES
   - is_state_capital ← STATE_CAPITALS
   - is_union_territory_capital ← UT_CAPITALS
   - is_smart_city ← SMART_CITIES
   - has_airport ← CITIES_WITH_AIRPORT
   - has_international_airport ← CITIES_WITH_INTERNATIONAL_AIRPORT
   - has_metro_rail ← CITIES_WITH_METRO_RAIL
   - has_seaport ← CITIES_WITH_SEAPORT
   - major_railway_station ← MAJOR_RAILWAY_STATION (boolean)

3. **Industry/Specialization Flags**:
   - is_it_hub ← IT_HUB_CITIES
   - is_manufacturing_hub ← MANUFACTURING_HUB_CITIES
   - is_financial_center ← FINANCIAL_CENTER_CITIES
   - is_textile_hub ← TEXTILE_HUB_CITIES
   - is_education_hub ← EDUCATION_HUB_CITIES
   - is_tourist_city ← TOURIST_CITIES

4. **Geographic Features**:
   - geographic_region ← STATE_TO_REGION (after state matching)
   - coastal_city ← COASTAL_DISTRICTS (district-level lookup)
     * Returns True if district_normalized in COASTAL_DISTRICTS, else False

5. **Demographic Features**:
   - literacy_rate (fallback) ← STATE_LITERACY_RATES (if district-level unavailable)

6. **Direct Lookups** (for derivation):
   - DISTRICT_TO_MAJOR_CITY ← used for major_city disambiguation in metro areas
"""
