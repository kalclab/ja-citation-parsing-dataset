#!/usr/bin/env python3
"""Recover 姓/名 boundaries for NDL @book authors from authority records (task #9).

Dependencies: Python stdlib only. Run with:
    uv run scripts/enrich_name_boundaries.py

Problem
-------
130/145 NDL book records store personal author names in concatenated form
("友岡賛") because the collector reads the readable dc:creator statement. Splitting
by guesswork would be fabrication, so we recover the boundary from a verifiable
source: the NDL name-authority record.

Two facts make this strong and cheap:
  1. The NDL SRU bib record already embeds, per creator, an authority entity link
     and the authorised heading, e.g.
       <dcterms:creator><foaf:Agent rdf:about="http://id.ndl.go.jp/auth/entity/00386128">
         <foaf:name>友岡, 賛, 1958-</foaf:name></foaf:Agent></dcterms:creator>
     The comma form "友岡, 賛" IS the 姓/名 split, and the rdf:about is a verifiable
     authority URL. Because NDL's own cataloguing linked this creator to that
     entity in THIS record, the correspondence is "strong" (not a name-string
     guess). The original collector missed these only because its regex did not
     allow the rdf:about attribute on <foaf:Agent>. We re-parse the cached raw
     SRU XML here -- no new bib requests needed for the split.
  2. Fetching the authority record (id.ndl.go.jp/auth/ndlna/<ID>.rdf) adds the
     reading (dcndl:transcription "トモオカ, ススム") -> yomi, and independently
     re-confirms the split.

Matching rule (strong): an authority heading matches a concatenated name iff their
kana/kanji joined forms are equal (comma/space/birth-year removed). Order within a
record is irrelevant. If no authority heading in the SAME record matches a name,
that name is left UNRESOLVED (we do not guess; a mis-split is worse than a gap).
A future name-only search fallback would be recorded as "weak"; none is applied
here because the bib-embedded links already cover the large majority.

Output (does NOT modify records.jsonl): data/interim/enrich_names/name_boundaries.jsonl,
one line per NDL record that has >=1 concatenated personal name, with the requested
fields (provisional_key, author_original, author_split, yomi, authority_url) plus a
per-name `names` detail list and a `resolution` summary. Raw authority RDF is cached
under data/raw/ndl_auth/. Idempotent: reuses cached authority RDF, rewrites output.
"""
from __future__ import annotations

import html
import json
import re
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
NDL_JSONL = ROOT / "data" / "interim" / "ndl" / "records.jsonl"
RAW_NDL = ROOT / "data" / "raw" / "ndl"
RAW_AUTH = ROOT / "data" / "raw" / "ndl_auth"
RAW_SEARCH = ROOT / "data" / "raw" / "ndl_auth_search"
OUT_DIR = ROOT / "data" / "interim" / "enrich_names"
UA = "ja-citation-parsing-dataset (mailto:anonymous@example.org)"
SLEEP = 1.5

INST_SUFFIXES = (
    "会", "會", "委員会", "委員會", "研究所", "研究会", "研究會", "センター", "学会",
    "學會", "省", "庁", "局", "大学", "機構", "協会", "協會", "編集部", "室", "会議",
    "本部", "財団", "学院", "部", "課", "所", "会社", "社", "回路", "機関",
)


def is_personal(name: str) -> bool:
    """A concatenated (no-space) Japanese personal name worth splitting."""
    n = name.strip()
    if not n or " " in n:  # already spaced (foreign or pre-split) -> skip
        return False
    if re.search(r"[A-Za-zＡ-Ｚａ-ｚ]", n):  # romaji / western -> skip
        return False
    if any(n.endswith(suf) for suf in INST_SUFFIXES):  # institutional -> skip
        return False
    return True


def joined(s: str) -> str:
    """Comparison key: drop commas, spaces, and a trailing birth/death year range."""
    s = re.sub(r"[,，、]\s*\d{3,4}(-\d{0,4})?\s*$", "", s)  # trailing year
    return re.sub(r"[\s,，、]", "", s)


def heading_to_split(foaf_name: str) -> str:
    """'友岡, 賛, 1958-' -> '友岡, 賛' (drop trailing year, keep the 姓, 名 comma)."""
    s = foaf_name.strip()
    s = re.sub(r"[,，]\s*\d{3,4}(-\d{0,4})?-?\s*$", "", s)  # drop ', 1958-'
    return s.strip().rstrip(",").strip()


def parse_raw_authorities() -> dict[str, list[tuple[str, str]]]:
    """Map bib source_url -> [(authority_entity_url, foaf_name_heading), ...]."""
    idx: dict[str, list[tuple[str, str]]] = {}
    for f in sorted(RAW_NDL.glob("*.xml")):
        u = html.unescape(f.read_text(encoding="utf-8"))
        for rd in re.findall(r"<recordData>(.*?)</recordData>", u, re.S):
            am = re.search(r'<dcndl:BibAdminResource rdf:about="([^"]+)"', rd)
            if not am:
                continue
            url = am.group(1)
            creators = re.findall(
                r'<dcterms:creator><foaf:Agent rdf:about="'
                r'(http://id\.ndl\.go\.jp/auth/entity/[^"]+)">\s*'
                r"<foaf:name>(.*?)</foaf:name>",
                rd, re.S,
            )
            idx.setdefault(url, [(a, html.unescape(n).strip()) for a, n in creators])
    return idx


def _strip_year_comma(s: str) -> str:
    return re.sub(r"[,，]\s*\d{3,4}(-\d{0,4})?-?\s*$", "", s).strip().rstrip(",").strip()


def authority_detail(entity_url: str) -> tuple[str | None, str | None]:
    """Fetch the authority RDF (cached) and return (split, yomi):
      split: the prefLabel kanji heading '姓, 名' (birth year dropped);
      yomi:  the ja-Kana reading 'セイ メイ' (comma -> space, year dropped).
    """
    m = re.search(r"/entity/([A-Za-z0-9]+)", entity_url)
    if not m:
        return None, None
    aid = m.group(1)
    cache = RAW_AUTH / f"{aid}.rdf"
    if cache.exists():
        xml = cache.read_text(encoding="utf-8")
    else:
        url = f"https://id.ndl.go.jp/auth/ndlna/{aid}.rdf"
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                xml = resp.read().decode("utf-8")
        except Exception:  # noqa: BLE001
            return None, None
        cache.write_text(xml, encoding="utf-8")
        time.sleep(SLEEP)
    # split from the preferred label's literalForm (kanji, '姓, 名, 年'). The
    # prefLabel wraps an rdf:Description; its literalForm (the first one carrying a
    # comma) is the authorised 姓, 名 heading. altLabels come later.
    split = None
    pm = re.search(r"<xl:literalForm[^>]*>([^<]*[,，][^<]*)</xl:literalForm>", xml)
    if pm:
        split = _strip_year_comma(pm.group(1))
    # yomi from the ja-Kana transcription ('セイ, メイ, 年' -> 'セイ メイ')
    yomi = None
    for lang, val in re.findall(
        r'<ndl:transcription xml:lang="([^"]+)">(.*?)</ndl:transcription>', xml, re.S
    ):
        if lang == "ja-Kana" or (re.search(r"[ァ-ヶ]", val) and not re.search(r"[A-Za-z]", val)):
            yomi = re.sub(r"\s*[,，]\s*", " ", _strip_year_comma(val)).strip()
            break
    return split, yomi


def sparql_name_lookup(name: str) -> str | None:
    """Name-only (weak) fallback: return the authority entity URL iff EXACTLY one
    NDL authority record has this concatenated foaf:name. 0 or >1 (homonyms) -> None
    (a mis-split is worse than a gap). Results are cached for idempotency."""
    RAW_SEARCH.mkdir(parents=True, exist_ok=True)
    cache = RAW_SEARCH / (re.sub(r"[^\w]", "_", name) + ".json")
    if cache.exists():
        data = json.loads(cache.read_text(encoding="utf-8"))
    else:
        sparql = ('PREFIX foaf: <http://xmlns.com/foaf/0.1/> '
                  'SELECT ?s WHERE { ?s foaf:name "%s" }' % name.replace('"', ""))
        url = "https://id.ndl.go.jp/auth/ndla?query=" + urllib.parse.quote(sparql)
        req = urllib.request.Request(
            url, headers={"User-Agent": UA, "Accept": "application/sparql-results+json"})
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                data = json.loads(resp.read().decode("utf-8"))
        except Exception:  # noqa: BLE001
            return None
        cache.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        time.sleep(SLEEP)
    binds = data.get("results", {}).get("bindings", [])
    if len(binds) == 1:
        return binds[0]["s"]["value"]
    return None


def main() -> None:
    RAW_AUTH.mkdir(parents=True, exist_ok=True)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    auth_idx = parse_raw_authorities()
    records = [json.loads(l) for l in NDL_JSONL.open(encoding="utf-8")]

    out_lines = []
    n_records = n_name_total = n_strong = n_weak = n_yomi = 0
    for r in records:
        bf = r["bibtex_fields"]
        headings = auth_idx.get(r["source_url"], [])
        # build a lookup: joined-key -> (authority_url, split)
        hmap: dict[str, tuple[str, str]] = {}
        for aurl, fname in headings:
            hmap.setdefault(joined(fname), (aurl, heading_to_split(fname)))

        rec_names = []
        touched = False
        for field in ("author", "editor"):
            val = bf.get(field)
            if not val:
                continue
            for name in val.split(" and "):
                name = name.strip()
                if not is_personal(name):
                    continue
                touched = True
                n_name_total += 1
                hit = hmap.get(joined(name))
                if hit:
                    # strong: authority link embedded in THIS bib record.
                    aurl, split = hit
                    _, yomi = authority_detail(aurl)
                    if yomi:
                        n_yomi += 1
                    rec_names.append({
                        "field": field, "original": name, "split": split,
                        "yomi": yomi, "authority_url": aurl, "match": "strong",
                    })
                    n_strong += 1
                    continue
                # weak: name-only authority search, accepted only if unique.
                aurl = sparql_name_lookup(name)
                if aurl:
                    split, yomi = authority_detail(aurl)
                    if split and joined(split) == joined(name):  # guard: same person kanji
                        if yomi:
                            n_yomi += 1
                        rec_names.append({
                            "field": field, "original": name, "split": split,
                            "yomi": yomi, "authority_url": aurl, "match": "weak",
                        })
                        n_weak += 1
                        continue
                rec_names.append({
                    "field": field, "original": name, "split": None,
                    "yomi": None, "authority_url": None, "match": "unresolved",
                })
        if not touched:
            continue
        n_records += 1
        resolved = [n for n in rec_names if n["match"] in ("strong", "weak")]
        resolution = ("full" if len(resolved) == len(rec_names)
                      else "partial" if resolved else "none")
        # convenience joined fields over the AUTHOR field (Phase 2 applies per field)
        au_names = [n for n in rec_names if n["field"] == "author"]
        def _join(key, fallback_key="original"):
            return " and ".join((n[key] or n[fallback_key]) for n in au_names)
        out_lines.append({
            "provisional_key": r["provisional_key"],
            "author_original": bf.get("author", ""),
            "author_split": _join("split") if au_names else "",
            "yomi": " and ".join(n["yomi"] for n in au_names if n["yomi"]) or None,
            "authority_url": [n["authority_url"] for n in rec_names if n["authority_url"]],
            "resolution": resolution,
            "names": rec_names,
        })

    out = OUT_DIR / "name_boundaries.jsonl"
    with out.open("w", encoding="utf-8") as f:
        for line in out_lines:
            f.write(json.dumps(line, ensure_ascii=False) + "\n")

    print(f"enrichment records written: {n_records} -> {out}")
    print(f"personal concatenated name mentions: {n_name_total}")
    print(f"  strong (authority-linked split): {n_strong} "
          f"({100*n_strong/max(n_name_total,1):.0f}%)")
    print(f"  weak (name-search only): {n_weak}")
    print(f"  unresolved: {n_name_total - n_strong - n_weak}")
    print(f"  with yomi: {n_yomi}")
    from collections import Counter
    print("  resolution per record: " + str(dict(Counter(l["resolution"] for l in out_lines))))


if __name__ == "__main__":
    main()
