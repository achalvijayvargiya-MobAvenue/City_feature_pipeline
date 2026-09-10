#!/usr/bin/env python3
"""
Download state-level data from official sources.

Sources (data.gov.in) may block automated requests. Use manual download when needed.
Run from project root: python true_source/state_lookups/download_state_sources.py
"""
import os
import sys
import csv
import urllib.request
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = SCRIPT_DIR

# data.gov.in and other official sources
DATA_SOURCES = {
    "internet_penetration": "https://www.data.gov.in/resource/stateut-wise-details-internet-penetration-internet-subscribers-100-population-urbanrural",
    "cpi": "https://www.data.gov.in/resource/state-level-consumer-price-index-ruralurban-upto-january-2024",
    "median_age": "https://www.data.gov.in/catalog/projected-population-characteristics-0",
    "income_nsdp": "https://en.wikipedia.org/wiki/List_of_Indian_states_and_union_territories_by_GDP_per_capita",
    "digital_payment_upi": "https://dataful.in/datasets/21563/",
    "property_nhb_residex": "https://residex.nhbonline.org.in/",
}

# data.gov.in API (if available) - format: https://api.data.gov.in/resource/{resource_id}
# API key required: https://data.gov.in/


def main():
    print("Data download sources (income, digital payment, property):")
    print("=" * 60)
    for name, url in DATA_SOURCES.items():
        print(f"  {name}: {url}")
    print()
    print("Note: data.gov.in often requires manual download or API key.")
    print("Current curated CSVs in this folder are from published reports.")
    print()
    print("To update manually:")
    print("  1. Visit the URLs above")
    print("  2. Download CSV/Zip")
    print("  3. Place in state_lookups/ and rename to match expected format")
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
