"""
ML study (v1, OPTIONAL module) — can embeddings improve the canonical-identity matcher?

HONEST FRAME (read this, it governs how results are phrased):
  At 84 strings / 11 majors the SHIPPED canonical map is HUMAN-VERIFIED; this matcher does NOT produce
  the dataset. We measure a *reproducible automated method that tries to reproduce the domain expert's
  judgment*, to learn whether it holds up and would scale. The 587-school scaling study is v2, not now.
  Never phrase any result as "ML built the dataset."

PRE-COMMITMENT (fixed BEFORE any number existed — see ml/README.md):
  Run all 3 models × 3 systems and report EVERY result, including "all embeddings lose to fuzzy" or
  "the hybrid does not beat the baseline" if that is what happens. Fuzzy is the baseline; embeddings
  earn their place only if the HYBRID (S3) beats fuzzy-alone (S1) on BOTH sides of the two-sided
  criterion. No run-until-it-works.

Systems (same normalize / strings / labels / prf harness as src/canonical_match.py; only the
similarity function changes):
  S1  fuzzy alone            — union-find, edge if difflib token-sort ratio >= FUZZY_THR (=0.80, prod)
  S2  embeddings alone       — union-find, edge if cosine >= emb_thr
  S3  hybrid (fuzzy ∪ emb)   — union-find, edge if (ratio >= FUZZY_THR) OR (cosine >= emb_thr)

Two-sided success (report BOTH every time):
  (i)  BRIDGE the cybersecurity synonyms (fuzzy's cluster recall is 0.27), AND
  (ii) KEEP SEPARATE the hard negatives — 0 false merges among:
       cong-nghe-ky-thuat-may-tinh↔ky-thuat-may-tinh, ky-thuat-may-tinh↔khoa-hoc-may-tinh,
       khoa-hoc-du-lieu↔khoa-hoc-may-tinh, ttnt-va-khoa-hoc-du-lieu↔tri-tue-nhan-tao.

Reporting: FULL 3,321-pair P/R/F1 (headline, comparable across systems) AND per-cluster recall
(diagnostic; the synonym cluster is ~15 pairs — small-n, one pair ≈ 7pp — stated explicitly).
Threshold: full sweep reported for transparency + 5-fold CV selection (tune on split, not test).
"""
from __future__ import annotations

import os
# Windows: torch + numpy/MKL can bring two OpenMP runtimes -> segfault when loading models
# sequentially. This workaround must be set before torch imports. Single-threaded for determinism.
os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("HF_HUB_DISABLE_PROGRESS_BARS", "1")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

import csv
import statistics
import sys
from collections import defaultdict
from itertools import combinations
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "src"))
from canonical_match import normalize, ground_truth, is_bundle, prf, tok, ratio  # noqa: E402

sys.stdout.reconfigure(encoding="utf-8")

FUZZY_THR = 0.80                       # production fuzzy operating point (precision-favouring)
SYNONYM_CANON = "an-toan-thong-tin"    # the cross-string synonym cluster fuzzy fails (recall 0.27)
HARD_NEGATIVES = [                     # canonical pairs that MUST stay separate (0 false merges)
    ("cong-nghe-ky-thuat-may-tinh", "ky-thuat-may-tinh"),
    ("ky-thuat-may-tinh", "khoa-hoc-may-tinh"),
    ("khoa-hoc-du-lieu", "khoa-hoc-may-tinh"),
    ("ttnt-va-khoa-hoc-du-lieu", "tri-tue-nhan-tao"),
]
MODELS = [
    {"key": "A", "hf": "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
     "prefix": "", "segment": False, "note": "multilingual MiniLM, 118M, no segmentation"},
    {"key": "B", "hf": "intfloat/multilingual-e5-base",
     "prefix": "query: ", "segment": False, "note": "multilingual E5 base, 278M, 'query:' prefix"},
    {"key": "C", "hf": "bkai-foundation-models/vietnamese-bi-encoder",
     "prefix": "", "segment": True, "note": "Vietnamese PhoBERT bi-encoder, needs pyvi segmentation"},
]
SWEEP = [round(x, 3) for x in np.arange(0.50, 0.951, 0.025)]


def load_data():
    rows = list(csv.DictReader((REPO / "data/processed/cutoffs_cs_thpt.csv").open(encoding="utf-8-sig")))
    names = sorted({r["raw_major_name"] for r in rows if not is_bundle(r["raw_major_name"])})
    norm = {n: normalize(n) for n in names}
    truth = {n: ground_truth(norm[n]) for n in names}
    return names, norm, truth


def union_find(names, edge):
    parent = {x: x for x in names}
    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]; x = parent[x]
        return x
    for a, b in combinations(names, 2):
        if edge(a, b):
            parent[find(a)] = find(b)
    return {x: find(x) for x in names}


def cluster_recall(names, truth, pred, canon):
    members = [n for n in names if truth[n] == canon]
    pairs = list(combinations(members, 2))
    if not pairs:
        return None, 0
    merged = sum(pred[a] == pred[b] for a, b in pairs)
    return merged / len(pairs), len(pairs)


def hardneg_fp(names, truth, pred):
    total, detail = 0, []
    for c1, c2 in HARD_NEGATIVES:
        g1 = [n for n in names if truth[n] == c1]
        g2 = [n for n in names if truth[n] == c2]
        fp = sum(pred[a] == pred[b] for a in g1 for b in g2)
        total += fp
        detail.append((c1, c2, fp))
    return total, detail


def evaluate(names, truth, pred):
    P, R, F, tp, fp, fn = prf(names, truth, pred)
    syn_r, syn_n = cluster_recall(names, truth, pred, SYNONYM_CANON)
    hn, hn_detail = hardneg_fp(names, truth, pred)
    return {"P": P, "R": R, "F1": F, "fp": fp, "fn": fn,
            "syn_recall": syn_r, "syn_pairs": syn_n, "hardneg_fp": hn, "hn_detail": hn_detail}


def embed(model, texts):
    from sentence_transformers import SentenceTransformer
    m = SentenceTransformer(model["hf"])
    ins = texts
    if model["segment"]:
        from pyvi import ViTokenizer
        ins = [ViTokenizer.tokenize(t) for t in texts]
    ins = [model["prefix"] + t for t in ins]
    v = m.encode(ins, normalize_embeddings=True, show_progress_bar=False)
    return np.asarray(v)


def cv_select_threshold(names, truth, cos, folds=5, seed=0):
    """5-fold over STRINGS (stratified by canonical). Tune emb_thr on train, eval on test (pairwise).
    Precision-favouring: among thresholds with 0 hard-negative FP on train, pick max F1. Returns the
    selected thr on the full set and the aggregated held-out P/R/F1 (generalisation estimate)."""
    idx = {n: i for i, n in enumerate(names)}
    by_c = defaultdict(list)
    for n in names:
        by_c[truth[n]].append(n)
    rng = np.random.default_rng(seed)
    fold_of = {}
    for c, mem in by_c.items():
        mem = list(mem); rng.shuffle(mem)
        for j, n in enumerate(mem):
            fold_of[n] = j % folds

    def pair_prf(pairs, thr):
        tp = fp = fn = 0
        for a, b in pairs:
            same_t = truth[a] == truth[b]
            same_p = cos[idx[a], idx[b]] >= thr
            tp += same_p and same_t; fp += same_p and not same_t; fn += (not same_p) and same_t
        P = tp / (tp + fp) if tp + fp else 1.0
        R = tp / (tp + fn) if tp + fn else 1.0
        return P, R, (2 * P * R / (P + R) if P + R else 0.0)

    def hard_fp(pairs, thr):
        hn = {(min(a, b), max(a, b)) for a, b in
              [(x, y) for c1, c2 in HARD_NEGATIVES
               for x in by_c.get(c1, []) for y in by_c.get(c2, [])]}
        return sum(1 for a, b in pairs if (min(a, b), max(a, b)) in hn and cos[idx[a], idx[b]] >= thr)

    test_scores, sel_thrs = [], []
    for f in range(folds):
        train = [n for n in names if fold_of[n] != f]
        test = [n for n in names if fold_of[n] == f]
        tr_pairs = list(combinations(train, 2))
        te_pairs = list(combinations(test, 2))
        if not te_pairs:
            continue
        best = None
        for thr in SWEEP:
            if hard_fp(tr_pairs, thr) > 0:
                continue
            _, _, f1 = pair_prf(tr_pairs, thr)
            if best is None or f1 > best[1]:
                best = (thr, f1)
        thr = best[0] if best else max(SWEEP)
        sel_thrs.append(thr)
        test_scores.append(pair_prf(te_pairs, thr))
    mean = lambda i: statistics.mean(s[i] for s in test_scores) if test_scores else float("nan")
    # threshold for deployment: precision-favouring on the FULL set (reported, transparent)
    full_pairs = list(combinations(names, 2))
    full_best = None
    for thr in SWEEP:
        if hard_fp(full_pairs, thr) > 0:
            continue
        _, _, f1 = pair_prf(full_pairs, thr)
        if full_best is None or f1 > full_best[1]:
            full_best = (thr, f1)
    return {"cv_thr_median": statistics.median(sel_thrs) if sel_thrs else None,
            "cv_test_P": mean(0), "cv_test_R": mean(1), "cv_test_F1": mean(2),
            "full_thr": full_best[0] if full_best else None}


def main() -> int:
    names, norm, truth = load_data()
    n_pairs = len(list(combinations(names, 2)))
    print(f"Strings: {len(names)}  pairs: {n_pairs}  canonicals: {len(set(truth.values()))}")
    print(f"Fuzzy production threshold: {FUZZY_THR}; embedding sweep {SWEEP[0]}..{SWEEP[-1]}\n")

    ratio_cache = {(a, b): ratio(norm[a], norm[b]) for a, b in combinations(names, 2)}
    def fuzzy_edge(a, b):
        return ratio_cache[(a, b) if (a, b) in ratio_cache else (b, a)] >= FUZZY_THR

    # ---- S1 fuzzy baseline (model-independent) ----
    s1 = evaluate(names, truth, union_find(names, fuzzy_edge))
    print("=" * 78)
    print(f"S1 FUZZY BASELINE (thr {FUZZY_THR}):  P={s1['P']:.3f} R={s1['R']:.3f} F1={s1['F1']:.3f}"
          f"  | synonym-cluster recall={s1['syn_recall']:.2f} (n={s1['syn_pairs']} pairs)"
          f"  | hard-neg FP={s1['hardneg_fp']}")
    print("=" * 78)

    idx = {n: i for i, n in enumerate(names)}
    for model in MODELS:
        print(f"\n########## MODEL {model['key']}: {model['hf']}")
        print(f"########## ({model['note']})")
        try:
            V = embed(model, [norm[n] for n in names])
        except Exception as e:  # noqa: BLE001
            print(f"  !! could not run model {model['key']}: {e}")
            continue
        cos = V @ V.T

        def emb_edge(a, b, thr):
            return cos[idx[a], idx[b]] >= thr

        print(f"  {'thr':>5} | {'S2 P':>6} {'S2 R':>6} {'S2 F1':>6} {'syn':>5} {'hnFP':>4} "
              f"|| {'S3 P':>6} {'S3 R':>6} {'S3 F1':>6} {'syn':>5} {'hnFP':>4}")
        for thr in SWEEP:
            s2 = evaluate(names, truth, union_find(names, lambda a, b, t=thr: emb_edge(a, b, t)))
            s3 = evaluate(names, truth,
                          union_find(names, lambda a, b, t=thr: fuzzy_edge(a, b) or emb_edge(a, b, t)))
            print(f"  {thr:>5.3f} | {s2['P']:>6.3f} {s2['R']:>6.3f} {s2['F1']:>6.3f} "
                  f"{(s2['syn_recall'] or 0):>5.2f} {s2['hardneg_fp']:>4} || "
                  f"{s3['P']:>6.3f} {s3['R']:>6.3f} {s3['F1']:>6.3f} "
                  f"{(s3['syn_recall'] or 0):>5.2f} {s3['hardneg_fp']:>4}")

        cv = cv_select_threshold(names, truth, cos)
        print(f"  CV (5-fold, tune-on-train): selected thr median={cv['cv_thr_median']}, "
              f"held-out P={cv['cv_test_P']:.3f} R={cv['cv_test_R']:.3f} F1={cv['cv_test_F1']:.3f} "
              f"[small-n]; full-set precision-favouring thr={cv['full_thr']}")
        # decision snapshot: S3 at the CV/full-set thr vs S1
        dthr = cv["full_thr"] or FUZZY_THR
        s3d = evaluate(names, truth,
                       union_find(names, lambda a, b, t=dthr: fuzzy_edge(a, b) or emb_edge(a, b, t)))
        verdict = ("BEATS" if (s3d["F1"] >= s1["F1"] and (s3d["syn_recall"] or 0) > (s1["syn_recall"] or 0)
                               and s3d["hardneg_fp"] == 0) else "does NOT beat")
        print(f"  DECISION S3(thr={dthr}) vs S1: F1 {s3d['F1']:.3f} vs {s1['F1']:.3f} | "
              f"syn {(s3d['syn_recall'] or 0):.2f} vs {s1['syn_recall']:.2f} | "
              f"hard-neg FP {s3d['hardneg_fp']} -> hybrid {verdict} fuzzy on the two-sided test.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
