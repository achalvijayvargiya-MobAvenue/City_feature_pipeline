import os
import requests
import zipfile
import logging
from pathlib import Path

# Try to use tqdm if available
try:
    from tqdm import tqdm
except ImportError:
    tqdm = None

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Using Cartographic Boundary Files (cb_) which are much smaller than TIGER/Line (tl_) and suitable for this task
# 2021/2020 are standard stable links. Update to 2023 if the census site stabilizes its links.
URLS = {
    "zcta": "https://www2.census.gov/geo/tiger/GENZ2020/shp/cb_2020_us_zcta520_500k.zip",
    "place": "https://www2.census.gov/geo/tiger/GENZ2021/shp/cb_2021_us_place_500k.zip",
    "county": "https://www2.census.gov/geo/tiger/GENZ2021/shp/cb_2021_us_county_500k.zip",
    "cbsa": "https://www2.census.gov/geo/tiger/GENZ2021/shp/cb_2021_us_cbsa_500k.zip"
}

def download_and_extract(url: str, name: str, dest_dir: Path):
    dest_dir.mkdir(parents=True, exist_ok=True)
    zip_path = dest_dir / f"{name}.zip"
    extract_dir = dest_dir / name
    
    if extract_dir.exists():
        logger.info(f"[{name}] already extracted at {extract_dir}")
        return

    logger.info(f"[{name}] Downloading from {url}")
    try:
        response = requests.get(url, stream=True)
        response.raise_for_status()
        
        total_size = int(response.headers.get('content-length', 0))
        
        with open(zip_path, 'wb') as f:
            if tqdm and total_size > 0:
                with tqdm(desc=name, total=total_size, unit='iB', unit_scale=True, unit_divisor=1024) as bar:
                    for data in response.iter_content(chunk_size=1024):
                        size = f.write(data)
                        bar.update(size)
            else:
                for data in response.iter_content(chunk_size=1024):
                    f.write(data)
                
        logger.info(f"[{name}] Extracting to {extract_dir}")
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(extract_dir)
            
        # Clean up zip
        os.remove(zip_path)
    except Exception as e:
        logger.error(f"Failed to download/extract {name}: {e}")

if __name__ == "__main__":
    data_dir = Path("data/reference/census")
    for name, url in URLS.items():
        download_and_extract(url, name, data_dir)
