# ML study results — the four findings (in sequence)

Run: `python embed_match.py` (raw embeddings + union hybrid) and `python classify2feat.py` (learned
2-feature classifier). Same `normalize()` / strings / `ground_truth()` labels / `prf()` harness as
`../src/canonical_match.py`; same 3,321-pair set; two-sided criterion (bridge the cybersecurity
synonyms **and** keep the hard negatives separate — 0 false merges). Reported per the pre-commitments
in `README.md`, **including the outcomes that don't favour a shipped model.**

## Verdict

**v1 ships fuzzy + the human-verified canonical map, as measured. The ML investigation is closed.**
The study did not produce a component whose one decisive capability (bridging cross-string synonyms)
can be *validated to generalise* at this scale — so the learned method is presented as the **v2**
method, not a v1 shipped component.

Baseline — S1 fuzzy @0.80: P 1.000 / R 0.924 / F1 0.961, synonym-cluster recall 0.13, hard-neg FP 0.

## Finding 1 — raw embeddings fail the two-sided test (all 3 models)

With a global cosine threshold, no model bridges the synonyms without also merging the hard negatives.
The only thresholds that keep hard negatives separate leave synonym recall at fuzzy's level (0.13);
the only thresholds that bridge synonyms (Model C reaches 0.67 at cos≈0.65) carry **73 hard-negative
false merges**. Model C (Vietnamese PhoBERT) is the sharpest embedder; multilingual E5 was nearly
useless on these short strings. Full sweep (0.50–0.95) printed by `embed_match.py`.

## Finding 2 — the union hybrid fails too

`fuzzy > t1 OR cos > t2` cannot beat the baseline for any model. An OR-union of two thresholds can only
carve axis-aligned regions, and the two classes do not separate along either axis alone.

## Finding 3 — the two signals ARE separable in 2D (this refutes the simple negative)

Findings 1–2 are a limitation of *raw cosine + a global threshold + an OR-union*, not of the embedding
*signal*. In the (fuzzy, embedding) plane the classes sit in different regions — synonyms at
**low-fuzzy / high-embedding**, hard negatives at **high-fuzzy / high-embedding**. A **depth-3 decision
tree** on `[fuzzy, cosine]` (≤8 leaves — too low-capacity to memorise 3,321 pairs) achieves, on full
data, synonym recall **0.67** with **0 hard-negative false merges** and F1 0.994. A *linear* model
(logistic regression) fails — it cannot carve the "high-embedding **and** low-fuzzy band" that isolates
synonyms from the higher-fuzzy hard negatives; the tree's conjunctive splits can. So: neither signal
alone works, the union can't represent the boundary, but a **learned combination can**.

| Model + classifier | full-fit synonym recall | full-fit hard-neg FP | full-fit F1 |
|---|---|---|---|
| C / A + logistic regression | 0.13 / 0.27 | 4 | 0.988 |
| **C / A + decision tree (d=3)** | **0.67** | **0** | **0.994** |

## Finding 4 — at this scale, generalisation of the fix cannot be validated (itself a result)

The Finding-3 "beats" is **full-fit/apply**. Under 5-fold string CV the tree generalises on *overall*
pair classification (held-out F1 ≈ 0.97, 0 hard-neg FP) — **but that number is dominated by easy pairs**
(~820 of the same-label pairs are CNTT surface variants). The one capability that would justify shipping
— **synonym bridging** — has exactly **n=1** synonym pair in held-out across all folds, because the data
contains **one** cybersecurity synonym cluster (6 strings). Full-fit on a single positive cluster is
near-zero evidence of generalisation. **So the honest, plainly-stated result is: at this scale the
dataset does not contain enough instances of the hard phenomenon to validate a solution to it.** That is
precisely what the **v2** scale (587 schools, many synonym clusters, no feasible human review) would fix
— and it is why the learned 2-feature method is the documented v2 method, not a v1 shipped component.

## What ships, and why this is the honest outcome

v1 ships **fuzzy + the human-verified map** (the dataset is correct by construction; the matcher's role
is only to be a reproducible method that reproduces that judgment). The ML study is a genuine, measured
investigation whose value is the four findings above — including Finding 4, which turns "we couldn't
prove the fix works" into a concrete, defensible statement about the data and a precise v2 objective.
No component is shipped that cannot be defended. The core pipeline stays standard-library-only; this
`ml/` module (pinned deps, venv-isolated) is optional and reproduces every number above.
