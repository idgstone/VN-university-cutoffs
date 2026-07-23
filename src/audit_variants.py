"""
Variant-stability audit (QA for program_variant, which is derived from drifting major-name strings).

program_variant is inferred from the name; names gain/drop CLC/joint/English tags across years, so a
STABLE admission unit can get an unstable label (the HANU 2019 CNTT bug). This audit flags every
(school, source_code) whose program_variant label is NOT constant across the years it appears — each
is either a genuine program change or a name-drift mislabel, for the owner to rule case by case.

It also prints the full trend-view dropped-series list (school-majors with no base offering in any
year, hence absent from cutoffs_cs_trend.csv).

LIMITATION (stated honestly): this catches label INCONSISTENCY across years. A program that is
mislabeled the SAME (wrong) way in every year (e.g. an always-English program whose name never
carries the tag) is stable and will NOT be flagged here — that residual is covered by the owner's
review of config/canonical_majors_draft.csv, not by this audit.
"""
from __future__ import annotations

import csv
import sys
from collections import defaultdict
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
REPO = Path(__file__).resolve().parent.parent
GOLD = REPO / "data" / "processed" / "cutoffs_cs.csv"


def code_signal(code: str) -> str | None:
    """High-confidence variant implied by the SOURCE CODE (corroborating signal only).
    Covers the year-stability audit's blind spot: a program mislabeled the SAME wrong way every year
    is stable, but if its code carries a variant marker the name never reflected, this catches it."""
    c = code.upper()
    if "TROY" in c or "LTU" in c or "VUW" in c or "GINP" in c:
        return "joint"                       # HUST foreign-partner programs
    if "VNH" in c:
        return "joint"                       # Việt-Nhật
    if "CLC" in c:
        return "clc"
    if "UDU" in c:
        return "advanced"                    # (cử nhân) định hướng ứng dụng
    if c.endswith("TA"):
        return "english"                     # e.g. 7480101TA
    return None


def main() -> int:
    rows = list(csv.DictReader(GOLD.open(encoding="utf-8")))

    # (school, code) -> {year: set(variants)}, plus a representative name per year
    bykey = defaultdict(lambda: defaultdict(set))
    names = defaultdict(dict)
    disp = {}
    for r in rows:
        k = (r["abbr"], r["source_major_code"])
        bykey[k][int(r["year"])].add(r["program_variant"])
        names[k][int(r["year"])] = r["raw_major_name"]
        disp[k] = r["canonical_major_name"]

    print("=== VARIANT-STABILITY AUDIT: (school, code) whose variant label changes across years ===")
    suspects = 0
    for k in sorted(bykey):
        years = bykey[k]
        allv = set().union(*years.values())
        # flag if more than one variant appears across the years for this stable code
        if len(allv) > 1:
            suspects += 1
            abbr, code = k
            print(f"\n  [{abbr} {code}] canonical={disp[k]}  variants seen: {sorted(allv)}")
            for y in sorted(years):
                print(f"     {y}: {sorted(years[y])}   \"{names[k][y]}\"")
    if not suspects:
        print("  none — every (school, code) has a constant variant label across its years.")
    print(f"\n  -> {suspects} suspect (school, code) series to rule on.")

    # ---- second pass: code-signal vs name-derived label (catches consistent mislabels) ----
    print("\n=== CODE-SIGNAL AUDIT: code implies a variant the name-derived label missed ===")
    seen, mism = set(), 0
    for r in rows:
        sig = code_signal(r["source_major_code"])
        lbl = r["program_variant"]
        if sig and sig != lbl:
            key = (r["abbr"], r["source_major_code"], sig, lbl)
            if key in seen:
                continue
            seen.add(key)
            mism += 1
            print(f"  [{r['abbr']} {r['source_major_code']}] code implies '{sig}' but label='{lbl}'"
                  f"  \"{r['raw_major_name'][:46]}\"")
    if not mism:
        print("  none — no code-signalled variant contradicts its name-derived label.")
    print(f"\n  -> {mism} code-vs-label mismatch(es) to review.")

    # full trend dropped-series list
    cells = defaultdict(lambda: defaultdict(list))
    for r in rows:
        cells[(r["abbr"], r["canonical_major_name"])][int(r["year"])].append(r["program_variant"])
    print("\n=== TREND-VIEW DROPPED SERIES (no base offering in ANY year -> absent from trend) ===")
    dropped = []
    for (abbr, name), byyear in sorted(cells.items()):
        has_base_any = any("base" in vs for vs in byyear.values())
        if not has_base_any:
            variants = sorted(set().union(*byyear.values()))
            yrs = f"{min(byyear)}-{max(byyear)}"
            dropped.append((abbr, name, variants, yrs))
    for abbr, name, variants, yrs in dropped:
        print(f"  {abbr:5} {name:38} years {yrs}  only-variants={variants}")
    print(f"\n  -> {len(dropped)} school-major series absent from the trend view "
          f"(each = 'no base offering', NOT 'no program').")
    return 0


if __name__ == "__main__":
    sys.exit(main())
