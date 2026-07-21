"""
Draft the B2 group-membership mapping:  (school_id, source_code) -> in_cs_group.

This is the *ground-truth* table for Task 1 (group membership). It is generated as a DRAFT by
applying one uniform semantic rule to every major across all 10 schools, then HAND-CORRECTED by
the domain owner. Code is only a supporting signal here; membership is decided by the rule:

    in-group  ==  core curriculum centers on computing / software / data
                  (NOT hardware / signals / communications / media / business / another domain)

Encoded as: name matches a CORE computing/software/data term AND is not vetoed by an
out-of-group domain marker. Data Science ("khoa học dữ liệu") is the one documented included
exception. The 10 blended cases the owner ruled OUT (robot+AI, electronics+informatics,
geoinformatics, business-analytics, scientific-data-management, ...) fall out via the veto.

Output:
  config/cs_group_mapping.csv  — every distinct (school_id, source_code) with a draft verdict.
  stdout                       — the in-group list + an "excluded despite a CS term" audit list,
                                 which is what the owner should eyeball.

NOTE: this writes a DRAFT the owner edits by hand; the pipeline later reads the *edited* CSV,
never re-derives membership silently.
"""
from __future__ import annotations

import csv
import json
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

REPO_ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = REPO_ROOT / "data" / "raw" / "thpt"
MANIFEST = REPO_ROOT / "data" / "raw" / "manifest.csv"
OUT_CSV = REPO_ROOT / "config" / "cs_group_mapping.csv"
OVERRIDES_CSV = REPO_ROOT / "config" / "cs_group_overrides.csv"

# CORE = computing/software/data field markers (Data Science included as the documented exception)
CORE = re.compile(
    r"công nghệ thông tin|khoa học máy tính|kỹ thuật máy tính|công nghệ kỹ thuật máy tính|"
    r"kỹ thuật phần mềm|hệ thống thông tin|mạng máy tính|trí tuệ nhân tạo|"
    r"an toàn thông tin|an ninh mạng|an toàn không gian số|khoa học dữ liệu|cyber|\bcntt\b",
    re.IGNORECASE,
)
# VETO = out-of-group domain markers that exclude even when a CORE term is present
VETO = re.compile(
    r"đa phương tiện|điện tử|viễn thông|cơ điện tử|tự động hóa|tự động hoá|robot|"
    r"thương mại điện tử|kinh doanh|địa không gian|địa tin học|trắc địa",
    re.IGNORECASE,
)
# things to surface for a human second look even when auto-decided
MIS = re.compile(r"hệ thống thông tin quản lý|quản lý", re.IGNORECASE)
CYBER = re.compile(r"an toàn không gian số|cyber|an ninh mạng", re.IGNORECASE)


def classify(name: str) -> tuple[bool, str]:
    core = bool(CORE.search(name))
    veto = VETO.search(name)
    if core and veto:
        return False, f"excluded_by_veto:{veto.group(0)}"
    if core:
        flags = []
        if MIS.search(name):
            flags.append("check_MIS")
        if CYBER.search(name):
            flags.append("check_cyber_variant")
        return True, ";".join(flags)
    return False, ""


def load_codes() -> dict:
    abbr = {}
    with MANIFEST.open(encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            abbr[r["school_id"]] = r["abbr"]
    # (school_id, code) -> {abbr, names:{year:name}, years:set}
    codes: dict[tuple[str, str], dict] = {}
    for path in sorted(RAW_DIR.glob("*.json")):
        sid, year = path.stem.split("_")
        obj = json.loads(path.read_text(encoding="utf-8"))
        for rec in obj.get("data", []):
            code = (rec.get("code") or "").strip()
            key = (sid, code)
            e = codes.setdefault(key, {"abbr": abbr.get(sid, sid), "names": {}, "years": set()})
            e["names"][int(year)] = rec.get("name", "")
            e["years"].add(int(year))
    return codes


def load_overrides() -> dict:
    """Explicit human corrections to the rule: (school_id, code) -> (in_cs_group, reason)."""
    ov = {}
    if OVERRIDES_CSV.exists():
        with OVERRIDES_CSV.open(encoding="utf-8") as fh:
            for r in csv.DictReader(fh):
                ov[(r["school_id"], r["source_code"])] = (r["in_cs_group"].strip().upper(), r["reason"])
    return ov


def main() -> int:
    codes = load_codes()
    overrides = load_overrides()
    applied = set()
    rows = []
    for (sid, code), e in codes.items():
        name_repr = e["names"][max(e["names"])]  # latest-year name
        in_group, review = classify(name_repr)
        ov = overrides.get((sid, code))
        if ov:
            in_group = (ov[0] == "TRUE")
            review = f"OVERRIDE: {ov[1]}"
            applied.add((sid, code))
        rows.append({
            "school_id": sid, "abbr": e["abbr"], "source_code": code,
            "name_repr": name_repr, "in_cs_group": str(in_group).upper(),
            "review": review, "n_name_variants": len(set(e["names"].values())),
            "years_seen": min(e["years"]), "years_seen_max": max(e["years"]),
        })
    rows.sort(key=lambda r: (r["abbr"], r["name_repr"]))

    unapplied = set(overrides) - applied
    if unapplied:
        print(f"WARNING: {len(unapplied)} override(s) matched no (school,code) in data: {sorted(unapplied)}\n")

    fields = ["school_id", "abbr", "source_code", "name_repr", "in_cs_group",
              "review", "n_name_variants", "years_seen", "years_seen_max"]
    with OUT_CSV.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)

    incl = [r for r in rows if r["in_cs_group"] == "TRUE"]
    veto_audit = [r for r in rows if r["review"].startswith("excluded_by_veto")]
    soft = re.compile(r"máy tính|phần mềm|tin học|toán tin|tính toán|khoa học dữ liệu", re.IGNORECASE)
    missing_audit = [r for r in rows if r["in_cs_group"] == "FALSE"
                     and not r["review"] and soft.search(r["name_repr"])]

    print(f"Draft written: {OUT_CSV}")
    print(f"Total distinct (school, code): {len(rows)} | in-group: {len(incl)} | "
          f"excluded-despite-CS-term (audit): {len(veto_audit)}\n")

    print("=== IN-GROUP (draft TRUE) — eyeball for anything WRONGLY INCLUDED or MISSING ===")
    cur = None
    for r in incl:
        if r["abbr"] != cur:
            cur = r["abbr"]; print(f"\n-- {cur} --")
        tag = f"   <{r['review']}>" if r["review"] else ""
        print(f"   {r['name_repr']}  [{r['source_code']}]{tag}")

    print("\n\n=== EXCLUDED despite containing a CS term (veto applied) — confirm these are OUT ===")
    cur = None
    for r in veto_audit:
        if r["abbr"] != cur:
            cur = r["abbr"]; print(f"\n-- {cur} --")
        print(f"   {r['name_repr']}  [{r['source_code']}]  ({r['review'].split(':',1)[1]})")

    print("\n\n=== POSSIBLE MISSING (excluded, but name has a soft computing hint) — confirm OUT ===")
    cur = None
    for r in missing_audit:
        if r["abbr"] != cur:
            cur = r["abbr"]; print(f"\n-- {cur} --")
        print(f"   {r['name_repr']}  [{r['source_code']}]")
    return 0


if __name__ == "__main__":
    sys.exit(main())
