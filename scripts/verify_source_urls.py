"""Re-fetch a stratified random sample of source_url and check existence + match.

Final-checklist item: draw ~N% of the released records (default 3%, stratified
by entry_type), re-fetch each source_url, and record whether it resolves and
whether the record's title is found on the page.

Verdicts:
  OK        HTTP 200 and the title (normalised, or its 12-char head) is present
            in the fetched HTML.
  RESOLVES  HTTP 200 but title not found (often JS-rendered pages, or PDF/other
            binary) — the URL exists but bibliographic match is inconclusive.
  FAIL      non-200 / network error.

Deterministic sample (fixed seed); live fetch results naturally reflect the run
date. Titles are read from ja_bib_full.bib (metadata.csv carries no title).
Polite: contact-bearing UA, 1.5 s between requests, redirects followed.
"""

from __future__ import annotations

import argparse
import csv
import random
import re
import sys
import time
import unicodedata
from collections import defaultdict
from datetime import date
from pathlib import Path

import requests
import bibtexparser
from bibtexparser.bparser import BibTexParser

UA = "ja-citation-parsing-dataset (mailto:anonymous@example.org)"
DELAY = 1.5
SEED = 20260807


def norm(s: str) -> str:
    s = unicodedata.normalize("NFKC", s).lower()
    return "".join(c for c in s if not c.isspace() and unicodedata.category(c)[0] not in ("P", "S"))


def load_titles(bib_path: Path) -> dict[str, str]:
    parser = BibTexParser(common_strings=True)
    parser.ignore_nonstandard_types = False
    db = bibtexparser.loads(bib_path.read_text(encoding="utf-8"), parser)
    return {e["ID"]: e.get("title", "") for e in db.entries}


def stratified_sample(rows: list[dict], rate: float) -> list[dict]:
    by_type: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        by_type[r["entry_type"]].append(r)
    rng = random.Random(SEED)
    sample: list[dict] = []
    for etype in sorted(by_type):
        group = sorted(by_type[etype], key=lambda r: r["key"])
        n = max(1, round(len(group) * rate / 100))
        sample.extend(rng.sample(group, min(n, len(group))))
    return sorted(sample, key=lambda r: r["key"])


def check(url: str, title: str) -> tuple[str, int | str, bool]:
    try:
        resp = requests.get(url, headers={"User-Agent": UA}, timeout=30, allow_redirects=True)
    except requests.RequestException as exc:
        return "FAIL", type(exc).__name__, False
    if resp.status_code != 200:
        return "FAIL", resp.status_code, False
    body = ""
    ctype = resp.headers.get("content-type", "")
    if "html" in ctype or "xml" in ctype or "text" in ctype:
        # many ministry pages are Shift-JIS without a charset header; decode by
        # sniffed encoding so the title match is not defeated by mojibake.
        resp.encoding = resp.apparent_encoding or resp.encoding
        body = resp.text
    nt, nbody = norm(title), norm(body)
    found = bool(nt) and (nt in nbody or (len(nt) >= 12 and nt[:12] in nbody))
    return ("OK" if found else "RESOLVES"), resp.status_code, found


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dataset-dir", type=Path, default=Path("dataset"))
    ap.add_argument("--rate", type=float, default=3.0, help="percent to sample (default 3)")
    ap.add_argument("--out", type=Path, default=Path("reports/qc/final_url_check.md"))
    args = ap.parse_args()

    rows = list(csv.DictReader((args.dataset_dir / "metadata.csv").open(encoding="utf-8")))
    titles = load_titles(args.dataset_dir / "ja_bib_full.bib")
    sample = stratified_sample(rows, args.rate)

    results = []
    for r in sample:
        verdict, code, _ = check(r["source_url"], titles.get(r["key"], ""))
        results.append((r, verdict, code))
        print(f"{r['key']} {verdict} ({code}) {r['source_url']}", file=sys.stderr)
        time.sleep(DELAY)

    n = len(results)
    ok = sum(1 for _, v, _ in results if v == "OK")
    res = sum(1 for _, v, _ in results if v == "RESOLVES")
    fail = sum(1 for _, v, _ in results if v == "FAIL")
    by_type = defaultdict(lambda: [0, 0, 0])
    for r, v, _ in results:
        by_type[r["entry_type"]][0 if v == "OK" else 1 if v == "RESOLVES" else 2] += 1

    lines = [
        "# 最終 source_url 再検証（3% 層化サンプル）", "",
        f"**実施日**: {date.today().isoformat()}  ",
        f"**対象**: dataset/metadata.csv 全 {len(rows)} 件から {args.rate:.0f}% を entry_type 層化で無作為抽出（seed={SEED}）= {n} 件  ",
        "**方法**: 各 source_url を再取得（UA に連絡先、リクエスト間 1.5 秒、リダイレクト追跡）。HTTP 200 かつ題目がページ本文に一致すれば OK、200 だが題目未検出（JS 描画・PDF 等）は RESOLVES、非 200・エラーは FAIL。", "",
        f"## 結果: OK {ok} / RESOLVES {res} / FAIL {fail}（到達 {ok + res}/{n} = {(ok + res) / n * 100:.0f}%）", "",
        "| entry_type | 標本 | OK | RESOLVES | FAIL |", "|---|---|---|---|---|",
    ]
    for t in sorted(by_type):
        o, rs, f = by_type[t]
        lines.append(f"| {t} | {o + rs + f} | {o} | {rs} | {f} |")
    lines += ["", "## 明細", "", "| key | verdict | HTTP | source_url |", "|---|---|---|---|"]
    for r, v, code in results:
        lines.append(f"| {r['key']} | {v} | {code} | {r['source_url']} |")
    if fail:
        lines += ["", "## FAIL 詳細（要確認）", ""]
        for r, v, code in results:
            if v == "FAIL":
                lines.append(f"- `{r['key']}` ({r['source_name']}): HTTP/err {code} — {r['source_url']}")
    else:
        lines += ["", "FAIL は 0 件（全標本が到達）。"]

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"\nwrote {args.out}: OK {ok} RESOLVES {res} FAIL {fail} (n={n})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
