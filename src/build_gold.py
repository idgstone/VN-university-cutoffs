"""
Layer 2b (gold): attach canonical_major_id to silver, then build the coverage grid and the wide pivot.

Inputs:  data/processed/cutoffs_cs_thpt.csv (silver, per-record)
         config/canonical_majors_draft.csv (raw_major_name -> canonical id; human-reviewable map)
         config/excluded_bundled.csv (names to keep OUT of the per-major table, logged)
Outputs: data/processed/cutoffs_cs.csv        gold per-record table (silver + canonical id/name)
         data/processed/coverage.csv          per (school, canonical, year) grid + present flags
         data/processed/cutoffs_cs_wide.csv    G2 wide pivot: canonical x school by year (comparison)

Coverage is measured at major x year grain, WITHIN each (school, canonical) active span (first..last
observed year) so that "not yet offered" years are not miscounted as THPT gaps. Two metrics, kept
separate (per design): DATASET coverage = cell has any THPT variant; COMPARISON-READINESS = cell has
a base offering. The wide pivot uses mark_normalized_30 with the base->english->clc->joint->advanced
representative fallback, and flags any non-base representative.
"""
from __future__ import annotations

import csv
import sys
from collections import defaultdict
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

REPO = Path(__file__).resolve().parent.parent
SILVER = REPO / "data" / "processed" / "cutoffs_cs_thpt.csv"
CANON = REPO / "config" / "canonical_majors_draft.csv"
GOLD = REPO / "data" / "processed" / "cutoffs_cs.csv"
COVERAGE = REPO / "data" / "processed" / "coverage.csv"
WIDE = REPO / "data" / "processed" / "cutoffs_cs_compare.csv"   # single-year cross-school (fallback rep.)
TREND = REPO / "data" / "processed" / "cutoffs_cs_trend.csv"    # time-series (base-only, explicit gaps)
YEARS = list(range(2019, 2026))
VARIANT_RANK = {"base": 0, "english": 1, "clc": 2, "joint": 3, "advanced": 4}

DISPLAY = {
    "Cong nghe thong tin": "Công nghệ thông tin",
    "Khoa hoc may tinh": "Khoa học máy tính",
    "Ky thuat may tinh": "Kỹ thuật máy tính",
    "Ky thuat phan mem": "Kỹ thuật phần mềm",
    "He thong thong tin": "Hệ thống thông tin",
    "Mang may tinh": "Mạng máy tính và truyền thông dữ liệu",
    "Tri tue nhan tao": "Trí tuệ nhân tạo",
    "Khoa hoc du lieu": "Khoa học dữ liệu",
    "TTNT & Khoa hoc du lieu": "Trí tuệ nhân tạo và Khoa học dữ liệu",
    "An toan thong tin / An ninh mang": "An toàn thông tin / An ninh mạng",
}


def main() -> int:
    canon = {r["raw_major_name"]: r["canonical_draft"]
             for r in csv.DictReader(CANON.open(encoding="utf-8"))}
    silver = list(csv.DictReader(SILVER.open(encoding="utf-8")))

    gold, excluded = [], 0
    for r in silver:
        cid = canon.get(r["raw_major_name"])
        if cid is None or cid == "UNRESOLVED":   # bundled/unmapped -> not in per-major table
            excluded += 1
            continue
        r["canonical_major_id"] = cid
        r["canonical_major_name"] = DISPLAY.get(cid, cid)
        gold.append(r)

    fields = list(silver[0].keys()) + ["canonical_major_id", "canonical_major_name"]
    with GOLD.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader(); w.writerows(gold)

    # ---- coverage grid (within active span) ----
    # (school, canonical) -> {year -> list of rows}
    cells = defaultdict(lambda: defaultdict(list))
    for r in gold:
        cells[(r["abbr"], r["canonical_major_id"])][int(r["year"])].append(r)

    cov_rows = []
    tot = present = base_present = gaps = 0
    gap_list = []
    for (abbr, cid), byyear in sorted(cells.items()):
        yrs = sorted(byyear)
        span = range(min(yrs), max(yrs) + 1)
        for y in span:
            rs = byyear.get(y, [])
            has_any = len(rs) > 0
            has_base = any(x["program_variant"] == "base" for x in rs)
            tot += 1; present += has_any; base_present += has_base
            if not has_any:
                gaps += 1; gap_list.append((abbr, DISPLAY.get(cid, cid), y))
            cov_rows.append({"abbr": abbr, "canonical_major_id": cid, "year": y,
                             "has_thpt": has_any, "has_base": has_base})
    with COVERAGE.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["abbr", "canonical_major_id", "year", "has_thpt", "has_base"])
        w.writeheader(); w.writerows(cov_rows)

    # ---- wide pivot: representative normalized mark per (school, canonical, year) ----
    def represent(rows):
        best = min(rows, key=lambda x: (VARIANT_RANK.get(x["program_variant"], 9),
                                        -float(x["mark_normalized_30"])))
        return best
    pivot = {}
    nonbase_flags = 0
    for (abbr, cid), byyear in cells.items():
        for y, rs in byyear.items():
            rep = represent(rs)
            pivot[(abbr, cid, y)] = (float(rep["mark_normalized_30"]), rep["program_variant"])
            if rep["program_variant"] != "base":
                nonbase_flags += 1
    keys = sorted({(abbr, cid) for (abbr, cid, _) in pivot})
    with WIDE.open("w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["canonical_major_name", "abbr"] + [str(y) for y in YEARS])
        for abbr, cid in sorted(keys, key=lambda k: (DISPLAY.get(k[1], k[1]), k[0])):
            row = [DISPLAY.get(cid, cid), abbr]
            for y in YEARS:
                v = pivot.get((abbr, cid, y))
                row.append("" if v is None else (f"{v[0]}*" if v[1] != "base" else f"{v[0]}"))
            w.writerow(row)

    # ---- TREND view: base-only, explicit gaps (never fills with a variant) ----
    # A blank here means "no BASE offering that year", NOT "no program" (a variant may exist).
    base_pivot = defaultdict(dict)
    for (abbr, cid), byyear in cells.items():
        for y, rs in byyear.items():
            base = [float(x["mark_normalized_30"]) for x in rs if x["program_variant"] == "base"]
            if base:
                base_pivot[(abbr, cid)][y] = max(base)
    dropped = [k for k in keys if k not in base_pivot]   # series with no base in ANY year
    with TREND.open("w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["canonical_major_name", "abbr"] + [str(y) for y in YEARS])
        for abbr, cid in sorted(base_pivot, key=lambda k: (DISPLAY.get(k[1], k[1]), k[0])):
            row = [DISPLAY.get(cid, cid), abbr]
            for y in YEARS:
                v = base_pivot[(abbr, cid)].get(y)
                row.append("" if v is None else f"{v}")
            w.writerow(row)

    # ---- report ----
    print(f"GOLD: {len(gold)} rows ({excluded} bundled/unresolved excluded) -> {GOLD}")
    print(f"Canonical majors: {len(set(r['canonical_major_id'] for r in gold))}")
    print(f"\nCOVERAGE (major x year, within active span):")
    print(f"   cells={tot}  present(any THPT)={present} ({present/tot:.0%})  "
          f"base-comparable={base_present} ({base_present/tot:.0%})  gaps={gaps}")
    print(f"   wide-pivot non-base representatives (annotate on charts): {nonbase_flags}")
    if gap_list:
        print("\n   THPT gap cells (major existed that span but no THPT that year):")
        for abbr, name, y in gap_list:
            print(f"      {abbr} {name} {y}")
    print(f"\nTREND view (base-only): {len(base_pivot)} series; "
          f"{len(dropped)} (school,major) series have NO base offering in any year "
          f"-> absent from the trend view (= 'no base', not 'no program'):")
    for abbr, cid in sorted(dropped, key=lambda k: (DISPLAY.get(k[1], k[1]), k[0])):
        print(f"      {abbr} {DISPLAY.get(cid, cid)}")
    print(f"\nWrote {COVERAGE.name}, {WIDE.name} (cross-school compare), {TREND.name} (trend, base-only)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
