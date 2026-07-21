"""
Layer 1 content sanity-check (read-only QA over the raw slice).

Goes beyond file integrity (HTTP/sha256) to check that the *content* is plausible THPT data,
which is the first slice of the cross-validation the project requires. Reports:
  (1) marks outside the plausible THPT range (bucketed; >40 is impossible, 30-40 may be a
      legitimate 40-point scale e.g. language x2, so we show context and do not auto-condemn);
  (2) school-years returning 0 or anomalously few records;
  (3) records missing a mark;
  (4) the distribution of admission method actually present in the pull (confirms THPT isolation).

Read-only: reads data/raw/thpt/*.json and data/raw/manifest.csv, writes nothing.
"""
from __future__ import annotations

import csv
import json
import sys
from collections import Counter
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")  # Windows console prints Vietnamese safely

REPO_ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = REPO_ROOT / "data" / "raw" / "thpt"
MANIFEST = REPO_ROOT / "data" / "raw" / "manifest.csv"

PLAUSIBLE_LO, PLAUSIBLE_HI = 15.0, 30.0   # typical 30-point THPT total
SCALE40_HI = 40.0                          # some combos weight a subject x2 -> up to 40


def load_all() -> list[dict]:
    """Flatten every raw record, tagging school/year from the manifest + filename."""
    abbr = {}
    with MANIFEST.open(encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            abbr[(r["school_id"], r["year"])] = r["abbr"]
    records = []
    for path in sorted(RAW_DIR.glob("*.json")):
        sid, year = path.stem.split("_")
        obj = json.loads(path.read_text(encoding="utf-8"))
        for rec in obj.get("data", []):
            rec["_abbr"] = abbr.get((sid, year), sid)
            rec["_year"] = int(year)
            records.append(rec)
    return records


def main() -> int:
    recs = load_all()
    n = len(recs)
    print(f"=== Layer 1 content sanity-check :: {n} raw records ===\n")

    # (4) method isolation ----------------------------------------------------
    print("(4) Admission method present in the raw pull (expect THPT only):")
    for label, key in (("admission_name", "admission_name"),
                       ("admission_alias", "admission_alias"),
                       ("mark_type", "mark_type"), ("type", "type")):
        c = Counter(r.get(key) for r in recs)
        print(f"    {label:16}: {dict(c)}")
    print()

    # (3) missing marks -------------------------------------------------------
    missing = [r for r in recs if r.get("mark") in (None, "", 0)]
    print(f"(3) Records missing/zero mark: {len(missing)}")
    for r in missing[:20]:
        print(f"    {r['_abbr']:6} {r['_year']}  mark={r.get('mark')!r}  {r.get('name')} [{r.get('code')}]")
    print()

    # (1) mark ranges ---------------------------------------------------------
    marks = [(r, float(r["mark"])) for r in recs if isinstance(r.get("mark"), (int, float))]
    buckets = Counter()
    for _, m in marks:
        if m < PLAUSIBLE_LO: buckets["<15"] += 1
        elif m <= PLAUSIBLE_HI: buckets["15-30"] += 1
        elif m <= SCALE40_HI: buckets["30-40 (maybe 40-scale)"] += 1
        else: buckets[">40 (IMPOSSIBLE for THPT)"] += 1
    vals = [m for _, m in marks]
    print(f"(1) Mark distribution (min={min(vals)}, max={max(vals)}, mean={sum(vals)/len(vals):.2f}):")
    for k in ("<15", "15-30", "30-40 (maybe 40-scale)", ">40 (IMPOSSIBLE for THPT)"):
        if buckets[k]:
            print(f"    {k:28}: {buckets[k]}")
    print()

    def dump(title, rows):
        print(f"    -- {title}: {len(rows)} --")
        for r, m in sorted(rows, key=lambda t: t[1]):
            print(f"       {r['_abbr']:6} {r['_year']}  mark={m:<7} {r.get('name')} [{r.get('code')}]  block={r.get('block')}")

    over40 = [(r, m) for r, m in marks if m > SCALE40_HI]
    band = [(r, m) for r, m in marks if PLAUSIBLE_HI < m <= SCALE40_HI]
    under15 = [(r, m) for r, m in marks if m < PLAUSIBLE_LO]
    if over40: dump("IMPOSSIBLE >40 (investigate — likely wrong method leaked in)", over40)
    if band:   dump("30-40 (verify: legit 40-scale vs leak)", band)
    if under15: dump("<15 (verify: real low cutoff vs placeholder)", under15)
    print()

    # (2) records per school-year --------------------------------------------
    per = Counter((r["_abbr"], r["_year"]) for r in recs)
    few = sorted([(k, v) for k, v in per.items() if v < 5])
    print(f"(2) School-years with <5 records (anomalously few / 0): {len(few)}")
    for (ab, yr), v in few:
        print(f"    {ab:6} {yr}: {v}")
    counts = sorted(per.values())
    print(f"    per-school-year record count: min={counts[0]}, max={counts[-1]} across {len(per)} cells")
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
