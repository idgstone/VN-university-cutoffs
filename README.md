# Vietnamese University Admission-Cutoff Dataset — Computing & IT, Hà Nội (2019–2025)

A clean, machine-readable dataset of Vietnamese university admission cutoff scores (**điểm chuẩn**) for
the **Computing & Information Technology** field group at **public universities in Hà Nội**, unified
across **2019–2025**, with the **fully reproducible, standard-library-only pipeline** that produces it.

The thing people actually want — cutoffs by *university × major × year*, cleaned and unified across
years — exists only behind lookup-only portals and scattered announcement PDFs/images. This assembles
one meaningful slice of it, **cleanly, correctly, and documented**, with every non-obvious decision
written down so it can be defended.

> **Scope is deliberately narrow.** Depth over breadth: 10 schools, one field group, one admission
> method, done carefully — not every school done sloppily. Other groups/regions are explicit *v2*.

---

## Quick start (reproduce the dataset — no dependencies)

```bash
python src/collect.py           # 1. bronze: pull raw JSON from the source API (polite, cached)
python src/build_cs_mapping.py  # 2. decide CS-group membership (rule + human overrides)
python src/build_silver.py      # 3. silver: clean/normalize per-record table
python src/canonical_match.py   # 4. canonical identity (fuzzy + human-verified map) + matcher eval
python src/build_gold.py        # 5. gold: canonical ids, coverage grid, trend & compare views
```

Python 3.12, **standard library only** — nothing to install to rebuild the dataset. QA passes:
`python src/sanity_raw.py` (content checks) and `python src/audit_variants.py` (variant audits). The
optional ML study lives in [`ml/`](ml/) with its own pinned dependencies (see below).

## What you get

| File | What |
|---|---|
| [`data/processed/cutoffs_cs.csv`](data/processed/cutoffs_cs.csv) | **The dataset** — one tidy row per (school × major × year × subject-block), 278 rows, 11 canonical majors, THPT method |
| `data/processed/cutoffs_cs_trend.csv` | Time-series view (single-variant lines, honest gaps) |
| `data/processed/cutoffs_cs_compare.csv` | Single-year cross-school comparison view |
| `data/processed/coverage.csv` | Coverage grid (major × year) |
| `data/raw/thpt/*.json` + `manifest.csv` | Immutable raw source responses + provenance (70 files, 2,361 records) |
| [`docs/data_dictionary.md`](docs/data_dictionary.md) | Column-by-column schema and every design decision |
| [`docs/reconciliation.md`](docs/reconciliation.md) | Source-reliability cross-validation |

Cutoffs are on the **30-point** national-exam scale (`mark`); a normalized column
(`mark_normalized_30`) makes cross-school/trend comparison valid — read the data dictionary before
plotting.

---

## Key decisions (the interview story)

### Scope: why this slice
- **Computing/IT group** — defined by a **uniform semantic rule** applied to all 10 schools (core
  curriculum centers on computing/software/data), with the Ministry field code `748` as a *supporting
  signal only*, not the definition. Membership is a hand-verified, auditable CSV.
- **Public universities in Hà Nội** — a homogeneous admission mechanism, so cross-school comparison is
  meaningful (private schools use more varied methods → deferred).
- **THPT (national-exam) method only** — the one method comparable across schools and years. Where a
  school didn't admit a major via THPT in a year, the cell is **null, not dropped**, and a coverage
  metric reports it honestly (99% of major-year cells within a major's active span have a THPT score;
  86% have a directly-comparable *base* offering).

### Source & legality
- Source: **tuyensinh247** (`diemthi.tuyensinh247.com`), an aggregator. I found and used its
  **undocumented JSON API** after confirming its `robots.txt` allows the path and its terms contain no
  anti-automation clause; the collector is single-threaded and rate-limited. Every raw response is
  saved verbatim (immutable "bronze") so results reproduce even if the API changes.
- Because it's an aggregator, I **cross-validate a sample against primary sources** (below).
- **No personal data** — only aggregate cutoffs, never individual scores.

### Architecture: bronze → silver → gold, with sourced overrides
Immutable raw layer; a cleaned per-record layer; a canonical/analytical layer. **Every departure from
the source is driven by an auditable override CSV** (`config/*_overrides.csv`, `mark_corrections.csv`)
and flagged + explained in the data itself — so any cell that differs from the source is defensible on
its own.

### The genuinely hard parts (and how they're solved)
1. **Score-scale heterogeneity.** HUS reports four programs on a **thang điểm 40** (Toán ×2) in
   2023–2024 only — which would fake a ~9-point spike-and-drop in a flagship Data Science trend. I
   confirmed the mechanism from primary sources (VNU/government), normalized to the 30-scale via
   **×0.75**, and **triangulated**: the normalized values land on the same major's other-year cutoffs.
2. **Entity resolution (the AI/ML problem).** The matcher resolves 82 distinct name strings → 11 canonical
   majors (plus 2 bundled multi-major rows excluded-with-record). A rule-based normalizer + `difflib`
   fuzzy matcher does the bulk; the **shipped map is
   human-verified**. Fuzzy scores P 1.000 / R 0.924 at a **precision-favouring threshold (0.80)** —
   chosen deliberately because a false merge silently conflates two distinct ngành (undetectable by a
   user) while a miss is a visible, override-fixable split. Precision/recall are reported at two levels
   (full 3,321-pair *and* per-cluster) — and a ground-truth error I made was caught in review, fixed,
   and the metrics restated. See the ML study below.
3. **Program variants & two chart views.** Programs carry variants (base / CLC / joint / English /
   advanced) with genuinely different cutoffs. Identity = the base major; the variant is an attribute.
   The **trend view** is base-preferred single-variant lines with honest gaps; the **compare view**
   uses a representative fallback for single-year cross-school comparison. Variant labels are derived
   from names, so a name-drift/whitespace/dash audit (`audit_variants.py`) plus sourced overrides keep
   them consistent.
4. **Codes are not stable identifiers.** One school reused a code for a *different* major across years
   (UET `CN8`: CNTT-CLC → Khoa học máy tính); another appends `x`/`y` year-suffixes to the same major
   (HUST). Keying identity on code would silently merge distinct majors — which is why identity is
   **name-based**, not code-based.
5. **A real aggregator error, caught and corrected.** Reconciliation surfaced HUS `Khoa học máy tính
   và thông tin` 2024 published as **34.0** vs the official **34.7**; corrected in the silver layer with
   a sourced note (bronze stays immutable).

### Reliability reconciliation — scoped honestly, never blended
Reported by **era** and by **verification strength** ([`docs/reconciliation.md`](docs/reconciliation.md)):
**2021–2025** random sample — 4/4 records matched against a *primary* source, 12/12 more matched an
*independent aggregator*, 0 discrepancies. **2019–2020** — primary sources are offline / blocked /
image-based / paginated, so **no reliability claim is made** for old years (the disappearance of
historical primary sources is itself a finding that motivates a maintained dataset).

---

## The ML investigation — four findings (closed)

I treated entity resolution as the ML question and asked whether **embeddings** could replace my
hand-verification, pre-committing to report the outcome either way ([`ml/`](ml/), optional module):

1. **Raw embeddings fail the two-sided test** (bridge the cybersecurity synonyms `An toàn thông tin` ≈
   `An ninh mạng` ≈ `An toàn không gian số` **and** keep hard negatives like `Khoa học máy tính` ↔
   `Khoa học dữ liệu` separate) across all three models — to every model the synonyms are no more
   similar than the near-misses that must stay apart.
2. **The union of fuzzy + embedding thresholds fails too** — it can only carve axis-aligned regions.
3. **But the two signals are separable in 2D** — a depth-3 decision tree on `[fuzzy, cosine]` bridges
   the synonyms (recall 0.67 vs fuzzy's 0.13) with **zero** hard-negative false merges on full data.
   This refutes the simple negative: neither signal alone works, a *learned combination* does.
4. **At this scale, the fix can't be validated to generalise** — the data contains exactly one
   synonym cluster (6 strings), so held-out synonym pairs are n=1. That is itself a result: *the
   dataset doesn't contain enough instances of the hard phenomenon to validate a solution to it* —
   precisely what a v2 at 587-school scale would fix.

**So v1 ships fuzzy + the human-verified map** (correct by construction); the learned 2-feature method
is the documented **v2** approach, not a v1 shipped component. Full detail + reproduction:
[`ml/RESULTS.md`](ml/RESULTS.md).

---

## Honest limitations

- One field group, 10 Hà Nội public universities, THPT method, 2019–2025 — by design.
- 2019–2020 values are **not** independently reconciled (sources gone); recent years are.
- The canonical map is human-verified at this scale; the automated matcher is a *method*, not the
  dataset's source of truth.
- `program_variant` records a program's **primary** attribute (fixed precedence), not a full
  description.

## Reproducibility & provenance philosophy

Standard-library-only core; immutable raw layer with sha256 + fetched-at manifest; every cleaned value
traces to its raw record; every non-source value is a flagged, sourced override. The optional
[`ml/`](ml/) study pins its dependencies and is not needed to rebuild the dataset.

## Credits

Source data aggregated by **tuyensinh247**; cutoffs cross-checked against university / VNU / Ministry
announcements where reachable (credited in `docs/reconciliation.md`). This repository redistributes a
re-derived, restructured dataset with attribution, not the source's page layout.
