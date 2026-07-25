---
license: cc-by-4.0
language:
  - vi
tags:
  - vietnam
  - education
  - admissions
  - dataset
pretty_name: Vietnamese University Admission Cutoffs — Computing & IT, Hà Nội (2019–2025)
size_categories:
  - n<1K
---

# Vietnamese University Admission Cutoffs — Computing & IT, Hà Nội (2019–2025)

Machine-readable admission cutoff scores (**điểm chuẩn**) for the **Computing & Information Technology**
field group at **10 public universities in Hà Nội**, unified across **2019–2025** for the **THPT
national-exam admission method**. **278 rows**, one per *(university × major × year × subject-block)*,
resolved into **11 canonical majors**. This slice is deliberately narrow (depth over breadth) and every
cleaning decision is documented and reproducible — see the GitHub repo below.

## Columns (`cutoffs_cs.csv`)

| Column | Description |
|---|---|
| `school_id`, `abbr`, `school_canonical` | University id, short tag, and canonical Vietnamese name |
| `source_major_code`, `raw_major_name` | Major identity **as published by the source** (not yet canonicalised) |
| `program_variant` | `base` / `clc` / `joint` / `english` / `advanced` (records the program's *primary* attribute) |
| `year` | Admission year, 2019–2025 |
| `method` | Always `THPT` (national-exam method) |
| `block_group` | Subject combination (tổ hợp) sharing one cutoff |
| `mark` | **The điểm chuẩn as published** (30-point scale), sourced corrections applied. **Use for lookup.** |
| `mark_scale` | `30` or `40` (see note below) |
| `mark_normalized_30` | Cutoff on a common 30-point scale. **Use for cross-school / trend comparison.** |
| `mark_corrected` | `true` if `mark` differs from the raw source (a sourced correction was applied) |
| `at_floor` | `true` if the cutoff is at the ~15 admission floor (floor admission, not a competitive cutoff) |
| `mark_source_note` | Human-readable provenance for any correction / normalization on that cell |
| `source_row_id`, `source_file` | Provenance back to the raw source record |
| `canonical_major_id` | ASCII slug key (e.g. `khoa-hoc-may-tinh`) |
| `canonical_major_name` | Vietnamese canonical major name (source of truth) |

## Before you use it

- **Two score columns, two purposes.** `mark` is the actual published cutoff (30-point scale) — use it
  for lookup. `mark_normalized_30` is the column for **cross-school and trend comparison**.
- **The 40-scale exception.** Four HUS records (Data Science & Computer-Science-and-Information,
  2023–2024) were published on a **40-point scale** (Toán ×2); they are normalized to 30 via ×0.75 in
  `mark_normalized_30` (mechanism confirmed against primary sources and triangulated against the same
  majors' other-year cutoffs). `mark_scale` flags them.
- **Nulls are structural, not missing data.** Where a school did not admit a major via THPT in a given
  year, there is simply **no row** for that cell — a real gap (the school used other methods that year),
  not a data hole. `coverage.csv` in the repo enumerates the full grid with `has_thpt` flags (99% of
  major-year cells within a major's active span have a THPT score; 86% have a directly-comparable
  `base` offering).
- **One corrected value.** HUS *Khoa học máy tính và thông tin* 2024 was published by the aggregator as
  `34.0`; the official figure is `34.7`. It is corrected in this dataset with `mark_corrected = true`
  and a note.

## Provenance & reliability

Aggregated from **tuyensinh247** (an aggregator), then cross-validated against primary sources and
reported honestly by era: for **2021–2025**, a random sample matched 4/4 against a *primary* source and
a further 12/12 against a *second aggregator* (corroboration only, not independent proof), with **0
discrepancies** — and the one aggregator error above was caught and corrected. For **2019–2020**,
primary sources are largely offline / image-based, so **no reliability claim is made** for those years.
No personal data: aggregate cutoffs only, never individual scores.

## Full pipeline, schema, and the decisions story

**GitHub (reproducible standard-library-only pipeline + data dictionary + decisions):**
<https://github.com/idgstone/VN-university-cutoffs>

## License

**CC-BY-4.0.** The license covers **this compilation** — the schema, normalization, canonical mapping,
corrections, and documentation. It does **not** claim ownership of the **cutoff numbers themselves**,
which are public facts published by the universities and the Ministry of Education & Training and are
not owned by anyone. Please credit this compilation, and also the underlying sources: **tuyensinh247**
(aggregation) and the **universities / VNU / Ministry** (primary sources of the figures).
