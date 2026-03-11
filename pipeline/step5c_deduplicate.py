"""
step5c_deduplicate.py
─────────────────────────────────────────────────────────────────────────────
Removes duplicate city_original rows. Each city_original maps to multiple
major_city when step2 finds multiple matches. This step keeps exactly one
record per city_original by ranking duplicates and selecting the best.

Ranking (higher score = better):
  - population_density  (higher = more urban/developed)
  - sex_ratio          (higher = more balanced)
  - literacy_rate      (higher = more educated; state-level fallback if null)
  - city_tier          (Tier 1 > Tier 2 > Tier 3)
  - match_source       (exact > fuzzy)
  - distance_to_state_capital (lower = closer to capital)
  - is_metro_city, is_smart_city, has_airport, etc. (tiebreakers)

Output: one-to-one mapping — each city_original → exactly one major_city.
"""
import pandas as pd
from utils import normalize_state, print_step_header, coverage_report, print_value_counts, save_checkpoint


def _rank_row(row: pd.Series, state_literacy: dict) -> float:
    """
    Compute a composite score for ranking. Higher = better.
    """
    score = 0.0

    # population_density (higher better) — scale to 0–1000
    pop_dens = pd.to_numeric(row.get("population_density"), errors="coerce")
    if pd.notna(pop_dens) and pop_dens > 0:
        score += min(pop_dens / 50.0, 1000)  # cap at 1000

    # sex_ratio (higher better) — scale 0–500
    sex = pd.to_numeric(row.get("sex_ratio"), errors="coerce")
    if pd.notna(sex) and sex > 0:
        score += min(sex / 2.0, 500)

    # literacy_rate (higher better) — use state fallback if null
    lit = pd.to_numeric(row.get("literacy_rate"), errors="coerce")
    if pd.isna(lit) or lit <= 0:
        state = (row.get("state_original") or "").strip()
        state_n = normalize_state(state)
        lit = state_literacy.get(state_n)
    if pd.notna(lit) and lit > 0:
        score += lit * 5  # e.g. 80% -> 400

    # city_tier (Tier 1 > Tier 2 > Tier 3)
    tier = str(row.get("city_tier") or "").strip()
    if tier == "Tier 1":
        score += 300
    elif tier == "Tier 2":
        score += 200
    elif tier == "Tier 3":
        score += 100

    # match_source (exact > fuzzy)
    src = str(row.get("match_source") or "").lower()
    if "exact" in src:
        score += 50
    elif "fuzzy" in src:
        score += 20

    # distance_to_state_capital (lower = better) — invert so closer = higher
    dist = pd.to_numeric(row.get("distance_to_state_capital"), errors="coerce")
    if pd.notna(dist) and dist >= 0:
        score += max(0, 100 - dist / 10)  # 0 km -> +100, 1000 km -> 0

    # Tiebreakers
    if row.get("is_metro_city") in (True, "True", "true", "1"):
        score += 30
    if row.get("is_smart_city") in (True, "True", "true", "1"):
        score += 15
    if row.get("has_airport") in (True, "True", "true", "1"):
        score += 10
    if row.get("is_state_capital") in (True, "True", "true", "1"):
        score += 25

    return score


def run(df: pd.DataFrame, config: dict) -> pd.DataFrame:
    print_step_header(7, "Deduplicate — one city_original → one major_city")

    state_literacy = config.get("STATE_LITERACY_RATES", {})
    if isinstance(state_literacy, dict):
        state_literacy = {normalize_state(k): v for k, v in state_literacy.items()}

    rows_before = len(df)
    dup_count = df.duplicated(subset=["city_original"], keep=False).sum()
    unique_cities = df["city_original"].nunique()

    print(f"\n  Input rows           : {rows_before:,}")
    print(f"  Unique city_original : {unique_cities:,}")
    print(f"  Duplicate rows       : {dup_count:,}  (will be reduced to 1 per city)")

    if dup_count == 0 and rows_before == unique_cities:
        print("\n  No duplicates found. Passing through.")
        save_checkpoint(df, config["PATHS"]["checkpoints"], step=7)
        return df

    # Compute rank for each row
    df = df.copy()
    df["_rank"] = df.apply(lambda r: _rank_row(r, state_literacy), axis=1)

    # Group by city_original, keep row with highest rank
    best_idx = df.groupby("city_original", sort=False)["_rank"].idxmax()
    out_df = df.loc[best_idx].drop(columns=["_rank"], errors="ignore").reset_index(drop=True)

    rows_after = len(out_df)
    removed = rows_before - rows_after

    print(f"\n  Output rows           : {rows_after:,}")
    print(f"  Rows removed          : {removed:,}")
    print(f"  One-to-one mapping    : {out_df['city_original'].nunique():,} city_original → 1 major_city each")

    coverage_report(out_df, ["city_original", "major_city", "state_original", "population_density", "sex_ratio", "literacy_rate"])
    save_checkpoint(out_df, config["PATHS"]["checkpoints"], step=7)
    return out_df
