"""
Create 3 enrichment queues from zip_master and export first RTB final features CSV
from usa_city_features_rtb_expanded.csv.
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

PROCESSED = Path(__file__).resolve().parents[1] / "data" / "processed"

QUEUE_SPECS = {
    "queue_1_exact_zcta": {
        "priority": 1,
        "label": "exact_zcta",
        "sources": {"exact_zcta"},
        "enrichment_action": "full_scrape_download",
    },
    "queue_2_inherited": {
        "priority": 2,
        "label": "inherited",
        "sources": {
            "inherited_hrsa",
            "inherited_censusreporter",
            "inherited_nearest_zcta",
        },
        "enrichment_action": "inherit_then_patch_weak_fields",
    },
    "queue_3_unmapped_stub": {
        "priority": 3,
        "label": "unmapped_stub",
        "sources": {"unmapped_stub"},
        "enrichment_action": "validate_or_leave_unknown",
    },
}


def _z5(series: pd.Series) -> pd.Series:
    s = series.astype(str).str.strip().str.replace(r"\.0$", "", regex=True)
    s = s.str.replace(r"[^0-9]", "", regex=True)
    return s.str.zfill(5)


def build_queues_and_final() -> dict:
    master = pd.read_csv(PROCESSED / "zip_master.csv", dtype=str)
    expanded = pd.read_csv(PROCESSED / "usa_city_features_rtb_expanded.csv", dtype=str)

    master["postal_code"] = _z5(master["postal_code"])
    expanded["pincode"] = _z5(expanded["pincode"])

    source_to_queue = {}
    for qname, spec in QUEUE_SPECS.items():
        for src in spec["sources"]:
            source_to_queue[src] = qname

    master["enrichment_queue"] = master["feature_source"].map(source_to_queue)
    master["enrichment_priority"] = master["enrichment_queue"].map(
        {q: QUEUE_SPECS[q]["priority"] for q in QUEUE_SPECS}
    )
    master["enrichment_action"] = master["enrichment_queue"].map(
        {q: QUEUE_SPECS[q]["enrichment_action"] for q in QUEUE_SPECS}
    )

    queue_paths = {}
    queue_counts = {}
    for qname, spec in QUEUE_SPECS.items():
        qdf = master[master["enrichment_queue"] == qname].copy()
        qdf = qdf.sort_values("postal_code").reset_index(drop=True)
        path = PROCESSED / f"{qname}.csv"
        qdf.to_csv(path, index=False)
        queue_paths[qname] = str(path)
        queue_counts[qname] = int(len(qdf))

    # Final RTB table from expanded + queue metadata
    meta = master[
        [
            "postal_code",
            "enrichment_queue",
            "enrichment_priority",
            "enrichment_action",
        ]
    ].drop_duplicates("postal_code")

    final = expanded.merge(
        meta,
        left_on="pincode",
        right_on="postal_code",
        how="left",
    )
    if "postal_code" in final.columns:
        # keep pincode as canonical ZIP key; also expose postal_code alias for RTB
        final["postal_code"] = final["pincode"]
    else:
        final["postal_code"] = final["pincode"]

    # Stable column order: ids first, then original features, then enrichment metadata
    front = ["#", "postal_code", "pincode", "feature_source", "source_zcta",
             "enrichment_queue", "enrichment_priority", "enrichment_action"]
    rest = [c for c in final.columns if c not in front]
    final = final[front + rest]
    final["#"] = range(1, len(final) + 1)
    final = final.sort_values(["enrichment_priority", "postal_code"], kind="mergesort").reset_index(drop=True)
    final["#"] = range(1, len(final) + 1)

    final_path = PROCESSED / "usa_rtb_zip_features_final.csv"
    final.to_csv(final_path, index=False)

    # Queue summary only (ZIP keys) for operators
    summary = {
        "total_zips": int(len(master)),
        "final_rows": int(len(final)),
        "queue_counts": queue_counts,
        "queue_paths": queue_paths,
        "final_path": str(final_path),
        "notes": {
            "queue_1": "Full scrape/download candidates (exact ZCTA)",
            "queue_2": "Inherited ZIPs - patch weak fields only",
            "queue_3": "Unmapped stubs - validate before spending scrape budget",
            "final_file": "First RTB final export built from expanded feature table + queue tags",
        },
    }
    summary_path = PROCESSED / "enrichment_queues_summary.json"
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)
    summary["summary_path"] = str(summary_path)
    return summary


if __name__ == "__main__":
    print(json.dumps(build_queues_and_final(), indent=2))
