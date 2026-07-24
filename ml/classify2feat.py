"""
Follow-up (time-boxed, one experiment): can a LEARNED 2-feature classifier on
[fuzzy_score, embedding_cosine] separate what neither signal nor their union can?

Motivation (see README pre-commitment): in the (fuzzy, embedding) plane the cybersecurity synonyms
sit at low-fuzzy/high-embedding and the hard negatives at high-fuzzy/high-embedding — different
regions of a DIAGONAL boundary that the union hybrid (S3) structurally cannot represent. A logistic
regression / shallow decision tree on both features can. Same harness, same CV folds, same two-sided
criterion. Reported regardless of outcome; then we stop.
"""
from __future__ import annotations

import statistics
import sys
from collections import defaultdict
from itertools import combinations

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.tree import DecisionTreeClassifier

from embed_match import (FUZZY_THR, HARD_NEGATIVES, MODELS, SYNONYM_CANON, embed,
                         evaluate, load_data, union_find)
from canonical_match import ratio  # same fuzzy similarity as the baseline

sys.stdout.reconfigure(encoding="utf-8")


def folds_by_string(names, truth, k=5, seed=0):
    by_c = defaultdict(list)
    for n in names:
        by_c[truth[n]].append(n)
    rng = np.random.default_rng(seed)
    fold = {}
    for _, mem in by_c.items():
        mem = list(mem); rng.shuffle(mem)
        for j, n in enumerate(mem):
            fold[n] = j % k
    return fold


def pairwise_scores(y_true, y_pred):
    tp = sum(t and p for t, p in zip(y_true, y_pred))
    fp = sum((not t) and p for t, p in zip(y_true, y_pred))
    fn = sum(t and (not p) for t, p in zip(y_true, y_pred))
    P = tp / (tp + fp) if tp + fp else 1.0
    R = tp / (tp + fn) if tp + fn else 1.0
    return P, R, (2 * P * R / (P + R) if P + R else 0.0)


def main() -> int:
    names, norm, truth = load_data()
    idx = {n: i for i, n in enumerate(names)}
    pairs = list(combinations(names, 2))
    fuzzy = {p: ratio(norm[p[0]], norm[p[1]]) for p in pairs}
    fold = folds_by_string(names, truth)

    syn_members = {n for n in names if truth[n] == SYNONYM_CANON}
    hard_pairs = {frozenset((x, y)) for c1, c2 in HARD_NEGATIVES
                  for x in names if truth[x] == c1 for y in names if truth[y] == c2}

    # fuzzy baseline (identical harness) for reference
    s1 = evaluate(names, truth, union_find(names,
                  lambda a, b: fuzzy[(a, b) if (a, b) in fuzzy else (b, a)] >= FUZZY_THR))
    print(f"Reference S1 FUZZY @{FUZZY_THR}: P={s1['P']:.3f} R={s1['R']:.3f} F1={s1['F1']:.3f} "
          f"| synonym recall={s1['syn_recall']:.2f} | hard-neg FP={s1['hardneg_fp']}\n")

    def feats(cos):
        X = np.array([[fuzzy[p], cos[idx[p[0]], idx[p[1]]]] for p in pairs])
        y = np.array([truth[p[0]] == truth[p[1]] for p in pairs], dtype=int)
        return X, y

    for mkey in ("C", "A"):
        model = next(m for m in MODELS if m["key"] == mkey)
        V = embed(model, [norm[n] for n in names])
        cos = V @ V.T
        X, y = feats(cos)

        for clf_name, mk in (("logreg", lambda: LogisticRegression(max_iter=1000)),
                             ("tree(d=3)", lambda: DecisionTreeClassifier(max_depth=3, random_state=0))):
            print(f"###### Model {mkey} + {clf_name}")
            # (1) 5-fold string CV — honest generalisation on held-out WITHIN-fold pairs
            yt_all, yp_all, hp_all = [], [], []
            for f in range(5):
                tr = [i for i, p in enumerate(pairs) if fold[p[0]] != f and fold[p[1]] != f]
                te = [i for i, p in enumerate(pairs) if fold[p[0]] == f and fold[p[1]] == f]
                if not te or len(set(y[tr])) < 2:
                    continue
                clf = mk().fit(X[tr], y[tr])
                pr = clf.predict(X[te])
                for k, i in enumerate(te):
                    yt_all.append(y[i]); yp_all.append(int(pr[k])); hp_all.append(frozenset(pairs[i]))
            P, R, F = pairwise_scores(yt_all, yp_all)
            syn_te = [(t, p) for t, p, pr_pair in zip(yt_all, yp_all, hp_all)
                      if len(pr_pair & syn_members) == 2]
            syn_r = (sum(p for _, p in syn_te) / len(syn_te)) if syn_te else float("nan")
            hn_fp = sum(1 for p, pr_pair in zip(yp_all, hp_all) if p and pr_pair in hard_pairs)
            print(f"   CV held-out (within-fold pairs, small-n): P={P:.3f} R={R:.3f} F1={F:.3f} "
                  f"| synonym recall={syn_r:.2f} (n={len(syn_te)}) | hard-neg FP={hn_fp}")

            # (2) full-fit -> full-apply -> cluster (best-case representability, comparable to S1)
            clf = mk().fit(X, y)
            pred_same = clf.predict(X)
            same_edges = {frozenset(p) for p, s in zip(pairs, pred_same) if s}
            full = evaluate(names, truth,
                            union_find(names, lambda a, b: frozenset((a, b)) in same_edges))
            beats = (full["F1"] >= s1["F1"] and (full["syn_recall"] or 0) > (s1["syn_recall"] or 0)
                     and full["hardneg_fp"] == 0)
            print(f"   FULL-fit/apply (optimistic): P={full['P']:.3f} R={full['R']:.3f} "
                  f"F1={full['F1']:.3f} | synonym recall={full['syn_recall']:.2f} | "
                  f"hard-neg FP={full['hardneg_fp']}  -> two-sided vs fuzzy: "
                  f"{'BEATS' if beats else 'does NOT beat'}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
