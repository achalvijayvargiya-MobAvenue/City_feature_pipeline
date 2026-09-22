"""Fix major_city Mc* casing typos on the latest USA deliverable.

Explicit overrides only (no generic Mc-titlecase):
  Mcdonald  -> McDonald
  Mcadoo    -> McAdoo
  Mcdaniel  -> McDaniel
  Mcalister -> McAlister
  Mcfaddin  -> McFaddin

Reads:  usa_city_features_36col_with_country_sexratio_india.csv
Writes: usa_city_features_36col_final.csv

Does not modify India data or the input file.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

PROCESSED = Path(__file__).resolve().parents[1] / "data" / "processed"
SRC = PROCESSED / "usa_city_features_36col_with_country_sexratio_india.csv"
OUT = PROCESSED / "usa_city_features_36col_final.csv"

CITY_FIXES = {
    "Mcdonald": "McDonald",
    "Mcadoo": "McAdoo",
    "Mcdaniel": "McDaniel",
    "Mcalister": "McAlister",
    "Mcfaddin": "McFaddin",
}


def main() -> None:
    if not SRC.exists():
        raise FileNotFoundError(SRC)

    df = pd.read_csv(SRC, dtype=str)
    n = len(df)

    before_counts = {
        bad: int((df["major_city"] == bad).sum()) for bad in CITY_FIXES
    }
    df["major_city"] = df["major_city"].replace(CITY_FIXES)
    after_counts = {
        bad: int((df["major_city"] == bad).sum()) for bad in CITY_FIXES
    }
    good_counts = {
        good: int((df["major_city"] == good).sum()) for good in CITY_FIXES.values()
    }

    df.to_csv(OUT, index=False)

    print(f"rows={n:,}")
    print(f"country_code={df['country_code'].dropna().unique().tolist()}")
    print("replacements (before -> after remaining bad):")
    for bad, good in CITY_FIXES.items():
        print(f"  {bad}: {before_counts[bad]} -> remaining_bad={after_counts[bad]}, {good}_total={good_counts[good]}")
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
