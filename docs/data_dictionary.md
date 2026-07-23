# Data dictionary — `data/processed/cutoffs_cs_thpt.csv` (silver, Layer 2a)

One tidy row per **(school × source major code × year × subject-block-group)** admission-cutoff
observation, for the **Computing/IT group** (Ministry field 748 + Data Science, defined by a uniform
semantic rule — see `config/cs_group_mapping.csv`), **THPT method only**, 10 public Hanoi
universities, 2019–2025. Built by `src/build_silver.py` from the immutable bronze layer
(`data/raw/thpt/*.json`) plus sourced override configs.

## Columns

| Column | Meaning |
|---|---|
| `school_id`, `abbr`, `school_canonical` | University (source id, short tag, canonical name). |
| `source_major_code`, `raw_major_name` | Major identity **as published by the source**. Not yet canonicalized (Task 2). |
| `program_variant` | First-pass rule tag: `base` / `clc` / `english` / `joint` / `advanced`. **Refinable** — attribute only, not part of identity. |
| `year` | Admission year (2019–2025). |
| `method` | Always `THPT` (national-exam method; the single canonical method for this dataset). |
| `block_group` | The tổ hợp (subject-combination) string sharing one cutoff. Part of the key: a major can have several block-groups with different cutoffs in one year. |
| `mark` | **The điểm chuẩn as published**, with sourced corrections applied. **Use this for LOOKUP.** |
| `mark_scale` | `30` or `40`. See normalization note below. |
| `mark_normalized_30` | **The column for CROSS-SCHOOL & TREND analysis.** See note. |
| `mark_corrected` | `True` if `mark` differs from the bronze value (a sourced correction was applied). |
| `at_floor` | `True` if `mark ≤ 15.0` — a heuristic marking floor-admission (e.g. 2019 điểm sàn) rather than a competitive cutoff. |
| `mark_source_note` | Human-readable provenance for any correction and/or normalization on this cell. |
| `source_row_id`, `source_file` | Provenance back to the exact bronze API record. |

## Score scale & normalization (read before plotting anything)

Most records are on Vietnam's **30-point** THPT scale. Four records — HUS `Khoa học dữ liệu` (QHT93)
and `Khoa học máy tính và thông tin` (QHT98), years **2023 & 2024** — are on a **40-point scale**:
điểm chuẩn = **Toán ×2 + the two other subjects (+ priority)**, per HUS/VNU announcements. Which
records are 40-scale is declared in `config/score_scale_overrides.csv` (sourced), **not** inferred
from `mark > 30` (priority points can push a genuine 30-scale total slightly over 30).

`mark_normalized_30` converts 40-scale cells to the 30-scale via **× 0.75** (the official VNU
thang-40 → thang-30 convention). **This is a controlled approximation:** because
`2·Toán + M2 + M3 = (4/3)(Toán + M2 + M3)` only when the three subjects are equal, ×0.75 is *exact*
when a candidate's three subject scores are equal and a close approximation otherwise. It is
**validated by triangulation**: the normalized values (26.14, 26.25, 26.03) land on each major's
own other-year 30-scale cutoffs (26.0–26.55), confirming both the mechanism and the factor.

**Consequently:**
- **Comparison / trend analysis → use `mark_normalized_30`.** Plotting raw `mark` across 2023–24
  would reintroduce a fake ~9-point spike-and-drop in HUS Data Science that is pure scale artifact.
- **Lookup of the actual published điểm chuẩn → use `mark`.**

## Corrections & provenance philosophy

Bronze (`data/raw/thpt/*.json`) is **immutable** and always reflects what the aggregator published.
The silver layer may depart from bronze only via **sourced override CSVs**
(`config/mark_corrections.csv`, `config/score_scale_overrides.csv`), and every such cell is flagged
(`mark_corrected`) and explained (`mark_source_note`) so it is individually defensible. Known
correction so far: HUS QHT98/2024 `34.0 → 34.7` (aggregator error, verified against the government
portal and two independent outlets).

## Canonical identity & gold layer (Layer 2b)

`canonical_major_id` groups source majors into **10 canonical CS majors** across schools/years
(`data/processed/cutoffs_cs.csv` = silver + `canonical_major_id` + `canonical_major_name`). The map
(`config/canonical_majors_draft.csv`, human-reviewable) was built by rule-based normalization +
token-sort fuzzy clustering, then the owner's granularity rulings (#1–#6). **Matching was a
rule/fuzzy problem, not ML:** fuzzy-only scored F1 0.991 / precision 1.000 vs the ground truth, with
perfect separation of hard negatives (Kỹ thuật ↔ Khoa học máy tính, etc.). Its *only* structural
failures were cross-string semantic synonyms — the cybersecurity cluster
(`An toàn thông tin` / `An ninh mạng` / `An toàn không gian số`, per-cluster recall **0.27**) and one
renamed base (`Kỹ thuật dữ liệu`→networks). Those are closed in the reviewed canonical map **as an interim, hand-verified stopgap so v1 can
ship** — this is *not* the ML component and does not count as solving the residual "with ML". If
embeddings later become the ML component, they are the principled, *measured* solution to this same
cybersecurity cluster (recall 0.27 → X), and they **replace** the interim map's role for it — the two
must never both claim credit for the same residual.

Bundled multi-major cutoff rows (`nhóm ngành …`) are **excluded-with-record** in
`config/excluded_bundled.csv` (not deleted), so "why no data for school X year Y" is always answerable.

## Coverage & wide pivot

- `data/processed/coverage.csv` — one row per `(school, canonical_major, year)` **within each
  major's active span** (first→last observed year, so "not yet offered" years aren't miscounted as
  gaps), with `has_thpt` (any variant) and `has_base`. Headline: **99%** dataset coverage,
  **88%** base-comparable; 2 genuine THPT gaps (HUST cybersecurity & AI+DS, 2022).
- `data/processed/cutoffs_cs_wide.csv` — G2 pivot (canonical major × school, year columns) of
  `mark_normalized_30`, using the base→english→clc→joint→advanced representative fallback; a trailing
  `*` marks a non-base representative (annotate on charts, per the base-less-school rule).

**Two verified caveats for anyone plotting the pivot:**
- The 2 coverage gaps (HUST cybersecurity & AI+DS, 2022) are **genuine no-THPT-that-year** — those
  programs exist in the 2021 and 2023 raw data but were not offered via THPT in 2022 (confirmed
  against bronze), not a matching miss.
- A `*` (non-base representative) cell can create an **artificial year-over-year jump** even after
  scale normalization, because it compares a variant to the base. Example: HUST Khoa học máy tính
  reads 28.43 (2021, base) → 25.15\* (2022, *joint* Troy — no base offered that year) → 29.42 (2023,
  base); the base series 28.43 → (gap) → 29.42 is smooth. **For trend lines, prefer base-only with
  gaps shown; use the fallback pivot for "what was available" lookups.**

## Still owed

- **Representative ~5–10% reliability reconciliation** across normal records — the HUS check was
  mechanism-only cross-validation (sample #1).
- **ML component decision** — leading validated candidate: embeddings on the cybersecurity synonym
  residual (fuzzy's real, measured failure). Deferred until the dataset is complete.
