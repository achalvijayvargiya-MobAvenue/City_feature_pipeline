# Step-by-Step: How "andher east" → Mumbai

## Example: Input = "andher east"

---

## Step 1: Normalize the input name

```
"andher east" → normalize → "andher east"
```
(Your `normalize_name()`: lowercase, strip accents, collapse spaces)

---

## Step 2: Search IN.txt for exact or fuzzy match

**Search in columns 2 (name) and 4 (alternatenames)**

```bash
# In IN.txt, search for "andher east" or "andheri east"
```

**Result found (line ~49565):**
```
7798655	Andheri East	Andheri East		19.11446	72.8712	P	PPL	IN		16	518	999	...
```

| Field | Value | Meaning |
|-------|-------|---------|
| geonameid | 7798655 | Unique ID |
| name | Andheri East | Official name |
| admin1_code | 16 | State code (Maharashtra) |
| admin2_code | 518 | District code (Mumbai Suburban) |
| feature_class | P | Populated place |
| feature_code | PPL | Village/locality |

**Note:** "andher east" needs fuzzy match → "Andheri East" (typo: missing 'i')

---

## Step 3: Resolve state from admin1_code

**admin1_code = 16** → Look up in `admin1CodesASCII.txt`

```
IN.16	Maharashtra	Maharashtra	1264418
```

**State = Maharashtra**

---

## Step 4: Resolve parent city from admin2_code

**admin2_code = 518** → District = Mumbai Suburban

You need `admin2Codes.txt` (download separately):
```
IN.16.518	Mumbai Suburban	Mumbai Suburban	1270836
```

**District = Mumbai Suburban**

---

## Step 5: Map district → parent city

**This is the missing piece.** GeoNames gives you district, not "parent city".

| District | Parent City |
|----------|-------------|
| Mumbai Suburban (518) | Mumbai |
| Mumbai (519) | Mumbai |
| Thane (517) | Thane |
| Pune | Pune |
| ... | ... |

**For Mumbai Suburban → Parent city = Mumbai**

---

## Final result

| Input | Resolved |
|-------|----------|
| city_original | andher east |
| city_normalized | andher east |
| **state_original** | Maharashtra |
| **canonical_city** | Mumbai |
| geonameid | 7798655 |
| match_source | geonames:exact |

---

## What you need to implement

1. **Load IN.txt** → Build lookup: `normalized_name → (geonameid, admin1, admin2, name, ...)`
   - Include `alternatenames` (col 4) — split by comma, normalize each, add to lookup

2. **Load admin1CodesASCII.txt** → `IN.XX → state_name`

3. **Load admin2Codes.txt** → `IN.XX.YYY → district_name`  
   - Download: https://download.geonames.org/export/dump/admin2Codes.txt

4. **District → City mapping** — Two options:
   - **Option A:** For most districts, district name = city name (Thane→Thane, Pune→Pune)
   - **Option B:** Curated table for metros: Mumbai Suburban→Mumbai, Delhi districts→Delhi, etc.

5. **Fuzzy match** for typos: "andher east" ≈ "andheri east" (RapidFuzz)

---

## Gaps in GeoNames

- **"andher east"** — Not in alternatenames; needs fuzzy match to "Andheri East"
- **District→City** — No built-in field; you must add this mapping
- **Ambiguity** — "Andheri" exists in multiple states (Maharashtra, Punjab, etc.); use population or admin2 to pick best match
