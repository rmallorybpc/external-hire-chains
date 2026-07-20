"""
01_extract_candidates.py
------------------------
Reads data/source/step5-classification-worksheet.csv, builds per-company
succession chains ordered by appointment date, computes CEO tenure in months,
and writes two candidate files:

  data/working/external-candidates.csv  — EXTERNAL hires, tenure < 24 months,
                                           successor appointed 2010-2022
  data/working/internal-candidates.csv  — same filter for INTERNAL hires

Rules fixed in docs/phase-0-pre-commitments.md govern every decision here.
"""

import os
import pandas as pd

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SOURCE = os.path.join(ROOT, "data", "source", "step5-classification-worksheet.csv")
WORKING = os.path.join(ROOT, "data", "working")
OUT_EXT = os.path.join(WORKING, "external-candidates.csv")
OUT_INT = os.path.join(WORKING, "internal-candidates.csv")

# ---------------------------------------------------------------------------
# Load
# ---------------------------------------------------------------------------
df = pd.read_csv(SOURCE, low_memory=False)

# Keep only the rows that carry a real classification; "excluded" rows (interims,
# co-CEOs, change-of-control artefacts) are removed before chain construction so
# they do not distort appointment dates or succession links.
df = df[df["classification"].isin(["internal", "external"])].copy()

df["anchor_date"] = pd.to_datetime(df["anchor_date"])

# ---------------------------------------------------------------------------
# Build succession chains
# Within each company, sort by anchor_date (= the date each CEO left office,
# which is also the date their successor was appointed).  The appointment date
# of CEO_n is therefore the anchor_date of CEO_{n-1}.
# ---------------------------------------------------------------------------
df.sort_values(["coname", "anchor_date"], inplace=True)
df.reset_index(drop=True, inplace=True)

# appointment_date: the anchor_date of the PRECEDING CEO at the same company.
df["appointment_date"] = df.groupby("coname")["anchor_date"].shift(1)

# tenure_months: calendar-month difference (exit - appointment).
# Rows where appointment_date is NaN (first CEO in a company's chain) will
# produce NaN tenure and are naturally excluded by the < 24 filter.
def _month_diff(exit_date, appt_date):
    """Integer calendar-month difference, floor toward zero."""
    if pd.isna(exit_date) or pd.isna(appt_date):
        return pd.NA
    delta = (exit_date.year - appt_date.year) * 12 + (exit_date.month - appt_date.month)
    # If the day-of-month hasn't been reached yet, subtract one month.
    if exit_date.day < appt_date.day:
        delta -= 1
    return delta

df["tenure_months"] = [
    _month_diff(r["anchor_date"], r["appointment_date"])
    for _, r in df.iterrows()
]
df["tenure_months"] = pd.to_numeric(df["tenure_months"], errors="coerce")

# ---------------------------------------------------------------------------
# Derive successor_origin
# The three-way split used by Rule 3 is: internal | boomerang | external.
# Primary signal: succ_flags on the current row.  If it contains "boomerang"
# the successor is a boomerang regardless of their own classification row.
# Fallback: the classification of the next non-excluded CEO at the same company
# (shift(-1) after we already removed excluded rows above).
# ---------------------------------------------------------------------------
df["successor_origin"] = df.groupby("coname")["classification"].shift(-1)

is_boomerang = df["succ_flags"].astype(str).str.contains("boomerang", na=False)
df.loc[is_boomerang, "successor_origin"] = "boomerang"

# ---------------------------------------------------------------------------
# Apply filters (Rule 1 & Rule 3 window)
# ---------------------------------------------------------------------------
# successor appointment year = anchor_date year of the current row (= the date
# the current CEO left and the successor took over).
successor_appt_year = df["anchor_date"].dt.year
window_filter = successor_appt_year.between(2010, 2022)
tenure_filter = df["tenure_months"] < 24

# ---------------------------------------------------------------------------
# Assemble output columns
# ---------------------------------------------------------------------------
OUTPUT_COLS = [
    "company",
    "ceo_name",
    "appointment_date",
    "exit_date",
    "tenure_months",
    "successor_name",
    "successor_origin",
    "exit_reason_ruling",
]

def _build_output(subset: pd.DataFrame) -> pd.DataFrame:
    out = subset[
        ["coname", "exec_fullname", "appointment_date", "anchor_date",
         "tenure_months", "successor_name", "successor_origin"]
    ].copy()
    out.columns = [
        "company", "ceo_name", "appointment_date", "exit_date",
        "tenure_months", "successor_name", "successor_origin",
    ]
    out["exit_reason_ruling"] = ""
    out = out[OUTPUT_COLS]
    out = out.sort_values(["company", "appointment_date"]).reset_index(drop=True)
    return out

ext_mask = (df["classification"] == "external") & tenure_filter & window_filter
int_mask = (df["classification"] == "internal") & tenure_filter & window_filter

external_df = _build_output(df[ext_mask])
internal_df = _build_output(df[int_mask])

# ---------------------------------------------------------------------------
# Write outputs
# ---------------------------------------------------------------------------
os.makedirs(WORKING, exist_ok=True)
external_df.to_csv(OUT_EXT, index=False)
internal_df.to_csv(OUT_INT, index=False)

# ---------------------------------------------------------------------------
# Console summary
# ---------------------------------------------------------------------------
print("=" * 60)
print("01_extract_candidates — candidate counts")
print("=" * 60)
print(f"  External candidates : {len(external_df):>4d}")
print(f"  Internal candidates : {len(internal_df):>4d}")
print()
print("Successor-origin breakdown (external candidates):")
print(external_df["successor_origin"].value_counts(dropna=False).to_string())
print()
print("Successor-origin breakdown (internal candidates):")
print(internal_df["successor_origin"].value_counts(dropna=False).to_string())
print()
print(f"Outputs written to:")
print(f"  {OUT_EXT}")
print(f"  {OUT_INT}")
print("=" * 60)
print("NOTE: Code each row's exit_reason_ruling before running 02_count_cells.py.")
print("      Valid values: FORCED | UNDERPERFORMANCE | (other — row excluded)")
