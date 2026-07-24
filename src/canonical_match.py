"""
Task 2 — canonical-identity matching, fuzzy/rule baseline + precision/recall eval.

Two separate objects (kept honest):
  * FUZZY MATCHER (under test): shared surface normalization (strip program-variant markers,
    parentheticals, the "CNTT:" dept prefix, newlines/typos) + token-sort string similarity
    (stdlib difflib, zero deps) + union-find clustering at a threshold. NO hand-coded synonym
    merges -- so cross-string synonyms (An toàn thông tin / An ninh mạng / Cyber) MUST fail here
    if fuzzy can't reach them. That failure is the whole point of the test.
  * GROUND TRUTH (reference): canonical id per major, built from the owner's granularity rulings
    #1-#6. Written to config/canonical_majors_draft.csv for human review; #6 bundled multi-major
    rows are routed to config/excluded_bundled.csv (excluded-with-record, not deleted).

Eval: all-pairs precision/recall/F1 of the fuzzy clusters vs the ground-truth canonical, across
thresholds (tiny N -> report the curve rather than a single tuned point), plus the specific hard
positives/negatives and the residual false-negative/false-positive lists.
"""
from __future__ import annotations

import csv
import re
import sys
from collections import defaultdict
from difflib import SequenceMatcher
from itertools import combinations
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

REPO = Path(__file__).resolve().parent.parent
SILVER = REPO / "data" / "processed" / "cutoffs_cs_thpt.csv"
OUT_MAP = REPO / "config" / "canonical_majors_draft.csv"
OUT_BUNDLE = REPO / "config" / "excluded_bundled.csv"

# Production operating point for the fuzzy candidate step: PRECISION-FAVOURING (owner ruling).
# A false merge silently conflates two distinct ngành and is undetectable by a data user; a miss
# leaves two separate clusters (visible, fixable by override). So favour precision and close the
# recall gap with the auditable human-verified map, not by buying recall with wrong merges.
# (The SHIPPED canonical assignment is the human-verified ground_truth map — threshold-independent —
# so it contains none of the fuzzy false merges regardless.)
PROD_THRESHOLD = 0.80

# variant / program-type phrases removed during surface normalization (after parenthetical strip).
VARIANT_PHRASES = [
    "chất lượng cao", "clc", "chương trình tiên tiến", "cttt", "chương trình", "tiên tiến",
    "dạy bằng tiếng anh", "bằng tiếng anh", "hợp tác với", "liên kết", "global ict",
    "việt - nhật", "việt-nhật", "việt – nhật", "việt - pháp", "việt-pháp", "việt – pháp",
    "việt - anh", "việt-anh", "tăng cường tiếng nhật", "tăng cường tiếng pháp",
    "định hướng thị trường nhật bản", "định hướng ứng dụng", "cử nhân định hướng ứng dụng",
    "theo tt23", "đh la trobe", "đh victoria", "la trobe", "victoria", "grenoble",
    "troy", "hoa kỳ", "hoa ký", "new zealand", "úc", "đh",
]


def normalize(name: str) -> str:
    n = name.replace("\n", " ").replace("\r", " ").lower()
    n = re.sub(r"\([^)]*\)", " ", n)          # drop parenthetical (variant/track/specialisation) info
    n = re.sub(r"\([^)]*$", " ", n)           # drop an unmatched trailing "(...."
    n = n.replace("*", " ")
    n = re.sub(r"^\s*nhóm\s+ngành\s+", " ", n)
    n = re.sub(r"^\s*ngành\s+", " ", n)
    n = re.sub(r"\bcntt\s*:\s*", " ", n)      # HUST dept prefix "CNTT:" -> keep the real major
    for ph in VARIANT_PHRASES:
        n = n.replace(ph, " ")
    n = re.sub(r"[^0-9a-zà-ỹ\s]", " ", n)     # strip stray punctuation/hyphens
    n = re.sub(r"\s+", " ", n).strip()
    return n


def is_bundle(name: str) -> bool:
    low = name.lower()
    return low.strip().startswith("nhóm ngành") or "; ngành" in low


def ground_truth(norm: str) -> str:
    """Canonical id (ASCII slug) from owner rulings (ordered: specific/combined before generic)."""
    n = norm
    if "trí tuệ nhân tạo" in n and "khoa học dữ liệu" in n:
        return "ttnt-va-khoa-hoc-du-lieu"                                  # #2
    if "an toàn thông tin" in n or "an ninh mạng" in n or "an toàn không gian" in n or "cyber" in n:
        return "an-toan-thong-tin"                                         # #1 (cross-string synonyms)
    if "kỹ thuật phần mềm" in n:
        return "ky-thuat-phan-mem"
    if "hệ thống thông tin" in n:
        return "he-thong-thong-tin"
    if "mạng máy tính" in n or "kỹ thuật dữ liệu" in n:
        return "mang-may-tinh"                                             # #5
    if "công nghệ kỹ thuật máy tính" in n:
        return "cong-nghe-ky-thuat-may-tinh"      # applied-tech ngành 7480108 — SEPARATE from KTMT
    if "kỹ thuật máy tính" in n or "máy tính và robot" in n:
        return "ky-thuat-may-tinh"                # engineering ngành 7480106; incl. UET CN2 rename
    if "khoa học máy tính" in n or "máy tính và khoa học thông tin" in n:
        return "khoa-hoc-may-tinh"                                         # #3, #4
    if "trí tuệ nhân tạo" in n:
        return "tri-tue-nhan-tao"
    if "khoa học dữ liệu" in n:
        return "khoa-hoc-du-lieu"
    if "công nghệ thông tin" in n:
        return "cong-nghe-thong-tin"
    return "UNRESOLVED"


def tok(s: str) -> str:
    return " ".join(sorted(s.split()))


def ratio(a: str, b: str) -> float:
    return SequenceMatcher(None, tok(a), tok(b)).ratio()


def cluster(names_norm: dict, thr: float) -> dict:
    """Union-find over names by token-sort similarity >= thr. Returns name -> cluster_id."""
    names = list(names_norm)
    parent = {x: x for x in names}
    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]; x = parent[x]
        return x
    def union(a, b):
        parent[find(a)] = find(b)
    for a, b in combinations(names, 2):
        if ratio(names_norm[a], names_norm[b]) >= thr:
            union(a, b)
    return {x: find(x) for x in names}


def prf(names, truth, pred):
    tp = fp = fn = tn = 0
    for a, b in combinations(names, 2):
        same_t = truth[a] == truth[b]
        same_p = pred[a] == pred[b]
        if same_p and same_t: tp += 1
        elif same_p and not same_t: fp += 1
        elif not same_p and same_t: fn += 1
        else: tn += 1
    P = tp / (tp + fp) if tp + fp else 1.0
    R = tp / (tp + fn) if tp + fn else 1.0
    F = 2 * P * R / (P + R) if P + R else 0.0
    return P, R, F, tp, fp, fn


def main() -> int:
    rows = list(csv.DictReader(SILVER.open(encoding="utf-8-sig")))
    by_name = defaultdict(lambda: {"n": 0, "schools": set()})
    for r in rows:
        e = by_name[r["raw_major_name"]]
        e["n"] += 1; e["schools"].add(r["abbr"])

    bundles = {nm: v for nm, v in by_name.items() if is_bundle(nm)}
    majors = {nm: v for nm, v in by_name.items() if not is_bundle(nm)}
    norm = {nm: normalize(nm) for nm in majors}
    truth = {nm: ground_truth(norm[nm]) for nm in majors}
    names = list(majors)

    unresolved = [nm for nm in names if truth[nm] == "UNRESOLVED"]

    # ---- threshold sweep ----
    print(f"Distinct majors: {len(names)} (+{len(bundles)} bundled rows excluded-with-record)")
    print(f"Ground-truth canonical count: {len(set(truth.values()))}"
          f"{' | UNRESOLVED: ' + str(len(unresolved)) if unresolved else ''}\n")
    print("Fuzzy-only pair P/R/F1 vs ground truth, by threshold:")
    preds = {}
    for thr in (0.70, 0.75, 0.80, 0.85, 0.90):
        pred = preds[thr] = cluster(norm, thr)
        P, R, F, tp, fp, fn = prf(names, truth, pred)
        star = "  <- PRODUCTION (precision-favouring)" if abs(thr - PROD_THRESHOLD) < 1e-9 else \
               ("  (best F1)" if thr == 0.70 else "")
        print(f"   thr={thr:.2f}  P={P:.3f} R={R:.3f} F1={F:.3f}  (TP={tp} FP={fp} FN={fn}){star}")
    print(f"\nPRODUCTION operating point = thr {PROD_THRESHOLD:.2f} (precision-favouring, owner ruling):")
    print("   thr 0.70 gives best F1 (P 0.996) but merges Công nghệ kỹ thuật máy tính into Kỹ thuật")
    print("   máy tính (false); thr >=0.80 gives P 1.000 (they separate). A wrong merge is invisible to")
    print("   a data user; a miss is a visible, override-fixable split -> favour precision.")
    print("   The SHIPPED map is the human-verified ground_truth assignment (threshold-independent);")
    print("   it keeps those two ngành separate regardless of the fuzzy operating point.")
    pred = preds[PROD_THRESHOLD]
    print(f"\nResidual analysis at the production threshold {PROD_THRESHOLD:.2f}:")

    # residual FN (truth-same, fuzzy split) and FP (fuzzy-merged, truth-diff)
    fn_pairs, fp_pairs = [], []
    for a, b in combinations(names, 2):
        st, sp = truth[a] == truth[b], pred[a] == pred[b]
        if st and not sp: fn_pairs.append((a, b))
        if sp and not st: fp_pairs.append((a, b))
    print(f"\n  FALSE NEGATIVES (same major, fuzzy failed to merge) -- {len(fn_pairs)}:")
    for a, b in fn_pairs[:40]:
        print(f"     [{truth[a]}]  {a!r}  <->  {b!r}")
    print(f"\n  FALSE POSITIVES (fuzzy wrongly merged) -- {len(fp_pairs)}:")
    for a, b in fp_pairs[:40]:
        print(f"     {a!r} [{truth[a]}]  <->  {b!r} [{truth[b]}]")

    # write ground-truth draft for review
    OUT_MAP.parent.mkdir(parents=True, exist_ok=True)
    with OUT_MAP.open("w", encoding="utf-8-sig", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["raw_major_name", "normalized", "canonical_draft", "fuzzy_cluster",
                    "n_rows", "schools", "review"])
        for nm in sorted(names, key=lambda x: (truth[x], normalize(x))):
            rev = "UNRESOLVED" if truth[nm] == "UNRESOLVED" else ""
            w.writerow([nm, norm[nm], truth[nm], pred[nm], majors[nm]["n"],
                        ";".join(sorted(majors[nm]["schools"])), rev])
    with OUT_BUNDLE.open("w", encoding="utf-8-sig", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["raw_major_name", "n_rows", "schools", "exclusion_reason"])
        for nm, v in sorted(bundles.items()):
            w.writerow([nm, v["n"], ";".join(sorted(v["schools"])),
                        "Bundled multi-major cutoff (nhom nganh / multiple nganh); not attributable "
                        "to a single major -> excluded from per-major table by design, logged."])
    print(f"\nWrote {OUT_MAP} and {OUT_BUNDLE}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
