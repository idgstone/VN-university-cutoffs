# Vietnamese University Admission-Cutoff Dataset — Computing & IT, Hà Nội (2019–2025)

A clean, machine-readable dataset of Vietnamese university admission cutoff scores (**điểm chuẩn**) for
the **Computing & Information Technology** field group at **public universities in Hà Nội**, unified
across **2019–2025**, with the **fully reproducible, standard-library-only pipeline** that produces it.

The thing people actually want — cutoffs by *university × major × year*, cleaned and unified across
years — exists only behind lookup-only portals and scattered announcement PDFs/images. This assembles
one meaningful slice of it, cleanly and documented, with every non-obvious decision written down so it
can be defended.

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
`python src/sanity_raw.py` and `python src/audit_variants.py`. The optional ML study lives in
[`ml/`](ml/) with its own pinned dependencies.

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

I work depth-first: one field group done carefully beats every school done sloppily. I chose
**Computing/IT** specifically because it's the field I understand best — so when the group-membership
rule or the name-matching goes wrong, I can catch it myself, which is an edge most candidates working
this data wouldn't have. Starting with one group also meant that if something went wrong I could redo it
quickly, instead of building everything and having to redo all of it.

I limited it to **public universities in Hà Nội**: Hà Nội concentrates most of the public schools, and
public schools lean on the THPT (national-exam) method with a more uniform scoring system, so
cross-school comparison is actually meaningful — private schools use far more varied admission methods,
which would make the comparison apples-to-oranges.

And I kept a **single admission method, THPT**, because it's the one method comparable across both
schools and years: other methods (ĐGNL, etc.) sit on entirely different score scales, so mixing them in
would be comparing incomparable numbers. Where a school didn't admit a major via THPT in a year, the
cell is **null, not dropped**, and a coverage metric reports it honestly (99% of major-year cells within
a major's active span have a THPT score; 86% have a directly-comparable *base* offering).

### Defining the CS group: code is a signal, not the definition

The CS group is defined by a **semantic rule** applied uniformly to all 10 schools: a major is in-group
if its core curriculum centers on computing/software/data, out if it centers on
hardware/signals/geoscience/business. I deliberately **do not** use the Ministry field code `748` as the
definition, because the code isn't trustworthy: 4 of the 10 schools use internal codes (`CN1`, `IT1`,
`TLA106`, `QHT93`) rather than Ministry codes, and even the schools that use Ministry codes apply them
inconsistently — the same kind of major coded `748` at one school and `732` at another. If the code
decided membership, the same major would be counted at one school and excluded at another.

So the code is only a **corroborating signal**: when it agrees with the content judgment it reinforces
it, and when they conflict, the content wins. The clearest example: HUMG's geoinformatics (Địa tin học)
carries code `748`, but I still excluded it — its core field is geoscience, with computing as an applied
tool. The code said "in," the content said "out," and the content won.

### Source & legality

The data lives behind an aggregator, **tuyensinh247**. Rather than scraping their HTML, I found and used
an **undocumented JSON API behind their interface** — cleaner, structured, and it exposes the major
code (which helps with membership). Before collecting anything I checked their **robots.txt** (it allows
the path) and their **terms of use** (no anti-automation clause), and kept the collector single-threaded
and rate-limited.

Because it's an aggregator and its numbers can be wrong, I **cross-validated a sample against primary
sources** — and it paid off: I caught a real error, HUS "Khoa học máy tính và thông tin" 2024 published
as **34.0** vs the official **34.7**, corrected in the cleaned layer with a sourced note while the raw
layer keeps the original. **No personal data** — only aggregate cutoffs, never individual student scores.

### Architecture: bronze → silver → gold

Three layers: an **immutable raw layer** (bronze), a **cleaned layer** (silver), and a
**canonical/analytical layer** (gold). Bronze is the source responses saved verbatim — 70 raw JSON files
with a sha256 + fetched-at manifest, never modified. Silver reads from bronze and does all the cleaning:
scale normalization, corrections, flags. Gold builds the canonical majors, the coverage grid, and the
trend/compare views.

The rule that matters: **every departure from the source happens in silver or gold, never by touching
bronze.** If you edit the raw layer and get it wrong, the error propagates into every layer downstream
and there's no original left to check against or roll back to — so bronze stays untouched, which is what
makes every number traceable to its source and the whole pipeline reproducible by anyone who clones it.
When I corrected 34.0 → 34.7, it happened in silver; bronze still holds the original.

### The genuinely hard parts

**1. Score-scale heterogeneity — the ×0.75 normalization.** Four HUS programs (including Data Science
and Khoa học máy tính và thông tin) were scored on a **40-point scale** in 2023–2024 only, because HUS
doubles the Maths subject (Toán ×2). So HUS's "Data Science 34.85" isn't comparable to another school's
"27.86" — different scales. Left raw, HUS Data Science reads 26 → 26 → **34.85 → 35** → 26 across years:
a fake 9-point spike-and-drop that's pure scale artifact.

The fix: normalize the 40-scale values to 30 via **×0.75**. But the important part is how I *know* ×0.75
is right, not just that I applied it. Two things: I **confirmed the mechanism from the primary source**
(the VNU/Ministry announcement — Toán ×2 → max 40), and I **verified it by triangulation** — after
×0.75, the 2023–2024 values land on ~26, right where the same major's other years (2020, 2021, 2025)
sit. If the conversion were wrong, the normalized number would be off. It isn't. (×0.75 is an
approximation — exact only when the three subjects score equally — so I state that, and the
triangulation is the check.)

**2. Entity resolution.** The same major is written 82 distinct ways (84 raw strings, 2 bundled rows
excluded) and needs to collapse to 11 canonical majors. A rule-based normalizer plus a `difflib` fuzzy
matcher handles the surface variants; the **shipped map is human-verified**. I chose a
precision-favoring threshold (0.80): a false merge silently conflates two distinct ngành, which a user
can't detect, whereas a miss is a visible split I can fix with an override. During review I caught a
ground-truth error in my own labels, fixed it, and restated the metrics — reported at two levels (full
3,321-pair *and* per-cluster, since a headline off ~15 pairs would be meaningless).

**3. Program variants and two chart views.** A major at a school can have several variants (base / CLC /
joint / English), each with a different cutoff. Identity is the *base* major; the variant is an
attribute. This forces two views. The **trend view** keeps each line to a single consistent variant and
leaves a **gap** where that variant is missing in a year — because an empty cell is the truth (the
program wasn't offered that way that year), while filling it with a different variant creates a **fake
jump**. HUST's Khoa học máy tính is the case: 2022 had no base program, only a joint Troy one (25.15), so
filling it would read 28.43 → 25.15 → 29.42, a spike that isn't real. The **compare view** does allow a
representative fallback, so no school vanishes from a single-year cross-school comparison.

**4. Codes are not stable identifiers.** UET reused code `CN8` for a *different* major across years
(CNTT-CLC → Khoa học máy tính); HUST appends `x`/`y` year-suffixes to the same major. Keying identity on
code would silently merge distinct majors — which is exactly why identity is **name-based**, not
code-based.

### Reliability reconciliation — scoped honestly, never blended

Reported by **era** and **verification strength** ([`docs/reconciliation.md`](docs/reconciliation.md)):
for **2021–2025**, a random sample matched 4/4 against a *primary* source and a further 12/12 against a
second aggregator (**corroboration only, not independent proof — aggregators may share an upstream
source**), 0 discrepancies across all 16. For **2019–2020**, primary sources are offline / blocked /
image-based / paginated, so **no reliability claim is made** — the disappearance of historical primary
sources is itself a finding that motivates a maintained dataset.

---

## The ML investigation — four findings (closed)

I treated entity resolution as the ML question: could **embeddings** bridge synonyms that fuzzy string
matching can't? The cybersecurity cluster is the case — `An toàn thông tin` ≈ `An ninh mạng` ≈ `An toàn
không gian số` are the same program under three names that share almost no characters, so fuzzy (which
compares characters) structurally can't reach them; embeddings (which compare meaning) should. I
pre-committed to reporting the outcome either way ([`ml/`](ml/), optional module). Four findings, in
order:

1. **Raw embeddings fail a two-sided test** — bridge those synonyms *and* keep hard negatives like
   `Khoa học máy tính` ↔ `Khoa học dữ liệu` separate — across all three models. To every model the
   synonyms are no more similar than the near-misses that must stay apart, so no global threshold
   satisfies both.
2. **The union of fuzzy + embedding thresholds fails too** — it can only carve axis-aligned regions, not
   the diagonal boundary the structure needs.
3. **But the two signals are separable in 2D.** Synonyms are low-fuzzy/high-embedding; hard negatives
   are high-fuzzy/high-embedding. A depth-3 decision tree on `[fuzzy, cosine]` bridges the synonyms
   (recall 0.67 vs fuzzy's 0.13) with **zero** hard-negative false merges. Neither signal alone works; a
   *learned combination* does.
4. **At this scale it can't be validated to generalize.** The data contains exactly one synonym cluster,
   so held-out synonym pairs are n=1 — I can't prove the method transfers to unseen clusters. That's
   itself a result: the dataset doesn't contain enough instances of the hard phenomenon to validate a
   solution to it.

**So v1 ships fuzzy + the human-verified map** — correct by construction at this scale. The learned
2-feature method is documented as the **v2 approach** (587-school scale, where synonym clusters are many
and human review is impossible), not a shipped v1 component. Shipping it now would be an overclaim I
can't back with the data I have. Full detail: [`ml/RESULTS.md`](ml/RESULTS.md).

---

## Honest limitations

- One field group, 10 Hà Nội public universities, THPT method, 2019–2025 — by design.
- 2019–2020 values are **not** independently reconciled (sources gone); recent years are.
- The canonical map is human-verified at this scale; the automated matcher is a *method*, not the
  dataset's source of truth.
- `program_variant` records a program's **primary** attribute (fixed precedence), not a full
  description.

## License

- **Code:** MIT.
- **Dataset:** CC-BY-4.0.

The license covers **my compilation** — the schema, normalization, canonical map, corrections, and
documentation. It does **not** cover the cutoff numbers themselves: those are public facts published by
the universities and the Ministry of Education & Training, and facts aren't owned by anyone. Please
credit this repository for the compilation, tuyensinh247 as the aggregation source, and the
universities/VNU/Ministry as the primary sources.

## Reproducibility & provenance

Standard-library-only core; immutable raw layer with sha256 + fetched-at manifest; every cleaned value
traces to its raw record; every non-source value is a flagged, sourced override. The optional
[`ml/`](ml/) study pins its dependencies and is not needed to rebuild the dataset.
