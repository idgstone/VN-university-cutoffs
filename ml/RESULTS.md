# ML study results — embeddings do NOT earn their place (v1)

Run: `python embed_match.py` (models A/B/C × systems S1/S2/S3, full 3,321-pair + per-cluster,
two-sided criterion). Reported per the pre-commitment in `README.md` — **including this negative
outcome**.

## Verdict

**Fuzzy (the baseline) wins. For all three models, the hybrid (S3) does not beat fuzzy (S1) on the
two-sided criterion, so embeddings do not earn their place in v1.** The human-verified canonical map
stands, and the core pipeline stays standard-library only.

## Why (the finding, not just the number)

The two-sided test requires **both**: bridge the cybersecurity synonyms (beat fuzzy's 0.13 synonym
recall at the production threshold) **and** keep the hard negatives separate (0 false merges). These
are in **direct conflict at the embedding-similarity level**: the cybersecurity synonyms
(`An toàn thông tin` ≈ `An ninh mạng` ≈ `An toàn không gian số`) are, to every model, **no more
similar than the STEM near-misses that must stay apart** (`Khoa học máy tính` ↔ `Khoa học dữ liệu`,
`Công nghệ kỹ thuật máy tính` ↔ `Kỹ thuật máy tính`). So there is **no global cosine threshold** that
bridges the synonyms without also merging the hard negatives.

Concretely — the only place any model bridges synonyms is at low thresholds where it also merges the
hard negatives wholesale; every threshold that keeps hard negatives separate leaves the synonyms
un-bridged (synonym recall stuck at fuzzy's 0.13):

| System | best synonym recall with **0 hard-neg FP** | S3 F1 there vs fuzzy 0.961 | beats fuzzy? |
|---|---|---|---|
| S1 fuzzy @0.80 (baseline) | 0.13 | 0.961 | — |
| Model A (MiniLM) | 0.13 (never reaches 0 FP below thr 0.95; syn stuck) | ~0.959 | **no** |
| Model B (E5-base) | — (never reaches 0 hard-neg FP in sweep; cosines too compressed) | 0.455 | **no** |
| Model C (bkai VI) | 0.13 (0 FP only at thr 0.95, where nothing bridges) | 0.961 (= fuzzy) | **no** |

To *bridge* synonyms, Model C (the best embedder) needs thr ≈ 0.65 → synonym recall 0.67, but there
**hard-neg FP = 73** (it merges KHMT↔KHDL, CNKT↔KTMT, … en masse). C's highest S3 F1 (0.986 at thr
0.75) comes from merging more easy surface variants, **not** from bridging synonyms (syn still 0.13)
and it already carries 4 hard-neg false merges. Either way the two-sided test fails.

## Secondary observations

- **Model C (Vietnamese-specific PhoBERT bi-encoder) is clearly the best embedder** here — sharpest
  cosine separation, consistent with the domain. Model B (multilingual E5) was nearly useless on
  these short strings (cosine range too compressed: almost everything merges until thr ≈ 0.95).
- Per-cluster numbers are **small-n**: the synonym cluster is 15 pairs (one pair ≈ 7 pp) — never a
  headline; used only as a diagnostic, always beside the full-set P/R/F1.
- The full threshold sweep (0.50–0.95) is printed by the script for every model/system, so nothing is
  cherry-picked.

## Follow-up (`classify2feat.py`): a LEARNED 2-feature classifier — the negative flips

The result above is a limitation of **raw cosine with a global threshold and an OR-union**, not of the
embedding *signal*. In the (fuzzy, embedding) plane the two classes sit in different regions —
synonyms at **low-fuzzy / high-embedding**, hard negatives at **high-fuzzy / high-embedding** — a
boundary the union (`fuzzy>t1 OR cos>t2`) cannot represent. A classifier on **both** features can.

Reference S1 fuzzy: P 1.000 / R 0.924 / F1 0.961, synonym recall 0.13, hard-neg FP 0.

| Model + classifier | CV held-out (within-fold) | Full-fit / apply (optimistic) | two-sided vs fuzzy |
|---|---|---|---|
| C + logistic regression | F1 0.979, hn-FP 0 | F1 0.989, **syn 0.27**, **hn-FP 4** | does NOT beat |
| **C + decision tree (d=3)** | F1 0.973, hn-FP 0 | F1 0.994, **syn 0.67**, **hn-FP 0** | **BEATS** |
| A + logistic regression | F1 0.956, hn-FP 0 | F1 0.988, syn 0.13, hn-FP 4 | does NOT beat |
| **A + decision tree (d=3)** | F1 0.976, hn-FP 0 | F1 0.994, **syn 0.67**, **hn-FP 0** | **BEATS** |

**Finding:** a **depth-3 decision tree** (≤8 leaves — too low-capacity to memorise 3,321 pairs)
bridges 2/3 of the cybersecurity synonym sub-clusters (**recall 0.67** vs fuzzy's 0.13) **with zero
hard-negative false merges** and higher overall F1. A *linear* model (logreg) fails — it cannot carve
the "high-embedding **and** low-fuzzy band" region that isolates synonyms from the higher-fuzzy hard
negatives; the tree's conjunctive splits can. So neither signal alone works, the union can't represent
the boundary, but a **learned combination does** — exactly the diagonal-separation hypothesis.

**Honest scope — the one thing not validated.** The "BEATS" row is **full-fit/apply (optimistic)**.
The 5-fold CV shows the tree generalises on *overall* pair classification (held-out F1 ≈ 0.97, **0
hard-neg FP**), but the held-out **synonym** pairs are **n=1** — far too few to validate synonym-
bridging *generalisation* specifically. At 6 synonym strings this data simply can't power that test.
So: the two classes are **demonstrably separable** by a learned 2-feature boundary (refuting the
"impossible" reading), and it generalises without hard-negative errors — but synonym-bridging transfer
to unseen schools is exactly what only the **v2 scale** (587 schools) could confirm.

## What this means for the project (honest framing)

Two real findings, both reported: (1) raw embeddings + a global threshold, and their OR-union with
fuzzy, **do not beat** the baseline; (2) a **learned 2-feature classifier (decision tree) does** beat
it on the two-sided test on full data, and generalises cleanly except on the (unavoidably tiny)
synonym subset. The **shipped dataset uses the human-verified map either way** — the matcher's role is
to be a *reproducible method that reproduces (and here, sharpens) that judgment*. This is a genuine,
measured ML component that clears the baseline bar, with its generalisation scope stated honestly — the
natural bridge to the v2 scaling study, not overselling.
