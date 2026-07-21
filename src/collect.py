"""
Layer 1 collector — Vietnamese university admission-cutoff dataset (Computing/IT, Hanoi, THPT).

WHAT
    Pulls raw admission-cutoff ("điểm chuẩn") records from the tuyensinh247 data API for a
    fixed list of universities x years, admission method = THPT ("Điểm thi THPT"), and stores
    each API response verbatim on disk plus a provenance manifest.

WHY (design decisions — for the README / interview defence)
    * Immutable raw ("bronze") layer: we save the *exact* bytes of every API response, untouched.
      All cleaning/normalisation happens in a later layer that reads these files. This makes the
      whole pipeline reproducible and lets us defend any published number by tracing it to the
      raw response that produced it — even if the upstream API later changes.
    * Undocumented API, used within the rules: the data is served by
      GET /api/common/cutoff-score?school_id=..&method_id=..&year=..  . This path is NOT disallowed
      by the site's robots.txt (only /tsBenchmarking/ajaxGetMore and /tsAjax/xephang are), and the
      terms of use contain no anti-automation clause. We still crawl politely (single-threaded,
      delay between calls, identifying User-Agent). The README states plainly that this is an
      undocumented API and that tuyensinh247 is an aggregator (hence the later cross-validation step).
    * method_id = 1  ==  "Điểm thi THPT" — the project's single canonical admission method. Other
      methods (ĐGNL/HSA, international certificates) use different score scales and are out of scope.
    * Standard library only (urllib) — no third-party dependencies, so `python src/collect.py` runs
      on a clean machine with nothing to install.
    * Idempotent & polite on re-run: an already-downloaded (school, year) file is reused, not
      re-fetched, unless --force is given. The manifest is always rebuilt from what's on disk so it
      stays consistent with the raw files.

USAGE
    python src/collect.py                      # all schools in config, years 2019-2025
    python src/collect.py --years 2022 2025    # inclusive range
    python src/collect.py --force              # ignore cache, refetch everything
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

# --- constants ---------------------------------------------------------------
API_BASE = "https://diemthi.tuyensinh247.com/api/common/cutoff-score"
METHOD_ID = 1                      # 1 = "Điểm thi THPT" (national-exam method) — the canonical series
METHOD_ALIAS = "diem-thi-thpt"
DEFAULT_YEARS = (2019, 2025)       # inclusive; confirmed to have full coverage for all 10 schools
USER_AGENT = (
    "vn-cutoff-dataset/0.1 (portfolio research project; polite single-threaded collector)"
)
REQUEST_TIMEOUT = 30               # seconds
MAX_RETRIES = 2                    # total attempts = 1 + retries on transient failure

# repo-relative paths (script lives in <repo>/src/)
REPO_ROOT = Path(__file__).resolve().parent.parent
SCHOOLS_CSV = REPO_ROOT / "config" / "schools.csv"
RAW_DIR = REPO_ROOT / "data" / "raw" / "thpt"
MANIFEST_CSV = REPO_ROOT / "data" / "raw" / "manifest.csv"


def load_schools() -> list[dict]:
    with SCHOOLS_CSV.open(encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def build_url(school_id: str | int, year: int) -> str:
    return f"{API_BASE}?school_id={school_id}&method_id={METHOD_ID}&year={year}"


def fetch(url: str) -> tuple[int, bytes]:
    """Return (http_status, raw_body_bytes). Retries transient errors with backoff."""
    last_err = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
                return resp.status, resp.read()
        except urllib.error.HTTPError as e:
            # An HTTP error is a real response — record it, don't retry 4xx.
            if 400 <= e.code < 500:
                return e.code, e.read()
            last_err = e
        except (urllib.error.URLError, TimeoutError) as e:
            last_err = e
        if attempt < MAX_RETRIES:
            time.sleep(2.0 * attempt)
    raise RuntimeError(f"fetch failed after {MAX_RETRIES} attempts: {url} :: {last_err}")


def raw_path(school_id: str, year: int) -> Path:
    return RAW_DIR / f"{school_id}_{year}.json"


def summarise(body: bytes) -> tuple[str, int]:
    """(api_success, n_rows) parsed from a response body, tolerant of non-JSON."""
    try:
        obj = json.loads(body)
    except json.JSONDecodeError:
        return "invalid_json", -1
    data = obj.get("data") if isinstance(obj, dict) else None
    n = len(data) if isinstance(data, list) else -1
    return str(obj.get("success")) if isinstance(obj, dict) else "unknown", n


def collect(years: tuple[int, int], delay: float, force: bool) -> list[dict]:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    schools = load_schools()
    y0, y1 = years
    manifest_rows: list[dict] = []

    for school in schools:
        sid, abbr = school["school_id"], school["abbr"]
        for year in range(y0, y1 + 1):
            path = raw_path(sid, year)
            url = build_url(sid, year)

            if path.exists() and not force:
                body = path.read_bytes()
                status, fetched_at, action = 200, "(cached)", "cached"
            else:
                status, body = fetch(url)
                path.write_bytes(body)
                fetched_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
                action = "fetched"
                time.sleep(delay)  # politeness delay only on real network calls

            success, n_rows = summarise(body)
            sha = hashlib.sha256(body).hexdigest()
            manifest_rows.append({
                "school_id": sid, "abbr": abbr, "year": year,
                "method_id": METHOD_ID, "method_alias": METHOD_ALIAS,
                "url": url, "http_status": status, "api_success": success,
                "n_rows": n_rows, "bytes": len(body), "sha256": sha,
                "fetched_at_utc": fetched_at,
            })
            print(f"  [{action:7}] {abbr:6} {year}  status={status} rows={n_rows}")

    return manifest_rows


def write_manifest(rows: list[dict]) -> None:
    fields = ["school_id", "abbr", "year", "method_id", "method_alias", "url",
              "http_status", "api_success", "n_rows", "bytes", "sha256", "fetched_at_utc"]
    with MANIFEST_CSV.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Collect raw THPT cutoff records (Layer 1).")
    p.add_argument("--years", nargs=2, type=int, metavar=("START", "END"),
                   default=DEFAULT_YEARS, help="inclusive year range (default 2019 2025)")
    p.add_argument("--delay", type=float, default=1.0, help="seconds between network calls")
    p.add_argument("--force", action="store_true", help="refetch even if cached file exists")
    args = p.parse_args(argv)

    years = (min(args.years), max(args.years))
    print(f"Collecting THPT cutoffs (method_id={METHOD_ID}) for years {years[0]}-{years[1]} ...")
    rows = collect(years, args.delay, args.force)
    write_manifest(rows)

    fetched = sum(1 for r in rows if r["fetched_at_utc"] != "(cached)")
    total_records = sum(r["n_rows"] for r in rows if r["n_rows"] > 0)
    print(f"\nDone. {len(rows)} (school, year) files "
          f"({fetched} fetched, {len(rows) - fetched} cached), "
          f"{total_records} raw records total.")
    print(f"Raw JSON:  {RAW_DIR}")
    print(f"Manifest:  {MANIFEST_CSV}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
