# scripts/

Two scripts that implement the Phase 0 pre-committed analysis pipeline.
Rules governing every decision are fixed in `docs/phase-0-pre-commitments.md`.

## Run order

**Step 1 — extract candidates**

```bash
python scripts/01_extract_candidates.py
```

Reads `data/source/step5-classification-worksheet.csv`, builds per-company
succession chains ordered by appointment date, computes CEO tenure in months,
and writes:

| File | Contents |
|------|----------|
| `data/working/external-candidates.csv` | Every EXTERNAL hire with tenure < 24 months whose successor was appointed 2010–2022 |
| `data/working/internal-candidates.csv` | Same filter applied to INTERNAL hires |

Each row contains: `company`, `ceo_name`, `appointment_date`, `exit_date`,
`tenure_months`, `successor_name`, `successor_origin`, `exit_reason_ruling`.

Candidate counts and successor-origin breakdowns are printed to the console.

**Step 1b — diagnose blank successor origins (optional)**

```bash
python scripts/03_diagnose_nan_origins.py
```

For every row in both candidate files where `successor_origin` is blank, reports
why the origin could not be derived: successor not found in the source at all,
found but marked `excluded`, or found but not linkable to this company's chain
(different company, company-name whitespace variant, or prior-stint boomerang
record).  Prints per-reason counts per file and writes row-level detail to
`data/working/nan-origin-diagnosis.csv`.  Run before manual coding to know which
`successor_origin` blanks require additional research.

**Step 2 — manual coding**

Open both CSV files and fill the `exit_reason_ruling` column for every row.
Valid values are `FORCED`, `UNDERPERFORMANCE`, or any other string (those rows
are excluded from the count).  Do not alter any other column.

**Step 3 — count cells and apply kill threshold**

```bash
python scripts/02_count_cells.py
```

Reads the coded candidate files, keeps only `FORCED` and `UNDERPERFORMANCE`
rows, prints the three-way successor-origin counts (internal / boomerang /
external) for each trigger group, and applies the Rule 3 single-digit
threshold:

- **PASS** — all three cells in the external-trigger split are ≥ 10; proceed
  to analysis.
- **KILL** — at least one cell is < 10; stop the study and publish the null
  count on the methods page.

## Dependencies

Python 3 with `pandas`.  No other packages required.
