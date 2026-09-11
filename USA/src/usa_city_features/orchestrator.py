import logging
from .config.loader import Config

logger = logging.getLogger(__name__)

class PipelineOrchestrator:
    def __init__(self, config: Config):
        self.config = config

    def download(self):
        print("Loading ZCTAs...")
        print("Fetching Census Data...")
        print("Fetching Infra Data...")

    def build_geography(self):
        print("Running Spatial Joins...")

    def build_features(self):
        print("Calculating Features...")

    def validate(self):
        print("Validating dataset...")

    def export(self, output_path: str):
        print(f"Exporting to {output_path}...")

    def run(self, offline: bool = False, output_path: str = 'data/processed/usa_city_features.csv'):
        # Step-by-step sequential execution
        if offline:
            print("Running in offline mode (skipping remote downloads if possible)...")
            
        self.download()
        self.build_geography()
        self.build_features()
        self.validate()
        self.export(output_path)
