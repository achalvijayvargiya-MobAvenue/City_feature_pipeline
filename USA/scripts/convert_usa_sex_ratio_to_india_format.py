"""Convert USA sex_ratio to India format (females per 1000 males).

Formula: sex_ratio = 100000.0 / old_sex_ratio
  (inverts USA male/female*100 into female/male*1000)

Rules:
  - blank / null / non-numeric -> null
  - <= 0 -> null
  - else convert

Reads:  USA/data/processed/usa_city_features_36col_with_country.csv
Writes: USA/data/processed/usa_city_features_36col_with_country_sexratio_india.csv

Does not modify India data or the input file.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

PROCESSED = Path(__file__).resolve().parents[1] / "data" / "processed"
SRC = PROCESSED / "usa_city_features_36col_with_country.csv"
OUT = PROCESSED / "usa_city_features_36col_with_country_sexratio_india.csv"


def convert_sex_ratio(series: pd.Series) -> pd.Series:
    old = pd.to_numeric(series, errors="coerce")
    new = pd.Series(pd.NA, index=series.index, dtype="Float64")
    mask = old.notna() & (old > 0)
    new.loc[mask] = 100000.0 / old.loc[mask]
    return new


def main() -> None:
    if not SRC.exists():
        raise FileNotFoundError(SRC)

    df = pd.read_csv(SRC, dtype=str)
    n = len(df)
    old = pd.to_numeric(df["sex_ratio"], errors="coerce")
    null_before = int(old.isna().sum())
    nonpos = int(((old.notna()) & (old <= 0)).sum())

    new = convert_sex_ratio(df["sex_ratio"])
    df["sex_ratio"] = new
    df.to_csv(OUT, index=False)

    print(f"rows={n:,}")
    print(f"null_before={null_before} nonpos_before={nonpos} null_after={int(new.isna().sum())}")
    print(f"old_median={float(old.median()):.4f}")
    print(f"new_median={float(new.median()):.4f}")
    print(f"new_p25={float(new.quantile(0.25)):.4f} new_p75={float(new.quantile(0.75)):.4f}")
    print(f"country_code={df['country_code'].dropna().unique().tolist()}")

    sample_idx = old[old.notna() & (old > 0)].head(5).index
    for i in sample_idx:
        o = float(old.loc[i])
        nval = float(new.loc[i])
        print(f"  spot row {i}: old={o:.6f} new={nval:.6f} expect={100000.0 / o:.6f}")

    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
