#!/usr/bin/env python3
"""Sample-inspection QC for the @book collectors (NDL + CiNii).

For each source, draw a reproducible random sample of 20 records, fetch the live
source_url page, and check that the record actually matches the page:
  - HTTP 200 (record exists / link is valid),
  - the title (or its long head before the subtitle) appears in the page text,
  - the ISBN (normalised, hyphen-insensitive) appears in the page,
  - at least one author/editor surname (first 2 chars of the first name) appears.

This catches parsing errors and broken links without re-deriving every field.
Results are appended to reports/qc/books.md by the caller; this script prints a
machine-readable summary and the per-record findings.

Run: uv run scripts/qc_books_sample.py   (stdlib only; ~2 s between fetches)
"""
from __future__ import annotations

import json
import random
import re
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
UA = "ja-citation-parsing-dataset (mailto:anonymous@example.org)"
SOURCES = {
    "ndl": ROOT / "data" / "interim" / "ndl" / "records.jsonl",
    "cinii": ROOT / "data" / "interim" / "cinii" / "records.jsonl",
}
SLEEP = 2.2
SAMPLE_N = 20


def fetch_text(url: str) -> tuple[int, str]:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return resp.status, resp.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:  # noqa: PERF203
        return e.code, ""
    except Exception as e:  # noqa: BLE001
        return -1, str(e)


def check(rec: dict, status: int, body: str) -> dict:
    bf = rec["bibtex_fields"]
    title = bf.get("title", "")
    head = re.split(r"\s:\s|：|=", title)[0].strip()
    isbn = re.sub(r"[-\s]", "", bf.get("isbn", ""))
    body_isbn = re.sub(r"[-\s]", "", body)
    names = []
    for fld in ("author", "editor"):
        if bf.get(fld):
            names += bf[fld].split(" and ")
    surname = names[0].split(" ")[0][:2] if names else ""
    return {
        "key": rec["provisional_key"],
        "http": status,
        "title_ok": bool(head) and head in body,
        "isbn_ok": bool(isbn) and isbn in body_isbn,
        "author_ok": bool(surname) and surname in body,
        "title": title[:50],
    }


def main() -> None:
    rng = random.Random(424242)
    overall = {}
    for src, path in SOURCES.items():
        if not path.exists():
            print(f"[{src}] no records file at {path}", file=sys.stderr)
            continue
        recs = [json.loads(l) for l in path.open(encoding="utf-8")]
        sample = rng.sample(recs, min(SAMPLE_N, len(recs)))
        print(f"\n### {src}: sampling {len(sample)} of {len(recs)}")
        results = []
        for rec in sample:
            status, body = fetch_text(rec["source_url"])
            r = check(rec, status, body)
            results.append(r)
            mark = "OK " if (r["http"] == 200 and r["title_ok"] and r["isbn_ok"]) else "!! "
            print(f"  {mark}{r['key']:32s} http={r['http']} title={int(r['title_ok'])} "
                  f"isbn={int(r['isbn_ok'])} author={int(r['author_ok'])}  {r['title']}")
            time.sleep(SLEEP)
        n = len(results)
        overall[src] = {
            "n": n,
            "http200": sum(1 for r in results if r["http"] == 200),
            "title_ok": sum(1 for r in results if r["title_ok"]),
            "isbn_ok": sum(1 for r in results if r["isbn_ok"]),
            "author_ok": sum(1 for r in results if r["author_ok"]),
        }
    print("\n=== SUMMARY ===")
    print(json.dumps(overall, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
