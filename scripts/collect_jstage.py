# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""J-Stage WebAPI collector for the ja-citation-parsing-dataset dataset (Phase 1).

Collects Japanese bibliographic metadata for `@article` and `@inproceedings`
records from the J-Stage search API (service=3, Atom+PRISM feed) and writes
contract-schema records to ``data/interim/jstage/records.jsonl``. Raw API
responses are cached under ``data/raw/jstage/`` (bibliographic metadata only;
no full text or abstracts are stored).

Run (no third-party dependencies -- stdlib only):

    uv run scripts/collect_jstage.py collect
    uv run scripts/collect_jstage.py qc      # sample-check 20 records vs source pages

Design notes
------------
* Stratified by discipline (人文社会 / 理工 / 医学生命, ~1/3 each for articles) and
  by learned society for proceedings, with a per-journal cap (<=30 for articles;
  pjsai/JSAI is deliberately central for proceedings per the task brief).
* Author names come from the ``<author><ja>`` block only. The Atom feed also
  carries an ``<en>`` block of romanised names -- reading all ``<name>`` tags
  indiscriminately would mix scripts, so we scope to the ja block.
* Filtering rules (drop entry if): no Japanese title, or no Japanese author
  (this also removes proceedings "session header" pseudo-entries that carry no
  author, e.g. old aamjsfst/jjrtsuppl collection headers).
* Notation is preserved as-is (full-width punctuation, 中黒, 波ダッシュ). The only
  transform is ``html.unescape`` when a stray HTML entity is present; that is
  recorded in ``notes``.
* Author format is already "姓 名" (space-separated) in J-Stage, matching the
  contract, so no author-format conversion is needed for this source.

Cleaning rules (derived from QC)
---------------------------------------------------------
* Skip entries whose ja author list is empty (proceedings session headers).
* Treat a whitespace-only ``prism:issn`` (pjsai returns spaces) as absent.
* Build ``pages`` from startingPage/endingPage; emit a single page when the two
  coincide or the end is missing. Non-numeric page labels (e.g. "4F11") are kept
  verbatim and flagged ``page_style``.
* ``html.unescape`` titles/journals only when an entity is detected; note it.
"""

from __future__ import annotations

import argparse
import html
import json
import random
import re
import time
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path
from xml.etree import ElementTree as ET

# --------------------------------------------------------------------------- #
# Constants & configuration
# --------------------------------------------------------------------------- #

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "data" / "raw" / "jstage"
INTERIM_DIR = ROOT / "data" / "interim" / "jstage"
QC_REPORT = ROOT / "reports" / "qc" / "jstage.md"

API_ENDPOINT = "https://api.jstage.jst.go.jp/searchapi/do"
USER_AGENT = "ja-citation-parsing-dataset (mailto:anonymous@example.org)"
REQUEST_WAIT_SEC = 1.5  # polite delay between requests (contract: 1-2 s)
POOL_SIZE = 200  # entries fetched per journal, evenly sampled down to target
JST = timezone(timedelta(hours=9))

NS = {
    "atom": "http://www.w3.org/2005/Atom",
    "prism": "http://prismstandard.org/namespaces/basic/2.0/",
    "opensearch": "http://a9.com/-/spec/opensearch/1.1/",
}

# Journals to sample. cdjournal codes and disciplines confirmed by live probes
# against the J-Stage API on 2026-07-17.
JOURNALS: list[dict] = [
    # --- @article: 人文社会 (~67) ---
    dict(cdjournal="jsr", entry_type="article", discipline="人文社会",
         subfield="社会学", target=24),
    dict(cdjournal="jjpsy", entry_type="article", discipline="人文社会",
         subfield="心理学", target=23),
    dict(cdjournal="jjep", entry_type="article", discipline="人文社会",
         subfield="教育心理学", target=20),
    # --- @article: 理工 (~67) ---
    dict(cdjournal="butsuri", entry_type="article", discipline="理工",
         subfield="物理学", target=24),
    dict(cdjournal="transjsme", entry_type="article", discipline="理工",
         subfield="機械工学", target=23),
    dict(cdjournal="kakoronbunshu1953", entry_type="article", discipline="理工",
         subfield="化学工学", target=20),
    # --- @article: 医学生命 (~66) ---
    dict(cdjournal="jami", entry_type="article", discipline="医学生命",
         subfield="医療情報学", target=24),
    dict(cdjournal="naika", entry_type="article", discipline="医学生命",
         subfield="内科学", target=22),
    dict(cdjournal="jans", entry_type="article", discipline="医学生命",
         subfield="看護学", target=20),
    # --- @inproceedings: JSAI-centred, 5 societies (130) ---
    dict(cdjournal="pjsai", entry_type="inproceedings", discipline="理工",
         subfield="人工知能 (JSAI 全国大会)", target=50),
    dict(cdjournal="esj", entry_type="inproceedings", discipline="医学生命",
         subfield="生態学 (日本生態学会大会)", target=28),
    dict(cdjournal="ieijac", entry_type="inproceedings", discipline="理工",
         subfield="照明工学 (照明学会全国大会)", target=22),
    dict(cdjournal="jams", entry_type="inproceedings", discipline="人文社会",
         subfield="経営システム (日本経営システム学会)", target=15),
    dict(cdjournal="proee2003", entry_type="inproceedings", discipline="理工",
         subfield="地震工学 (地震工学研究発表会)", target=15),
]

# difficulty_flags detection -------------------------------------------------
LATIN_RUN = re.compile(r"[A-Za-z]{2,}")
SUBTITLE_MARKERS = ("：", "；", "—", "―", "‐", "〜", "~", ":", "──", "――")
WAREKI = ("令和", "平成", "昭和", "大正", "明治")
INST_KEYWORDS = ("委員会", "研究会", "学会", "機構", "協会", "事務局",
                 "編集部", "ワーキンググループ", "研究班", "調査会")
NUMERIC = re.compile(r"^\d+$")
ENTITY = re.compile(r"&(?:[a-zA-Z]+|#\d+|#x[0-9a-fA-F]+);")
TAG = re.compile(r"</?[A-Za-z][A-Za-z0-9]*\s*/?>")


# --------------------------------------------------------------------------- #
# HTTP
# --------------------------------------------------------------------------- #

def _get(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=60) as resp:
        return resp.read().decode("utf-8")


def fetch_journal_feed(cdjournal: str, count: int) -> str:
    params = urllib.parse.urlencode(
        {"service": 3, "cdjournal": cdjournal, "start": 1, "count": count}
    )
    url = f"{API_ENDPOINT}?{params}"
    xml = _get(url)
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    (RAW_DIR / f"{cdjournal}.xml").write_text(xml, encoding="utf-8")
    return xml


PAGE_META_CACHE = RAW_DIR / "page_meta.json"


def _load_page_cache() -> dict:
    if PAGE_META_CACHE.exists():
        return json.loads(PAGE_META_CACHE.read_text(encoding="utf-8"))
    return {}


def _save_page_cache(cache: dict) -> None:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    PAGE_META_CACHE.write_text(
        json.dumps(cache, ensure_ascii=False, indent=1), encoding="utf-8"
    )


# citation_* meta tags we persist. Deliberately bibliographic-only -- the page
# body/abstract is never stored (contract: 本文・抄録は保存しない).
_META_KEEP = (
    "citation_title", "citation_author", "citation_firstpage",
    "citation_lastpage", "citation_doi", "citation_publication_date",
    "citation_online_date", "citation_journal_title", "citation_volume",
    "citation_issue",
)


def fetch_page_meta(url: str, cache: dict) -> dict:
    """Return bibliographic citation_* meta for an article page (cached)."""
    if url in cache:
        return cache[url]
    try:
        page = _get(url)
        meta = {k: v for k, v in _extract_meta(page).items() if k in _META_KEEP}
    except Exception as exc:  # network hiccup -> empty, retry on next run
        print(f"  ! page fetch failed {url}: {exc}")
        meta = {}
    cache[url] = meta
    time.sleep(REQUEST_WAIT_SEC)
    return meta


def fix_missing_authors(records: list[dict], cache: dict) -> int:
    """Repair author lists that dropped foreign co-authors. The search API's ja
    block omits authors who have no Japanese-name form, so a partially-foreign
    paper loses co-authors. The article page's ``citation_author`` is the
    authoritative ordered list -- and already mixes scripts correctly (Japanese
    where available, romanised otherwise), exactly the desired output. We adopt
    it only when it lists strictly MORE authors than we captured, so
    English-primary journals (whose citation_author is fully romanised but same
    length as our Japanese list) keep their preferred Japanese names."""
    n = 0
    for rec in records:
        meta = fetch_page_meta(rec["source_url"], cache)
        page_authors = [a.strip() for a in meta.get("citation_author", []) if a.strip()]
        page_authors = [html.unescape(a) for a in page_authors]
        cur = rec["bibtex_fields"]["author"].split(" and ")
        if len(page_authors) > len(cur):
            rec["bibtex_fields"]["author"] = " and ".join(page_authors)
            note = (f"外国人共著者が API の ja 著者ブロックから欠落していたため、"
                    f"著者リストを論文ページの citation_author で補完 "
                    f"({len(cur)}名→{len(page_authors)}名)")
            rec["notes"] = "; ".join(p for p in (rec["notes"], note) if p)
            fl = set(rec["difficulty_flags"])
            if any(LATIN_RUN.search(a) for a in page_authors):
                fl.add("english_mixed")
            rec["difficulty_flags"] = sorted(fl)
            n += 1
    return n


def enrich_subtitles(records: list[dict], cache: dict) -> int:
    """Recover subtitles the search API drops, from the article page's Japanese
    ``citation_title``. Guarded by a strict prefix test so English-primary
    titles (whose citation_title is English) are left as the API's Japanese
    main title rather than being overwritten."""
    n = 0
    for rec in records:
        meta = fetch_page_meta(rec["source_url"], cache)
        ct = meta.get("citation_title", [])
        full = html.unescape(ct[0]).strip() if ct else ""
        cur = rec["bibtex_fields"]["title"]
        if full and full != cur and full.startswith(cur) and len(full) > len(cur):
            rec["bibtex_fields"]["title"] = full
            note = ("副題を J-Stage 論文ページの citation_title から補完 "
                    "(検索 API は主題のみ返すため)")
            rec["notes"] = "; ".join(p for p in (rec["notes"], note) if p)
            fl = set(rec["difficulty_flags"])
            if any(m in full for m in SUBTITLE_MARKERS):
                fl.add("subtitle")
            if LATIN_RUN.search(full):
                fl.add("english_mixed")
            rec["difficulty_flags"] = sorted(fl)
            n += 1
    return n


# --------------------------------------------------------------------------- #
# Parsing
# --------------------------------------------------------------------------- #

def _text(el) -> str:
    return (el.text or "").strip() if el is not None else ""


def _clean(value: str, notes: list[str], label: str) -> str:
    """Unescape stray HTML entities and strip embedded presentation markup
    (e.g. ``<I>`` around Latin species names, ``<SUB>`` in CO<SUB>2</SUB>).
    These are display tags, not bibliographic content -- the article page's
    citation_title carries the same text tag-free -- so they must not leak into
    the citation string. Both transforms are recorded in notes."""
    if not value:
        return value
    if ENTITY.search(value):
        new = html.unescape(value)
        if new != value:
            notes.append(f"{label} の HTML エンティティをアンエスケープ")
            value = new
    if TAG.search(value):
        value = TAG.sub("", value)
        notes.append(f"{label} の埋め込み HTML タグ (例 <I>/<SUB>) を除去")
    return value


def parse_entries(xml_text: str) -> list[dict]:
    """Extract raw fields from an Atom+PRISM feed into plain dicts."""
    root = ET.fromstring(xml_text)
    entries = []
    for entry in root.findall("atom:entry", NS):
        ja_title = _text(entry.find("atom:article_title/atom:ja", NS))
        en_title = _text(entry.find("atom:article_title/atom:en", NS))
        ja_authors = [
            _text(n) for n in entry.findall("atom:author/atom:ja/atom:name", NS)
        ]
        ja_authors = [a for a in ja_authors if a]
        en_authors = [
            _text(n) for n in entry.findall("atom:author/atom:en/atom:name", NS)
        ]
        journal = _text(entry.find("atom:material_title/atom:ja", NS))
        link = _text(entry.find("atom:article_link/atom:ja", NS))
        issn = _text(entry.find("prism:issn", NS))
        entries.append(dict(
            ja_title=ja_title,
            en_title=en_title,
            ja_authors=ja_authors,
            en_authors=[a for a in en_authors if a],
            journal=journal,
            link=link,
            issn=issn if issn and issn.strip() else "",
            volume=_text(entry.find("prism:volume", NS)),
            number=_text(entry.find("prism:number", NS)),
            start_page=_text(entry.find("prism:startingPage", NS)),
            end_page=_text(entry.find("prism:endingPage", NS)),
            year=_text(entry.find("atom:pubyear", NS)),
            doi=_text(entry.find("prism:doi", NS)),
        ))
    return entries


# --------------------------------------------------------------------------- #
# Record building
# --------------------------------------------------------------------------- #

def _pages(start: str, end: str) -> str:
    start, end = start.strip(), end.strip()
    if not start:
        return ""
    if end and end != start:
        return f"{start}-{end}"
    return start


def _detect_flags(entry_type: str, fields: dict, raw: dict,
                  author_names: list[str]) -> list[str]:
    flags: set[str] = set()
    title = fields.get("title", "")
    container = fields.get("journal") or fields.get("booktitle", "")
    # author_names: the individual names actually used (NOT the ' and '-joined
    # field, whose separator is Latin syntax).

    if any(m in title for m in SUBTITLE_MARKERS):
        flags.add("subtitle")
    # english_mixed: Latin-script content inside the Japanese bibliographic
    # fields themselves (English subtitle, romanised term, gene/acronym, etc.).
    if (LATIN_RUN.search(title) or LATIN_RUN.search(container)
            or any(LATIN_RUN.search(a) for a in author_names)):
        flags.add("english_mixed")
    if any(w in title for w in WAREKI):
        flags.add("wareki")
    if any(k in a for a in author_names for k in INST_KEYWORDS):
        flags.add("institutional_author")

    vol = fields.get("volume", "")
    if vol and not NUMERIC.match(vol):
        flags.add("nonstandard_volume")

    start = raw.get("start_page", "")
    if start and not NUMERIC.match(start):
        flags.add("page_style")

    return sorted(flags)


def build_record(raw: dict, cfg: dict, seq: int) -> dict | None:
    # Filter: require Japanese title and at least one Japanese author name.
    if not raw["ja_title"] or not raw["ja_authors"]:
        return None

    notes: list[str] = []
    title = _clean(raw["ja_title"], notes, "title")
    journal = _clean(raw["journal"], notes, "journal")

    # Default author list: the ja block, in "姓 名" form. This is complete for
    # the common all-Japanese case. Records with foreign co-authors (where the
    # ja block is a partial list) are repaired later from the article page's
    # citation_author meta -- see fix_missing_authors(); the ja/en Atom blocks
    # are structured too inconsistently to merge reliably on their own.
    author_names = raw["ja_authors"]
    authors = " and ".join(author_names)

    fields: dict[str, str] = {"author": authors, "title": title}
    entry_type = cfg["entry_type"]

    if entry_type == "article":
        fields["journal"] = journal
        if raw["volume"]:
            fields["volume"] = raw["volume"]
        if raw["number"] and raw["number"].strip():
            fields["number"] = raw["number"]
        pages = _pages(raw["start_page"], raw["end_page"])
        if pages:
            fields["pages"] = pages
        fields["year"] = raw["year"]
        if raw["issn"]:
            fields["issn"] = raw["issn"]
    else:  # inproceedings
        fields["booktitle"] = journal
        fields["year"] = raw["year"]
        pages = _pages(raw["start_page"], raw["end_page"])
        if pages:
            fields["pages"] = pages
        if raw["volume"]:
            fields["volume"] = raw["volume"]

    if raw["doi"]:
        fields["doi"] = raw["doi"]

    # source_url: DOI preferred, else the ja article page.
    if raw["doi"]:
        source_url = f"https://doi.org/{raw['doi']}"
    else:
        source_url = raw["link"]
    if not source_url:
        return None  # cannot verify existence -> drop (never fabricate)

    flags = _detect_flags(entry_type, fields, raw, author_names)

    return {
        "provisional_key": f"jstage-{seq:06d}",
        "entry_type": entry_type,
        "bibtex_fields": fields,
        "discipline": cfg["discipline"],
        "subfield": cfg["subfield"],
        "difficulty_flags": flags,
        "source_name": "J-Stage WebAPI",
        "source_url": source_url,
        "retrieved_at": datetime.now(JST).isoformat(timespec="seconds"),
        "notes": "; ".join(notes),
    }


def _even_sample(items: list, k: int) -> list:
    """Pick k evenly-spaced items to spread across volumes/years."""
    n = len(items)
    if n <= k:
        return items
    idx = sorted({round(i * (n - 1) / (k - 1)) for i in range(k)})
    return [items[i] for i in idx]


# --------------------------------------------------------------------------- #
# Commands
# --------------------------------------------------------------------------- #

def cmd_collect(_args) -> None:
    INTERIM_DIR.mkdir(parents=True, exist_ok=True)
    records: list[dict] = []
    seen_ids: set[str] = set()  # dedup by doi or link
    seq = 1

    for cfg in JOURNALS:
        cdj = cfg["cdjournal"]
        target = cfg["target"]
        xml = fetch_journal_feed(cdj, POOL_SIZE)
        raws = parse_entries(xml)
        # keep only entries that survive the filter, dedup, then even-sample.
        valid = []
        for raw in raws:
            key = raw["doi"] or raw["link"]
            if not raw["ja_title"] or not raw["ja_authors"] or not key:
                continue
            if key in seen_ids:
                continue
            seen_ids.add(key)
            valid.append(raw)
        chosen = _even_sample(valid, target)
        n_added = 0
        for raw in chosen:
            rec = build_record(raw, cfg, seq)
            if rec is None:
                continue
            records.append(rec)
            seq += 1
            n_added += 1
        print(f"[{cdj:20s}] {cfg['entry_type']:14s} "
              f"pool={len(raws):3d} valid={len(valid):3d} "
              f"target={target:3d} added={n_added:3d}")
        time.sleep(REQUEST_WAIT_SEC)

    if _args.enrich:
        cache = _load_page_cache()
        print(f"\nenriching from article pages "
              f"({len(records)} records, cache={len(cache)}) ...")
        n_authors = fix_missing_authors(records, cache)
        n_enriched = enrich_subtitles(records, cache)
        _save_page_cache(cache)
        print(f"  著者補完: {n_authors} records / subtitle補完: {n_enriched} records")

    out = INTERIM_DIR / "records.jsonl"
    with out.open("w", encoding="utf-8") as fh:
        for rec in records:
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")

    _print_summary(records)
    print(f"\nWrote {len(records)} records -> {out}")


def _print_summary(records: list[dict]) -> None:
    from collections import Counter
    by_type = Counter(r["entry_type"] for r in records)
    by_disc = Counter((r["entry_type"], r["discipline"]) for r in records)
    flagged = Counter(
        r["entry_type"] for r in records if r["difficulty_flags"]
    )
    print("\n=== summary ===")
    for t in ("article", "inproceedings"):
        n = by_type[t]
        f = flagged[t]
        pct = (100 * f / n) if n else 0
        print(f"  {t:14s} n={n:3d}  flagged={f:3d} ({pct:.0f}%)")
        for disc in ("人文社会", "理工", "医学生命"):
            c = by_disc[(t, disc)]
            if c:
                print(f"      {disc}: {c}")


def _extract_meta(page_html: str) -> dict:
    """Pull Highwire citation_* meta tags from a J-Stage article page."""
    meta: dict[str, list[str]] = {}
    for m in re.finditer(
        r'<meta\s+name="(citation_[^"]+)"\s+content="([^"]*)"', page_html
    ):
        meta.setdefault(m.group(1), []).append(m.group(2))
    return meta


def cmd_qc(args) -> None:
    records = [
        json.loads(line)
        for line in (INTERIM_DIR / "records.jsonl").read_text(
            encoding="utf-8"
        ).splitlines()
        if line.strip()
    ]
    rng = random.Random(args.seed)
    sample = rng.sample(records, min(args.n, len(records)))

    lines: list[str] = []
    mismatches = {"title": 0, "authors": 0, "year": 0,
                  "firstpage": 0, "doi": 0, "no_meta": 0}
    accepted = {"title": 0, "authors": 0}  # English-primary meta, JP kept
    mojibake = 0
    cjk = re.compile(r"[぀-ヿ一-鿿]")

    def _is_romaji(s: str) -> bool:
        return bool(LATIN_RUN.search(s)) and not cjk.search(s)

    for rec in records:  # mojibake scan over ALL records
        blob = json.dumps(rec, ensure_ascii=False)
        if "�" in blob:
            mojibake += 1

    for i, rec in enumerate(sample, 1):
        f = rec["bibtex_fields"]
        page = _get(rec["source_url"])
        time.sleep(REQUEST_WAIT_SEC)
        meta = _extract_meta(page)
        if not meta:
            mismatches["no_meta"] += 1
            lines.append(f"### {i}. {rec['provisional_key']} — meta なし (要目視)\n"
                         f"- source_url: {rec['source_url']}\n")
            continue

        row = [f"### {i}. {rec['provisional_key']} ({rec['entry_type']})",
               f"- source_url: {rec['source_url']}"]

        m_title = html.unescape(meta.get("citation_title", [""])[0]).strip()
        if m_title == f["title"].strip():
            status = "OK"
        elif _is_romaji(m_title) and cjk.search(f["title"]):
            status = "ACCEPTED (英語優先 meta・日本語主題を維持)"
            accepted["title"] += 1
        else:
            status = "DIFF"
            mismatches["title"] += 1
        row.append(f"- title: {status} | ours=`{f['title']}` | page=`{m_title}`")

        page_authors = [html.unescape(a).strip()
                        for a in meta.get("citation_author", []) if a.strip()]
        our_authors = f["author"].split(" and ")
        if page_authors == our_authors:
            status = "OK"
        elif (len(page_authors) == len(our_authors)
              and all(_is_romaji(a) for a in page_authors)):
            status = "ACCEPTED (英語優先 meta・日本語表記を維持)"
            accepted["authors"] += 1
        else:
            status = "DIFF"
            mismatches["authors"] += 1
        row.append(f"- authors: {status} | ours={our_authors} | page={page_authors}")

        m_year = ""
        for k in ("citation_publication_date", "citation_date",
                  "citation_online_date"):
            if k in meta:
                m_year = re.sub(r"\D.*$", "", meta[k][0])[:4]
                break
        ok_year = m_year == f.get("year", "")
        if not ok_year:
            mismatches["year"] += 1
        row.append(f"- year: {'OK' if ok_year else 'DIFF'} "
                   f"| ours={f.get('year')} | page={m_year}")

        m_fp = meta.get("citation_firstpage", [""])[0].strip()
        our_fp = f.get("pages", "").split("-")[0]
        ok_fp = (m_fp == our_fp) or (not m_fp and not our_fp)
        if not ok_fp:
            mismatches["firstpage"] += 1
        row.append(f"- firstpage: {'OK' if ok_fp else 'DIFF'} "
                   f"| ours={our_fp} | page={m_fp}")

        m_doi = meta.get("citation_doi", [""])[0].strip()
        ok_doi = (m_doi == f.get("doi", "")) or not m_doi
        if not ok_doi:
            mismatches["doi"] += 1
        row.append(f"- doi: {'OK' if ok_doi else 'DIFF'} "
                   f"| ours={f.get('doi')} | page={m_doi}")

        lines.append("\n".join(row) + "\n")

    QC_REPORT.parent.mkdir(parents=True, exist_ok=True)
    header = [
        "# J-Stage 収集 QC レポート",
        "",
        f"- 実行日時: {datetime.now(JST).isoformat(timespec='seconds')}",
        f"- 総レコード数: {len(records)}",
        f"- サンプル検査件数: {len(sample)} (seed={args.seed})",
        "- 検査方法: 各サンプルの source_url ページの Highwire "
        "`citation_*` meta タグと収集フィールドを突き合わせ",
        "",
        "## 集計",
        "",
        f"- 文字化け (U+FFFD) を含むレコード: {mojibake} / {len(records)}",
        "",
        "DIFF=要修正の不一致、ACCEPTED=英語優先ページ meta との既知の差異で"
        "日本語表記を意図的に維持したもの (不良ではない)。",
        "",
        "| 項目 | DIFF (要修正) | ACCEPTED (許容) |",
        "|---|---|---|",
        f"| title | {mismatches['title']} | {accepted['title']} |",
        f"| authors | {mismatches['authors']} | {accepted['authors']} |",
        f"| year | {mismatches['year']} | - |",
        f"| firstpage | {mismatches['firstpage']} | - |",
        f"| doi | {mismatches['doi']} | - |",
        f"| meta タグなし | {mismatches['no_meta']} | - |",
        "",
        "## クリーニング規則 (docstring と一致)",
        "",
        "- ja 著者名が空のエントリは除外 (予稿集のセッション見出し擬似エントリ)。",
        "- 空白のみの `prism:issn` (pjsai) は欠損扱い。",
        "- `pages` は startingPage/endingPage から構築。両者一致または end 欠損時は単一ページ。",
        "- 非数値ページ (例 `4F11`) は原表記のまま保持し `page_style` を付与。",
        "- HTML エンティティ検出時のみ `html.unescape` し notes に記録。",
        "- タイトル・誌名の埋め込み HTML タグ (種名の `<I>`、CO<SUB>2</SUB> 等) を除去し "
        "notes に記録 (表示用マークアップで書誌本文ではない)。本収集で 6 件。",
        "- 副題欠落の補完: 検索 API の `article_title` は主題のみ返すため、論文ページの "
        "`citation_title` がこちらの title を接頭辞に含みかつ長い場合はページ側を採用 "
        "(英語主題誌は接頭辞不一致で除外し日本語主題を維持)。notes 記録・subtitle/"
        "english_mixed フラグ再判定。本収集で 37 件補完。",
        "- 外国人共著者の欠落補完: ja 著者ブロックが一部著者を落とすため、論文ページの "
        "`citation_author` の著者数がこちらを上回る場合はページ側を採用 "
        "(ja 表記優先・無ければローマ字の順序を保持)。english_mixed 付与・notes 記録。"
        "本収集で 4 件補完。",
        "",
        "## サンプル明細",
        "",
    ]
    QC_REPORT.write_text("\n".join(header) + "\n".join(lines), encoding="utf-8")
    print(f"QC done. mojibake={mojibake} DIFF={mismatches} ACCEPTED={accepted}")
    print(f"Report -> {QC_REPORT}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)
    col = sub.add_parser("collect", help="collect records into interim jsonl")
    col.add_argument("--no-enrich", dest="enrich", action="store_false",
                     help="skip subtitle enrichment from article pages")
    col.set_defaults(enrich=True)
    qc = sub.add_parser("qc", help="sample-check records against source pages")
    qc.add_argument("--n", type=int, default=20)
    qc.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    if args.cmd == "collect":
        cmd_collect(args)
    elif args.cmd == "qc":
        cmd_qc(args)


if __name__ == "__main__":
    main()
