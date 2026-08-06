#!/usr/bin/env python3
"""Build annotations/manual_name_table.jsonl from the manual /
Web-verified name-split sources.

Inputs (annotations/):
  - manual_name_splits.txt    : round 1. Space-split lines = confirmed splits
    (provenance manual). No-space non-`*` lines = orgs/single names (kept
    concatenated). Trailing `*`/`**` = resolved via the followup report (WEB /
    CONVENTION maps below; provenance web-verified with authority URL).
  - manual_name_splits_2.txt  : round 2. All lines space-split (manual).
  - (followup: reports/qc/name_manual_followup.md — encoded in WEB/CONVENTION)

Output: {name (concatenated), split ("姓, 名"), provenance, source_url[, note]}
one JSON object per line. `name` is the space/comma-stripped form, so it joins
onto author/editor/translator fields regardless of the source's spacing.

Names left concatenated on purpose (not written): organisations and single
names (regnal names) — the split operation is bibliographically undefined.
`吉田` (surname-only record) was dropped from the dataset upstream.

Run: uv run python scripts/build_manual_name_table.py
"""
from __future__ import annotations

import json
import re
from pathlib import Path

ENRICH = Path("annotations")
SRC1 = ENRICH / "manual_name_splits.txt"
SRC2 = ENRICH / "manual_name_splits_2.txt"
OUT = ENRICH / "manual_name_table.jsonl"

# `*`/`**` names resolved by Web/authority (reports/qc/name_manual_followup.md),
# plus a translator found later. Keyed by the concatenated name.
WEB: dict[str, tuple[str, list[str]]] = {
    "ジェプカラファウ": ("ジェプカ, ラファウ", ["https://researchmap.jp/rafal_rzepka/"]),
    "邊土名朝飛": ("邊土名, 朝飛", ["https://www.ai-shift.co.jp/publications/page/2"]),
    "田野": ("田, 野", ["https://www.anlp.jp/proceedings/annual_meeting/2024/pdf_dir/C10-2.pdf"]),
    "肖桐": ("肖, 桐", ["https://www.anlp.jp/proceedings/annual_meeting/2024/pdf_dir/C10-2.pdf"]),
    "小木曽智信": ("小木曽, 智信", ["https://researchmap.jp/togiso"]),
    "曾秋桂": ("曾, 秋桂", ["https://www.tfjx.tku.edu.tw/tfjx/?page_id=17336"]),
    "陸宇傑": ("陸, 宇傑", ["https://forest.ynu.ac.jp/mori/ja/pub.html"]),
    "韓東力": ("韓, 東力", ["https://researchmap.jp/read0131843"]),
    "高忠輝": ("高, 忠輝", ["https://www.anlp.jp/proceedings/annual_meeting/2024/pdf_dir/C10-2.pdf"]),
    "辰巳守祐": ("辰巳, 守祐", ["https://www.anlp.jp/proceedings/annual_meeting/2019/pdf_dir/B4-6.pdf"]),
    # 訳者（NDL 図書 R100000002-I034714816、著者標目「ヤン, ジャクリン」）
    "ヤンジャクリン": ("ヤン, ジャクリン", ["https://ndlsearch.ndl.go.jp/books/R100000002-I034714816"]),
}
# 慣習ベースの手動判断（ローマ字典拠未取得）。provenance は manual。
CONVENTION: dict[str, tuple[str, list[str], str]] = {
    "葉夌": ("葉, 夌", ["https://www.anlp.jp/proceedings/annual_meeting/2022/pdf_dir/D7-1.pdf"],
             "2 文字中国語名の慣習に基づく手動判断（ローマ字典拠未取得）"),
}
SKIP = {"吉田"}  # 姓のみレコードは upstream で drop 済み

# ソース txt に現れない、個別に確定した名前（訳者フィールド等の取りこぼし）。
# 無条件に出力する。
EXTRA: list[dict] = [
    {"name": "ヤンジャクリン", "split": "ヤン, ジャクリン", "provenance": "web-verified",
     "source_url": ["https://ndlsearch.ndl.go.jp/books/R100000002-I034714816"]},
]

_STRIP = re.compile(r"[ 　,]")
_WS = re.compile(r"[ 　]+")


def process(path: Path, rows: list[dict], skipped: list[str], anomalies: list[str],
            all_manual: bool = False) -> None:
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line:
            continue
        marker = line.endswith("*")
        name = line.rstrip("*").strip()
        concat = _STRIP.sub("", name)
        if concat in CONVENTION:
            split, url, note = CONVENTION[concat]
            rows.append({"name": concat, "split": split, "provenance": "manual",
                         "source_url": url, "note": note})
            continue
        if concat in SKIP:
            skipped.append(name)
            continue
        parts = _WS.split(name)
        if len(parts) == 2:
            prov, url = ("web-verified", WEB.get(concat, (None, []))[1]) if (marker and not all_manual) \
                else ("manual", [])
            rows.append({"name": concat, "split": f"{parts[0]}, {parts[1]}",
                         "provenance": prov, "source_url": url})
        elif len(parts) == 1 and marker and concat in WEB:
            split, url = WEB[concat]
            rows.append({"name": concat, "split": split, "provenance": "web-verified", "source_url": url})
        elif len(parts) == 1:
            skipped.append(name)          # org / single name -> keep concatenated
        else:
            anomalies.append(name)


def main() -> int:
    rows: list[dict] = []
    skipped: list[str] = []
    anomalies: list[str] = []
    process(SRC1, rows, skipped, anomalies)
    if SRC2.exists():
        process(SRC2, rows, skipped, anomalies, all_manual=True)
    rows.extend(EXTRA)
    # a name may recur across sources; keep first occurrence
    seen: dict[str, dict] = {}
    for r in rows:
        seen.setdefault(r["name"], r)
    final = list(seen.values())
    OUT.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in final) + "\n", encoding="utf-8")
    my = sum(1 for r in final if r["provenance"] == "manual")
    wv = sum(1 for r in final if r["provenance"] == "web-verified")
    print(f"wrote {OUT}: {len(final)} splits (manual={my}, web-verified={wv})")
    print(f"kept concatenated: {sorted(set(skipped))}")
    if anomalies:
        print(f"ANOMALIES (>2 tokens, review): {anomalies}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
