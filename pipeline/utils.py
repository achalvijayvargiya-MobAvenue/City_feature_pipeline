"""
utils.py — Shared helpers: normalization, coverage reporting, checkpointing.
"""
import os
import re
import unicodedata
import pandas as pd


# ─────────────────────────────────────────────
# TEXT NORMALIZATION
# ─────────────────────────────────────────────

def normalize_name(name: str) -> str:
    """
    Lowercase, strip accents, remove punctuation, collapse whitespace.
    e.g. "Bengalûru!!" → "bengaluru"
    """
    if not isinstance(name, str):
        return ""
    name = unicodedata.normalize("NFKD", name)
    name = name.encode("ascii", "ignore").decode("ascii")
    name = name.lower().strip()
    name = re.sub(r"[^a-z0-9\s]", " ", name)
    name = re.sub(r"\s+", " ", name).strip()
    return name


def normalize_state(name: str) -> str:
    """Normalize state name for dict lookups."""
    return normalize_name(name)


def contains_mojibake(text: str) -> bool:
    """
    Detect likely mojibake (corrupted encoding) e.g. Ø§Ù„Ù†Ø¹Ø§ÙŠÙ.
    Returns True if text has 3+ consecutive Latin-1 supplement chars (U+0080–U+00FF).
    """
    if not isinstance(text, str):
        return True
    return bool(re.search(r"[\u0080-\u00ff]{3,}", text))


def contains_invalid_chars(text: str) -> bool:
    """
    Returns True if text contains any char other than letters, digits, spaces,
    or parentheses/brackets. Discards e.g. "2337722-2-1" (hyphen), "1400ØŒØŒ" (Arabic).
    Keeps "faridabad (sector 11)" — letters, digits, space, parens allowed.
    """
    if not isinstance(text, str):
        return True
    return bool(re.search(r"[^a-zA-Z0-9\s\(\)\[\]\{\}]", text))


# ─────────────────────────────────────────────
# COVERAGE REPORTING
# ─────────────────────────────────────────────

def print_step_header(step_num: int, title: str):
    bar = "=" * 60
    print(f"\n{bar}")
    print(f"  STEP {step_num}: {title}")
    print(f"{bar}")


def coverage_report(df: pd.DataFrame, columns: list, label: str = ""):
    """Print null/fill rate for given columns."""
    total = len(df)
    print(f"\n  {'Column':<25} {'Filled':>8} {'Missing':>8} {'Coverage':>10}")
    print(f"  {'-'*25} {'-'*8} {'-'*8} {'-'*10}")
    for col in columns:
        if col not in df.columns:
            print(f"  {col:<25} {'N/A':>8}")
            continue
        filled  = df[col].notna().sum()
        missing = total - filled
        pct     = (filled / total * 100) if total > 0 else 0
        print(f"  {col:<25} {filled:>8,} {missing:>8,} {pct:>9.1f}%")
    if label:
        print(f"\n  Note: {label}")


def print_value_counts(df: pd.DataFrame, col: str, top_n: int = 10):
    """Print top-N value distribution for a column."""
    if col not in df.columns:
        return
    counts = df[col].value_counts(dropna=False).head(top_n)
    print(f"\n  Top {top_n} values for '{col}':")
    for val, cnt in counts.items():
        pct = cnt / len(df) * 100
        print(f"    {str(val):<35} {cnt:>8,}  ({pct:.1f}%)")


# ─────────────────────────────────────────────
# CHECKPOINT HELPERS
# ─────────────────────────────────────────────

def checkpoint_path(checkpoints_dir: str, step: int) -> str:
    return os.path.join(checkpoints_dir, f"step{step:02d}_output.csv")


def save_checkpoint(df: pd.DataFrame, checkpoints_dir: str, step: int):
    os.makedirs(checkpoints_dir, exist_ok=True)
    path = checkpoint_path(checkpoints_dir, step)
    df.to_csv(path, index=False)
    print(f"\n  [OK] Checkpoint saved -> {path}  ({len(df):,} rows)")


def load_checkpoint(checkpoints_dir: str, step: int) -> pd.DataFrame | None:
    path = checkpoint_path(checkpoints_dir, step)
    if os.path.exists(path):
        df = pd.read_csv(path, dtype=str)
        print(f"  [OK] Loaded checkpoint from step {step} -> {path}  ({len(df):,} rows)")
        return df
    return None
