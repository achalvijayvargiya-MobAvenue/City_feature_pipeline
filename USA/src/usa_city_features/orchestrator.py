import logging
import pandas as pd
import geopandas as gpd
from pathlib import Path

from .config.loader import Config
from .storage.cache import LocalCache
from .sources.base import SourceRequest
from .sources.census import CensusAdapter
from .sources.faa import FAAAdapter
from .sources.bts import BTSAdapter
from .sources.fra import FRAAdapter
from .sources.bls import BLSAdapter
from .sources.marad import MARADAdapter
from .sources.noaa import NOAAAdapter

from .geography.spatial_join import SpatialJoiner
from .geography.regions import get_region_for_state
from .geography.state_capitals import is_state_capital, distance_to_state_capital
from .geography.manual_flags import resolve_boolean_flags

from .features.demographic_features import extract_demographic_features, get_population_bucket
from .features.infrastructure_features import (
    calculate_has_airport, calculate_has_metro_rail, calculate_has_major_railway,
    calculate_has_seaport, calculate_is_coastal
)
from .features.derived_features import (
    get_city_tier, calculate_digital_payment_index, calculate_smart_city_score,
    is_smart_city
)

from .storage.output import map_to_36_columns, export_dataset

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class PipelineOrchestrator:
    def __init__(self, config: Config):
        self.config = config
        self.cache = LocalCache(base_dir="data/raw")
        
        # Initialize Adapters
        self.census = CensusAdapter(self.cache)
        self.faa = FAAAdapter(self.cache)
        self.bts = BTSAdapter(self.cache)
        self.fra = FRAAdapter(self.cache)
        self.bls = BLSAdapter(self.cache)
        self.marad = MARADAdapter(self.cache)
        self.noaa = NOAAAdapter(self.cache)
        
        # Data containers
        self.zcta_gdf = None
        self.places_gdf = None
        self.counties_gdf = None
        self.cbsa_gdf = None
        
        self.census_data = []
        self.census_county_data = []
        self.faa_data = {}
        self.bts_data = {}
        self.fra_data = {}
        self.marad_data = {}
        self.noaa_data = {}
        
        self.internal_df = None

    def download(self):
        logger.info("Loading Geography Shapefiles...")
        base_ref = Path("data/reference/census")
        
        try:
            # Load and standardize shapefiles
            self.zcta_gdf = gpd.read_file(base_ref / "zcta" / "cb_2020_us_zcta520_500k.shp")
            self.places_gdf = gpd.read_file(base_ref / "place" / "cb_2021_us_place_500k.shp")
            self.counties_gdf = gpd.read_file(base_ref / "county" / "cb_2021_us_county_500k.shp")
            self.cbsa_gdf = gpd.read_file(base_ref / "cbsa" / "cb_2021_us_cbsa_500k.shp")
            
            # Standardize CRS to EPSG:4326
            for gdf in [self.zcta_gdf, self.places_gdf, self.counties_gdf, self.cbsa_gdf]:
                if gdf is not None and gdf.crs is None:
                    gdf.set_crs(epsg=4326, inplace=True)
                    
            # Rename columns to avoid collisions during spatial joins
            if self.places_gdf is not None:
                self.places_gdf = self.places_gdf[['geometry', 'NAME', 'STATEFP']].rename(columns={'NAME': 'place_name', 'STATEFP': 'state_fips'})
            if self.counties_gdf is not None:
                self.counties_gdf = self.counties_gdf[['geometry', 'NAME', 'STATEFP', 'COUNTYFP']].rename(columns={'NAME': 'county_name', 'STATEFP': 'county_state_fips', 'COUNTYFP': 'county_fips'})
            if self.cbsa_gdf is not None:
                self.cbsa_gdf = self.cbsa_gdf[['geometry', 'NAME']].rename(columns={'NAME': 'cbsa_name'})
                
        except Exception as e:
            logger.warning(f"Could not load all shapefiles. Did you run download_sources.py? Error: {e}")
            # Create dummy ZCTA for testing if missing
            if self.zcta_gdf is None:
                from shapely.geometry import Point
                self.zcta_gdf = gpd.GeoDataFrame({'ZCTA5CE20': ['90210']}, geometry=[Point(-118.4, 34.07)], crs="EPSG:4326")

        logger.info("Fetching Census Data...")
        req = SourceRequest(
            dataset=self.config.sources.census.acs_dataset,
            version=str(self.config.sources.census.acs_year),
            params={
                "get": "NAME,B01003_001E,B01002_001E,B01001_002E,B01001_026E,B19013_001E,B15003_001E,B15003_022E,B28001_001E,B28001_005E,B28002_002E",
                "for": "zip code tabulation area:*"
            }
        )
        try:
            res = self.census.fetch(req)
            self.census_data = self.census.parse_response(res)
            
            # Fetch County population for City Tier and District Population
            req_county = SourceRequest(
                dataset=self.config.sources.census.acs_dataset,
                version=str(self.config.sources.census.acs_year),
                params={
                    "get": "B01003_001E",
                    "for": "county:*"
                }
            )
            self.census_county_data = self.census.parse_response(self.census.fetch(req_county))
        except Exception as e:
            logger.error(f"Census fetch failed: {e}")

        logger.info("Fetching Infra Data...")
        try:
            self.faa_data = self.faa.fetch(SourceRequest(dataset="airports", version="v1")).data
            self.bts_data = self.bts.fetch(SourceRequest(dataset="transit", version="v1")).data
            self.fra_data = self.fra.fetch(SourceRequest(dataset="rail", version="v1")).data
            self.marad_data = self.marad.fetch(SourceRequest(dataset="ports", version="v1")).data
            self.noaa_data = self.noaa.fetch(SourceRequest(dataset="coastline", version="v1")).data
            
            # Fetch BLS CPI Data
            logger.info("Fetching BLS Data...")
            self.bls_data = self.bls.fetch_cpi(start_year="2024", end_year="2024").data
        except Exception as e:
            logger.error(f"Infra fetch failed: {e}")

    def build_geography(self):
        logger.info("Running Spatial Joins...")
        if self.zcta_gdf is None:
            return
            
        joiner = SpatialJoiner(self.places_gdf, self.counties_gdf, self.cbsa_gdf)
        
        if 'ZCTA5CE20' in self.zcta_gdf.columns:
            self.zcta_gdf = self.zcta_gdf.rename(columns={'ZCTA5CE20': 'zcta5'})
            
        logger.info("Assigning Places...")
        self.zcta_gdf = joiner.assign_place(self.zcta_gdf)
            
        logger.info("Assigning Counties...")
        self.zcta_gdf = joiner.assign_county(self.zcta_gdf)
        
        logger.info("Assigning CBSA (Metro)...")
        self.zcta_gdf = joiner.assign_cbsa(self.zcta_gdf)
        self.zcta_gdf['is_metro_city'] = self.zcta_gdf.get('cbsa_name', pd.Series(dtype=str)).notna()
        
        # Extract lat/lon for distance calculations (using centroid since ZCTAs are polygons)
        self.zcta_gdf['latitude'] = self.zcta_gdf.geometry.centroid.y
        self.zcta_gdf['longitude'] = self.zcta_gdf.geometry.centroid.x

    def build_features(self):
        logger.info("Calculating Features...")
        if self.zcta_gdf is None:
            return
            
        # 1. Merge Census Data
        census_df = pd.DataFrame(self.census_data)
        if not census_df.empty:
            census_df = census_df.rename(columns={'zip code tabulation area': 'zcta5'})
            df = self.zcta_gdf.merge(census_df, on='zcta5', how='left')
        else:
            df = self.zcta_gdf.copy()
            
        # Merge County Population
        county_df = pd.DataFrame(self.census_county_data)
        if not county_df.empty and 'county_fips' in df.columns:
            county_df = county_df.rename(columns={'state': 'county_state_fips', 'county': 'county_fips', 'B01003_001E': 'true_county_pop'})
            df = df.merge(county_df[['county_state_fips', 'county_fips', 'true_county_pop']], on=['county_state_fips', 'county_fips'], how='left')
            
        # 2. Infra Features
        logger.info("Calculating Infrastructure Buffers...")
        df = calculate_has_airport(df, self.faa_data)
        df = calculate_has_metro_rail(df, self.bts_data)
        df = calculate_has_major_railway(df, self.fra_data)
        df = calculate_has_seaport(df, self.marad_data)
        df = calculate_is_coastal(df, self.noaa_data)
        
        # 3. Apply Demographic & Derived Features
        vars_map = {
            "population": "B01003_001E",
            "median_age": "B01002_001E",
            "male_population": "B01001_002E",
            "female_population": "B01001_026E",
            "median_income": "B19013_001E",
            "population_25_plus": "B15003_001E",
            "population_hs_plus": "B15003_022E",
            "total_households": "B28001_001E",
            "smartphone_households": "B28001_005E",
            "internet_households": "B28002_002E"
        }
        
        fips_to_usps = {
            '01': 'AL', '02': 'AK', '04': 'AZ', '05': 'AR', '06': 'CA', '08': 'CO', '09': 'CT', '10': 'DE', 
            '11': 'DC', '12': 'FL', '13': 'GA', '15': 'HI', '16': 'ID', '17': 'IL', '18': 'IN', '19': 'IA', 
            '20': 'KS', '21': 'KY', '22': 'LA', '23': 'ME', '24': 'MD', '25': 'MA', '26': 'MI', '27': 'MN', 
            '28': 'MS', '29': 'MO', '30': 'MT', '31': 'NE', '32': 'NV', '33': 'NH', '34': 'NJ', '35': 'NM', 
            '36': 'NY', '37': 'NC', '38': 'ND', '39': 'OH', '40': 'OK', '41': 'OR', '42': 'PA', '44': 'RI', 
            '45': 'SC', '46': 'SD', '47': 'TN', '48': 'TX', '49': 'UT', '50': 'VT', '51': 'VA', '53': 'WA', 
            '54': 'WV', '55': 'WI', '56': 'WY'
        }
        
        records = []
        for idx, row in df.iterrows():
            demo = extract_demographic_features(row.to_dict(), vars_map)
            
            state_fips = row.get('state_fips')
            state_code = fips_to_usps.get(str(state_fips), "") if pd.notnull(state_fips) else ""
            region = get_region_for_state(state_code)
            
            lat = row.get('latitude')
            lon = row.get('longitude')
            
            dist_capital = distance_to_state_capital(lat, lon, state_code) if pd.notnull(lat) and state_code else None
            is_cap = is_state_capital(str(row.get('place_name', '')), state_code)
            
            # Use true county population for tier and district population, fallback to ZCTA pop
            true_county_pop = row.get('true_county_pop')
            if pd.notnull(true_county_pop):
                try:
                    pop = int(true_county_pop)
                except:
                    pop = demo.get('district_population_numeric')
            else:
                pop = demo.get('district_population_numeric')
                
            tier = get_city_tier(pop)
            pop_bucket = get_population_bucket(pop)
            
            # Use BLS CPI value if available, else fallback to mock
            cpi_val = 315.0
            if hasattr(self, 'bls_data') and self.bls_data:
                try:
                    # Parse the BLS JSON response to get the latest CPI value
                    series = self.bls_data.get("Results", {}).get("series", [])
                    if series and series[0].get("data"):
                        cpi_val = float(series[0]["data"][0]["value"])
                except Exception:
                    pass
            
            # Curated config overrides (India-style static lookups) when APIs are empty
            flags = resolve_boolean_flags(
                place_name=row.get('place_name'),
                state_fips=row.get('county_state_fips', row.get('state_fips')),
                county_fips=row.get('county_fips'),
                existing={
                    "has_airport": row.get('has_airport', False),
                    "has_international_airport": row.get('has_international_airport', False),
                    "has_metro_rail": row.get('has_metro_rail', False),
                    "has_seaport": row.get('has_seaport', False),
                    "major_railway_station": row.get('has_major_railway', False),
                    "is_coastal": row.get('is_coastal', False),
                },
            )

            dpi = calculate_digital_payment_index(
                demo.get('internet_penetration_state'),
                demo.get('smartphone_penetration_state'),
                demo.get('income_bucket'),
                row.get('is_metro_city', False)
            )
            
            it_hub = flags["is_it_hub"]
            mfg_hub = flags["is_manufacturing_hub"]
            
            smart_score = calculate_smart_city_score(
                flags["has_metro_rail"],
                flags["has_airport"],
                demo.get('internet_penetration_state'),
                demo.get('smartphone_penetration_state'),
                dpi,
                it_hub
            )
            
            record = {
                "zcta5": row.get('zcta5'),
                "state_code": state_code,
                "place_name": row.get('place_name'),
                "latitude": lat,
                "longitude": lon,
                "region": region,
                "is_coastal": flags["is_coastal"],
                "distance_to_state_capital_km": dist_capital,
                "city_tier": tier,
                "is_metro_city": row.get('is_metro_city', False),
                "is_smart_city": is_smart_city(smart_score),
                "is_state_capital": is_cap,
                "has_airport": flags["has_airport"],
                "has_international_airport": flags["has_international_airport"],
                "has_metro_rail": flags["has_metro_rail"],
                "has_seaport": flags["has_seaport"],
                "major_railway_station": flags["major_railway_station"],
                "digital_payment_index": dpi,
                "is_it_hub": it_hub,
                "is_manufacturing_hub": mfg_hub,
                "is_financial_center": flags["is_financial_center"],
                "is_textile_hub": flags["is_textile_hub"],
                "is_education_hub": flags["is_education_hub"],
                "is_tourist_city": flags["is_tourist_city"],
                "county_population": pop,
                "district_population": pop_bucket,
                "cpi_value": cpi_val
            }
            record.update(demo)
            # Override the ZCTA population with the true county population for the final output
            record["district_population_numeric"] = pop
            records.append(record)
            
        self.internal_df = pd.DataFrame(records)

    def validate(self):
        # Handled inside export_dataset
        pass

    def export(self, output_path: str):
        logger.info(f"Exporting to {output_path}...")
        if self.internal_df is None or self.internal_df.empty:
            logger.error("No data to export!")
            return
            
        final_df = map_to_36_columns(self.internal_df)
        report_path = str(Path(output_path).parent / "usa_city_features_quality_report.json")
        
        export_dataset(final_df, output_path, report_path)
        logger.info(f"Export complete. Quality report saved to {report_path}")

    def run(self, offline: bool = False, output_path: str = 'data/processed/usa_city_features.csv'):
        if offline:
            logger.info("Running in offline mode (using cached data)...")
            
        self.download()
        self.build_geography()
        self.build_features()
        self.validate()
        self.export(output_path)
