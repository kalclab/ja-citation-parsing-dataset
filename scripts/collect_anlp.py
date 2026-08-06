"""Collect @inproceedings records from the ANLP annual-meeting archive.

Source: 言語処理学会年次大会 permanent proceedings archive at
    https://www.anlp.jp/proceedings/annual_meeting/<year>/
No BibTeX is offered; records are built from the program index HTML, which
lists, per paper, a paper id, title (span.title), a permanent PDF link, and an
author line of the form `○著者1, 著者2 (所属), 著者3 (所属2)`.

Output: data/interim/anlp/records.jsonl (interim record schema).
Raw program indexes are cached under data/raw/anlp/ (bibliographic listing
only; no paper full text is stored) together with fetch_log.json.

Politeness: www.anlp.jp serves no robots.txt (404 as of 2026-07); we still
crawl low-frequency — one request per year, 2 s between requests, UA carrying
a contact address. Re-runs reuse the cache and do not hit the network unless
--refresh is given.

Cleaning rules (also in README):
- Author line: strip the ○/◯/● presenter marker and every "(...)"/"（…）"
  affiliation group, then split remaining names on ,/、/，. Join with " and ".
- 姓名 delimiter: the ANLP index concatenates surname+given with NO separator
  (e.g. 「川原田将之」). We cannot split this without guessing, so names are
  kept verbatim in source form and this is noted per record. (Contrast the
  CiNii collector, which converts "姓, 名" -> "姓 名".)
- booktitle: built from the page title 「第N回年次大会(NLP<year>)」 as
  「言語処理学会第N回年次大会発表論文集」; year and N taken from the same title.
- pages are not present in the index and are therefore omitted (optional for
  @inproceedings).

Idempotent: sampling is deterministic (even stride over program order);
retrieved_at is taken from the cached fetch time, so re-runs reproduce output.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

import requests
from lxml import html
from urllib.parse import urljoin

JST = timezone(timedelta(hours=9))
UA = "ja-citation-parsing-dataset (mailto:anonymous@example.org)"
BASE = "https://www.anlp.jp/proceedings/annual_meeting/{year}/"
REQUEST_DELAY_SEC = 2.0
PAPER_ID_RE = re.compile(r"^[A-Za-z]+\d+-\d+$")
TITLE_META_RE = re.compile(r"第(\d+)回年次大会\(NLP(\d+)\)")
PAGES_RE = re.compile(r"\(\s*pp?\.\s*([0-9]+\s*[-–—]\s*[0-9]+)\s*\)")
# Presenter / annotation marks the index attaches to author names (presenter ○,
# award candidate ◊, special-session ♠, etc.). Stripped from names. NOTE: the
# katakana name separator "・" is deliberately NOT here — it belongs to names.
ANNOT_MARKS = set("○◯●◊◇♠♣♥♦★☆▲△▽▼*†‡§")
CONTROL_RE = re.compile(r"[\x00-\x1f]")
LATIN_RUN_RE = re.compile(r"[A-Za-z]{2,}")
# Subtitle markers used by ANLP titles. Bare "-" is intentionally excluded:
# it mostly appears inside English compounds (Image-based, Sequence-to-Sequence).
# We flag: 「―副題―」/「—副題—」 bars, full-width colon, colon + space/CJK, and a
# paired " -副題-" (space-hyphen … hyphen-at-end).
SUBTITLE_RE = re.compile(
    r"[―—]|：|[:：]\s|[:：][ぁ-んァ-ヶー一-龠]|\s[-–][^-–]*[-–]\s*$"
)


def fetch_index(year: int, raw_dir: Path, refresh: bool) -> tuple[str, str]:
    """Return (html_text, fetched_at_iso). Cache under raw_dir; polite fetch."""
    raw_dir.mkdir(parents=True, exist_ok=True)
    cache = raw_dir / f"nlp{year}_program.html"
    log_path = raw_dir / "fetch_log.json"
    log = json.loads(log_path.read_text(encoding="utf-8")) if log_path.exists() else {}

    if cache.exists() and not refresh and str(year) in log:
        return cache.read_text(encoding="utf-8"), log[str(year)]["fetched_at"]

    url = BASE.format(year=year)
    time.sleep(REQUEST_DELAY_SEC)
    resp = requests.get(url, headers={"User-Agent": UA}, timeout=30)
    fetched_at = datetime.now(JST).isoformat(timespec="seconds")
    resp.raise_for_status()
    resp.encoding = resp.apparent_encoding or "utf-8"
    text = resp.text
    cache.write_text(text, encoding="utf-8")
    log[str(year)] = {"url": url, "fetched_at": fetched_at,
                      "http_status": resp.status_code, "bytes": len(resp.content)}
    log_path.write_text(json.dumps(log, ensure_ascii=False, indent=2), encoding="utf-8")
    return text, fetched_at


def parse_names(raw: str) -> list[str]:
    s = CONTROL_RE.sub("", raw)
    s = "".join(c for c in s if c not in ANNOT_MARKS)
    s = re.sub(r"（[^）]*）", "", s)  # full-width affiliation groups
    s = re.sub(r"\([^)]*\)", "", s)   # half-width affiliation groups
    # collapse whitespace runs (HTML line-wraps inside romanized names)
    return [re.sub(r"\s+", " ", n).strip() for n in re.split(r"[,、，]", s) if n.strip()]


def parse_papers(page: str) -> tuple[int, int, list[dict]]:
    """Return (kai, year, papers). Each paper: pid/title/authors/pdf_path."""
    doc = html.fromstring(page)
    meta = TITLE_META_RE.search(doc.findtext(".//title") or "")
    if not meta:
        raise ValueError("could not read 第N回/NLPyyyy from page title")
    kai, year = int(meta.group(1)), int(meta.group(2))

    papers: list[dict] = []
    for pid_span in doc.xpath('//td[@class="pid"]/span[@id]'):
        pid = pid_span.get("id")
        if not PAPER_ID_RE.match(pid):
            continue
        # A paper spans the pid row (tr1) plus the following row (tr2). The
        # layout moved between years: pre-2016 keeps title+pdf+pages in tr1
        # and authors in tr2; 2016+ keeps title in tr1 and pdf+authors in tr2.
        # So gather title/pdf/pages from tr1∪tr2 and take authors from the
        # first non-empty td that holds neither the title span nor a pdf link.
        tr1 = pid_span.getparent().getparent()
        tr2 = tr1.getnext()
        rows = [r for r in (tr1, tr2) if r is not None]

        tspan = [s for r in rows for s in r.xpath('.//span[@class="title"]')]
        pdf = [h for r in rows for h in r.xpath('.//a[contains(@href,".pdf")]/@href')]
        if not tspan or not pdf:
            continue
        title = tspan[0].text_content().strip()

        author_raw = None
        for r in rows:
            for td in r.xpath("./td"):
                if (td.get("class") == "pid" or td.xpath(".//span[@id]")
                        or td.xpath('.//span[@class="title"]')
                        or td.xpath('.//a[contains(@href,".pdf")]')):
                    continue
                text = td.text_content().strip()
                if text:
                    author_raw = text
                    break
            if author_raw:
                break
        if not (title and author_raw):
            continue
        names = parse_names(author_raw)
        if not names:
            continue

        pm = PAGES_RE.search("".join(r.text_content() for r in rows))
        pages = re.sub(r"\s+", "", pm.group(1)) if pm else None
        papers.append({"pid": pid, "title": title, "names": names,
                       "pdf_path": pdf[0], "pages": pages})
    return kai, year, papers


def even_stride(items: list, n: int) -> list:
    """Deterministically pick n items spread across the ordered list."""
    if n >= len(items):
        return list(items)
    step = len(items) / n
    return [items[int(i * step)] for i in range(n)]


def difficulty_flags(title: str, names: list[str]) -> list[str]:
    flags = []
    if SUBTITLE_RE.search(title):
        flags.append("subtitle")
    if LATIN_RUN_RE.search(title) or any(LATIN_RUN_RE.search(n) for n in names):
        flags.append("english_mixed")
    return flags


def build_record(paper: dict, kai: int, year: int, url: str, fetched_at: str) -> dict:
    booktitle = f"言語処理学会第{kai}回年次大会発表論文集"
    fields = {
        "author": " and ".join(paper["names"]),
        "title": paper["title"],
        "booktitle": booktitle,
        "year": str(year),
    }
    if paper.get("pages"):
        fields["pages"] = paper["pages"]
    fields["url"] = url
    fields["organization"] = "言語処理学会"
    return {
        "entry_type": "inproceedings",
        "bibtex_fields": fields,
        "discipline": "理工",
        "subfield": "自然言語処理",
        "difficulty_flags": difficulty_flags(paper["title"], paper["names"]),
        "source_name": "言語処理学会年次大会アーカイブ",
        "source_url": url,
        "retrieved_at": fetched_at,
        "notes": ("ANLP索引は姓名を区切らないため著者名は連結形のまま保持。"
                  "所属（括弧内）と発表者マーク○は除去。"),
        "_sort": (year, paper["pid"]),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--years", default="2015-2024",
                    help="inclusive range 'YYYY-YYYY' or comma list (default 2015-2024)")
    ap.add_argument("--per-year", type=int, default=6,
                    help="target papers per year (default 6 -> 60 over 10 years)")
    ap.add_argument("--out", type=Path, default=Path("data/interim/anlp/records.jsonl"))
    ap.add_argument("--raw-dir", type=Path, default=Path("data/raw/anlp"))
    ap.add_argument("--refresh", action="store_true", help="force re-download")
    args = ap.parse_args()

    if "-" in args.years and "," not in args.years:
        lo, hi = (int(x) for x in args.years.split("-"))
        years = list(range(lo, hi + 1))
    else:
        years = [int(x) for x in args.years.split(",")]

    records: list[dict] = []
    per_year_counts: dict[int, int] = {}
    for year in years:
        try:
            page, fetched_at = fetch_index(year, args.raw_dir, args.refresh)
            kai, page_year, papers = parse_papers(page)
        except (requests.RequestException, ValueError) as exc:
            print(f"WARN {year}: skipped ({exc})", file=sys.stderr)
            continue
        chosen = even_stride(papers, args.per_year)
        per_year_counts[page_year] = len(chosen)
        for paper in chosen:
            url = urljoin(BASE.format(year=page_year), paper["pdf_path"])
            records.append(build_record(paper, kai, page_year, url, fetched_at))

    records.sort(key=lambda r: r.pop("_sort"))
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", encoding="utf-8") as fh:
        for i, rec in enumerate(records, start=1):
            rec = {"provisional_key": f"anlp-{i:06d}", **rec}
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")

    flagged = sum(1 for r in records if r["difficulty_flags"])
    print(f"wrote {len(records)} records -> {args.out}")
    print("per-year:", {y: per_year_counts[y] for y in sorted(per_year_counts)})
    print(f"difficulty-flagged: {flagged}/{len(records)} "
          f"({flagged/len(records)*100:.0f}%)" if records else "no records")
    return 0


if __name__ == "__main__":
    sys.exit(main())
