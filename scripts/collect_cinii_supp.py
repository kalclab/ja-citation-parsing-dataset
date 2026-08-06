"""Supplemental collector: CiNii Research OpenSearch (@article + @inproceedings).

Complements J-Stage/CrossRef with venues they do not cover, prioritising
non-AI/NLP conference proceedings (人文社会系の学会大会要旨を優先) and journals
absent from the J-Stage pull. Output goes to data/interim/cinii_supp/ (kept
separate from the books collector's data/interim/cinii/ to avoid write clashes).

Method: query CiNii Research OpenSearch `articles` by `publicationTitle`
(venue name) — free-text search returns front-matter noise, whereas venue
queries return clean authored records. entry_type is fixed per curated venue
(CiNii marks conference papers as dc:type=Article, so it cannot distinguish
them; the venue does). No API key; 2 s between requests; contact-bearing UA.

Cleaning / quality rules (also in README):
- Drop front-matter (目次/会則/奥付/巻頭言/…) and records lacking a person author,
  a numeric start page, a venue name, or a year.
- Author names: kept in CiNii's dc:creator form as-is (mixes 「姓, 名」/「姓 名」/
  romanized across sources) per conventions L67; the mixture is the realistic
  difficulty and is noted per record.
- pages = start-end (endpage dropped when absent); year = leading 4 digits of
  prism:publicationDate; DOI from dc:identifier cir:DOI; ISSN/publisher kept.
- @article requires volume; a non-numeric or missing-but-number volume is kept
  as-is and flagged nonstandard_volume (never fabricated).

Dedup: DOIs already in data/interim/jstage/records.jsonl are skipped (snapshot
at run time) to avoid wasteful overlap; final cross-source dedup is the merge's
job. Idempotent: fixed venues, deterministic selection by crid, cached raw
pages, retrieved_at from the cached fetch time.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
import urllib.parse
from datetime import datetime, timezone, timedelta
from pathlib import Path

import requests

JST = timezone(timedelta(hours=9))
UA = "ja-citation-parsing-dataset (mailto:anonymous@example.org)"
ENDPOINT = "https://cir.nii.ac.jp/opensearch/articles"
DELAY = 2.0
POOL = 100  # items fetched per venue before selecting

FRONT = re.compile(r"(目次|会則|奥付|表紙|裏表紙|編集後記|投稿規定|執筆要領|彙報|巻頭言"
                   r"|Contents|総目次|会報|名簿|正誤|訂正|お知らせ|案内|一覧)")
ORG = re.compile(r"(学会|協会|委員会|研究所|研究会|センター|機構|編集部|事務局|会$|社$|省$|庁$)")
LATIN_RUN = re.compile(r"[A-Za-z]{2,}")

# (venue publicationTitle, entry_type, discipline, subfield, target)
VENUES = [
    ("史学雑誌", "article", "人文社会", "歴史学", 7),
    ("教育社会学研究", "article", "人文社会", "教育社会学", 7),
    ("地学雑誌", "article", "理工", "地理学", 13),
    ("老年社会科学", "article", "医学生命", "老年社会科学", 13),
    ("日本心理学会大会発表論文集", "inproceedings", "人文社会", "心理学", 15),
    ("日本地理学会発表要旨集", "inproceedings", "人文社会", "地理学", 15),
    ("日本建築学会大会学術講演梗概集", "inproceedings", "理工", "建築学", 8),
    ("日本地質学会学術大会講演要旨", "inproceedings", "理工", "地質学", 7),
    ("日本公衆衛生学会総会抄録集", "inproceedings", "医学生命", "公衆衛生", 15),
]


def load_jstage_dois(path: Path) -> set[str]:
    dois: set[str] = set()
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                doi = json.loads(line).get("bibtex_fields", {}).get("doi", "").strip().lower()
                if doi:
                    dois.add(doi)
    return dois


def fetch_venue(venue: str, idx: int, raw_dir: Path, refresh: bool) -> tuple[list[dict], str]:
    raw_dir.mkdir(parents=True, exist_ok=True)
    log_path = raw_dir / "fetch_log.json"
    log = json.loads(log_path.read_text(encoding="utf-8")) if log_path.exists() else {}
    cache = raw_dir / f"venue{idx:02d}.json"
    if cache.exists() and not refresh and venue in log:
        return json.loads(cache.read_text(encoding="utf-8")).get("items", []), log[venue]["fetched_at"]
    time.sleep(DELAY)
    url = ENDPOINT + "?" + urllib.parse.urlencode(
        {"publicationTitle": venue, "count": POOL, "format": "json", "lang": "ja"})
    resp = requests.get(url, headers={"User-Agent": UA}, timeout=30)
    fetched_at = datetime.now(JST).isoformat(timespec="seconds")
    resp.raise_for_status()
    data = resp.json()
    cache.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    log[venue] = {"fetched_at": fetched_at, "total": data.get("opensearch:totalResults"),
                  "url": url}
    log_path.write_text(json.dumps(log, ensure_ascii=False, indent=2), encoding="utf-8")
    return data.get("items", []), fetched_at


def _doi(it: dict) -> str:
    for ident in it.get("dc:identifier", []):
        if isinstance(ident, dict) and ident.get("@type") == "cir:DOI":
            return ident.get("@value", "").strip()
    return ""


def _year(it: dict) -> str:
    m = re.match(r"(\d{4})", str(it.get("prism:publicationDate", "")))
    return m.group(1) if m else ""


def _pages(it: dict) -> str:
    start = str(it.get("prism:startingPage", "")).strip()
    end = str(it.get("prism:endingPage", "")).strip()
    if end and end != "-":
        return f"{start}-{end}"
    return start


def _authors(it: dict) -> list[str]:
    return [a.strip() for a in (it.get("dc:creator") or []) if a and a.strip()]


def parse_volume(raw_vol: str, raw_num: str) -> tuple[str, str, bool]:
    """Decode CiNii volume. Returns (volume, number, nonstandard).

    CiNii encodes volume+issue as "123(6)" — a standard volume/issue, decoded
    here (not fabrication). A genuinely non-numeric volume (第78回 / 通巻 / D-2)
    or a missing volume with only an issue is kept as-is and marked nonstandard.
    """
    raw_vol = (raw_vol or "").strip()
    raw_num = (raw_num or "").strip()
    m = re.match(r"^(\d+)\(([^)]+)\)$", raw_vol)  # "123(6)"
    if m:
        return m.group(1), (raw_num or m.group(2)), False
    if raw_vol.isdigit():
        return raw_vol, raw_num, False
    if raw_vol:
        return raw_vol, raw_num, True
    if raw_num:
        return "", raw_num, True
    return "", "", False


def qualifies(it: dict, entry_type: str) -> bool:
    authors = _authors(it)
    start = str(it.get("prism:startingPage", "")).strip()
    if not authors or FRONT.search(it.get("title", "")):
        return False
    if not (it.get("prism:publicationName") or it.get("dc:publisher")) or not _year(it):
        return False
    if not re.match(r"^\d+$", start):  # real content start page
        return False
    if entry_type == "article" and not (it.get("prism:volume") or it.get("prism:number")):
        return False
    return True


def build_record(it: dict, entry_type: str, disc: str, sub: str, fetched_at: str) -> dict:
    authors = _authors(it)
    venue_name = it.get("prism:publicationName") or ""
    fields: dict[str, str] = {"author": " and ".join(authors), "title": it["title"].strip()}
    if entry_type == "article":
        fields["journal"] = venue_name
    else:
        fields["booktitle"] = venue_name

    flags: list[str] = []
    vol, num, nonstd = parse_volume(str(it.get("prism:volume", "")),
                                    str(it.get("prism:number", "")))
    if vol:
        fields["volume"] = vol
    if num:
        fields["number"] = num
    # nonstandard volume only matters for @article (where volume is required)
    if entry_type == "article" and nonstd:
        flags.append("nonstandard_volume")
    if _pages(it):
        fields["pages"] = _pages(it)
    fields["year"] = _year(it)
    if it.get("prism:issn"):
        fields["issn"] = it["prism:issn"]
    if it.get("dc:publisher"):
        fields["publisher"] = it["dc:publisher"]
    if _doi(it):
        fields["doi"] = _doi(it)

    text = fields["title"] + " " + fields["author"].replace(" and ", " ")
    if LATIN_RUN.search(text):
        flags.append("english_mixed")
    if re.search(r"[：]|[:：]\s|[―—]|\s[-–][^-–]*[-–]\s*$", fields["title"]):
        flags.append("subtitle")
    if any(ORG.search(a) and "," not in a and " " not in a for a in authors):
        flags.append("institutional_author")

    return {
        "entry_type": entry_type,
        "bibtex_fields": fields,
        "discipline": disc,
        "subfield": sub,
        "difficulty_flags": flags,
        "source_name": "CiNii Research OpenSearch",
        "source_url": it["@id"],
        "retrieved_at": fetched_at,
        "notes": "著者名はCiNiiのdc:creator形式のまま保持（姓,名／姓 名／ローマ字が混在）",
        "_crid": it["@id"],
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=Path("data/interim/cinii_supp/records.jsonl"))
    ap.add_argument("--raw-dir", type=Path, default=Path("data/raw/cinii_supp"))
    ap.add_argument("--jstage", type=Path, default=Path("data/interim/jstage/records.jsonl"))
    ap.add_argument("--refresh", action="store_true")
    args = ap.parse_args()

    jstage_dois = load_jstage_dois(args.jstage)
    records: list[dict] = []
    stats: dict[str, dict[str, int]] = {}
    skipped_dup = 0
    for idx, (venue, etype, disc, sub, target) in enumerate(VENUES):
        items, fetched_at = fetch_venue(venue, idx, args.raw_dir, args.refresh)
        qual = sorted((it for it in items if qualifies(it, etype)), key=lambda x: x["@id"])
        chosen = 0
        for it in qual:
            if chosen >= target:
                break
            doi = _doi(it).lower()
            if doi and doi in jstage_dois:
                skipped_dup += 1
                continue
            records.append(build_record(it, etype, disc, sub, fetched_at))
            chosen += 1
        stats.setdefault(etype, {}).setdefault(disc, 0)
        stats[etype][disc] += chosen
        print(f"{venue[:20]} ({etype}/{disc}): pool={len(items)} qual={len(qual)} chosen={chosen}",
              file=sys.stderr)

    records.sort(key=lambda r: (r["entry_type"], r.pop("_crid")))
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", encoding="utf-8") as fh:
        for i, rec in enumerate(records, start=1):
            fh.write(json.dumps({"provisional_key": f"cinii_supp-{i:06d}", **rec},
                                ensure_ascii=False) + "\n")

    n_art = sum(1 for r in records if r["entry_type"] == "article")
    n_inp = sum(1 for r in records if r["entry_type"] == "inproceedings")
    flagged = sum(1 for r in records if r["difficulty_flags"])
    print(f"wrote {len(records)} records -> {args.out} (article {n_art}, inproceedings {n_inp})")
    print("by type/discipline:", stats)
    print(f"skipped (J-Stage DOI dup): {skipped_dup}")
    print(f"difficulty-flagged: {flagged}/{len(records)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
