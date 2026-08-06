#!/usr/bin/env python
"""Post-collection cleanup for webmisc records.jsonl:
  1. Enrich 国土交通白書 titles (page <title> is generic "国土交通白書 - 国土交通省";
     the page carries a year-specific heading "令和N年版国土交通白書" which we adopt so
     editions are distinguishable). Re-fetched from the live page -- not fabricated.
  2. Recompute difficulty_flags with a tighter heuristic that ignores the trailing
     site-name suffix ("｜省庁名", " - コトバンク") when detecting subtitles / English.
  3. Drop remaining exact-duplicate titles (keep first occurrence).
  4. Reassign sequential provisional_key.
Run after collect_webmisc.py. Idempotent.
"""
from __future__ import annotations
import json, re, time
from pathlib import Path
import requests

ROOT = Path(__file__).resolve().parent.parent
PATH = ROOT / "data" / "interim" / "webmisc" / "records.jsonl"
UA = "ja-citation-parsing-dataset (mailto:anonymous@example.org)"
WAREKI = {"令和": 2018, "平成": 1988, "昭和": 1925}


def core_title(t: str) -> str:
    """Strip the trailing site-name suffix used by many pages."""
    t = re.split(r"\s*[｜|]\s*", t)[0]
    t = re.sub(r"\s*-\s*(コトバンク|国土交通省|環境省|厚生労働省|総務省統計局|総務省|"
               r"文部科学省|情報処理学会).*$", "", t)
    t = re.sub(r"とは？\s*意味や使い方.*$", "", t)
    return t.strip()


def derive_year(title: str):
    for era, base in WAREKI.items():
        m = re.search(era + r"\s*(元|\d{1,2})\s*年", title)
        if m:
            return str(base + (1 if m.group(1) == "元" else int(m.group(1))))
    m = re.search(r"(19|20)\d{2}\s*年", title)
    if m:
        return m.group(0).replace("年", "").strip()
    return None


def flags_for(full_title: str, is_institutional: bool) -> list[str]:
    core = core_title(full_title)
    f = []
    if is_institutional:
        f.append("institutional_author")
    if re.search(r"令和|平成|昭和", core):
        f.append("wareki")
    if re.search(r"年版|第\s*\d+\s*版|改訂|新版", core):
        f.append("nonstandard_volume")
    # subtitle: a real subtitle separator followed by a substantive tail
    if re.search(r"[：―—〜～]|『.+』|【.+】", core) and len(core) > 20:
        f.append("subtitle")
    if len(re.findall(r"[A-Za-z]", core)) >= 6:
        f.append("english_mixed")
    return f


def main():
    recs = [json.loads(l) for l in PATH.read_text().splitlines() if l.strip()]
    sess = requests.Session()
    sess.headers.update({"User-Agent": UA})

    # 1. enrich 国土交通白書 titles
    for r in recs:
        if r["source_name"] != "国土交通白書":
            continue
        url = r["bibtex_fields"]["url"]
        try:
            resp = sess.get(url, timeout=30, allow_redirects=True)
            resp.encoding = resp.apparent_encoding
            m = re.search(r"(令和|平成)\s*[\d元]+\s*年版国土交通白書", resp.text)
            if m:
                r["bibtex_fields"]["title"] = m.group(0)
                r.setdefault("notes", "")
                note = "title taken from page heading (<title> is generic)"
                r["notes"] = (r["notes"] + "; " + note).strip("; ")
        except Exception as e:
            r["notes"] = (r.get("notes", "") + f"; enrich_failed: {e}").strip("; ")
        time.sleep(1.5)

    # 2. recompute year + flags
    for r in recs:
        bf = r["bibtex_fields"]
        is_inst = ("author" in bf) and (r["source_name"] != "コトバンク 辞典項目")
        yr = derive_year(bf["title"])
        if yr:
            bf["year"] = yr
        elif "year" in bf and not derive_year(bf["title"]):
            pass  # keep any previously derived year
        r["difficulty_flags"] = flags_for(bf["title"], is_inst)

    # 3a. drop mislabeled mext pages: /b_menu/hakusho/YYYY/mext_*.html under the
    #     hakusho path are 法令・省令 notices, not white papers.
    recs = [r for r in recs if not (
        r["source_name"] == "文部科学省 白書"
        and re.search(r"/hakusho/\d{4}/mext_", r["bibtex_fields"]["url"]))]
    # drop non-substantive redirect stub pages (title literally "（リダイレクト）")
    recs = [r for r in recs if "（リダイレクト）" not in r["bibtex_fields"]["title"]
            and "_redirect/" not in r["bibtex_fields"]["url"]]

    # 3b. drop exact-duplicate titles (keep first)
    seen, out = set(), []
    for r in recs:
        t = r["bibtex_fields"]["title"]
        if t in seen:
            continue
        seen.add(t)
        out.append(r)

    # 4. reassign keys
    with PATH.open("w") as f:
        for i, r in enumerate(out, 1):
            r["provisional_key"] = f"webmisc-{i:06d}"
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    import collections
    print(f"kept {len(out)} (dropped {len(recs)-len(out)} dup-title)")
    print("flagged:", sum(1 for r in out if r["difficulty_flags"]))
    print("flag freq:", dict(collections.Counter(
        fl for r in out for fl in r["difficulty_flags"])))
    print("discipline:", dict(collections.Counter(r["discipline"] for r in out)))


if __name__ == "__main__":
    main()
