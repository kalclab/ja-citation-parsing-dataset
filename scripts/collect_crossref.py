"""Collect English-mixed @article records from CrossRef REST (Japanese journals).

Purpose : deliberately supply the
"欧文混じり" hard cases — Japanese-journal articles whose bibliography mixes
scripts (romanized/English-caps author names, English titles/subtitles). Every
emitted record carries the `english_mixed` flag.

Method: pull works per journal by ISSN (CrossRef polite pool, mailto). A fixed
curated journal list gives discipline balance (人文社会 / 理工 / 医学生命, ~20 each).
Within a journal we fetch a fixed pool (sort=published asc) and select records
that satisfy the @article required fields, preferring those that also carry a
Japanese `original-title` (the richest mixed cases).

Survey-observed quirks handled (both recorded in each record's notes):
  (a) HTML entities in title/journal (&lt; &amp; …) -> unescaped.
  (b) Japanese author given/family swap: CrossRef/J-Stage deposits the surname
      in ALL-CAPS. If the surname appears to sit in `given` (given is caps,
      family is not) we swap it back; otherwise we trust CrossRef's fields.
      Romanized names are emitted as "Family, Given" (unambiguous for BibTeX);
      undecidable cases are noted.

Output: data/interim/crossref/records.jsonl ; raw pages cached under
data/raw/crossref/. Idempotent: fixed journal list + fixed sort + deterministic
selection + retrieved_at taken from the cached fetch time.
"""

from __future__ import annotations

import argparse
import html
import json
import re
import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

import requests

JST = timezone(timedelta(hours=9))
MAILTO = "anonymous@example.org"
UA = f"ja-citation-parsing-dataset (mailto:{MAILTO})"
API = "https://api.crossref.org/journals/{issn}/works"
DELAY = 1.5
ROWS = 50
POOL = 400  # works fetched per journal before selecting
LATIN_RUN = re.compile(r"[A-Za-z]{2,}")
CJK_RE = re.compile(r"[぀-ヿ一-鿿]")

# Curated Japanese journals: (issn, discipline, subfield, target). The
# mixed-script pattern (Japanese title + romanized authors, or Japanese title
# with embedded English) occurs only in journals that romanize author names —
# concentrated in medicine/engineering; humanities journals are mostly script-
# consistent, so the english_mixed set skews STEM/medical by data availability.
# Journals below were probed for mixed-record yield before selection.
JOURNALS = [
    ("0021-5414", "人文社会", "社会学", 10),         # Japanese Sociological Review 社会学評論
    ("0387-3145", "人文社会", "教育社会学", 5),       # The Journal of Educational Sociology 教育社会学研究
    ("2186-0661", "理工", "電子情報通信", 20),       # IEICE Communications Society Magazine
    ("0300-9173", "医学生命", "老年医学", 15),        # Nippon Ronen Igakkai Zasshi 日本老年医学会雑誌
    ("0445-2429", "医学生命", "医学図書館情報", 5),    # Igaku Toshokan 医学図書館
    ("0021-5384", "医学生命", "内科学", 5),          # Nihon Naika Gakkai Zasshi 日本内科学会雑誌
]
SELECT = ("DOI,title,original-title,author,container-title,short-container-title,"
          "volume,issue,page,published,issued,ISSN,publisher,URL")


def fetch_pool(issn: str, raw_dir: Path, refresh: bool) -> tuple[list[dict], str]:
    """Fetch a fixed pool of works for a journal; cache raw pages. Return
    (items, fetched_at)."""
    raw_dir.mkdir(parents=True, exist_ok=True)
    log_path = raw_dir / "fetch_log.json"
    log = json.loads(log_path.read_text(encoding="utf-8")) if log_path.exists() else {}
    items: list[dict] = []
    fetched_at = None
    for page in range(POOL // ROWS):
        cache = raw_dir / f"{issn}_p{page}.json"
        if cache.exists() and not refresh:
            data = json.loads(cache.read_text(encoding="utf-8"))
            fetched_at = fetched_at or log.get(issn, {}).get("fetched_at")
        else:
            time.sleep(DELAY)
            resp = requests.get(
                API.format(issn=issn),
                params={"filter": "type:journal-article", "rows": ROWS,
                        "offset": page * ROWS, "select": SELECT,
                        "sort": "published", "order": "desc", "mailto": MAILTO},
                headers={"User-Agent": UA}, timeout=30)
            resp.raise_for_status()
            data = resp.json()
            cache.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
            fetched_at = datetime.now(JST).isoformat(timespec="seconds")
        batch = data.get("message", {}).get("items", [])
        items.extend(batch)
        if len(batch) < ROWS:
            break
    log[issn] = {"fetched_at": fetched_at, "pool": len(items)}
    log_path.write_text(json.dumps(log, ensure_ascii=False, indent=2), encoding="utf-8")
    return items, fetched_at


def clean_text(s: str) -> tuple[str, bool]:
    """Unescape HTML entities and strip inline tags. Return (text, changed)."""
    unescaped = html.unescape(s)
    stripped = re.sub(r"<[^>]+>", "", unescaped)
    return stripped.strip(), (stripped.strip() != s.strip())


def pick_title(it: dict) -> tuple[str, str]:
    orig = [t for t in (it.get("original-title") or []) if t.strip()]
    eng = [t for t in (it.get("title") or []) if t.strip()]
    if orig:
        return orig[0], "orig"
    if eng:
        return eng[0], "eng"
    return "", ""


def format_authors(authors: list[dict]) -> tuple[str, list[str]]:
    out, notes = [], []
    for a in authors:
        fam = (a.get("family") or "").strip()
        giv = (a.get("given") or "").strip()
        nm = (a.get("name") or "").strip()
        if nm and not fam and not giv:
            out.append(nm)
            continue
        if fam and not giv:
            out.append(fam)
            continue
        if giv and not fam:
            out.append(giv)
            notes.append(f"given-only:{giv}")
            continue
        if giv.isupper() and not fam.isupper():  # surname likely in `given`
            out.append(f"{giv}, {fam}")
            notes.append(f"given/family swap補正:{fam}/{giv}")
        else:
            out.append(f"{fam}, {giv}")
    return " and ".join(out), notes


def qualifies(it: dict) -> bool:
    title, _ = pick_title(it)
    return bool(
        it.get("author") and title and it.get("volume") and it.get("page")
        and (it.get("container-title") or it.get("short-container-title"))
        and _year(it))


def _author_tokens(it: dict) -> list[str]:
    return [f"{a.get('family','')}{a.get('given','')}{a.get('name','')}"
            for a in (it.get("author") or [])]


def is_mixed(it: dict) -> bool:
    """True iff the record mixes scripts: both a CJK char and a Latin run appear
    across (chosen title + author name tokens). Journal name is excluded since it
    is English for every record here and would trivialise the test."""
    text = clean_text(pick_title(it)[0])[0] + " " + " ".join(_author_tokens(it))
    return bool(CJK_RE.search(text)) and bool(LATIN_RUN.search(text))


def _year(it: dict) -> str:
    for key in ("published", "issued"):
        parts = (it.get(key) or {}).get("date-parts") or [[None]]
        if parts and parts[0] and parts[0][0]:
            return str(parts[0][0])
    return ""


def build_record(it: dict, disc: str, sub: str) -> dict | None:
    title, tkind = pick_title(it)
    title, t_changed = clean_text(title)
    container = (it.get("container-title") or it.get("short-container-title") or [""])[0]
    journal, j_changed = clean_text(container)
    author, aut_notes = format_authors(it.get("author") or [])
    if not (title and author and journal):
        return None

    fields = {
        "author": author,
        "title": title,
        "journal": journal,
        "volume": str(it.get("volume", "")).strip(),
        "year": _year(it),
    }
    if it.get("issue"):
        fields["number"] = str(it["issue"]).strip()
    fields["pages"] = str(it.get("page", "")).strip()
    if it.get("ISSN"):
        fields["issn"] = it["ISSN"][0]
    if it.get("publisher"):
        fields["publisher"] = it["publisher"].strip()
    fields["doi"] = it["DOI"]
    fields["url"] = it.get("URL", f"https://doi.org/{it['DOI']}")

    flags = ["english_mixed"]  # required for this source; asserted below
    if re.search(r"[：]|[:：]\s|[―—]|\s[-–][^-–]*[-–]\s*$", title):
        flags.append("subtitle")

    notes = ["著者はCrossRefのfamily/given由来。ローマ字名は「Family, Given」形式で出力"]
    if not CJK_RE.search(title):
        notes.append("タイトルは欧文（日本語誌の欧文論文）")
    if t_changed or j_changed:
        notes.append("タイトル/誌名のHTML実体参照をアンエスケープ")
    notes.extend(aut_notes)

    return {
        "entry_type": "article",
        "bibtex_fields": fields,
        "discipline": disc,
        "subfield": sub,
        "difficulty_flags": flags,
        "source_name": "Crossref REST API",
        "source_url": fields["url"],
        "retrieved_at": None,  # filled by caller
        "notes": "; ".join(notes),
        "_doi": it["DOI"],
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=Path("data/interim/crossref/records.jsonl"))
    ap.add_argument("--raw-dir", type=Path, default=Path("data/raw/crossref"))
    ap.add_argument("--refresh", action="store_true")
    args = ap.parse_args()

    records: list[dict] = []
    per_disc: dict[str, int] = {}
    for order, (issn, disc, sub, target) in enumerate(JOURNALS):
        pool, fetched_at = fetch_pool(issn, args.raw_dir, args.refresh)
        # require genuine mixed script (english_mixed guaranteed); prefer records
        # whose title is Japanese (CJK) — the richest mixed case. Deterministic by DOI.
        qual = [it for it in pool if qualifies(it) and is_mixed(it)]
        def ja_title(it):
            return bool(CJK_RE.search(clean_text(pick_title(it)[0])[0]))
        with_ja = sorted((it for it in qual if ja_title(it)), key=lambda x: x["DOI"])
        without = sorted((it for it in qual if not ja_title(it)), key=lambda x: x["DOI"])
        chosen, n = [], 0
        for it in with_ja + without:
            if n >= target:
                break
            rec = build_record(it, disc, sub)
            if rec is None:
                continue
            rec["retrieved_at"] = fetched_at
            rec["_order"] = order
            chosen.append(rec)
            n += 1
        per_disc[disc] = per_disc.get(disc, 0) + len(chosen)
        records.extend(chosen)
        print(f"{issn} ({disc}/{sub}): pool={len(pool)} qual={len(qual)} chosen={len(chosen)}", file=sys.stderr)

    records.sort(key=lambda r: (r.pop("_order"), r.pop("_doi")))
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", encoding="utf-8") as fh:
        for i, rec in enumerate(records, start=1):
            fh.write(json.dumps({"provisional_key": f"crossref-{i:06d}", **rec},
                                ensure_ascii=False) + "\n")

    em = sum(1 for r in records if "english_mixed" in r["difficulty_flags"])
    print(f"wrote {len(records)} records -> {args.out}")
    print("discipline:", per_disc)
    print(f"english_mixed: {em}/{len(records)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
