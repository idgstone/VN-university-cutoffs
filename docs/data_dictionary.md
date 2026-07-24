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

`canonical_major_id` (ASCII slug, e.g. `khoa-hoc-may-tinh`) groups source majors into **11 canonical
CS majors** across schools/years; `canonical_major_name` holds the Vietnamese display name (the source
of truth). `data/processed/cutoffs_cs.csv` = silver + these two columns. The map
(`config/canonical_majors_draft.csv`, human-reviewable) was built by rule-based normalization +
token-sort fuzzy clustering, then the owner's granularity rulings. **Matching was a rule/fuzzy
problem, not ML** — see the honest metrics restatement below.

**Two same-looking majors that are NOT the same** (for non-Vietnamese readers): `Kỹ thuật máy tính`
(engineering ngành, Ministry code **7480106**) and `Công nghệ kỹ thuật máy tính` (applied-technology
ngành, code **7480108**) are *different* degrees and separate canonicals — the names cannot be told
apart without this fact.

**Eval metrics — honestly restated (a ground-truth error found in domain review).** An initial run
reported precision **1.000 at every threshold**. Domain review then split `Công nghệ kỹ thuật máy tính`
from `Kỹ thuật máy tính` (above), correcting the ground truth; fuzzy had merged them, so under the
corrected labels those 4 pairs became **false positives** — the perfect precision was partly an
artifact of the label error. Restated over **11** canonicals: best-F1 threshold 0.70 → **P=0.996,
R=0.983, F1=0.989** (4 FP, all `Công nghệ kỹ thuật máy tính` ↔ `Kỹ thuật máy tính` near-misses);
threshold ≥0.80 → **P=1.000, R=0.924** (the two families separate). Hard negatives that held at all
thresholds: `Kỹ thuật ↔ Khoa học máy tính`, `Khoa học dữ liệu ↔ Khoa học máy tính`, `AI+DS ↔ AI`; the
`Công nghệ kỹ thuật máy tính ↔ Kỹ thuật máy tính` pair is now in the labeled hard-negative set.

**Threshold — a deliberate, precision-favouring choice.** The fuzzy candidate step runs at
**threshold 0.80** (`PROD_THRESHOLD` in `canonical_match.py`), *not* the best-F1 0.70. Reasoning: a
*false merge* silently conflates two distinct ngành and is **undetectable** by a data user, whereas a
*miss* leaves two visible clusters that an **override fixes**. So favour precision (P 1.000 at 0.80)
and close the recall gap (R 0.924) with the auditable human-verified map, rather than buying recall
with merges known to be wrong. Both operating points are reported for transparency — 0.70
(P 0.996 / R 0.983, best F1, but the 4 CNKT-máy-tính false merges) and 0.80 (P 1.000 / R 0.924). The
**shipped `canonical_major_id` is the human-verified assignment — threshold-independent** — so it
carries none of the fuzzy false merges (verified: `Công nghệ kỹ thuật máy tính` and `Kỹ thuật máy tính`
are separate in the shipped map).

**ML-component study — done, negative result (see `../ml/RESULTS.md`).** Embeddings were evaluated as
a candidate for the cybersecurity synonym residual, against a *two-sided* criterion: bridge the
synonyms (`An toàn thông tin` / `An ninh mạng` / `An toàn không gian số`) **and** keep the hard
negatives separate — `Công nghệ kỹ thuật máy tính ↔ Kỹ thuật máy tính`, `Kỹ thuật ↔ Khoa học máy
tính`, `Khoa học dữ liệu ↔ Khoa học máy tính`, `AI+DS ↔ AI` (0 false merges). Three models (multilingual
MiniLM, multilingual E5, Vietnamese PhoBERT bi-encoder) × three systems (fuzzy S1 / embeddings S2 /
hybrid S3) were run on the same 3,321-pair harness. **Outcome (two findings, both reported):** (1) the *union* hybrid `fuzzy>t1 OR cos>t2` does **not**
beat the baseline for any model — a global cosine threshold can't isolate the synonyms from the STEM
near-misses; but (2) a **learned 2-feature classifier** on `[fuzzy, cosine]` (a depth-3 decision tree)
**does** beat it on the two-sided test on full data — synonym recall 0.67 (vs fuzzy 0.13) with **zero
hard-negative false merges** and F1 0.994 — because the two classes separate diagonally in the joint
feature space (synonyms low-fuzzy/high-embedding; hard negatives high-fuzzy/high-embedding), which the
union cannot represent but conjunctive tree splits can. Honest scope: 5-fold CV generalises overall
(held-out F1 ≈ 0.97, 0 hard-neg FP) but held-out **synonym** pairs are n=1 — synonym-bridging
*generalisation* is under-powered at 6 synonym strings and is exactly what the **v2 scale** (587
schools) would confirm. The **shipped dataset uses the human-verified map regardless**; the matcher is
a reproducible method that reproduces (and here sharpens) that judgment. Core pipeline stays
standard-library-only; the ML study (`../ml/`, pinned deps) is optional. Full detail: `../ml/RESULTS.md`. Its *only* structural
failures were cross-string semantic synonyms — the cybersecurity cluster
(`An toàn thông tin` / `An ninh mạng` / `An toàn không gian số`, per-cluster recall **0.27**) and one
renamed base (`Kỹ thuật dữ liệu`→networks). Those are closed in the reviewed canonical map **as an interim, hand-verified stopgap so v1 can
ship** — this is *not* the ML component and does not count as solving the residual "with ML". If
embeddings later become the ML component, they are the principled, *measured* solution to this same
cybersecurity cluster (recall 0.27 → X), and they **replace** the interim map's role for it — the two
must never both claim credit for the same residual.

Bundled multi-major cutoff rows (`nhóm ngành …`) are **excluded-with-record** in
`config/excluded_bundled.csv` (not deleted), so "why no data for school X year Y" is always answerable.

**Group membership is decided at the admission-unit (ngành) level, not the internal chuyên-ngành
level.** A ngành is in-group by its own identity; specialisations chosen *after* admission do not
change that. E.g. EPU admits a single ngành "Công nghệ thông tin" (code 7480201, one cutoff) whose
four internal chuyên ngành include "Hệ thống thương mại điện tử" — this does **not** conflict with
e-commerce being excluded from the CS group, because at EPU e-commerce is a track inside CNTT, not a
separately-admitted ngành with its own code and cutoff.

**Data-quality finding — major codes are not stable identifiers.** UET reused code `CN8` for a
*different* major across years: "Công nghệ thông tin (CLC)" in 2019–2021, then "Khoa học máy tính" in
2022–2025. This is direct evidence for a core design decision: **canonical identity is name-based, not
code-based** — keying identity on `(school, code)` would have silently merged two distinct majors.
(Related: HUST reuses codes with `x`/`y`/`z` year-suffixes for the same major, the inverse problem.)

## Coverage & wide pivot

- `data/processed/coverage.csv` — one row per `(school, canonical_major, year)` **within each
  major's active span**, with `has_thpt` (any variant) and `has_base`.
  - **Active span (exact definition, as `build_gold.py` implements it):** for each
    `(school, canonical_major)`, every year from its **first to its last observed year, inclusive**
    (`range(min(years), max(years)+1)`). Years before it first appears or after it is discontinued are
    **not** counted — so "not yet offered" / "no longer offered" years are never miscounted as THPT
    gaps. Summing these spans over all `(school, canonical_major)` pairs gives the **denominator = 210
    cells**.
  - **Headline (verified against the committed file):** **99%** dataset coverage (208/210 cells have a
    THPT score in any variant) and **86%** base-comparable (181/210 have a `base` offering); 2 genuine
    THPT gaps (HUST cybersecurity & AI+DS, 2022).
Two pivot views, each for one purpose (like `mark` vs `mark_normalized_30`) — **do not swap them**:

- `data/processed/cutoffs_cs_compare.csv` — **single-year cross-school comparison.** Canonical major ×
  school, year columns, `mark_normalized_30`, using the base→english→clc→joint→advanced representative
  fallback so no school silently vanishes from a given year's comparison; a trailing `*` marks a
  non-base representative (annotate on charts, per the base-less-school rule).
- `data/processed/cutoffs_cs_trend.csv` — **time series (hybrid, single-variant lines).** Each series
  is one variant only, chosen by rule: **base-preferred** — if the school ever offers a base program
  for that major, the line is the base series *with explicit gaps* in years it wasn't offered (the
  trajectory is preserved, not deleted); **otherwise** the line is the school's *consistent non-base
  variant*, and the `variant` column labels it (`english`/`joint`/`advanced`/`clc`). A series with no
  base whose variant *switches* mid-run is the genuine defect and is **excluded**. Columns:
  `variant` and `n_points` precede the year columns.
  - **Levels are NOT comparable across lines of different variants.** The trend view shows *shape over
    time within a line*; cross-line *level* comparison is the compare view's job. Always plot each
    line with its `variant` label visible.
  - A blank cell = **"no offering of this line's variant that year", NOT "no program"** (a different
    variant may exist — see the compare view). HANU CNTT appears here as an `english` line, not absent.
  - **`n_points` < 3 ⇒ do not present as an ordinary trend line** (a 1–2 point "trend" is meaningless
    and will be over-read). There are **8** such short series (e.g. EPU/UET Khoa học dữ liệu, several
    2025-only firsts, HUST Hệ thống thông tin joint = 2019 only); filter or separate them.

Why the hybrid rule (and not the naive compare fallback for trends): the compare view's
representative fallback is safe within one year but **manufactures fake year-over-year jumps** when a
line's variant changes. Example: HUST Khoa học máy tính via the fallback reads 28.43 (2021, base) →
25.15 (2022, *joint* Troy — no base that year) → 29.42 (2023, base), a false +4.27; the trend view
keeps it a base line, 28.43 → (gap) → 29.42.

Coverage caveat: the 2 gaps (HUST cybersecurity & AI+DS, 2022) are **genuine no-THPT-that-year** —
those programs exist in the 2021 and 2023 raw data but weren't offered via THPT in 2022 (confirmed
against bronze), not a matching miss.

### `program_variant` — how it's assigned

A first-pass rule over the (whitespace- and dash-normalized) major name, applied in a **fixed,
deterministic precedence** — the first match wins:

1. `joint` (liên kết / hợp tác / Việt-Nhật·Pháp·Anh / Troy / La Trobe / Victoria / Grenoble / PFIEV /
   quốc tế / Global ICT)
2. `english` (dạy bằng tiếng Anh / …TA)
3. `clc` (chất lượng cao / CLC)
4. `advanced` (chương trình tiên tiến / CTTT / (cử nhân) định hướng ứng dụng)
5. `base` (none of the above)

**`program_variant` records the *primary* attribute, not a complete description** — a program can
carry several (e.g. HANU's "CNTT (dạy bằng tiếng Anh) - CLC" is both English-taught and CLC; the
precedence records `english`). This precedence is load-bearing: it determines how a series appears in
the trend view, so it must not change silently (e.g. via a refactor). Name-derived labels are
corrected where needed via sourced overrides in `config/program_variant_overrides.csv` (HANU 2019
CNTT → `english`; HUS QHT40 2019–20 → `clc`), and audited by `src/audit_variants.py` (year-stability
+ code-signal passes).

## Encoding, keys, and normalizer notes

- **Encoding.** All published CSVs are written **UTF-8 with BOM (`utf-8-sig`)** so Excel on Windows
  auto-detects them (it otherwise reads CSV as cp1252 and shows Vietnamese as mojibake, e.g.
  `Khoa há»c mÃ¡y tÃ­nh`). The files are valid UTF-8 either way; pandas/`csv` read them unchanged. The
  same cp1252 default is why console scripts set `PYTHONUTF8=1` / reconfigure stdout.
- **Keys vs display.** `canonical_major_id` is an ASCII slug (safe join key, stable across tools);
  `canonical_major_name` is Vietnamese **with diacritics — the source of truth**. There is no English
  translation column by design (this data dictionary and the README, both English, cover that need).
- **Normalizer residue (known, harmless).** `normalize()` strips *known* variant/parenthetical tokens
  but leaves unrecognised trailing tokens in the normalized string — e.g. `… - TT` → `…tt`,
  `ĐH Victoria Wellington` → `…wellington`. These rows still land in the correct canonical (via fuzzy
  similarity / the reviewed map), not via clean normalization, so it is a cosmetic limitation of the
  stripper, not a correctness bug.

## Still owed

- **Representative ~5–10% reliability reconciliation** across normal records — the HUS check was
  mechanism-only cross-validation (sample #1).
- **ML component decision** — leading validated candidate: embeddings on the cybersecurity synonym
  residual (fuzzy's real, measured failure). Deferred until the dataset is complete.
