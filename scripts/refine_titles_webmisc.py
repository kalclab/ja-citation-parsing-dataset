#!/usr/bin/env python
"""Replace the raw <title> of each webmisc record with a citation-style title
(page heading without SEO boilerplate), per team-lead acceptance condition.

Rule: prefer the page's own heading -- an og:title / <h1> that carries the
document's specifics -- else the rule-cleaned <title>. All chosen text exists
verbatim on the page (heading or title), so this is not fabrication. The raw
<title> is preserved in notes as `raw_title:`.

Two phases (so cleaning rules can be tuned without re-fetching):
  --probe : re-fetch all records (1.5 s wait), cache raw_title/og/h1s to
            data/raw/webmisc/title_probe.jsonl
  --dry   : apply cleaning to the cache, print before->after + collisions
  --apply : write cleaned titles back into records.jsonl (needs the cache)
"""
from __future__ import annotations
import argparse, collections, json, re, time
from pathlib import Path
import requests

ROOT = Path(__file__).resolve().parent.parent
RECORDS = ROOT / "data" / "interim" / "webmisc" / "records.jsonl"
PROBE = ROOT / "data" / "raw" / "webmisc" / "title_probe.jsonl"
UA = "ja-citation-parsing-dataset (mailto:anonymous@example.org)"
WAREKI = {"令和": 2018, "平成": 1988, "昭和": 1925}

MINISTRY = ["総務省統計局", "総務省", "内閣府男女共同参画局", "内閣府", "厚生労働省",
            "環境省", "国土交通省", "文部科学省", "個人情報保護委員会",
            "情報処理学会", "人工知能学会"]
SITE_LABELS = ["統計局ホームページ", "コトバンク", "Mindsガイドラインライブラリ",
               "防災情報のページ", "総合環境政策"] + MINISTRY


def cleanhtml(x: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", x)).strip()


def clean_title(t: str) -> str:
    t = re.sub(r"\s*（(読み|その他表記|英語表記|別称|別表記|旧称|ローマ字表記)）.*$",
               "", t)                                          # kotobank annotation tail
    t = re.sub(r"\s*とは[?？]\s*意味や使い方.*$", "", t)        # kotobank boilerplate
    t = re.sub(r"^\s*(?:" + "|".join(map(re.escape, MINISTRY))
               + r")[\s_｜|/：:－-]+", "", t)                   # leading org label
    parts = re.split(r"\s*[｜|/]\s*", t)                        # drop site-label segments
    parts = [p for p in parts if p.strip() and p.strip() not in SITE_LABELS]
    t = " ".join(parts)
    t = re.sub(r"\s*[:：]\s*防災情報のページ.*$", "", t)
    t = re.sub(r"\s*[-–—－]\s*(?:" + "|".join(map(re.escape, SITE_LABELS))
               + r").*$", "", t)
    t = t.strip(" 　-－:：｜|/")
    return re.sub(r"\s+", " ", t).strip()


# generic section headings that must never become the title on their own
GENERIC = {"目次", "表紙", "本文", "概要", "図表", "トップ", "ホーム", "トップページ",
           "PDF版", "HTML版", "PDF", "HTML", "index", "前のページ", "次のページ", ""}
MARKER = re.compile(r"白書|ガイドライン|指針|綱領|要綱|調査|統計|年版|令和|平成|昭和|"
                    r"\d{4}|法律|事例|規程|方針|報告|年鑑|センサス|辞典|事典")


def pick_base(p: dict) -> str:
    raw_ct = clean_title(p["raw_title"])
    h1_ct = [clean_title(x) for x in (cleanhtml(h) for h in p.get("h1s", [])) if x]
    yr = [x for x in h1_ct if MARKER.search(x)]
    og_ct = [clean_title(p["og"])] if p.get("og") else []
    # priority: a heading carrying a document marker, then the marker-bearing
    # <title>, then any non-generic heading, then og / <title>.
    ordered = (sorted(yr, key=len, reverse=True)
               + ([raw_ct] if MARKER.search(raw_ct) else [])
               + sorted(h1_ct, key=len, reverse=True)
               + og_ct + [raw_ct])
    for c in ordered:
        if c and c not in GENERIC:
            return c
    return raw_ct or p["raw_title"]


def derive_year(title: str):
    for era, base in WAREKI.items():
        m = re.search(era + r"\s*(元|\d{1,2})\s*年", title)
        if m:
            return str(base + (1 if m.group(1) == "元" else int(m.group(1))))
    m = re.search(r"(19|20)\d{2}\s*年", title)
    if m:
        return m.group(0).replace("年", "").strip()
    return None


def flags_for(title: str, is_inst: bool) -> list[str]:
    f = []
    if is_inst:
        f.append("institutional_author")
    if re.search(r"令和|平成|昭和", title):
        f.append("wareki")
    if re.search(r"年版|第\s*\d+\s*版|改訂|新版", title):
        f.append("nonstandard_volume")
    if re.search(r"[：―—〜～－−]|『.+』|【.+】", title) and len(title) > 16:
        f.append("subtitle")
    if len(re.findall(r"[A-Za-z]", title)) >= 6:
        f.append("english_mixed")
    return f


def do_probe(recs):
    sess = requests.Session()
    sess.headers.update({"User-Agent": UA})
    done = set()
    if PROBE.exists():
        for l in PROBE.read_text().splitlines():
            if l.strip():
                done.add(json.loads(l)["key"])
    with PROBE.open("a") as out:
        for r in recs:
            k = r["provisional_key"]
            if k in done:
                continue
            url = r["bibtex_fields"]["url"]
            rec = {"key": k, "url": url, "raw_title": "", "og": "", "h1s": []}
            try:
                resp = sess.get(url, timeout=30, allow_redirects=True)
                resp.encoding = resp.apparent_encoding
                t = re.search(r"<title[^>]*>(.*?)</title>", resp.text, re.S | re.I)
                rec["raw_title"] = cleanhtml(t.group(1)) if t else ""
                og = (re.search(r'<meta[^>]+property=["\']og:title["\'][^>]+content=["\']([^"\']+)', resp.text, re.I)
                      or re.search(r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']og:title["\']', resp.text, re.I))
                rec["og"] = cleanhtml(og.group(1)) if og else ""
                rec["h1s"] = re.findall(r"<h1[^>]*>(.*?)</h1>", resp.text, re.S | re.I)
            except Exception as e:
                rec["error"] = str(e)
            out.write(json.dumps(rec, ensure_ascii=False) + "\n")
            out.flush()
            time.sleep(1.5)
    print(f"probe cached -> {PROBE}")


def load_probe():
    return {json.loads(l)["key"]: json.loads(l)
            for l in PROBE.read_text().splitlines() if l.strip()}


def do_dry(recs):
    probe = load_probe()
    newtitles = {}
    for r in recs:
        k = r["provisional_key"]
        p = probe.get(k)
        if not p or p.get("error"):
            newtitles[k] = r["bibtex_fields"]["title"]
            continue
        newtitles[k] = pick_base(p)
    changed = sum(1 for r in recs
                  if newtitles[r["provisional_key"]] != r["bibtex_fields"]["title"])
    dup = [t for t, n in collections.Counter(newtitles.values()).items() if n > 1]
    print(f"changed: {changed}/{len(recs)}  new-dup-titles: {len(dup)}")
    for d in dup:
        print("  DUP:", d)
    shown = set()
    for r in recs:
        s = r["source_name"]
        if s in shown:
            continue
        shown.add(s)
        k = r["provisional_key"]
        print(f"[{s}]\n   OLD: {r['bibtex_fields']['title']}\n   NEW: {newtitles[k]}")


def do_apply(recs):
    probe = load_probe()
    newtitles = {}
    for r in recs:
        k = r["provisional_key"]
        p = probe.get(k)
        newtitles[k] = pick_base(p) if p and not p.get("error") else r["bibtex_fields"]["title"]
    # guard: if cleaning would create a duplicate title, keep the record's current title
    counts = collections.Counter(newtitles.values())
    for r in recs:
        k = r["provisional_key"]
        bf = r["bibtex_fields"]
        p = probe.get(k)
        nt = newtitles[k]
        if counts[nt] > 1:
            nt = bf["title"]  # revert to avoid collision
        raw = p["raw_title"] if p else ""
        if nt != bf["title"]:
            if raw:
                note = f"raw_title: {raw}"
                r["notes"] = (r.get("notes", "") + "; " + note).strip("; ")
            bf["title"] = nt
        yr = derive_year(nt)
        if yr:
            bf["year"] = yr
        is_inst = ("author" in bf) and (r["source_name"] != "コトバンク 辞典項目")
        r["difficulty_flags"] = flags_for(nt, is_inst)
    with RECORDS.open("w") as f:
        for i, r in enumerate(recs, 1):
            r["provisional_key"] = f"webmisc-{i:06d}"
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    titles = [r["bibtex_fields"]["title"] for r in recs]
    print(f"applied. dup-titles now: {len(titles)-len(set(titles))}")
    print("flag freq:", dict(collections.Counter(
        fl for r in recs for fl in r["difficulty_flags"])))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--probe", action="store_true")
    ap.add_argument("--dry", action="store_true")
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()
    recs = [json.loads(l) for l in RECORDS.read_text().splitlines() if l.strip()]
    if args.probe:
        do_probe(recs)
    if args.dry:
        do_dry(recs)
    if args.apply:
        do_apply(recs)


if __name__ == "__main__":
    main()
