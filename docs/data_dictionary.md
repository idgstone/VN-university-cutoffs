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

## Deferred (not in this table yet)

- **`canonical_major_id`** — Task 2 (entity matching + precision/recall eval). Until then, identity
  is `source_major_code`; HUST's cross-year code churn (`IT2`→`IT2y`), block-variant codes
  (`IT1x`), and name drift are the canonical-identity cases Task 2 resolves.
- **Coverage grid & metrics** (dataset coverage vs comparison-readiness, at major×year grain) and the
  **wide pivot (G2)** — Layer 2b, after canonical majors exist.
- **Representative ~5–10% reliability reconciliation** across normal records — still owed
  (the HUS check was mechanism-only cross-validation, sample #1).
