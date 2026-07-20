"""
03_diagnose_nan_origins.py
--------------------------
For every row in data/working/external-candidates.csv and
data/working/internal-candidates.csv where successor_origin is blank,
explains why the origin could not be derived from the succession chain.

Three diagnostic reasons (matching phase-0 framing):
  not_in_dataset   — successor_name does not appear in exec_fullname anywhere
                     in the source worksheet.
  found_excluded   — successor_name is found in the source, but every matching
                     row carries classification = 'excluded' (interim CEO,
                     co-CEO, change-of-control artefact, etc.).
  found_not_linked — successor_name is found in the source with a non-excluded
                     classification, but the record cannot serve as a forward
                     chain link for this transition.  Sub-types recorded in
                     the detail column:
                       different_company     : match is at a different company
                       anchor_precedes_exit  : match is at the same company but
                                               the source anchor_date pre-dates
                                               the candidate's exit (the person
                                               was a prior CEO who returned as a
                                               boomerang; their re-appointment is
                                               not separately tracked in the
                                               dataset)
                       company_name_variant  : match is at the same company
                                               modulo whitespace / punctuation;
                                               chain derivation missed them
                                               because groupby used the raw name

Outputs:
  console  — per-reason counts for each candidate file
  data/working/nan-origin-diagnosis.csv — row-level detail
"""

import os
import pandas as pd

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SOURCE = os.path.join(ROOT, "data", "source", "step5-classification-worksheet.csv")
WORKING = os.path.join(ROOT, "data", "working")
EXT_FILE = os.path.join(WORKING, "external-candidates.csv")
INT_FILE = os.path.join(WORKING, "internal-candidates.csv")
OUT_CSV = os.path.join(WORKING, "nan-origin-diagnosis.csv")

# ---------------------------------------------------------------------------
# Load data
# ---------------------------------------------------------------------------
src = pd.read_csv(SOURCE, low_memory=False)
src["anchor_date"] = pd.to_datetime(src["anchor_date"])

ext_df = pd.read_csv(EXT_FILE)
int_df = pd.read_csv(INT_FILE)

# ---------------------------------------------------------------------------
# Normalisation helper for fuzzy company-name comparison
# ---------------------------------------------------------------------------
def _normalise_company(name: str) -> str:
    """Lower-case, collapse whitespace, strip punctuation."""
    import re
    if pd.isna(name):
        return ""
    return re.sub(r"\s+", " ", str(name).lower().strip())


src["_coname_norm"] = src["coname"].map(_normalise_company)

# ---------------------------------------------------------------------------
# Diagnosis logic
# ---------------------------------------------------------------------------
REASONS = ["not_in_dataset", "found_excluded", "found_not_linked"]

def _diagnose_row(candidate_row: pd.Series, candidate_file_label: str) -> dict:
    """
    Return a dict with keys: file, company, ceo_name, exit_date,
    successor_name, reason, detail.
    """
    succ_name = candidate_row["successor_name"]
    exit_date = pd.to_datetime(candidate_row["exit_date"])
    company_raw = candidate_row["company"]
    company_norm = _normalise_company(company_raw)

    base = {
        "file": candidate_file_label,
        "company": company_raw,
        "ceo_name": candidate_row["ceo_name"],
        "exit_date": candidate_row["exit_date"],
        "successor_name": succ_name,
    }

    # --- 1. Not in dataset at all ---
    if pd.isna(succ_name):
        return {**base, "reason": "not_in_dataset",
                "detail": "successor_name is blank in source worksheet"}

    matches = src[src["exec_fullname"] == succ_name].copy()
    if matches.empty:
        return {**base, "reason": "not_in_dataset",
                "detail": "exec_fullname not found in source worksheet"}

    # --- 2. Found but all matches are excluded ---
    non_excl = matches[matches["classification"] != "excluded"]
    if non_excl.empty:
        excl_companies = matches["coname"].unique().tolist()
        excl_anchors = matches["anchor_date"].dt.date.astype(str).unique().tolist()
        return {
            **base,
            "reason": "found_excluded",
            "detail": (
                f"found at {excl_companies}; "
                f"classification=excluded; anchor={excl_anchors}"
            ),
        }

    # --- 3. Found with non-excluded classification but chain link is broken ---
    details = []
    for _, m in non_excl.iterrows():
        m_company_norm = _normalise_company(m["coname"])
        m_anchor = m["anchor_date"]

        anchor_str = m_anchor.date() if pd.notna(m_anchor) else "NaT"
        if m_company_norm == company_norm:
            # Normalised name matches — could still differ by whitespace in raw form
            if m["coname"] != company_raw:
                # Raw names differ (whitespace / punctuation variant); groupby
                # treated them as distinct companies so shift(-1) missed this row.
                details.append(
                    f"company_name_variant: source has '{m['coname']}' vs "
                    f"candidate has '{company_raw}'; "
                    f"class={m['classification']} anchor={anchor_str}"
                )
            elif pd.notna(m_anchor) and m_anchor <= exit_date:
                # Same raw name and same company, but this row records the
                # successor's *prior* stint as CEO — they returned as a boomerang
                # and the re-appointment is not a separate row in the dataset.
                details.append(
                    f"anchor_precedes_exit: '{m['coname']}' "
                    f"class={m['classification']} anchor={anchor_str} "
                    f"<= exit={exit_date.date()} "
                    f"(prior-stint record; boomerang return not separately tracked)"
                )
            else:
                # Same company, same raw name, anchor after exit — should have
                # been picked up by shift(-1); flag for manual review.
                details.append(
                    f"unexpected: '{m['coname']}' "
                    f"class={m['classification']} anchor={anchor_str}"
                )
        else:
            details.append(
                f"different_company: found at '{m['coname']}' "
                f"class={m['classification']} anchor={anchor_str}"
            )

    return {
        **base,
        "reason": "found_not_linked",
        "detail": " | ".join(details),
    }


# ---------------------------------------------------------------------------
# Run diagnosis on both files
# ---------------------------------------------------------------------------
records = []

for label, df in [("external-candidates.csv", ext_df),
                  ("internal-candidates.csv", int_df)]:
    nan_rows = df[df["successor_origin"].isna()]
    for _, row in nan_rows.iterrows():
        records.append(_diagnose_row(row, label))

diag_df = pd.DataFrame(records, columns=[
    "file", "company", "ceo_name", "exit_date",
    "successor_name", "reason", "detail",
])

# ---------------------------------------------------------------------------
# Print counts
# ---------------------------------------------------------------------------
SEP = "=" * 62

print(SEP)
print("03_diagnose_nan_origins — successor-origin gap report")
print(SEP)

for label in ["external-candidates.csv", "internal-candidates.csv"]:
    subset = diag_df[diag_df["file"] == label]
    print(f"\n{label}  (n gaps = {len(subset)})")
    print(f"  {'Reason':<22}  Count")
    print(f"  {'-'*22}  -----")
    counts = subset["reason"].value_counts().reindex(REASONS, fill_value=0)
    for reason in REASONS:
        print(f"  {reason:<22}  {counts[reason]:>5}")

# Sub-type detail for found_not_linked
not_linked = diag_df[diag_df["reason"] == "found_not_linked"]
if not_linked.empty:
    pass
else:
    print(f"\nfound_not_linked sub-types (across both files):")

    def _extract_subtype(detail: str) -> str:
        for sub in ("anchor_precedes_exit", "company_name_variant",
                    "different_company", "unexpected"):
            if sub in detail:
                return sub
        return "other"

    not_linked = not_linked.copy()
    not_linked["subtype"] = not_linked["detail"].map(_extract_subtype)
    print(
        not_linked.groupby(["file", "subtype"])
        .size()
        .rename("count")
        .to_string()
    )

print()
print(f"Row-level detail written to:")
print(f"  {OUT_CSV}")
print(SEP)

# ---------------------------------------------------------------------------
# Write CSV
# ---------------------------------------------------------------------------
os.makedirs(WORKING, exist_ok=True)
diag_df.to_csv(OUT_CSV, index=False)
