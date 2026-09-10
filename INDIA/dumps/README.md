# GeoNames Dump — India (IN)

Downloaded from [GeoNames Export](https://download.geonames.org/export/dump/).

## Files

| File | Description |
|------|-------------|
| **IN.txt** | ~660k places in India. Tab-delimited. |
| **admin1CodesASCII.txt** | Admin1 code → State name (e.g. IN.16 → Maharashtra) |
| **hierarchy.txt** | Parent-child relationships (parentId, childId, type) |

## IN.txt Column Layout

| Col | Field | Example |
|-----|-------|---------|
| 1 | geonameid | 1265495 |
| 2 | name | Kurla |
| 3 | asciiname | Kurla |
| 4 | alternatenames | Cooria,Kurla,krla,... |
| 5 | latitude | 19.07128 |
| 6 | longitude | 72.88304 |
| 7 | feature_class | P (populated), A (admin), H (hydro), ... |
| 8 | feature_code | PPL, PPLA, PPLA2, ADM2, ... |
| 9 | country_code | IN |
| 10 | cc2 | (alternate countries) |
| 11 | admin1_code | 16 (Maharashtra) |
| 12 | admin2_code | 518 (Mumbai Suburban) |
| 13 | admin3_code | |
| 14 | admin4_code | |
| 15 | population | 0 |
| 16 | elevation | |
| 17 | dem | |
| 18 | timezone | Asia/Kolkata |
| 19 | modification_date | 2024-05-22 |

## Feature Codes (relevant)

- **PPL** — populated place (village, locality)
- **PPLA** — seat of admin1 (state capital)
- **PPLA2** — seat of admin2 (district HQ)
- **ADM2** — admin division level 2 (district)

## Usage for City Mapping

1. **Exact match:** Normalize input name, lookup in `name` or `alternatenames`
2. **State resolution:** Use `admin1_code` + admin1CodesASCII → state name
3. **Parent city:** Use `hierarchy.txt` for parent of locality, or infer from district (admin2)

## Refresh

To re-download:

```bash
# From project root
Invoke-WebRequest -Uri "https://download.geonames.org/export/dump/IN.zip" -OutFile "dumps\IN.zip" -UseBasicParsing
Expand-Archive -Path "dumps\IN.zip" -DestinationPath "dumps" -Force
```

License: CC BY 4.0 — https://creativecommons.org/licenses/by/4.0/
