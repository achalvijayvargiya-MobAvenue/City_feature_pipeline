import pandas as pd
import zipfile
from pathlib import Path

check = ["11680", "11700", "11711", "11723", "01000", "03000", "00140", "11722", "11724", "11701"]

cur = pd.read_csv(r"C:\Code\City_Specs\USA\data\reference\crosswalk\curated_us_zips.csv", dtype=str)
cur["zip"] = cur["zip_code"].str.zfill(5)

hrsa = pd.read_excel(r"C:\Code\City_Specs\USA\data\reference\crosswalk\zip_to_zcta_hrsa.xlsx", dtype=str)
hrsa["zip"] = hrsa["ZIP_CODE"].str.zfill(5)

with zipfile.ZipFile(r"C:\Code\City_Specs\USA\data\reference\crosswalk\geonames_US.zip") as zf:
    with zf.open("US.txt") as f:
        gn = pd.read_csv(f, sep="\t", header=None, dtype=str, usecols=[1, 2, 4], names=["zip", "city", "state"])
gn["zip"] = gn["zip"].str.zfill(5)

valid = pd.read_csv(r"C:\Code\City_Specs\USA\data\processed\usa_rtb_zip_features_final_valid_v2.csv", dtype=str)
inv = pd.read_csv(r"C:\Code\City_Specs\USA\data\processed\usa_rtb_zip_features_final_invalid_v2.csv", dtype=str)
valid_z = set(valid["pincode"].str.zfill(5))
inv_z = set(inv["pincode"].str.zfill(5))

print("ZIP | curated | HRSA | GeoNames | valid_file | invalid_file | detail")
for z in check:
    c = cur[cur["zip"] == z]
    h = hrsa[hrsa["zip"] == z]
    g = gn[gn["zip"] == z]
    details = []
    if not h.empty:
        details.append(f"HRSA={h.iloc[0]['PO_NAME']}/{h.iloc[0]['STATE']}/{h.iloc[0].get('ZIP_TYPE','')}")
    if not c.empty:
        details.append(f"CUR={c.iloc[0]['city']}/{c.iloc[0]['state']}")
    if not g.empty:
        details.append(f"GEO={g.iloc[0]['city']}/{g.iloc[0]['state']}")
    print(
        f"{z} | {not c.empty} | {not h.empty} | {not g.empty} | {z in valid_z} | {z in inv_z} | {'; '.join(details)}"
    )

# Export proof table for ALL current invalid stubs
stubs = inv.copy()
stubs["pincode"] = stubs["pincode"].astype(str).str.zfill(5)
stubs["in_hrsa"] = stubs["pincode"].isin(set(hrsa["zip"]))
stubs["in_curated"] = stubs["pincode"].isin(set(cur["zip"]))
stubs["in_geonames"] = stubs["pincode"].isin(set(gn["zip"]))
stubs["proof_status"] = stubs.apply(
    lambda r: "found_in_reference_db" if (r["in_hrsa"] or r["in_curated"] or r["in_geonames"]) else "not_found_in_hrsa_curated_geonames",
    axis=1,
)

out = Path(r"C:\Code\City_Specs\USA\data\processed\invalid_zip_proof_audit.csv")
stubs[
    ["pincode", "postal_code", "in_hrsa", "in_curated", "in_geonames", "proof_status", "major_city", "state_original"]
].to_csv(out, index=False)

print("\nProof summary for invalid file:")
print(stubs["proof_status"].value_counts().to_string())
print("found count", int((stubs["proof_status"] == "found_in_reference_db").sum()))
print("not found count", int((stubs["proof_status"] == "not_found_in_hrsa_curated_geonames").sum()))
print("wrote", out)
