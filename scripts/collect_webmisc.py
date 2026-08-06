#!/usr/bin/env python
"""Collect real Japanese web pages as @misc records for the cite-parse dataset.

Design (anti-fabrication): every recorded URL is obtained by
  fetch(seed listing page) -> extract candidate links from the returned HTML
  -> fetch(each candidate) -> require HTTP 200 and a usable <title>/<h1>.
No URL is written from model memory. Seeds that 404/403 are logged and skipped.

Politeness: shared UA carrying a mailto contact, 1.5 s wait between requests,
and we avoid the robots.txt Disallow paths observed on 2026-07-17 (documented in
reports/qc/webmisc_targets.md). Only bibliographic metadata (title/url/org/year)
is stored; no page body or PDF content is saved.

Cleaning rules (also in README):
  - title is kept verbatim from <title> (falls back to first <h1>) -- the page's
    own表記 including any "｜省庁名" suffix. Not normalised.
  - year is derived from 令和/平成/昭和 or a西暦 in the title when present; the
    original wareki表記 stays in the title and the `wareki` flag is set.
  - institutional author (省庁・学協会 etc.) goes in `author`; `institutional_author`
    flag is set accordingly.

Usage:  uv run scripts/collect_webmisc.py [--only NAME[,NAME...]] [--probe NAME]
"""
from __future__ import annotations
import argparse, gzip, hashlib, json, re, sys, time
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urljoin, urlparse
import requests

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw" / "webmisc"
INTERIM = ROOT / "data" / "interim" / "webmisc"
RAW.mkdir(parents=True, exist_ok=True)
INTERIM.mkdir(parents=True, exist_ok=True)

UA = "ja-citation-parsing-dataset (mailto:anonymous@example.org)"
URLDATE = "2026-07-17"
WAIT = 1.5
TIMEOUT = 30

session = requests.Session()
session.headers.update({"User-Agent": UA})

# robots.txt Disallow paths to honour (observed 2026-07-17). Host -> prefixes.
ROBOTS_DISALLOW = {
    "www.mhlw.go.jp": ["/cgi-bin/", "/images/", "/topics/bukyoku/iyaku/kaisyu/"],
    "www.stat.go.jp": ["/library/opac/"],
    "www.env.go.jp": ["/cgi-bin/"],
    "www.ppc.go.jp": ["/common/", "/hardcore/", "/hc_config/", "/image/", "/webadmin/"],
    "www.ipsj.or.jp": ["/prms/", "/pms/", "/sample/", "/clickm/"],
    "kotobank.jp": ["/search"],
}


def robots_ok(url: str) -> bool:
    p = urlparse(url)
    for pref in ROBOTS_DISALLOW.get(p.netloc, []):
        if p.path.startswith(pref):
            return False
    return True


_last = {"t": 0.0}


def polite_get(url: str):
    dt = time.time() - _last["t"]
    if dt < WAIT:
        time.sleep(WAIT - dt)
    _last["t"] = time.time()
    return session.get(url, timeout=TIMEOUT, allow_redirects=True)


def extract_links(html: str, base: str):
    out = []
    for m in re.finditer(r'<a[^>]+href="([^"#]+)"[^>]*>(.*?)</a>', html, re.S | re.I):
        href = urljoin(base, m.group(1).strip())
        text = re.sub(r"<[^>]+>", " ", m.group(2))
        text = re.sub(r"\s+", " ", text).strip()
        out.append((href, text))
    return out


def get_title(html: str) -> str | None:
    m = re.search(r"<title[^>]*>(.*?)</title>", html, re.S | re.I)
    t = None
    if m:
        t = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", m.group(1))).strip()
    if not t:
        h = re.search(r"<h1[^>]*>(.*?)</h1>", html, re.S | re.I)
        if h:
            t = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", h.group(1))).strip()
    if not t:
        return None
    if re.match(r"^\s*(40\d|50\d|Forbidden|Not Found|Error|Access Denied)", t, re.I):
        return None
    return t


WAREKI = {"令和": 2018, "平成": 1988, "昭和": 1925}


def refine_discipline(default: str, title: str) -> str:
    """Official statistics span fields; label by topic keyword in the title."""
    if re.search(r"物価|住宅|土地|建設|科学技術|情報通信|エネルギー|産業|生産|"
                 r"サービス|小売|企業|事業所|経済センサス|鉱工業", title):
        return "理工"
    if re.search(r"医療|健康|衛生|死因|生命表|患者|受療", title):
        return "医学生命"
    return default


def derive_year(title: str) -> str | None:
    for era, base in WAREKI.items():
        m = re.search(era + r"\s*(元|\d{1,2})\s*年", title)
        if m:
            n = 1 if m.group(1) == "元" else int(m.group(1))
            return str(base + n)
    m = re.search(r"(19|20)\d{2}\s*年", title)
    if m:
        return m.group(0).replace("年", "").strip()
    m = re.search(r"\b(19|20)\d{2}\b", title)
    if m:
        return m.group(0)
    return None


def flags_for(title: str, org_author: bool) -> list[str]:
    f = []
    if org_author:
        f.append("institutional_author")
    if re.search(r"令和|平成|昭和", title):
        f.append("wareki")
    if re.search(r"年版|第\s*\d+\s*版|改訂|新版", title):
        if "nonstandard_volume" not in f:
            f.append("nonstandard_volume")
    if re.search(r"[—―－\-：:〜～]|◆|『", title) and len(title) > 24:
        f.append("subtitle")
    if len(re.findall(r"[A-Za-z]", title)) >= 6:
        f.append("english_mixed")
    return f


@dataclass
class Source:
    name: str
    seeds: list[str]
    include: str  # regex a candidate href must match
    discipline: str
    subfield: str
    category: str  # hakusho | toukei | kijun_guideline_gakkyokai_dict
    org: str
    cap: int
    exclude: str = ""  # optional regex to drop candidates
    two_level: bool = False  # crawl one extra level: seed -> subindex -> leaves
    sub_include: str = ""    # on two_level, links from seed matching this are subindexes
    sitemap: str = ""        # if set: gunzip this XML sitemap and take <loc> matching `include`


def gather_candidates(src: Source, log) -> list[str]:
    if src.sitemap:
        try:
            r = polite_get(src.sitemap)
            raw = gzip.decompress(r.content) if src.sitemap.endswith(".gz") else r.content
            locs = re.findall(r"<loc>([^<]+)</loc>", raw.decode("utf-8", "replace"))
        except Exception as e:
            log({"event": "sitemap_error", "url": src.sitemap, "err": str(e)})
            return []
        cands = [u for u in locs if re.search(src.include, u) and robots_ok(u)
                 and not (src.exclude and re.search(src.exclude, u))]
        # deterministic, spread across the sitemap rather than first-N clustering
        step = max(1, len(cands) // (src.cap * 3)) if cands else 1
        cands = cands[::step]
        log({"event": "sitemap", "url": src.sitemap, "n_loc": len(locs),
             "n_cand": len(cands)})
        return cands
    cands: list[str] = []
    seen = set()

    def add_from(html, base):
        for href, _ in extract_links(html, base):
            if href in seen:
                continue
            if not robots_ok(href):
                continue
            if src.exclude and re.search(src.exclude, href):
                continue
            if re.search(src.include, href):
                seen.add(href)
                cands.append(href)

    subindexes = []
    for seed in src.seeds:
        if not robots_ok(seed):
            log({"event": "seed_robots_block", "url": seed})
            continue
        try:
            r = polite_get(seed)
        except Exception as e:
            log({"event": "seed_error", "url": seed, "err": str(e)})
            continue
        r.encoding = r.apparent_encoding
        log({"event": "seed", "url": seed, "status": r.status_code, "final": r.url})
        if r.status_code != 200:
            continue
        add_from(r.text, r.url)
        if src.two_level and src.sub_include:
            for href, _ in extract_links(r.text, r.url):
                if re.search(src.sub_include, href) and href not in subindexes:
                    subindexes.append(href)
    for sidx in subindexes:
        if not robots_ok(sidx):
            continue
        try:
            r = polite_get(sidx)
        except Exception as e:
            log({"event": "subindex_error", "url": sidx, "err": str(e)})
            continue
        r.encoding = r.apparent_encoding
        log({"event": "subindex", "url": sidx, "status": r.status_code})
        if r.status_code == 200:
            add_from(r.text, r.url)
    return cands


def collect_source(src: Source, log, existing_urls: set) -> list[dict]:
    cands = gather_candidates(src, log)
    log({"event": "candidates", "name": src.name, "n": len(cands)})
    records = []
    for url in cands:
        if len(records) >= src.cap:
            break
        if url in existing_urls:
            continue
        try:
            r = polite_get(url)
        except Exception as e:
            log({"event": "fetch_error", "url": url, "err": str(e)})
            continue
        r.encoding = r.apparent_encoding
        title = get_title(r.text) if r.status_code == 200 else None
        log({"event": "fetch", "url": url, "status": r.status_code,
             "final": r.url, "title": title})
        if r.status_code != 200 or not title:
            continue
        final = r.url
        if final in existing_urls:
            continue
        existing_urls.add(final)
        existing_urls.add(url)
        # kotobank is an aggregating portal, not the institutional author of the
        # entry -> don't mark institutional_author there.
        org_author = bool(src.org) and src.name != "コトバンク 辞典項目"
        fields = {"title": title, "url": final, "urldate": URLDATE}
        if src.org:
            fields["author"] = src.org
        yr = derive_year(title)
        if yr:
            fields["year"] = yr
        notes = []
        if final.rstrip("/") != url.rstrip("/"):
            notes.append(f"redirect: {url} -> {final}")
        disc = refine_discipline(src.discipline, title) if src.category == "toukei" else src.discipline
        rec = {
            "provisional_key": None,
            "entry_type": "misc",
            "bibtex_fields": fields,
            "discipline": disc,
            "subfield": src.subfield,
            "difficulty_flags": flags_for(title, org_author),
            "source_name": src.name,
            "source_url": final,
            "retrieved_at": "2026-07-17T00:00:00+09:00",
            "notes": "; ".join(notes),
        }
        records.append(rec)
    log({"event": "collected", "name": src.name, "n": len(records)})
    return records


# --------------------------------------------------------------------------
# Source configuration. Seeds are index/listing pages; `include` selects the
# citable leaf pages within them.
SOURCES: list[Source] = [
    # ---- 省庁白書 (80) --------------------------------------------------
    Source("内閣府 高齢社会白書", ["https://www8.cao.go.jp/kourei/whitepaper/index-w.html"],
           r"kourei/whitepaper/w-\d{4}/html/(zenbun|gaiyou)/index\.html",
           "人文社会", "高齢化・社会保障", "hakusho", "内閣府", cap=15),
    Source("内閣府 男女共同参画白書", ["https://www.gender.go.jp/about_danjo/whitepaper/index.html"],
           r"about_danjo/whitepaper/[hr]\d+/zentai/index\.html",
           "人文社会", "ジェンダー", "hakusho", "内閣府男女共同参画局", cap=7,
           exclude=r"english"),
    Source("内閣府 防災白書", ["https://www.bousai.go.jp/kaigirep/hakusho/"],
           r"kaigirep/hakusho/[hr]\d+/index",
           "理工", "防災", "hakusho", "内閣府", cap=12),
    Source("総務省 情報通信白書", ["https://www.soumu.go.jp/johotsusintokei/whitepaper/"],
           r"johotsusintokei/whitepaper/ja/[hr]\d+/(index|html/[a-z]+\.html)",
           "理工", "情報通信", "hakusho", "総務省", cap=6, exclude=r"errata|riyou"),
    Source("環境省 環境白書", ["https://www.env.go.jp/policy/hakusyo/"],
           r"env\.go\.jp/policy/hakusyo/(index|[hr]\d+/index)\.html",
           "理工", "環境", "hakusho", "環境省", cap=6, exclude=r"\.pdf|hyoshi"),
    Source("国土交通白書", ["https://www.mlit.go.jp/statistics/file000004.html",
                       "https://www.mlit.go.jp/statistics/mlithakusyo_bkn.html"],
           r"statistics/hakusyo\.mlit\.[hr]\d+\.html",
           "理工", "国土交通", "hakusho", "国土交通省", cap=12),
    Source("厚生労働白書", ["https://www.mhlw.go.jp/toukei_hakusho/hakusho/"],
           r"/wp/hakusyo/kousei/\d",
           "医学生命", "社会保障・厚生", "hakusho", "厚生労働省", cap=30,
           exclude=r"_en|index_en"),
    # ---- 統計 (40) ------------------------------------------------------
    Source("総務省統計局 統計調査", ["https://www.stat.go.jp/data/index.html",
                             "https://www.stat.go.jp/data/guide/1.html"],
           r"stat\.go\.jp/data/[a-z][a-z0-9-]+/(index|index1|\d{4}/index)",
           "人文社会", "公的統計", "toukei", "総務省統計局", cap=40,
           exclude=r"/guide/|/topics/|/opac/"),
    # ---- 規格・ガイドライン・学協会・辞典 (80) ---------------------------
    Source("Minds 診療ガイドライン", ["https://minds.jcqhc.or.jp/",
                              "https://minds.jcqhc.or.jp/s/guideline_list"],
           r"minds\.jcqhc\.or\.jp/summary/c\d+",
           "医学生命", "診療ガイドライン", "kijun_guideline_gakkyokai_dict",
           "日本医療機能評価機構", cap=40),
    Source("個人情報保護委員会 ガイドライン", ["https://www.ppc.go.jp/personalinfo/legal/",
                                 "https://www.ppc.go.jp/legal/policy/"],
           r"ppc\.go\.jp/(personalinfo/)?legal/[a-zA-Z]",
           "人文社会", "個人情報保護", "kijun_guideline_gakkyokai_dict",
           "個人情報保護委員会", cap=15, exclude=r"\?ref=|leakAction|optout|kondankai"),
    Source("情報処理学会 倫理綱領", ["https://www.ipsj.or.jp/ipsjcode.html"],
           r"ipsjcode(-jirei|-old)?\.html",
           "理工", "研究倫理", "kijun_guideline_gakkyokai_dict",
           "情報処理学会", cap=3),
    Source("人工知能学会 倫理指針", ["https://www.ai-gakkai.or.jp/ai-elsi/"],
           r"ai-elsi/(about|report)/[a-z_]+$",
           "理工", "AI倫理", "kijun_guideline_gakkyokai_dict",
           "人工知能学会", cap=6),
    # /b_menu/hakusho/YYYY/mext_*.html are 法令・省令 notices, not white papers;
    # only html/kagaku.htm (科学技術・イノベーション白書) is a genuine 白書 here.
    Source("文部科学省 白書", ["https://www.mext.go.jp/b_menu/hakusho/hakusho.htm"],
           r"mext\.go\.jp/b_menu/hakusho/html/kagaku\.htm",
           "理工", "科学技術", "hakusho", "文部科学省", cap=2,
           exclude=r"_e\.htm"),
    # オンライン辞典: kotobank Japanese encyclopedia (百科事典) entries via sitemap
    # (robots permits our UA). Only bibliographic metadata (headword in the title)
    # is stored; no dictionary body text is saved.
    Source("コトバンク 辞典項目", [], r"kotobank\.jp/word/",
           "人文社会", "オンライン百科事典", "kijun_guideline_gakkyokai_dict",
           "コトバンク", cap=58,
           sitemap="https://kotobank.jp/sitemap-xml/sitemap_word_001.xml.gz"),
]


def load_existing() -> tuple[list[dict], set]:
    path = INTERIM / "records.jsonl"
    recs, urls = [], set()
    if path.exists():
        for line in path.read_text().splitlines():
            if line.strip():
                r = json.loads(line)
                recs.append(r)
                urls.add(r["bibtex_fields"]["url"])
                urls.add(r["source_url"])
    return recs, urls


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default="")
    ap.add_argument("--probe", default="")
    args = ap.parse_args()

    logf = (RAW / "fetch_log.jsonl").open("a")

    def log(d):
        d["ts"] = time.strftime("%H:%M:%S")
        logf.write(json.dumps(d, ensure_ascii=False) + "\n")
        logf.flush()

    if args.probe:
        src = next(s for s in SOURCES if s.name == args.probe)
        cands = gather_candidates(src, log)
        print(f"{src.name}: {len(cands)} candidates")
        for c in cands[:40]:
            print("  ", c)
        return

    only = set(args.only.split(",")) if args.only else None
    existing, urls = load_existing()
    print(f"existing records: {len(existing)}")
    all_new = []
    for src in SOURCES:
        if only and src.name not in only:
            continue
        recs = collect_source(src, log, urls)
        all_new.extend(recs)
        print(f"[{src.name}] +{len(recs)}  (total new {len(all_new)})")

    # merge + write idempotently
    merged = existing + all_new
    path = INTERIM / "records.jsonl"
    with path.open("w") as f:
        for i, r in enumerate(merged, 1):
            r["provisional_key"] = f"webmisc-{i:06d}"
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"TOTAL records: {len(merged)} -> {path}")
    # category tally
    from collections import Counter
    cat = Counter(r["source_name"] for r in merged)
    for k, v in cat.items():
        print(f"   {v:3d}  {k}")


if __name__ == "__main__":
    main()
