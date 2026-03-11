"""
run_pipeline.py
─────────────────────────────────────────────────────────────────────────────
Main orchestrator. Runs all steps in order, with checkpointing so you can
resume from any step without re-running earlier ones.

Usage:
  python run_pipeline.py                   # run all steps from scratch
  python run_pipeline.py --from-step 3     # resume from step 3
  python run_pipeline.py --only-step 5     # run a single step
  python run_pipeline.py --no-wiki         # skip Wikipedia API calls
  python run_pipeline.py --enable-llm      # enable LLM enrichment step

Output:
  checkpoints/step0X_output.csv   — intermediate outputs per step
  OutputData/city_features.csv    — final merged output
"""
import sys
import os
import argparse
import time
import pandas as pd

# Force UTF-8 output on Windows so non-ASCII city names print safely
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# ── Add pipeline directory to path ──────────────────────────────────────────
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import config as cfg
import step1_load_normalize
import step2_dataset_match
import step2b_geojson_validate
import step3_static_lookups
import step4_derived_fields
import step5_literacy
import step5b_district_census
import step5c_deduplicate
import step6_llm_enrichment
from utils import load_checkpoint, save_checkpoint, print_step_header, coverage_report, print_value_counts


# ──────────────────────────────────────────────────────────────────────────────
# Build runtime config dict from module-level constants
# ──────────────────────────────────────────────────────────────────────────────

def build_config(args) -> dict:
    c = {
        "PATHS":                       cfg.PATHS,
        "FUZZY_THRESHOLD":             cfg.FUZZY_THRESHOLD,
        "GEOPY_MAX_ROWS":              cfg.GEOPY_MAX_ROWS,
        "DISTRICT_TO_MAJOR_CITY":      cfg.DISTRICT_TO_MAJOR_CITY,
        "METRO_CITIES":                cfg.METRO_CITIES,
        "CAPITAL_CITIES":              cfg.CAPITAL_CITIES,
        "TIER2_CITIES":                cfg.TIER2_CITIES,
        "SMART_CITIES":                getattr(cfg, "SMART_CITIES", set()),
        "STATE_CAPITALS":              getattr(cfg, "STATE_CAPITALS", set()),
        "UT_CAPITALS":                 getattr(cfg, "UT_CAPITALS", set()),
        "CITIES_WITH_AIRPORT":         getattr(cfg, "CITIES_WITH_AIRPORT", set()),
        "CITIES_WITH_INTERNATIONAL_AIRPORT": getattr(cfg, "CITIES_WITH_INTERNATIONAL_AIRPORT", set()),
        "CITIES_WITH_METRO_RAIL":     getattr(cfg, "CITIES_WITH_METRO_RAIL", set()),
        "CITIES_WITH_SEAPORT":        getattr(cfg, "CITIES_WITH_SEAPORT", set()),
        "MAJOR_RAILWAY_STATION":       getattr(cfg, "MAJOR_RAILWAY_STATION", set()),
        "IT_HUB_CITIES":               getattr(cfg, "IT_HUB_CITIES", set()),
        "MANUFACTURING_HUB_CITIES":    getattr(cfg, "MANUFACTURING_HUB_CITIES", set()),
        "FINANCIAL_CENTER_CITIES":     getattr(cfg, "FINANCIAL_CENTER_CITIES", set()),
        "TEXTILE_HUB_CITIES":          getattr(cfg, "TEXTILE_HUB_CITIES", set()),
        "EDUCATION_HUB_CITIES":        getattr(cfg, "EDUCATION_HUB_CITIES", set()),
        "TOURIST_CITIES":              getattr(cfg, "TOURIST_CITIES", set()),
        "STATE_TO_REGION":             cfg.STATE_TO_REGION,
        "COASTAL_STATES":              cfg.COASTAL_STATES,
        "STATE_LITERACY_RATES":        cfg.STATE_LITERACY_RATES,
        "LLM_ENABLED":                 cfg.LLM_ENABLED or getattr(args, "enable_llm", False),
        "LLM_PROVIDER":                cfg.LLM_PROVIDER,
        "LLM_MODEL":                   cfg.LLM_MODEL,
        "LLM_API_KEY":                 cfg.LLM_API_KEY,
        "LLM_BATCH_SIZE":              cfg.LLM_BATCH_SIZE,
    }
    return c


# ──────────────────────────────────────────────────────────────────────────────
# Step registry
# ──────────────────────────────────────────────────────────────────────────────

def get_steps(config, args):
    wiki_enabled = not getattr(args, "no_wiki", False)
    return [
        (1, "Load & Normalize",       lambda df: step1_load_normalize.run(config)),
        (2, "Dataset Match",         lambda df: step2_dataset_match.run(df, config)),
        (3, "GeoJSON Validate",      lambda df: step2b_geojson_validate.run(df, config)),
        (4, "Static Lookups",        lambda df: step3_static_lookups.run(df, config)),
        (5, "Derived Fields",        lambda df: step4_derived_fields.run(df, config)),
        (6, "District Census",       lambda df: step5b_district_census.run(df, config)),
        (7, "Deduplicate",           lambda df: step5c_deduplicate.run(df, config)),
        (8, "Literacy Enrichment",   lambda df: step5_literacy.run(df, config, wiki_enabled=wiki_enabled)),
        (9, "LLM Enrichment",        lambda df: step6_llm_enrichment.run(df, config)),
    ]


# ──────────────────────────────────────────────────────────────────────────────
# Final report
# ──────────────────────────────────────────────────────────────────────────────

def print_final_report(df: pd.DataFrame):
    bar = "=" * 60
    print(f"\n{bar}")
    print(f"  FINAL PIPELINE REPORT")
    print(f"{bar}")
    print(f"\n  Total rows in output: {len(df):,}")

    coverage_report(df, cfg.OUTPUT_COLUMNS)

    print(f"\n  -- Field Distributions --")
    for col in ["city_tier", "geographic_region", "match_source", "literacy_source", "is_valid", "is_metro_city", "is_smart_city"]:
        print_value_counts(df, col, top_n=8)

    # Literacy stats
    lit = pd.to_numeric(df["literacy_rate"], errors="coerce")
    if lit.notna().any():
        print(f"\n  literacy_rate stats:")
        print(f"    min : {lit.min():.2f}%")
        print(f"    max : {lit.max():.2f}%")
        print(f"    mean: {lit.mean():.2f}%")
        print(f"    std : {lit.std():.2f}%")

    print(f"\n{bar}")


# ──────────────────────────────────────────────────────────────────────────────
# Save final output
# ──────────────────────────────────────────────────────────────────────────────

def save_final_output(df: pd.DataFrame, config: dict):
    # Reorder columns — keep extras at end
    cols = [c for c in cfg.OUTPUT_COLUMNS if c in df.columns]
    extras = [c for c in df.columns if c not in cols]
    df = df[cols + extras]

    out_path = config["PATHS"]["output"]
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    df.to_csv(out_path, index=False)
    print(f"\n  [OK] Final output saved -> {out_path}  ({len(df):,} rows)")


# ──────────────────────────────────────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="City Features ML Pipeline")
    parser.add_argument("--from-step",  type=int, default=1,
                        help="Resume from this step (1-9). Loads checkpoint from step N-1.")
    parser.add_argument("--only-step",  type=int, default=None,
                        help="Run only this single step and save its checkpoint.")
    parser.add_argument("--no-wiki",    action="store_true",
                        help="Skip Wikipedia API calls in step 7.")
    parser.add_argument("--enable-llm", action="store_true",
                        help="Enable LLM enrichment in step 8.")
    args = parser.parse_args()

    config     = build_config(args)
    steps      = get_steps(config, args)
    start_time = time.time()

    # ── Determine run range ───────────────────────────────────────────────
    only = args.only_step
    start = args.from_step if only is None else only

    if only is not None:
        run_steps = [s for s in steps if s[0] == only]
    else:
        run_steps = [s for s in steps if s[0] >= start]

    # ── Load checkpoint for the step before start ─────────────────────────
    df = None
    if start > 1:
        df = load_checkpoint(config["PATHS"]["checkpoints"], start - 1)
        if df is None:
            print(f"\n  [WARN] No checkpoint found for step {start-1}. Starting from step 1.")
            run_steps = steps

    # ── Execute steps ─────────────────────────────────────────────────────
    for step_num, step_name, step_fn in run_steps:
        t0 = time.time()
        df = step_fn(df)
        elapsed = time.time() - t0
        print(f"\n  [DONE] Step {step_num} completed in {elapsed:.1f}s")

    # ── Final output & report ─────────────────────────────────────────────
    if df is not None:
        print_final_report(df)
        save_final_output(df, config)

    total_time = time.time() - start_time
    print(f"\n  Total pipeline time: {total_time:.1f}s  ({total_time/60:.1f} min)")
    print("\n  Pipeline complete.\n")


if __name__ == "__main__":
    main()
