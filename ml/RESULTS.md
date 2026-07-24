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

## What this means for the project (honest framing)

This is a **genuine, measured ML investigation with a negative result** — which is itself the finding:
at this scale, fuzzy + a human-verified map is the right tool, and embeddings would be the overselling
the project set out to avoid. A *targeted* method (embeddings only to surface synonym candidates for
human/rule confirmation, or a supervised pair classifier) might separate the two forces — but that is
**v2 scaling work** (587 schools, no human review), not evidenced here, and explicitly out of scope
for v1.
