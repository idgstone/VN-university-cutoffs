"""
Layer 2a (silver core): bronze raw JSON -> a clean, tidy per-record cutoff table for the CS group.

Reads the immutable bronze layer and the auditable config overrides, and emits one tidy row per
(school, source major code, year, block-group) observation, restricted to in-group CS majors.
Everything that departs from "as-published by tuyensinh247" is (a) driven by a sourced override
CSV, not hard-coded, and (b) made visible by a flag + a provenance note, so any cell that differs
from bronze is defensible on its own.

Design decisions encoded here (see docs/data_dictionary.md for the dataset-level statement):
  * mark            = as-published value, with sourced corrections applied (bronze stays immutable).
  * mark_scale      = 30 or 40. Default 30; set to 40 only via config/score_scale_overrides.csv
                      (sourced), NOT a fragile "mark>30" threshold (priority points can push a
                      30-scale total past 30).
  * mark_normalized_30 = the column for CROSS-SCHOOL & TREND analysis. = mark on a 30-scale row;
                      = round(mark*0.75, 2) on a 40-scale row. x0.75 is the official VNU thang-40
                      -> thang-30 convention; it is EXACT only when the three subject scores are
                      equal (2T+M2+M3 = (4/3)(T+M2+M3) iff T=M2=M3), a controlled approximation
                      otherwise, validated against each major's other-year values. Use raw `mark`
                      for LOOKUP; never plot raw `mark` across the 40-scale years or you reintroduce
                      a fake spike.
  * mark_corrected  = True where mark differs from bronze (a correction was applied).
  * at_floor        = True where mark <= FLOOR (heuristic for 2019-style "admitted everyone above
                      the national floor", so competitive cutoffs are not averaged with floor ones).

Canonical identity (canonical_major_id) and the coverage grid / wide pivot are Task 2 and Layer 2b;
this table is keyed on SOURCE identity and is complete without them.
"""
from __future__ import annotations

import csv
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

REPO = Path(__file__).resolve().parent.parent
RAW_DIR = REPO / "data" / "raw" / "thpt"
CFG = REPO / "config"
OUT = REPO / "data" / "processed" / "cutoffs_cs_thpt.csv"

FLOOR = 15.0          # <= this THPT total => floor admission, not a competitive cutoff
NORM_FACTOR = 0.75    # thang-40 (Toan x2) -> thang-30, official VNU convention


def load_lookup(path, key, val):
    with (CFG / path).open(encoding="utf-8-sig") as fh:
        return {tuple(r[k] for k in key) if len(key) > 1 else r[key[0]]:
                (r[val] if isinstance(val, str) else {k: r[k] for k in val})
                for r in csv.DictReader(fh)}


def program_variant(name: str) -> str:
    """First-pass rule-based variant tag (refinable). Precedence: joint > english > clc > advanced.

    Names are whitespace- and dash-normalized before matching so spacing / newline / en-dash
    variants (e.g. 'chất lượng\\ncao', 'Việt – Nhật') cannot defeat tag detection — this closes the
    whole name-drift mislabel class, not just individual instances.
    """
    n = name.lower()
    n = re.sub(r"[–—‐]", "-", n)        # unify en/em/other dashes to hyphen
    n = re.sub(r"\s+", " ", n)           # collapse newlines / multiple spaces
    n = re.sub(r"\s*-\s*", "-", n)       # drop spaces around hyphens
    joint = ("liên kết", "hợp tác", "việt-nhật", "việt-pháp", "việt-anh",
             "troy", "la trobe", "victoria", "grenoble", "pfiev",
             "quốc tế", "định hướng thị trường nhật", "global ict")
    if any(t in n for t in joint):
        return "joint"
    if "tiếng anh" in n or "(ta" in n or " ta)" in n or n.endswith("ta"):
        return "english"
    if "chất lượng cao" in n or "clc" in n:
        return "clc"
    if "tiên tiến" in n or "cttt" in n or "định hướng ứng dụng" in n or "cử nhân định hướng" in n:
        return "advanced"
    return "base"


def main() -> int:
    schools = {r["school_id"]: r for r in csv.DictReader((CFG / "schools.csv").open(encoding="utf-8-sig"))}
    ingroup = {(r["school_id"], r["source_code"]) for r in
               csv.DictReader((CFG / "cs_group_mapping.csv").open(encoding="utf-8-sig"))
               if r["in_cs_group"] == "TRUE"}
    scale_ov, corr, var_ov = {}, {}, {}
    for r in csv.DictReader((CFG / "score_scale_overrides.csv").open(encoding="utf-8-sig")):
        scale_ov[(r["school_id"], r["source_code"], r["year"])] = (int(r["mark_scale"]), r["source_note"])
    for r in csv.DictReader((CFG / "mark_corrections.csv").open(encoding="utf-8-sig")):
        corr[(r["school_id"], r["source_code"], r["year"])] = (float(r["correct_mark"]), r["source_note"])
    vpath = CFG / "program_variant_overrides.csv"
    if vpath.exists():
        for r in csv.DictReader(vpath.open(encoding="utf-8-sig")):
            var_ov[(r["school_id"], r["source_code"], r["year"])] = r["program_variant"]

    seen, rows = set(), []
    dup_count = 0
    conflict = defaultdict(set)
    used_scale, used_corr = set(), set()

    for path in sorted(RAW_DIR.glob("*.json")):
        sid, year = path.stem.split("_")
        sch = schools.get(sid, {})
        for rec in json.load(path.open(encoding="utf-8-sig")).get("data", []):
            code = (rec.get("code") or "").strip()
            if (sid, code) not in ingroup:
                continue
            name = rec.get("name", "")
            block = (rec.get("block") or "").strip()
            raw_mark = rec.get("mark")
            if not isinstance(raw_mark, (int, float)):
                continue
            dedup_key = (sid, code, year, block, raw_mark, name)
            if dedup_key in seen:
                dup_count += 1
                continue
            seen.add(dedup_key)

            notes = []
            mark = float(raw_mark)
            ck = (sid, code, year)
            corrected = False
            if ck in corr:
                new_mark, note = corr[ck]
                if abs(new_mark - mark) > 1e-9:
                    corrected = True
                    notes.append(f"CORRECTED from bronze {mark} -> {new_mark}: {note}")
                    mark = new_mark
                used_corr.add(ck)

            scale, snote = 30, None
            if ck in scale_ov:
                scale, snote = scale_ov[ck]
                used_scale.add(ck)
            norm = round(mark * NORM_FACTOR, 2) if scale == 40 else mark
            if scale == 40:
                notes.append(f"NORMALIZED thang40->30 via x{NORM_FACTOR} (assumes near-equal subjects): {snote}")

            conflict[(sid, code, year, block)].add(mark)
            rows.append({
                "school_id": sid, "abbr": sch.get("abbr", ""),
                "school_canonical": sch.get("name_canonical", ""),
                "source_major_code": code, "raw_major_name": name,
                "program_variant": var_ov.get(ck, program_variant(name)),
                "year": int(year), "method": "THPT", "block_group": block,
                "mark": mark, "mark_scale": scale, "mark_normalized_30": norm,
                "mark_corrected": corrected, "at_floor": mark <= FLOOR,
                "mark_source_note": " | ".join(notes),
                "source_row_id": rec.get("id"),
                "source_file": f"data/raw/thpt/{sid}_{year}.json",
            })

    rows.sort(key=lambda r: (r["abbr"], r["raw_major_name"], r["year"], r["block_group"]))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    fields = ["school_id", "abbr", "school_canonical", "source_major_code", "raw_major_name",
              "program_variant", "year", "method", "block_group", "mark", "mark_scale",
              "mark_normalized_30", "mark_corrected", "at_floor", "mark_source_note",
              "source_row_id", "source_file"]
    with OUT.open("w", encoding="utf-8-sig", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)

    # ---- report ----
    print(f"Silver written: {OUT}")
    print(f"Rows: {len(rows)} | exact duplicates removed: {dup_count}")
    print(f"Variant mix: {dict(Counter(r['program_variant'] for r in rows))}")
    print(f"40-scale rows normalized: {sum(r['mark_scale']==40 for r in rows)} | "
          f"corrected rows: {sum(r['mark_corrected'] for r in rows)} | "
          f"at_floor rows: {sum(r['at_floor'] for r in rows)}")

    unused = (set(scale_ov) - used_scale) | (set(corr) - used_corr)
    if unused:
        print(f"WARNING: override(s) never matched a record: {sorted(unused)}")
    real_conflicts = {k: v for k, v in conflict.items() if len(v) > 1}
    if real_conflicts:
        print(f"WARNING: same (school,code,year,block) with differing marks: {real_conflicts}")

    print("\n40-scale + corrected rows (verify normalization & correction):")
    for r in rows:
        if r["mark_scale"] == 40 or r["mark_corrected"]:
            print(f"   {r['abbr']} {r['year']} {r['raw_major_name']} [{r['source_major_code']}] "
                  f"mark={r['mark']} scale={r['mark_scale']} norm30={r['mark_normalized_30']} "
                  f"corrected={r['mark_corrected']}")
    print("\nat_floor rows:")
    for r in rows:
        if r["at_floor"]:
            print(f"   {r['abbr']} {r['year']} {r['raw_major_name']} mark={r['mark']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
