"""
Add country_code to India/USA feature CSVs; normalize USA income_bucket to L/M/H.

India income_bucket is left unchanged.
USA mapping: L→L, M→M, H→H, VH→H.

Note (USA thresholds): existing buckets were built roughly as
  L < $50K, M $50–100K, H $100–200K, VH ≥ $200K.
Target product bands use L < $40K, M $40–100K, H > $100K.
Without raw median income we cannot split old L at $40K; VH is folded into H only.

Outputs (new files; inputs not overwritten):
  USA/data/processed/pincode_data_ind_with_country.csv
  USA/data/processed/usa_city_features_36col_with_country.csv
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

PROCESSED = Path(__file__).resolve().parents[1] / "data" / "processed"

INDIA_IN = PROCESSED / "pincode_data_ind.csv"
USA_IN = PROCESSED / "usa_city_features_36col.csv"

INDIA_OUT = PROCESSED / "pincode_data_ind_with_country.csv"
USA_OUT = PROCESSED / "usa_city_features_36col_with_country.csv"

USA_INCOME_MAP = {
    "L": "L",
    "M": "M",
    "H": "H",
    "VH": "H",
}


def _normalize_usa_income(value: object) -> object:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    text = str(value).strip().upper()
    if text in {"", "NAN", "NONE", "NULL"}:
        return None
    return USA_INCOME_MAP.get(text, text)


def process_india(path_in: Path, path_out: Path) -> dict:
    df = pd.read_csv(path_in, dtype=str)
    n = len(df)
    income_before = df["income_bucket"].value_counts(dropna=False).to_dict() if "income_bucket" in df.columns else {}

    if "country_code" in df.columns:
        df = df.drop(columns=["country_code"])
    df.insert(0, "country_code", "IND")

    df.to_csv(path_out, index=False)
    income_after = df["income_bucket"].value_counts(dropna=False).to_dict() if "income_bucket" in df.columns else {}
    return {
        "rows": n,
        "out": str(path_out),
        "income_before": income_before,
        "income_after": income_after,
        "income_unchanged": income_before == income_after,
    }


def process_usa(path_in: Path, path_out: Path) -> dict:
    df = pd.read_csv(path_in, dtype=str)
    n = len(df)
    income_before = df["income_bucket"].value_counts(dropna=False).to_dict() if "income_bucket" in df.columns else {}

    if "country_code" in df.columns:
        df = df.drop(columns=["country_code"])
    df.insert(0, "country_code", "USA")

    if "income_bucket" in df.columns:
        df["income_bucket"] = df["income_bucket"].map(_normalize_usa_income)

    df.to_csv(path_out, index=False)
    income_after = df["income_bucket"].value_counts(dropna=False).to_dict() if "income_bucket" in df.columns else {}
    return {
        "rows": n,
        "out": str(path_out),
        "income_before": income_before,
        "income_after": income_after,
    }


def main() -> None:
    if not INDIA_IN.exists():
        raise FileNotFoundError(INDIA_IN)
    if not USA_IN.exists():
        raise FileNotFoundError(USA_IN)

    india = process_india(INDIA_IN, INDIA_OUT)
    usa = process_usa(USA_IN, USA_OUT)

    print("India")
    print(f"  rows={india['rows']:,}  country_code=IND")
    print(f"  income_bucket unchanged={india['income_unchanged']}")
    print(f"  income_bucket={india['income_after']}")
    print(f"  wrote {india['out']}")
    print("USA")
    print(f"  rows={usa['rows']:,}  country_code=USA")
    print(f"  income_bucket before={usa['income_before']}")
    print(f"  income_bucket after ={usa['income_after']}")
    print(f"  wrote {usa['out']}")
    print("Note: USA VH->H only; $50K vs $40K Low cutoff not applied (no raw income).")


if __name__ == "__main__":
    main()
