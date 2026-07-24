# ML study (optional module) — embeddings for canonical-identity matching

**This module is optional and NOT required to reproduce the dataset.** The core pipeline
(`../src/*`) is standard-library only; cloning the repo to rebuild the dataset needs nothing
installed. Only running *this study* needs the models below.

> **Result: [`RESULTS.md`](RESULTS.md) — four findings, in sequence:**
> **(1)** raw embeddings fail the two-sided test across all 3 models; **(2)** the union hybrid fails too;
> **(3)** the two signals ARE separable in 2D — a learned depth-3 tree on `[fuzzy, cosine]` bridges
> synonyms (0.67) with 0 hard-negative false merges on full data, refuting the simple negative; **(4)**
> but with exactly one synonym cluster in the data, that fix's *generalisation* cannot be validated
> (held-out synonym pairs n=1) — itself a result: at this scale the dataset lacks enough instances of
> the hard phenomenon to validate a solution to it. **So v1 ships fuzzy + the human-verified map; the
> learned 2-feature method is the documented v2 approach, not a v1 shipped component.**

## The honest frame

At 84 major-name strings across 11 canonical majors, the **shipped canonical map is human-verified**
(`../config/canonical_majors_draft.csv`). This matcher does **not** produce the dataset. What it
measures is a **reproducible automated method that tries to reproduce the domain expert's judgment** —
to learn whether that judgment holds up under an automatic method and whether it would scale. The
real scaling target (587 schools, where per-string human review is impossible) is an explicit **v2**,
after v1 publishes. No result here should ever be phrased as "ML built the dataset."

## Pre-commitment (fixed before any number was computed)

To keep this a comparison and not model-shopping, the following was decided **in advance**:

1. Run **all three models × three systems** and **report every result** — including
   "all embeddings lose to fuzzy" or "the hybrid does not beat the baseline" if that is the outcome.
   No running until something works.
2. **Fuzzy (`difflib`) is the baseline (S1).** Embeddings earn their place **only if the hybrid (S3)
   beats fuzzy-alone (S1)** on the two-sided criterion below — same rule applied to forecasting: we do
   not ship a component that loses to its baseline just to have an "ML" box ticked.

## Follow-up pre-commitment (added before running it)

The union hybrid (S3) can only carve axis-aligned regions, so it cannot represent a boundary that runs
diagonally across the (fuzzy, embedding) plane — yet that is exactly where the two classes separate
(synonyms: low-fuzzy / high-embedding; hard negatives: high-fuzzy / high-embedding). One follow-up is
therefore run and **reported regardless of outcome**: a **2-feature supervised classifier**
(logistic regression + shallow decision tree) on `[fuzzy_score, embedding_cosine]`, same CV folds and
same two-sided criterion, on the best embedder (Model C) plus one other (A) for robustness
(`classify2feat.py`). If it beats fuzzy on the two-sided test → a genuine shipped ML component (neither
signal alone works, a learned combination does). If it also fails → the negative result is *more*
robust (raw embeddings failed, the union failed, and a learned combination of both signals failed).
**Time-boxed to this one experiment** — no further model variants; then we ship.

## Systems, criterion, and reporting

- **S1** fuzzy alone · **S2** embeddings alone (diagnostic) · **S3** hybrid = fuzzy ∪ embeddings
  (each above its own threshold). The decision is **S3 vs S1**, not S2 vs S1 — embeddings are meant
  to handle only the residual that fuzzy structurally cannot.
- **Two-sided success (both required):** (i) **bridge** the cybersecurity synonyms (fuzzy's
  cluster recall is 0.27), and (ii) **keep the hard negatives separate** — 0 false merges among
  `Công nghệ kỹ thuật máy tính ↔ Kỹ thuật máy tính`, `Kỹ thuật ↔ Khoa học máy tính`,
  `Khoa học dữ liệu ↔ Khoa học máy tính`, `AI+DS ↔ AI`.
- **Reporting at two levels, always:** full 3,321-pair P/R/F1 (comparable across systems) **and**
  per-cluster recall (diagnostic). The synonym cluster is ~15 pairs — small-n, one pair ≈ 7pp — stated
  explicitly. Full threshold sweep reported for transparency; operating threshold chosen by 5-fold CV
  (tuned on train folds, never on the test pairs), precision-favouring.

Same `normalize()` / strings / `ground_truth()` labels / `prf()` harness as `../src/canonical_match.py`
— only the similarity function changes (fuzzy `difflib` ratio → embedding cosine).

## Run

```
python -m venv .venv && . .venv/Scripts/activate      # Windows; use .venv/bin/activate on POSIX
pip install -r requirements.txt
python embed_match.py                                  # downloads the 3 models on first run (~2 GB)
```

Models (all free, local, no paid API): **A** `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`
(118M, Apache-2.0); **B** `intfloat/multilingual-e5-base` (278M, MIT); **C**
`bkai-foundation-models/vietnamese-bi-encoder` (PhoBERT-base, Apache-2.0, needs `pyvi` word
segmentation).
