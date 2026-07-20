"""
02_count_cells.py
-----------------
Reads both candidate files produced by 01_extract_candidates.py after manual
coding, retains rows whose exit_reason_ruling is FORCED or UNDERPERFORMANCE,
and prints the three-way successor-origin counts for each trigger group.

Rule 3 (from docs/phase-0-pre-commitments.md):
  If any cell in the external-trigger split is single-digit (< 10), the study
  stops and the null count is published on the methods page.
"""

import os
import sys
import pandas as pd

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WORKING = os.path.join(ROOT, "data", "working")
EXT_FILE = os.path.join(WORKING, "external-candidates.csv")
INT_FILE = os.path.join(WORKING, "internal-candidates.csv")

VALID_RULINGS = {"FORCED", "UNDERPERFORMANCE"}
ORIGINS = ["internal", "boomerang", "external"]

# ---------------------------------------------------------------------------
# Load and validate
# ---------------------------------------------------------------------------
for path in (EXT_FILE, INT_FILE):
    if not os.path.exists(path):
        print(f"ERROR: {path} not found.  Run 01_extract_candidates.py first.")
        sys.exit(1)

ext_raw = pd.read_csv(EXT_FILE)
int_raw = pd.read_csv(INT_FILE)

# Keep only coded rows with a qualifying ruling.
ext_coded = ext_raw[ext_raw["exit_reason_ruling"].isin(VALID_RULINGS)].copy()
int_coded = int_raw[int_raw["exit_reason_ruling"].isin(VALID_RULINGS)].copy()

# ---------------------------------------------------------------------------
# Count helper
# ---------------------------------------------------------------------------
def _count_table(df: pd.DataFrame, label: str) -> pd.Series:
    """Return successor_origin value counts with all three categories present."""
    counts = df["successor_origin"].value_counts()
    # Ensure all three categories appear (zeros for absent ones).
    for origin in ORIGINS:
        if origin not in counts.index:
            counts[origin] = 0
    return counts[ORIGINS]

ext_counts = _count_table(ext_coded, "EXTERNAL trigger")
int_counts = _count_table(int_coded, "INTERNAL trigger")

# ---------------------------------------------------------------------------
# Print results
# ---------------------------------------------------------------------------
SEP = "=" * 55

print(SEP)
print("02_count_cells — post-coding successor-origin counts")
print(SEP)

print(f"\nEXTERNAL trigger  (n coded = {len(ext_coded)})")
print(f"  {'Origin':<12}  Count")
print(f"  {'-'*12}  -----")
for origin in ORIGINS:
    print(f"  {origin:<12}  {ext_counts[origin]:>5}")

print(f"\nINTERNAL trigger  (n coded = {len(int_coded)})")
print(f"  {'Origin':<12}  Count")
print(f"  {'-'*12}  -----")
for origin in ORIGINS:
    print(f"  {origin:<12}  {int_counts[origin]:>5}")

# ---------------------------------------------------------------------------
# Rule 3 — kill threshold
# ---------------------------------------------------------------------------
print(f"\n{'Rule 3 (kill threshold)':}")
print(f"  Single-digit threshold : < 10")
single_digit_cells = [origin for origin in ORIGINS if ext_counts[origin] < 10]

if single_digit_cells:
    print(f"  Single-digit cells in external-trigger split: {single_digit_cells}")
    print(f"\n  >> KILL — one or more cells in the external-trigger split are")
    print(f"             single-digit.  Publish null count on the methods page.")
else:
    print(f"  All external-trigger cells >= 10.")
    print(f"\n  >> PASS — proceed to analysis.")

print(SEP)
