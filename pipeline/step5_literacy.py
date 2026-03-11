"""
step5_literacy.py
─────────────────────────────────────────────────────────────────────────────
Resolves literacy_rate using a two-tier strategy:

  Tier A — Wikipedia API
    Queries the MediaWiki REST API for each UNIQUE city that was matched to a
    state.  Parses the article wikitext for a literacy figure.
    Results are cached to  checkpoints/wiki_literacy_cache.csv  so reruns are
    free.  Rate-limited to ~1 req/sec to be polite.

  Tier B — State-level Census 2011 average (fallback)
    For cities where Wikipedia returned nothing, we assign the state-level
    literacy average from config.STATE_LITERACY_RATES.

Fills:
  literacy_rate    — float (percent, e.g. 83.78)
  literacy_source  — "wikipedia" | "state_average" | "unresolved"
"""
import re
import time
import os
import requests
import pandas as pd
from utils import normalize_state, print_step_header, coverage_report, save_checkpoint

WIKI_API = "https://en.wikipedia.org/w/api.php"
CACHE_FILE_NAME = "wiki_literacy_cache.csv"

# Regex patterns to extract literacy % from wikitext / plain text
LITERACY_PATTERNS = [
    r"literacy[^0-9]{0,40}?(\d{2,3}(?:\.\d{1,2})?)\s*%",
    r"(\d{2,3}(?:\.\d{1,2})?)\s*%[^0-9]{0,40}?literate",
    r"literacy\s*rate[^0-9]{0,30}(\d{2,3}(?:\.\d{1,2})?)",
]


# ──────────────────────────────────────────────────────────────────────────────
# Wikipedia helpers
# ──────────────────────────────────────────────────────────────────────────────

def _query_wikipedia(city: str, state: str) -> float | None:
    """
    Try querying Wikipedia for '<city>, <state>' then just '<city>'.
    Returns literacy rate as float or None.
    """
    queries = [f"{city}, {state}", city]
    for q in queries:
        try:
            # Step 1 — resolve exact page title via search
            search_resp = requests.get(
                WIKI_API,
                params={"action": "query", "list": "search", "srsearch": q,
                        "srlimit": 1, "format": "json"},
                timeout=10,
            )
            hits = search_resp.json().get("query", {}).get("search", [])
            if not hits:
                continue
            title = hits[0]["title"]

            # Step 2 — fetch page wikitext (revisions)
            content_resp = requests.get(
                WIKI_API,
                params={"action": "query", "titles": title, "prop": "revisions",
                        "rvprop": "content", "rvslots": "main",
                        "rvsection": 0, "format": "json"},
                timeout=15,
            )
            pages = content_resp.json().get("query", {}).get("pages", {})
            for page in pages.values():
                text = (page.get("revisions", [{}])[0]
                           .get("slots", {}).get("main", {})
                           .get("*", ""))
                rate = _parse_literacy(text)
                if rate is not None:
                    return rate
        except Exception:
            pass
    return None


def _parse_literacy(text: str) -> float | None:
    """Extract literacy rate float from wikitext snippet."""
    text_lower = text.lower()
    for pattern in LITERACY_PATTERNS:
        m = re.search(pattern, text_lower)
        if m:
            val = float(m.group(1))
            if 20.0 <= val <= 100.0:   # sanity check
                return round(val, 2)
    return None


# ──────────────────────────────────────────────────────────────────────────────
# Cache helpers
# ──────────────────────────────────────────────────────────────────────────────

def _load_cache(checkpoints_dir: str) -> dict:
    path = os.path.join(checkpoints_dir, CACHE_FILE_NAME)
    if os.path.exists(path):
        cache_df = pd.read_csv(path, dtype=str)
        cache = {}
        for _, row in cache_df.iterrows():
            val = row.get("literacy_rate")
            cache[row["city_key"]] = float(val) if pd.notna(val) and val != "" else None
        print(f"  Loaded Wikipedia cache: {len(cache):,} entries from {path}")
        return cache
    return {}


def _save_cache(cache: dict, checkpoints_dir: str):
    path = os.path.join(checkpoints_dir, CACHE_FILE_NAME)
    rows = [{"city_key": k, "literacy_rate": v} for k, v in cache.items()]
    pd.DataFrame(rows).to_csv(path, index=False)


# ──────────────────────────────────────────────────────────────────────────────
# Main step function
# ──────────────────────────────────────────────────────────────────────────────

def run(df: pd.DataFrame, config: dict, wiki_enabled: bool = True) -> pd.DataFrame:
    print_step_header(8, "Literacy Rate — Wikipedia API + State Average Fallback")

    state_literacy = config["STATE_LITERACY_RATES"]
    checkpoints    = config["PATHS"]["checkpoints"]
    cache          = _load_cache(checkpoints)

    lit_col    = df["literacy_rate"].tolist()
    src_col    = df["literacy_source"].tolist()

    wiki_hits  = 0
    state_hits = 0
    unresolved = 0
    wiki_calls = 0

    # ── Identify unique (city, state) pairs that need Wikipedia lookup ────
    need_wiki = (
        df["state_original"].notna() &
        df["literacy_rate"].isna()
    )
    unique_pairs = (
        df[need_wiki][["city_normalized", "state_original"]]
        .drop_duplicates()
        .values.tolist()
    )
    print(f"\n  Cities needing literacy resolution : {need_wiki.sum():,}")
    print(f"  Unique (city, state) pairs         : {len(unique_pairs):,}")
    if wiki_enabled:
        print(f"  Wikipedia API: ENABLED  (cache has {len(cache):,} entries)")
    else:
        print(f"  Wikipedia API: DISABLED  (skipping to state average)")

    for i, row in enumerate(df.itertuples(index=False)):
        # Skip if already has a real numeric value
        val = lit_col[i]
        if val is not None and not (isinstance(val, float) and pd.isna(val)):
            try:
                float(val)   # covers str like "83.78" loaded from checkpoint
                continue
            except (TypeError, ValueError):
                pass

        city_n  = row.city_normalized if isinstance(row.city_normalized, str) else ""
        state   = row.state_original  if isinstance(row.state_original, str)  else ""
        state_n = normalize_state(state)

        # ── Tier A: Wikipedia ─────────────────────────────────────────────
        if wiki_enabled and city_n:
            cache_key = f"{city_n}|{state_n}"

            if cache_key not in cache:
                rate = _query_wikipedia(city_n, state)
                cache[cache_key] = rate
                wiki_calls += 1
                time.sleep(0.5)   # polite rate limit

                # Save cache every 100 new calls
                if wiki_calls % 100 == 0:
                    _save_cache(cache, checkpoints)
                    print(f"    ...{wiki_calls} Wikipedia calls made so far")
            else:
                rate = cache[cache_key]

            if rate is not None:
                lit_col[i]  = rate
                src_col[i]  = "wikipedia"
                wiki_hits  += 1
                continue

        # ── Tier B: State average ─────────────────────────────────────────
        if state_n and state_n in state_literacy:
            lit_col[i]  = state_literacy[state_n]
            src_col[i]  = "state_average"
            state_hits += 1
            continue

        # ── Unresolved ────────────────────────────────────────────────────
        src_col[i]  = "unresolved"
        unresolved += 1

    # Save updated cache
    if wiki_enabled and wiki_calls > 0:
        _save_cache(cache, checkpoints)
        print(f"\n  Wikipedia API calls made  : {wiki_calls:,}")

    df["literacy_rate"]   = lit_col
    df["literacy_source"] = src_col

    # ── Summary ───────────────────────────────────────────────────────────
    total    = len(df)
    resolved = df["literacy_rate"].notna().sum()
    print(f"\n  Resolved via Wikipedia    : {wiki_hits:>8,}")
    print(f"  Resolved via state avg    : {state_hits:>8,}")
    print(f"  Unresolved                : {unresolved:>8,}")
    print(f"  Total literacy_rate filled: {resolved:>8,} / {total:,}  ({resolved/total*100:.1f}%)")

    coverage_report(df, ["literacy_rate", "literacy_source"])
    save_checkpoint(df, config["PATHS"]["checkpoints"], step=8)
    return df
