#!/usr/bin/env python3
"""Collect @book records from CiNii Research OpenSearch (CiNii Books), 105 target.

Dependencies: Python stdlib only. Run with:
    uv run scripts/collect_cinii_books.py
(No third-party deps, so plain `python3 scripts/collect_cinii_books.py` works too.)

Operation notes
---------------
- Endpoint: https://cir.nii.ac.jp/opensearch/books (returns dc:type=Book only).
- No appid is registered yet, so we run key-less and SLOWLY: >= 2 s between
  requests (per the team-lead instruction), polite User-Agent with contact.
- Discipline stratification is achieved by issuing scholarly subject-keyword
  queries grouped by field; the discipline label is taken from the query group
  (CiNii OpenSearch carries no NDC in the summary). Target ~35 per discipline.

Quality / cleaning rules (see reports/qc/books.md)
- ISBN gate: keep only records with an ISBN (drops pre-war reprints and
  ISBN-less pamphlets, biasing toward modern academic books).
- Japanese-title gate: title must contain a Japanese character.
- Author names: CiNii gives "姓, 名" (comma). Per the updated contract
  (phase1_conventions L67, 仕様書 L91 のソース忠実性優先) we KEEP the source form
  verbatim -- no reformatting in the collector -- and record in notes that the
  form differs from the "姓 名" basic form. The comma-form -> space-form
  adjustment for BibTeX name parsing happens only in the Phase 2 derived file.
  Multiple creators are joined with " and ".
- Cross-source dedup: ISBNs already collected by the NDL collector are excluded
  (data/interim/ndl/records.jsonl), so the two book sources do not overlap.

Output: data/interim/cinii/records.jsonl (entry_type=book). Raw JSON responses
are saved under data/raw/cinii/. Idempotent: rewrites records.jsonl each run.
"""
from __future__ import annotations

import json
import re
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from book_screening import screen_book  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "data" / "raw" / "cinii"
OUT_DIR = ROOT / "data" / "interim" / "cinii"
NDL_JSONL = ROOT / "data" / "interim" / "ndl" / "records.jsonl"
ENDPOINT = "https://cir.nii.ac.jp/opensearch/books"
UA = "ja-citation-parsing-dataset (mailto:anonymous@example.org)"
JST = timezone(timedelta(hours=9))
SLEEP = 2.2  # key-less: keep requests >= 2 s apart

TARGET_TOTAL = 105
DISC_CAP = {"人文社会": 36, "理工": 36, "医学生命": 36}
PER_QUERY_MAX = 8          # cap contribution of any single keyword query
COUNT = 50                 # records per request
WINDOW_STARTS = (1, 101, 201)  # sample beyond the most-relevant head

SUBJECT_QUERIES = {
    "人文社会": [
        # NB: the bare "法学" subject on CiNii is a magnet for foreign (CN/KR/TW)
        # and licensing-exam law books; use the specific academic subject 法社会学
        # (yields the 有斐閣 法社会学講座 monographs) instead.
        "社会学", "歴史学", "経済学", "法社会学", "哲学", "心理学",
        "言語学", "政治学", "教育学", "文化人類学",
    ],
    "理工": [
        "物理学", "有機化学", "情報科学", "機械工学", "電気工学",
        "土木工学", "統計学", "地球科学", "材料工学",
    ],
    "医学生命": [
        "内科学", "看護学", "分子生物学", "薬理学", "公衆衛生",
        "生理学", "免疫学", "生化学", "微生物学",
    ],
}

INST_SUFFIXES = (
    "会", "委員会", "研究所", "研究会", "センター", "学会", "省", "庁", "局",
    "大学", "機構", "協会", "編集部", "室", "会議", "本部", "財団", "学院",
    # old-kanji / variant organisation forms seen in CiNii (會 = 会, 學會 = 学会)
    "會", "學會", "研究會", "委員會", "協會", "書院", "學會編",
)


def fetch(q: str, start: int) -> tuple[dict, bool]:
    """Return (data, fetched_live). Reuse a cached raw response when present so
    reruns are idempotent and add no external load; only fetch missing windows."""
    cache = RAW_DIR / f"q_{q}_{start}.json"
    if cache.exists():
        return json.loads(cache.read_text(encoding="utf-8")), False
    params = {"q": q, "count": str(COUNT), "start": str(start), "format": "json"}
    url = ENDPOINT + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=60) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    cache.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return data, True


def has_japanese(s: str) -> bool:
    return bool(re.search(r"[぀-ヿ㐀-鿿]", s))


def looks_institutional(name: str) -> bool:
    n = name.replace(" ", "")
    return any(n.endswith(suf) for suf in INST_SUFFIXES)


def load_ndl_isbns() -> set[str]:
    isbns: set[str] = set()
    if NDL_JSONL.exists():
        for line in NDL_JSONL.open(encoding="utf-8"):
            rec = json.loads(line)
            isbn = rec.get("bibtex_fields", {}).get("isbn")
            if isbn:
                isbns.add(re.sub(r"[-\s]", "", isbn))
    return isbns


CINII_QUALIFIER = re.compile(r"\s*[（(]\s*[^）)]*[）)]\s*$")


def author_form(raw: str) -> tuple[str, bool, bool]:
    """Return (name, is_comma_form, had_qualifier).

    Name *format* is preserved verbatim per the source-fidelity rule: CiNii's
    "姓, 名" comma order stays. The one exception is CiNii's trailing author-
    authority qualifier -- e.g. "加藤, 明彦 (内科学)", "斎藤, 篤 ( 内科学)" -- which is a
    homonym-disambiguation tag CiNii attaches to the person entity, not part of
    the name, and would otherwise pollute the reference string. We strip it and
    record that in notes (analogous to the HTML-entity unescape exception)."""
    s = raw.strip()
    had_qual = bool(CINII_QUALIFIER.search(s))
    if had_qual:
        s = CINII_QUALIFIER.sub("", s).strip()
    is_comma = bool(re.search(r"[^\s],\s*\S", s))  # "姓, 名" style comma inside
    return s, is_comma, had_qual


def parse_item(item: dict, disc: str) -> dict | None:
    if item.get("dc:type") != "Book":
        return None
    title = (item.get("title") or "").strip()
    if not title or not has_japanese(title):
        return None
    ids = item.get("dc:identifier") or []
    isbn = None
    ncid = None
    for d in ids:
        if d.get("@type") == "cir:ISBN" and not isbn:
            isbn = d.get("@value")
        if d.get("@type") == "cir:NCID" and not ncid:
            ncid = d.get("@value")
    if not isbn:
        return None
    year = None
    pd = item.get("prism:publicationDate") or ""
    ym = re.search(r"(\d{4})", pd)
    if ym:
        year = ym.group(1)
    if not year:
        return None
    publisher = item.get("dc:publisher")
    if isinstance(publisher, list):
        publisher = publisher[0] if publisher else None
    if publisher and " : " in publisher:  # e.g. "東京 : 電気学会" contamination
        address, publisher = [p.strip() for p in publisher.split(" : ", 1)]
    else:
        address = None
    if not publisher:
        return None

    creators = item.get("dc:creator") or []
    if isinstance(creators, str):
        creators = [creators]
    names = []
    comma_form = False
    qualifier_stripped = False
    inst_flag = False
    for c in creators:
        nm, is_comma, had_qual = author_form(c)
        comma_form = comma_form or is_comma
        qualifier_stripped = qualifier_stripped or had_qual
        if looks_institutional(nm):
            inst_flag = True
        names.append(nm)
    if not names:
        return None

    url = (item.get("link") or {}).get("@id") or item.get("@id")
    if not url:
        return None

    bf: dict[str, str] = {"author": " and ".join(names), "title": title,
                          "publisher": publisher, "year": year, "isbn": isbn}
    if address:
        bf["address"] = address
    if ncid:
        bf["ncid"] = ncid
    series = item.get("description")
    if isinstance(series, str) and series.strip():
        bf["series"] = series.strip()

    flags = []
    if re.search(r"\s:\s|：|――|―", title):
        flags.append("subtitle")
    if inst_flag:
        flags.append("institutional_author")
    if bf.get("series") or re.search(r"第\s*[0-9０-９一二三四五六七八九十]+\s*[巻册冊]", title):
        flags.append("nonstandard_volume")
    if re.search(r"=\s*[A-Za-zＡ-Ｚａ-ｚ]", title) or re.search(r"[A-Za-zＡ-Ｚａ-ｚ]{4,}", title):
        flags.append("english_mixed")
    elif any(re.search(r"[A-Za-zＡ-Ｚａ-ｚ]{4,}", n) for n in names):
        flags.append("english_mixed")
    flags = sorted(set(flags))

    notes = []
    if comma_form:
        notes.append("著者名はソースの「姓, 名」形式のまま保持（基本形「姓 名」と異なる。書式調整は Phase 2 派生ファイルで実施）")
    if qualifier_stripped:
        notes.append("CiNii の著者末尾の同名識別修飾（例「(内科学)」）を除去")

    crid = re.search(r"crid/(\d+)", url)
    prov = "cinii-" + (crid.group(1) if crid else str(abs(hash(url)) % 10**9))

    return {
        "provisional_key": prov,
        "entry_type": "book",
        "bibtex_fields": bf,
        "discipline": disc,
        "subfield": None,
        "difficulty_flags": flags,
        "source_name": "CiNii Research OpenSearch (Books)",
        "source_url": url,
        "retrieved_at": datetime.now(JST).isoformat(timespec="seconds"),
        "notes": "; ".join(notes),
    }


def main() -> None:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    ndl_isbns = load_ndl_isbns()
    print(f"loaded {len(ndl_isbns)} NDL ISBNs to exclude")

    pool: dict[str, dict] = {}
    isbn_seen: set[str] = set(ndl_isbns)
    disc_count = {"人文社会": 0, "理工": 0, "医学生命": 0}

    for disc, queries in SUBJECT_QUERIES.items():
        for q in queries:
            if sum(disc_count.values()) >= TARGET_TOTAL or disc_count[disc] >= DISC_CAP[disc]:
                break
            added = 0
            for start in WINDOW_STARTS:
                if added >= PER_QUERY_MAX or disc_count[disc] >= DISC_CAP[disc]:
                    break
                try:
                    data, live = fetch(q, start)
                except Exception as e:  # noqa: BLE001
                    print(f"  ! fetch failed {q}@{start}: {e}", file=sys.stderr)
                    time.sleep(SLEEP)
                    continue
                for item in data.get("items", []):
                    if added >= PER_QUERY_MAX:
                        break
                    try:
                        parsed = parse_item(item, disc)
                    except Exception as e:  # noqa: BLE001
                        print(f"  ! parse error ({q}): {e}", file=sys.stderr)
                        continue
                    if not parsed:
                        continue
                    bfp = parsed["bibtex_fields"]
                    excluded, why = screen_book(bfp["title"], bfp.get("publisher", ""), bfp.get("series"))
                    if excluded:
                        continue
                    isbn = re.sub(r"[-\s]", "", parsed["bibtex_fields"]["isbn"])
                    if isbn in isbn_seen:
                        continue
                    if parsed["provisional_key"] in pool:
                        continue
                    if disc_count[disc] >= DISC_CAP[disc]:
                        break
                    pool[parsed["provisional_key"]] = parsed
                    isbn_seen.add(isbn)
                    disc_count[disc] += 1
                    added += 1
                    if sum(disc_count.values()) >= TARGET_TOTAL:
                        break
                if live:
                    time.sleep(SLEEP)
                if sum(disc_count.values()) >= TARGET_TOTAL:
                    break
            print(f"  {disc:6s} q={q}: +{added} (totals {disc_count})")
        if sum(disc_count.values()) >= TARGET_TOTAL:
            break

    records = list(pool.values())
    out = OUT_DIR / "records.jsonl"
    with out.open("w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    from collections import Counter
    n_flag = sum(1 for r in records if r["difficulty_flags"])
    fc = Counter(fl for r in records for fl in r["difficulty_flags"])
    print(f"\nCiNii Books collected {len(records)} records -> {out}")
    print(f"  discipline: {disc_count}")
    print(f"  with >=1 difficulty flag: {n_flag} ({100*n_flag/max(len(records),1):.0f}%)")
    print(f"  flag histogram: {dict(fc)}")


if __name__ == "__main__":
    main()
