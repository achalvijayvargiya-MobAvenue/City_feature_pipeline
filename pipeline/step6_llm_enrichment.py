"""
step6_llm_enrichment.py
─────────────────────────────────────────────────────────────────────────────
Uses an LLM (OpenAI GPT or Anthropic Claude) to fill fields that are still
missing after all previous steps.  Targeted at:

  • state_original   — cities completely unmatched by datasets
  • literacy_rate    — cities where state could not be resolved

Sends cities in batches of LLM_BATCH_SIZE to minimise API calls and cost.
Each batch response is a JSON array — parsed and merged back row-by-row.

Set LLM_ENABLED = True  in config.py to activate this step.
Set your API key as env var:  OPENAI_API_KEY  or  ANTHROPIC_API_KEY
"""
import os
import json
import time
import pandas as pd
from utils import normalize_state, print_step_header, coverage_report, print_value_counts, save_checkpoint


# ──────────────────────────────────────────────────────────────────────────────
# Prompt builder
# ──────────────────────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """You are an expert on Indian geography.
For each Indian city/town/village name provided, return a JSON array where each element has:
  "city"           : the input city name (unchanged)
  "state"          : Indian state or UT name (English, official name). null if not Indian.
  "literacy_rate"  : estimated literacy rate as a number (0-100). Use Census 2011 data if known. null if unknown.

Return ONLY valid JSON. No explanation, no markdown fences."""

USER_PROMPT_TEMPLATE = """Provide data for these Indian cities:
{city_list}

Return a JSON array with one object per city, fields: city, state, literacy_rate."""


def _build_user_prompt(cities: list[str]) -> str:
    city_list = "\n".join(f"- {c}" for c in cities)
    return USER_PROMPT_TEMPLATE.format(city_list=city_list)


# ──────────────────────────────────────────────────────────────────────────────
# LLM callers
# ──────────────────────────────────────────────────────────────────────────────

def _call_openai(cities: list[str], model: str, api_key: str) -> list[dict]:
    from openai import OpenAI
    client   = OpenAI(api_key=api_key)
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user",   "content": _build_user_prompt(cities)},
        ],
        temperature=0,
        response_format={"type": "json_object"},
    )
    raw = response.choices[0].message.content
    data = json.loads(raw)
    # GPT sometimes wraps in {"cities": [...]} or {"data": [...]}
    if isinstance(data, dict):
        data = next(iter(data.values()))
    return data if isinstance(data, list) else []


def _call_anthropic(cities: list[str], model: str, api_key: str) -> list[dict]:
    import anthropic
    client   = anthropic.Anthropic(api_key=api_key)
    response = client.messages.create(
        model=model,
        max_tokens=4096,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": _build_user_prompt(cities)}],
    )
    raw  = response.content[0].text.strip()
    # Strip markdown fences if present
    raw  = raw.strip("```json").strip("```").strip()
    data = json.loads(raw)
    if isinstance(data, dict):
        data = next(iter(data.values()))
    return data if isinstance(data, list) else []


def _call_llm(cities: list[str], config: dict) -> list[dict]:
    provider = config.get("LLM_PROVIDER", "openai").lower()
    model    = config.get("LLM_MODEL", "gpt-4o-mini")
    api_key  = config.get("LLM_API_KEY", "")

    if provider == "anthropic":
        return _call_anthropic(cities, model, api_key)
    return _call_openai(cities, model, api_key)


# ──────────────────────────────────────────────────────────────────────────────
# Main step function
# ──────────────────────────────────────────────────────────────────────────────

def run(df: pd.DataFrame, config: dict) -> pd.DataFrame:
    print_step_header(9, "LLM Enrichment — Fill Remaining Gaps")

    if not config.get("LLM_ENABLED", False):
        print("\n  LLM_ENABLED = False in config.py — skipping this step.")
        print("  To enable: set LLM_ENABLED = True and provide your API key.")
        save_checkpoint(df, config["PATHS"]["checkpoints"], step=9)
        return df

    if not config.get("LLM_API_KEY", ""):
        print("\n  [WARN] LLM_API_KEY is not set. Skipping LLM step.")
        save_checkpoint(df, config["PATHS"]["checkpoints"], step=9)
        return df

    batch_size = config.get("LLM_BATCH_SIZE", 50)
    state_lr   = config["STATE_LITERACY_RATES"]

    # ── Find rows that still have gaps ───────────────────────────────────
    needs_state = df["state_original"].isna() | (df["state_original"] == "") | (df["match_source"] == "unresolved")
    gap_df      = df[needs_state].copy()
    total_gaps  = len(gap_df)

    print(f"\n  Rows missing state_original: {total_gaps:,}")
    if total_gaps == 0:
        print("  Nothing to do — all rows resolved!")
        save_checkpoint(df, config["PATHS"]["checkpoints"], step=9)
        return df

    cities_to_resolve = gap_df["city_original"].tolist()
    batches = [cities_to_resolve[i:i+batch_size]
               for i in range(0, len(cities_to_resolve), batch_size)]

    print(f"  Batches to send             : {len(batches):,}  (batch_size={batch_size})")
    print(f"  Model                       : {config.get('LLM_MODEL')}")

    # ── Build a result map: city_original → {state, literacy_rate} ───────
    results_map: dict[str, dict] = {}
    success_batches = 0

    for batch_idx, batch in enumerate(batches):
        try:
            results = _call_llm(batch, config)
            for item in results:
                city_key = str(item.get("city", "")).strip()
                if city_key:
                    results_map[city_key] = item
            success_batches += 1
            print(f"    Batch {batch_idx+1:>4}/{len(batches)}  — {len(results)} results received")
            time.sleep(0.5)
        except Exception as e:
            print(f"    Batch {batch_idx+1:>4}/{len(batches)}  — ERROR: {e}")

    # ── Merge results back into df ────────────────────────────────────────
    filled_state = 0
    filled_lit   = 0

    for i, row in df.iterrows():
        city_orig = str(row["city_original"]).strip()
        if city_orig not in results_map:
            continue
        item = results_map[city_orig]

        # Fill state if still missing
        if pd.isna(row["state_original"]) or row["match_source"] == "unresolved":
            state = item.get("state")
            if state and str(state).lower() not in ("null", "none", ""):
                df.at[i, "state_original"] = normalize_state(str(state))
                df.at[i, "match_source"]   = "llm"
                filled_state += 1

                # Re-derive region / coastal from newly resolved state
                from config import STATE_TO_REGION, COASTAL_STATES
                state_n = normalize_state(str(state))
                df.at[i, "geographic_region"] = STATE_TO_REGION.get(state_n)
                df.at[i, "is_coastal"]        = state_n in {s.lower() for s in COASTAL_STATES}

        # Fill literacy if still missing
        if pd.isna(row["literacy_rate"]):
            lr = item.get("literacy_rate")
            if lr is not None and str(lr).lower() not in ("null", "none", ""):
                try:
                    val = float(lr)
                    if 10.0 <= val <= 100.0:
                        df.at[i, "literacy_rate"]   = val
                        df.at[i, "literacy_source"] = "llm"
                        filled_lit += 1
                except (ValueError, TypeError):
                    pass

    # For newly-resolved states, apply state avg literacy where still missing
    for i, row in df.iterrows():
        if row["match_source"] == "llm" and pd.isna(row["literacy_rate"]):
            state_n = normalize_state(str(row["state_original"]))
            if state_n in state_lr:
                df.at[i, "literacy_rate"]   = state_lr[state_n]
                df.at[i, "literacy_source"] = "state_average"

    # ── Summary ───────────────────────────────────────────────────────────
    print(f"\n  Successful batches          : {success_batches} / {len(batches)}")
    print(f"  state_original filled by LLM: {filled_state:,}")
    print(f"  literacy_rate filled by LLM : {filled_lit:,}")

    print_value_counts(df, "match_source")
    coverage_report(df, ["state_original", "literacy_rate", "geographic_region", "is_coastal"])

    save_checkpoint(df, config["PATHS"]["checkpoints"], step=9)
    return df
