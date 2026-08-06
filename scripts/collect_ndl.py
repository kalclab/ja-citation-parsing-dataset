#!/usr/bin/env python3
"""Collect @book records from the NDL Search SRU API (145 target).

Dependencies: Python stdlib only (urllib, xml/regex). Run with:
    uv run scripts/collect_ndl.py
(No third-party deps, so plain `python3 scripts/collect_ndl.py` also works.)

Strategy
--------
NDL's default SRU sort is by title reading, which surfaces low-quality material
(local reports, children's/general books, ISBN-less pamphlets). To obtain
genuine academic books we query by *academic publisher* (`publisher=...`),
which reliably returns scholarly monographs/textbooks with ISBNs. Publishers are
grouped by discipline to steer the stratification, but the final `discipline`
label for each record is derived from its actual NDC classification, not from
the query bucket -- so labels stay accurate even when a publisher crosses fields.

Quality gates:
  - materialType must be Book (dcndl:materialType / description "type : book").
  - Title must contain a Japanese character (drop pure-English / romaji books).
  - ISBN must be present (proxy for a properly published academic book).
  - audience must not be 児童 (drop children's books).

Cleaning rules resolved from the Phase 0-A survey observations:
  - Duplicate title fields: dcterms:title and dc:title/rdf:value carry the same
    string; we take dcterms:title as the primary title.
  - Publisher/place contamination ("飯塚 : 日本知能情報ファジィ学会" type): place is
    taken from dcndl:location when present; otherwise, if the publisher foaf:name
    contains " : ", it is split into address (before) + publisher (after).
  - Author names: book records give a slash-delimited 姓/名 in
    dcterms:creator/foaf:name (e.g. "天野/絵里子"); we convert "/" -> " " to match
    the contract's "姓 名" form. When only the concatenated dc:creator string is
    available (no structured foaf:Agent), we keep it as-is and record that in
    notes. Roles (編/著/訳/監修) are read from the dc:creator statements.

Output: data/interim/ndl/records.jsonl (intermediate schema). Raw SRU XML is
saved under data/raw/ndl/.
The script is idempotent: it rewrites records.jsonl deterministically each run.
"""
from __future__ import annotations

import html
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
RAW_DIR = ROOT / "data" / "raw" / "ndl"
OUT_DIR = ROOT / "data" / "interim" / "ndl"
SRU = "https://ndlsearch.ndl.go.jp/api/sru"
UA = "ja-citation-parsing-dataset (mailto:anonymous@example.org)"
JST = timezone(timedelta(hours=9))

TARGET_TOTAL = 145
# Per-discipline soft caps (sum >= target; we stop at TARGET_TOTAL overall while
# keeping each bucket near a third).
DISC_CAP = {"人文社会": 50, "理工": 50, "医学生命": 50}

# Academic publishers grouped by the discipline we EXPECT them to feed. The real
# discipline label comes from each record's NDC; grouping only steers sampling.
PUBLISHER_GROUPS = {
    "人文社会": [
        "有斐閣", "岩波書店", "勁草書房", "東京大学出版会", "ミネルヴァ書房",
        "名古屋大学出版会", "慶應義塾大学出版会", "弘文堂", "日本評論社", "白水社",
    ],
    "理工": [
        "共立出版", "朝倉書店", "オーム社", "コロナ社", "森北出版",
        "培風館", "丸善出版", "裳華房", "近代科学社",
    ],
    "医学生命": [
        "医学書院", "南江堂", "羊土社", "南山堂", "金原出版",
        "文光堂", "医歯薬出版", "中山書店", "メジカルビュー社",
    ],
}

WINDOW = 30            # records per SRU request
WINDOW_FRACTIONS = (0.0, 0.30, 0.60)  # sample across the title-reading sort
PER_PUB_MAX = 10       # cap contribution of any single publisher (diversity)
ROLE_TOKENS = [
    "編著", "編集", "編纂", "編訳", "監訳", "監修", "翻訳", "共著", "共編",
    "他著", "編", "訳", "著", "述", "撰",
]
EDITOR_ROLES = {"編", "編著", "編集", "編纂", "共編", "監修"}
TRANSLATOR_ROLES = {"訳", "編訳", "監訳", "翻訳"}
INST_SUFFIXES = (
    "会", "委員会", "研究所", "研究会", "センター", "学会", "省", "庁", "局",
    "大学", "機構", "協会", "編集部", "室", "部会", "会議", "本部", "財団",
)


def fetch(query: str, maximum: int = WINDOW, start: int = 1) -> str:
    params = {
        "operation": "searchRetrieve",
        "version": "1.2",
        "recordSchema": "dcndl",
        "maximumRecords": str(maximum),
        "startRecord": str(start),
        "query": query,
    }
    url = SRU + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=60) as resp:
        return resp.read().decode("utf-8")


def has_japanese(s: str) -> bool:
    return bool(re.search(r"[぀-ヿ㐀-鿿]", s))


def looks_institutional(name: str) -> bool:
    return any(name.endswith(suf) for suf in INST_SUFFIXES)


def strip_role(stmt: str) -> tuple[str, str | None]:
    """From a dc:creator statement return (name, role_token).

    Handles "小松佳代子 編著", "天野絵里子 [ほか]編集", "ポール・エリュアール／著".
    """
    s = stmt.strip()
    s = re.sub(r"\[[^\]]*\]", "", s)  # drop [ほか] / [著] annotations
    role = None
    # role after a slash: "ポール・エリュアール／著"
    m = re.search(r"／\s*(" + "|".join(ROLE_TOKENS) + r")\s*$", s)
    if m:
        role = m.group(1)
        s = s[: m.start()]
    else:
        m = re.search(r"\s+(" + "|".join(ROLE_TOKENS) + r")\s*$", s)
        if m:
            role = m.group(1)
            s = s[: m.start()]
    return s.strip(), role


def parse_creators(rec: str) -> tuple[list[dict], list[dict]]:
    """Return (structured_creators, dc_creator_statements).

    structured_creators: [{name, yomi}] from dcterms:creator/foaf:Agent.
    dc_creator_statements: [{name, role}] parsed from dc:creator strings
      (also split on ' ; ' to separate e.g. author + translator).
    """
    structured = []
    for block in re.findall(r"<dcterms:creator><foaf:Agent>(.*?)</foaf:Agent>", rec, re.S):
        nm = re.search(r"<foaf:name>(.*?)</foaf:name>", block, re.S)
        if not nm:
            continue
        yo = re.search(r"<dcndl:transcription>(.*?)</dcndl:transcription>", block, re.S)
        structured.append({"name": nm.group(1).strip(), "yomi": yo.group(1).strip() if yo else None})

    dc_stmts = []
    for raw in re.findall(r"<dc:creator>(.*?)</dc:creator>", rec, re.S):
        for part in re.split(r"\s*;\s*", raw.strip()):
            name, role = strip_role(part)
            if not name:
                continue
            # a single statement may list several persons before one role token,
            # e.g. "松永しのぶ, 井上奈智, 沢辺均 編". Split those on comma/、.
            subs = re.split(r"\s*[,、，]\s*", name)
            subs = [s for s in subs if len(s) >= 2]
            if len(subs) > 1:
                for s in subs:
                    dc_stmts.append({"name": s, "role": role})
            else:
                dc_stmts.append({"name": name, "role": role})
    return structured, dc_stmts


def normalize_name(name: str) -> tuple[str, bool]:
    """Convert 姓/名 -> 姓 名. Return (name, converted_from_slash)."""
    if "/" in name:
        return name.replace("/", " ").strip(), True
    return name.strip(), False


def role_for(name: str, dc_stmts: list[dict]) -> str | None:
    """Find role of a structured name by matching against dc:creator statements."""
    key = name.replace("/", "").replace(" ", "")
    for st in dc_stmts:
        if st["name"].replace(" ", "").startswith(key) or key.startswith(st["name"].replace(" ", "")):
            return st["role"]
    return None


NDC_URL_RE = re.compile(r"class/ndc(?:10|9|8)?/([0-9]+)")


def ndc_to_discipline(ndc_codes: list[str]) -> tuple[str | None, str | None]:
    """Map an NDC code to (discipline, subfield_hint). Uses the first usable code."""
    for code in ndc_codes:
        if not code or not code[0].isdigit():
            continue
        n = int(code[:3].ljust(3, "0")) if len(code) >= 1 else None
        c0 = code[0]
        # medicine / life science: 460-499 (biology, zoology, botany, medicine),
        # 490-499 medicine, 610-620 agriculture
        try:
            head = int(code[:3])
        except ValueError:
            head = int(c0) * 100
        if 460 <= head <= 499 or 610 <= head <= 629:
            return "医学生命", code
        if c0 in "45" or (600 <= head <= 699):
            # 400-459 pure science, 500-599 engineering, 630-699 industry/tech
            if c0 == "0":
                return "理工", code
            return "理工", code
        if c0 == "0":
            # 007 information science -> 理工; others (010 LIS, general) -> 人文社会
            if code.startswith("007"):
                return "理工", code
            return "人文社会", code
        if c0 in "12378 9":
            return "人文社会", code
        # fallback by first digit
        if c0 in "456":
            return "理工", code
        return "人文社会", code
    return None, None


def parse_record(rec: str, query_disc: str) -> dict | None:
    # material type gate
    if "ndltype/Book" not in rec and "type : book" not in rec:
        return None
    # title (primary = dcterms:title)
    tm = re.search(r"<dcterms:title>(.*?)</dcterms:title>", rec, re.S)
    if not tm:
        return None
    title = tm.group(1).strip()
    if not has_japanese(title):
        return None
    # audience filter
    aud = re.search(r"<dcterms:audience>(.*?)</dcterms:audience>", rec, re.S)
    if aud and "児童" in aud.group(1):
        return None
    # ISBN gate
    isbns = re.findall(r'terms/ISBN">([^<]+)', rec)
    if not isbns:
        return None
    isbn = isbns[0].strip()
    # book detail page URL (BibAdminResource about)
    am = re.search(r"<dcndl:BibAdminResource rdf:about=\"([^\"]+)\"", rec)
    url = am.group(1) if am else None
    if not url:
        return None
    # year
    year = None
    iss = re.findall(r"<dcterms:issued[^>]*>([^<]+)", rec)
    for v in iss:
        ym = re.search(r"(\d{4})", v)
        if ym:
            year = ym.group(1)
            break
    date_raw = re.findall(r"<dcterms:date>([^<]+)", rec)
    if not year:
        for v in date_raw:
            ym = re.search(r"(\d{4})", v)
            if ym:
                year = ym.group(1)
                break
    if not year:
        return None
    # publisher + place
    pubname = re.search(r"<dcterms:publisher><foaf:Agent>\s*<foaf:name>(.*?)</foaf:name>", rec, re.S)
    loc = re.search(r"<dcndl:location>(.*?)</dcndl:location>", rec, re.S)
    publisher = pubname.group(1).strip() if pubname else None
    address = None
    if publisher and " : " in publisher:
        address, publisher = [p.strip() for p in publisher.split(" : ", 1)]
    if loc:
        address = re.sub(r"[\[\]〔〕]", "", loc.group(1)).strip() or address
    if not publisher:
        return None
    # creators / roles
    structured, dc_stmts = parse_creators(rec)
    notes = []
    authors, editors, translators = [], [], []
    inst_flag = False
    if structured:
        for c in structured:
            nm, converted = normalize_name(c["name"])
            role = role_for(c["name"], dc_stmts)
            if looks_institutional(nm.replace(" ", "")):
                inst_flag = True
            if role in TRANSLATOR_ROLES:
                translators.append(nm)
            elif role in EDITOR_ROLES:
                editors.append(nm)
            else:
                authors.append(nm)
        if any("/" in c["name"] for c in structured):
            notes.append("著者名はソースで「姓/名」形式のためスラッシュを半角スペースに変換")
    else:
        # fall back to dc:creator concatenated names (no 姓名 boundary available)
        for st in dc_stmts:
            nm = st["name"]
            if looks_institutional(nm.replace(" ", "")):
                inst_flag = True
            if st["role"] in TRANSLATOR_ROLES:
                translators.append(nm)
            elif st["role"] in EDITOR_ROLES:
                editors.append(nm)
            else:
                authors.append(nm)
        if authors or editors or translators:
            notes.append("構造化著者(foaf:name)が無く dc:creator の連結表記(姓名境界なし)を保持")
    # dedup preserving order; a person credited as both editor and author (common
    # in edited volumes) is kept only as editor.
    def _dedup(seq):
        seen, out = set(), []
        for x in seq:
            if x not in seen:
                seen.add(x)
                out.append(x)
        return out
    editors = _dedup(editors)
    translators = _dedup(translators)
    authors = _dedup([a for a in authors if a not in set(editors)])
    if not (authors or editors):
        return None
    # yomi (title reading) from dc:title block
    yomi = None
    tt = re.search(
        r"<dc:title><rdf:Description>\s*<rdf:value>.*?</rdf:value>\s*<dcndl:transcription>(.*?)</dcndl:transcription>",
        rec, re.S,
    )
    if tt:
        yomi = tt.group(1).strip()
    # series / volume. These elements may be a plain string OR an
    # rdf:Description wrapper (<rdf:value> + <dcndl:transcription>); take the value.
    def _field(tag: str):
        m = re.search(rf"<dcndl:{tag}>(.*?)</dcndl:{tag}>", rec, re.S)
        if not m:
            return None
        inner = m.group(1)
        v = re.search(r"<rdf:value>(.*?)</rdf:value>", inner, re.S)
        text = (v.group(1) if v else inner).strip()
        return text or None

    series_v = _field("seriesTitle")
    volume_v = _field("volume")
    edition_v = _field("edition")
    # NDC -> discipline
    ndc_codes = NDC_URL_RE.findall(rec)
    disc, sub_ndc = ndc_to_discipline(ndc_codes)
    if disc is None:
        disc = query_disc  # fallback to query bucket
        sub_ndc = None

    # build bibtex_fields
    bf: dict[str, str] = {}
    if authors:
        bf["author"] = " and ".join(authors)
    if editors:
        bf["editor"] = " and ".join(editors)
    bf["title"] = title
    bf["publisher"] = publisher
    bf["year"] = year
    if address:
        bf["address"] = address
    if isbn:
        bf["isbn"] = isbn
    if series_v:
        bf["series"] = series_v
    if volume_v:
        bf["volume"] = volume_v
    if edition_v:
        bf["edition"] = edition_v
    if translators:
        bf["translator"] = " and ".join(translators)
    if yomi:
        bf["yomi"] = yomi

    # difficulty flags
    flags = []
    if re.search(r"\s:\s|――|―|--", title) or " : " in title:
        flags.append("subtitle")
    if editors or any(st["role"] in EDITOR_ROLES for st in dc_stmts):
        flags.append("edited_volume")
    if translators or any(st["role"] in TRANSLATOR_ROLES for st in dc_stmts):
        flags.append("translated")
    if inst_flag:
        flags.append("institutional_author")
    if bf.get("volume") or re.search(r"第\s*[0-9０-９一二三四五六七八九十]+\s*[巻册冊]", title):
        flags.append("nonstandard_volume")
    if re.search(r"明治|大正|昭和|平成|令和", " ".join(date_raw)):
        flags.append("wareki")
    # english_mixed: a parallel English title ("... = English ..."), a substantial
    # Latin word (>=4 letters) in the title, or a Latin-script author name. Short
    # acronyms/single letters (R, AI, ICD) do not qualify on their own.
    if re.search(r"=\s*[A-Za-zＡ-Ｚａ-ｚ]", title) or re.search(r"[A-Za-zＡ-Ｚａ-ｚ]{4,}", title):
        flags.append("english_mixed")
    elif any(re.search(r"[A-Za-zＡ-Ｚａ-ｚ]{4,}", a) for a in authors + editors):
        flags.append("english_mixed")
    flags = sorted(set(flags))

    # provisional key from NDL bib id in URL
    kid = re.search(r"/books/([^/#\"]+)", url)
    prov = "ndl-" + (kid.group(1) if kid else str(abs(hash(url)) % 10**9))

    return {
        "provisional_key": prov,
        "entry_type": "book",
        "bibtex_fields": bf,
        "discipline": disc,
        "subfield": f"NDC{sub_ndc}" if sub_ndc else None,
        "difficulty_flags": flags,
        "source_name": "NDL Search SRU (dcndl)",
        "source_url": url,
        "retrieved_at": datetime.now(JST).isoformat(timespec="seconds"),
        "notes": "; ".join(notes) if notes else "",
    }


def publisher_matches(record_pub: str, queried: str) -> bool:
    """NDL's publisher index also matches distributors, so a query for an academic
    publisher can return books it merely distributes (e.g. 丸善出版 -> シオン mooks).
    Keep a record only when its own publisher name matches the queried one."""
    a = re.sub(r"[\s\[\]（）:：　]", "", record_pub)
    b = re.sub(r"[\s\[\]（）:：　]", "", queried)
    return b in a or a in b


def candidates_for_publisher(pub: str, group: str) -> list[dict]:
    """Fetch several offset windows spread across the title-reading sort and return
    parsed, publisher-matched, qualifying records for one publisher."""
    out: dict[str, dict] = {}
    total = None
    for frac in WINDOW_FRACTIONS:
        start = 1 if total is None else max(1, int(total * frac))
        try:
            xml = fetch(f"mediatype=books AND publisher={pub}", maximum=WINDOW, start=start)
        except Exception as e:  # noqa: BLE001
            print(f"  ! fetch failed for {pub}@{start}: {e}", file=sys.stderr)
            time.sleep(2)
            continue
        (RAW_DIR / f"pub_{pub}_{start}.xml").write_text(xml, encoding="utf-8")
        if total is None:
            m = re.search(r"<numberOfRecords>(\d+)", xml)
            total = min(int(m.group(1)), 3000) if m else WINDOW
        for rd in re.findall(r"<recordData>(.*?)</recordData>", xml, re.S):
            rec = html.unescape(rd)
            try:
                parsed = parse_record(rec, group)
            except Exception as e:  # noqa: BLE001
                print(f"  ! parse error ({pub}): {e}", file=sys.stderr)
                continue
            if not parsed:
                continue
            if not publisher_matches(parsed["bibtex_fields"]["publisher"], pub):
                continue
            bfp = parsed["bibtex_fields"]
            excluded, why = screen_book(bfp["title"], bfp.get("publisher", ""), bfp.get("series"))
            if excluded:
                parsed["_screen_reason"] = why  # for optional logging
                continue
            out.setdefault(parsed["provisional_key"], parsed)
        time.sleep(1.5)
        if total is not None and total <= WINDOW:
            break  # small result set: one window already covered it
    return list(out.values())


def main() -> None:
    import random

    RAW_DIR.mkdir(parents=True, exist_ok=True)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    rng = random.Random(20260717)

    pool: dict[str, dict] = {}  # provisional_key -> record
    isbn_seen: set[str] = set()
    disc_count = {"人文社会": 0, "理工": 0, "医学生命": 0}

    for group, publishers in PUBLISHER_GROUPS.items():
        for pub in publishers:
            if sum(disc_count.values()) >= TARGET_TOTAL:
                break
            cands = candidates_for_publisher(pub, group)
            rng.shuffle(cands)  # avoid always taking alphabetically-first titles
            added = 0
            for parsed in cands:
                if added >= PER_PUB_MAX:
                    break
                d = parsed["discipline"]
                isbn = parsed["bibtex_fields"].get("isbn", "").replace("-", "")
                if isbn and isbn in isbn_seen:
                    continue
                if disc_count.get(d, 0) >= DISC_CAP.get(d, 50):
                    continue
                if parsed["provisional_key"] in pool:
                    continue
                pool[parsed["provisional_key"]] = parsed
                if isbn:
                    isbn_seen.add(isbn)
                disc_count[d] = disc_count.get(d, 0) + 1
                added += 1
                if sum(disc_count.values()) >= TARGET_TOTAL:
                    break
            print(f"  {group:6s} publisher={pub}: +{added} (totals {disc_count})")
        if sum(disc_count.values()) >= TARGET_TOTAL:
            break

    records = list(pool.values())
    out = OUT_DIR / "records.jsonl"
    with out.open("w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    # summary
    n_flag = sum(1 for r in records if r["difficulty_flags"])
    print(f"\nNDL collected {len(records)} records -> {out}")
    print(f"  discipline: {disc_count}")
    print(f"  with >=1 difficulty flag: {n_flag} ({100*n_flag/max(len(records),1):.0f}%)")
    from collections import Counter
    fc = Counter(fl for r in records for fl in r["difficulty_flags"])
    print(f"  flag histogram: {dict(fc)}")


if __name__ == "__main__":
    main()
