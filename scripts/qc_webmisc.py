#!/usr/bin/env python
"""QC for webmisc: re-fetch a random sample and verify each recorded title
  (a) exists verbatim on the live page (as the <title>, an <h1>, or og:title),
      i.e. not fabricated, and
  (b) is free of SEO boilerplate (site-name suffixes, "とは？ 意味や使い方",
      "統計局ホームページ", "（読み）", stray "｜" separators, etc.).
Writes data/qc/webmisc.md.

Usage: uv run scripts/qc_webmisc.py [--n 20] [--seed 424242]
"""
from __future__ import annotations
import argparse, json, random, re, time
from pathlib import Path
import requests

ROOT = Path(__file__).resolve().parent.parent
RECORDS = ROOT / "data" / "interim" / "webmisc" / "records.jsonl"
OUT = ROOT / "data" / "qc" / "webmisc.md"
UA = "ja-citation-parsing-dataset (mailto:anonymous@example.org)"

BOILERPLATE = re.compile(
    r"とは[?？]\s*意味や使い方|統計局ホームページ|-\s*コトバンク|コトバンク$|"
    r"Mindsガイドラインライブラリ|防災情報のページ|（読み）|[｜|]|"
    r"：\s*文部科学省")


def clean(x: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", x)).strip()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=20)
    ap.add_argument("--seed", type=int, default=424242)
    args = ap.parse_args()

    recs = [json.loads(l) for l in RECORDS.read_text().splitlines() if l.strip()]
    sample = random.Random(args.seed).sample(recs, min(args.n, len(recs)))

    sess = requests.Session()
    sess.headers.update({"User-Agent": UA})
    rows, npass = [], 0
    for r in sample:
        url = r["bibtex_fields"]["url"]
        rt = r["bibtex_fields"]["title"]
        try:
            resp = sess.get(url, timeout=30, allow_redirects=True)
            resp.encoding = resp.apparent_encoding
            status = resp.status_code
            title = re.search(r"<title[^>]*>(.*?)</title>", resp.text, re.S | re.I)
            title = clean(title.group(1)) if title else ""
            h1s = [clean(h) for h in re.findall(r"<h1[^>]*>(.*?)</h1>", resp.text, re.S | re.I)]
            og = re.search(r'og:title["\'][^>]+content=["\']([^"\']+)', resp.text, re.I)
            og = clean(og.group(1)) if og else ""
            page_blob = " || ".join([title, og] + h1s)
        except Exception as e:
            status, page_blob = "ERR", str(e)
        exists = status == 200 and rt in page_blob
        clean_ok = not BOILERPLATE.search(rt)
        ok = exists and clean_ok
        npass += ok
        note = "" if ok else ("boilerplate!" if not clean_ok else "not-on-page")
        rows.append((r["provisional_key"], status, "PASS" if ok else "CHECK",
                     rt, note, url))
        time.sleep(1.5)

    lines = [
        "# @misc QC 再取得レポート（webmisc・タイトル整形後）", "",
        f"作成日: 2026-07-17　サンプル: {len(sample)} 件（seed={args.seed}）",
        f"合格（HTTP 200 かつ記録タイトルがページ見出しに実在 かつ 定型句なし）: "
        f"**{npass}/{len(sample)}**", "",
        "判定: (a) 記録タイトルが再取得ページの `<title>`/`<h1>`/`og:title` に verbatim 出現、",
        "(b) SEO 定型句（サイト名サフィックス・「とは？ 意味や使い方」・「統計局ホームページ」・",
        "「（読み）」・区切り `｜` 等）を含まない、の両方を満たすこと。", "",
        "| key | HTTP | 判定 | 記録タイトル | 備考 | URL |",
        "|---|---|---|---|---|---|",
    ]
    for k, st, judge, rt, note, url in rows:
        cell = rt.replace("|", "\\|")[:52]
        lines.append(f"| {k} | {st} | {judge} | {cell} | {note} | {url} |")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join(lines) + "\n")
    print(f"pass {npass}/{len(sample)} -> {OUT}")


if __name__ == "__main__":
    main()
