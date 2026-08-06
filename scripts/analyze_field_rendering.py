#!/usr/bin/env python3
"""スタイル×文献タイプ×BibTeX フィールドの出力有無を実測する。

ja_bib_derived.bib（生成に実際に投入したファイル）の各フィールド値が、
ref_strings.jsonl の当該レコード×スタイルの文字列に現れるかをフィールド別の
正規化つき包含判定で検査し、(style, entry_type, field) ごとの検出率を集計する。
reports/style_field_matrix.md の対応表はこの集計に基づく（中間率のセルは
条件付き出力か判定副作用かを個別に検証して脚注化している）。

Usage:
    uv run python scripts/analyze_field_rendering.py \
        [--out data/interim/field_render_matrix.json]
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from collections import defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))
import biblib  # noqa: E402

_DASH_RE = re.compile(r"[–—―‐−‑‒ー-]+")
# CSL スタイルは引用符をロケール変換する（“...” → 『...』/「...」）ため、
# 引用符類は両辺から除去して比較する。
QUOTES = "「」『』“”\"〈〉《》‘’'"


def _base(s: str) -> str:
    s = unicodedata.normalize("NFKC", s).casefold()
    s = s.replace("--", "-")
    s = _DASH_RE.sub("-", s)
    s = s.replace("{", "").replace("}", "")
    for q in QUOTES:
        s = s.replace(q, "")
    return s


def norm(s: str) -> str:
    """casefold + NFKC + 空白全除去 + ダッシュ統一 + 引用符除去。"""
    return re.sub(r"\s+", "", _base(s))


def norm_ws(s: str) -> str:
    """同上だが空白を単一スペースに保持（数値の桁境界判定用）。"""
    return re.sub(r"\s+", " ", _base(s)).strip()


_AND = re.compile(r"\s+and\s+")


def name_parts(nm: str) -> list[str]:
    nm = nm.strip()
    parts = [p.strip() for p in nm.split(",")] if "," in nm else nm.split()
    return [p for p in parts if p]


def _try_name(surname: str, given_parts: list[str], nref: str) -> bool:
    sn = norm(surname)
    if not sn or sn not in nref:
        # ドット連結の単一トークン（"J.M.Neutze"）は最長英字チャンクで判定
        chunks = [c for c in re.split(r"[.・]", surname) if len(c) >= 2]
        if not given_parts and chunks:
            return norm(max(chunks, key=len)) in nref
        return False
    if not given_parts:
        return True
    given = norm("".join(given_parts))
    if given and given in nref:
        return True
    if given and given[0].isascii():  # ローマ字名のイニシャル化（"K."）
        return given[0] + "." in nref
    return False


def match_author(value: str, nref: str) -> bool:
    """筆頭名の姓＋（名 or イニシャル）が現れれば出力ありとみなす。

    空白形の名前は語順が両義（日本語=姓が先、欧文自然順=姓が後）なので
    どちらの読みでも許容する。
    """
    first = _AND.split(value.strip())[0]
    parts = name_parts(first)
    if not parts:
        return False
    if _try_name(parts[0], parts[1:], nref):
        return True
    if "," not in first and len(parts) > 1:
        return _try_name(parts[-1], parts[:-1], nref)
    return False


def match_numeric_bounded(value: str, nref: str, wsref: str) -> bool:
    v = norm(value)
    if not v:
        return False
    if not v.isdigit():
        return v in nref
    return re.search(r"(?<![0-9])" + re.escape(v) + r"(?![0-9])", wsref) is not None


def _collapse_variants(v: str) -> list[str]:
    """chicago はページ範囲の終端を短縮する（124-125 → 124-25）。"""
    out = [v]
    for m in re.finditer(r"(\d+)-(\d+)", v):
        a, b = m.groups()
        for k in range(1, len(b)):
            out.append(v[: m.start()] + f"{a}-{b[k:]}" + v[m.end():])
    return out


def match_pages(value: str, nref: str, wsref: str) -> bool:
    v = norm(value)
    if not v:
        return False
    if any(c in nref for c in _collapse_variants(v)):
        return True
    if v.isdigit():
        return re.search(r"(?<![0-9])" + re.escape(v) + r"(?![0-9])", wsref) is not None
    return False


def match_year(value: str, nref: str) -> bool:
    m = re.search(r"\d{4}", value)
    return (m.group(0) in nref) if m else (norm(value) in nref)


def match_date(value: str, nref: str) -> bool:
    """urldate (yyyy-mm-dd) の ISO／和文日付など複数表記を許容。"""
    v = norm(value)
    if v in nref:
        return True
    m = re.match(r"^(\d{4})-(\d{1,2})-(\d{1,2})$", v)
    if not m:
        return False
    y, mo, d = m.groups()
    cands = [
        f"{y}年{int(mo)}月{int(d)}日", f"{y}年{mo}月{d}日",
        f"{y}/{int(mo)}/{int(d)}", f"{y}.{int(mo)}.{int(d)}",
        f"{int(mo)}月{int(d)}日,{y}",
    ]
    return any(c in nref for c in cands)


def match_id(value: str, nref: str) -> bool:
    return norm(value).replace("-", "") in nref.replace("-", "")


def match_plain(value: str, nref: str) -> bool:
    v = norm(value)
    return bool(v) and v in nref


MATCHERS = {
    "author": match_author, "editor": match_author, "translator": match_author,
    "year": match_year, "urldate": match_date,
    "isbn": match_id, "issn": match_id, "ncid": match_id, "doi": match_id,
}
NUMERIC_FIELDS = {"volume", "number", "pages"}
SKIP_FIELDS = {"ID", "ENTRYTYPE"}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--bib", type=Path, default=REPO / "dataset" / "ja_bib_derived.bib")
    ap.add_argument("--refs", type=Path, default=REPO / "dataset" / "ref_strings.jsonl")
    ap.add_argument("--out", type=Path, default=REPO / "data" / "interim" / "field_render_matrix.json")
    args = ap.parse_args()

    entries = {e["ID"]: e for e in biblib.load_bib(args.bib)}
    agg: dict[tuple[str, str, str], list[int]] = defaultdict(lambda: [0, 0])
    misses: dict[tuple[str, str, str], list[str]] = defaultdict(list)

    with args.refs.open(encoding="utf-8") as fh:
        for line in fh:
            r = json.loads(line)
            if not r["generation_status"].startswith("ok"):
                continue
            e = entries.get(r["key"])
            if e is None:
                continue
            etype = e["ENTRYTYPE"].lower()
            nref, wsref = norm(r["ref_string"]), norm_ws(r["ref_string"])
            for fld, val in e.items():
                if fld in SKIP_FIELDS or not str(val).strip():
                    continue
                if fld in NUMERIC_FIELDS:
                    hit = (match_pages if fld == "pages" else match_numeric_bounded)(str(val), nref, wsref)
                else:
                    hit = MATCHERS.get(fld, match_plain)(str(val), nref)
                a = agg[(r["style"], etype, fld)]
                a[0] += 1
                a[1] += hit
                if not hit and len(misses[(r["style"], etype, fld)]) < 5:
                    misses[(r["style"], etype, fld)].append(r["key"])

    cells = [
        {"style": s, "entry_type": t, "field": f, "n": a[0], "hit": a[1],
         "rate": round(a[1] / a[0], 4), "miss_examples": misses[(s, t, f)]}
        for (s, t, f), a in sorted(agg.items())
    ]
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps({"cells": cells}, ensure_ascii=False, indent=1), encoding="utf-8")

    w = max(len(c["style"]) for c in cells)
    for c in cells:
        print(f'{c["style"]:<{w}} {c["entry_type"]:<13} {c["field"]:<12} '
              f'{c["hit"]:>3}/{c["n"]:<3} {c["rate"]:.2f}')
    print(f"\nwrote {args.out} ({len(cells)} cells)", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
