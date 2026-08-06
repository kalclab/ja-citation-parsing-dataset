#!/usr/bin/env python3
"""Phase 2 post-generation verification (spec: 生成後の検証).

Given the generated ref_strings and the source-faithful .bib, produce:
  1. per-style random-N comparison tables (ref_string vs 原 BibTeX) for 目視確認;
  2. the cross-style identical-output rate (how often two styles yield the same
     string — a style-diversity check).

Deterministic: the random sample uses a fixed --seed.

Usage:
    uv run python scripts/verify_refs.py \
        --refs data/interim/pilot/full/ref_strings_bst.jsonl \
               data/interim/pilot/full/ref_strings_csl.jsonl \
        --bib dataset/ja_bib_full.bib --out data/refs_verification.md
"""
from __future__ import annotations

import argparse
import collections
import json
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import biblib  # noqa: E402

_ORIG_FIELDS = ("author", "editor", "title", "journal", "booktitle",
                "publisher", "volume", "number", "pages", "year", "doi", "url")


def compact_orig(e: dict) -> str:
    parts = [f"{f}={e[f]}" for f in _ORIG_FIELDS if e.get(f)]
    return " / ".join(parts)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--refs", nargs="+", type=Path, required=True)
    ap.add_argument("--bib", type=Path, default=Path("dataset/ja_bib_full.bib"))
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--seed", type=int, default=20260717)
    ap.add_argument("--n", type=int, default=20, help="records sampled per style")
    args = ap.parse_args()

    orig = {e["ID"]: e for e in biblib.load_bib(args.bib)}
    rows = [json.loads(l) for f in args.refs for l in f.read_text(encoding="utf-8").splitlines() if l.strip()]
    by_style: dict[str, dict[str, dict]] = collections.defaultdict(dict)
    per_record: dict[str, dict[str, str]] = collections.defaultdict(dict)
    for r in rows:
        by_style[r["style"]][r["key"]] = r
        per_record[r["key"]][r["style"]] = r["ref_string"]
    styles = sorted(by_style)

    # --- cross-style identical-output rate -------------------------------
    n_rec = len(per_record)
    distinct = [len(set(v.values())) for v in per_record.values()]
    n_styles = max((len(v) for v in per_record.values()), default=0)
    collided = sum(1 for d in distinct if d < n_styles)
    pair_collisions: collections.Counter = collections.Counter()
    for v in per_record.values():
        items = list(v.items())
        for i in range(len(items)):
            for j in range(i + 1, len(items)):
                if items[i][1] == items[j][1]:
                    pair_collisions[tuple(sorted((items[i][0], items[j][0])))] += 1

    # --- write report ----------------------------------------------------
    out = []
    out.append("# Phase 2 生成後検証（突き合わせ＋スタイル多様性）\n")
    out.append(f"対象: {n_rec} レコード × {n_styles} スタイル。random seed = {args.seed}。\n")

    out.append("## スタイル間 出力同一率\n")
    out.append(f"- 1 レコードあたりの相異なる文字列数: 平均 {sum(distinct)/len(distinct):.2f} / {n_styles}")
    out.append(f"- いずれか 2 スタイルが同一文字列になるレコード: **{collided} / {n_rec}"
               f"（{100*collided/n_rec:.1f}%）**")
    out.append(f"- 全スタイル同一のレコード: {sum(1 for d in distinct if d==1)}\n")
    if pair_collisions:
        out.append("スタイル対ごとの同一出力レコード数（上位）:\n")
        out.append("| スタイル対 | 同一レコード数 |")
        out.append("|---|---|")
        for (a, b), c in pair_collisions.most_common(10):
            out.append(f"| {a} × {b} | {c} |")
        out.append("")
    else:
        out.append("スタイル対の同一出力: なし（全対で相違）。\n")

    out.append("## generation_status 内訳（スタイル別）\n")
    out.append("| style | ok | ok_partial | failed |")
    out.append("|---|---|---|---|")
    for st in styles:
        c = collections.Counter(
            ("failed" if r["generation_status"].startswith("failed")
             else "ok_partial" if r["generation_status"].startswith("ok_partial")
             else "ok")
            for r in by_style[st].values())
        out.append(f"| {st} | {c['ok']} | {c['ok_partial']} | {c['failed']} |")
    out.append("")

    rng = random.Random(args.seed)
    for st in styles:
        keys = sorted(by_style[st])
        sample = sorted(rng.sample(keys, min(args.n, len(keys))))
        out.append(f"## {st}: ランダム {len(sample)} 件 突き合わせ\n")
        out.append("| key | type | status | 原 BibTeX（圧縮） | ref_string |")
        out.append("|---|---|---|---|---|")
        for k in sample:
            r = by_style[st][k]
            e = orig.get(k, {})
            o = compact_orig(e).replace("|", "\\|")
            rs = r["ref_string"].replace("|", "\\|")
            out.append(f"| {k} | {e.get('ENTRYTYPE','?')} | {r['generation_status']} | {o} | {rs} |")
        out.append("")

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text("\n".join(out), encoding="utf-8")
    print(f"wrote {args.out}  ({n_rec} records, {n_styles} styles; "
          f"collided {collided}/{n_rec})", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
