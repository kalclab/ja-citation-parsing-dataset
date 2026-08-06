"""Merge per-source intermediate records into the release BibTeX + metadata.

Reads data/interim/<source>/records.jsonl (schema: docs/phase1_conventions.md),
detects cross-source duplicates, assigns final citation keys, and writes
dataset/ja_bib_full.bib and dataset/metadata.csv.

Idempotent: identical input -> byte-identical output. All ordering is by a
stable sort on provisional_key, so results do not depend on filesystem or
dict iteration order.

Duplicate detection (three independent match keys, unioned transitively):
  - DOI equality (prefix/scheme-normalised, case-folded)
  - ISBN equality (hyphen/space-stripped, case-folded)
  - normalised-title + year equality (NFKC fold, whitespace/punct removed);
    normalisation is internal to matching and never affects output notation.

Keep-decision within a duplicate cluster (deterministic):
  1. highest field completeness (most non-empty BibTeX fields),
  2. then source priority (jstage > crossref > cinii > ndl > anlp > webmisc),
  3. then lexicographically smallest provisional_key.
Dropped members are logged to stdout with the winning key and match reason.

Key assignment: art/inp/bok/web prefix by entry_type (incollection shares the
bok counter), 4-digit sequential within each family, numbered in provisional_key
order.
"""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

import biblib
from biblib import Record

# Tie-break priority when completeness is equal (lower index wins).
SOURCE_PRIORITY = ["jstage", "crossref", "cinii", "ndl", "anlp", "webmisc"]


def _source_rank(source: str) -> tuple[int, str]:
    try:
        return (SOURCE_PRIORITY.index(source), source)
    except ValueError:
        return (len(SOURCE_PRIORITY), source)


class _UnionFind:
    def __init__(self, n: int) -> None:
        self.parent = list(range(n))

    def find(self, x: int) -> int:
        while self.parent[x] != x:
            self.parent[x] = self.parent[self.parent[x]]
            x = self.parent[x]
        return x

    def union(self, a: int, b: int) -> None:
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.parent[max(ra, rb)] = min(ra, rb)


def cluster_duplicates(records: list[Record]) -> list[list[int]]:
    """Return index clusters of mutually-duplicate records."""
    uf = _UnionFind(len(records))
    key_to_first: dict[tuple[str, str], int] = {}
    for idx, rec in enumerate(records):
        for key in biblib.dedup_keys(rec.bibtex_fields):
            if key in key_to_first:
                uf.union(key_to_first[key], idx)
            else:
                key_to_first[key] = idx
    clusters: dict[int, list[int]] = {}
    for idx in range(len(records)):
        clusters.setdefault(uf.find(idx), []).append(idx)
    return list(clusters.values())


def _keep_sort_key(rec: Record) -> tuple:
    # Sort ascending; first element is the kept record.
    return (-rec.completeness(), _source_rank(rec.source), rec.provisional_key)


def _match_reason(kept: Record, dropped: Record) -> str:
    reasons = []
    if (d := biblib.norm_doi(kept.bibtex_fields)) and d == biblib.norm_doi(dropped.bibtex_fields):
        reasons.append("doi")
    if (i := biblib.norm_isbn(kept.bibtex_fields)) and i == biblib.norm_isbn(dropped.bibtex_fields):
        reasons.append("isbn")
    if (t := biblib.norm_title_year(kept.bibtex_fields)) and t == biblib.norm_title_year(dropped.bibtex_fields):
        reasons.append("title+year")
    return ",".join(reasons) or "transitive"


def resolve(records: list[Record]) -> tuple[list[Record], list[tuple[Record, Record, str]]]:
    """Return (kept records, dropped=[(dropped, kept, reason), ...])."""
    kept: list[Record] = []
    dropped: list[tuple[Record, Record, str]] = []
    for cluster in cluster_duplicates(records):
        members = sorted((records[i] for i in cluster), key=_keep_sort_key)
        winner = members[0]
        kept.append(winner)
        for loser in members[1:]:
            dropped.append((loser, winner, _match_reason(winner, loser)))
    return kept, dropped


def assign_keys(kept: list[Record]) -> list[tuple[str, Record]]:
    """Assign final keys; return [(key, record), ...] in output order."""
    counters: dict[str, int] = {}
    assigned: list[tuple[str, Record]] = []
    # Group by prefix, number within group in provisional_key order.
    by_prefix: dict[str, list[Record]] = {}
    for rec in kept:
        prefix = biblib.TYPE_PREFIX[rec.entry_type]
        by_prefix.setdefault(prefix, []).append(rec)
    for prefix in sorted(by_prefix, key=lambda p: biblib.PREFIX_ORDER[p]):
        for rec in sorted(by_prefix[prefix], key=lambda r: r.provisional_key):
            counters[prefix] = counters.get(prefix, 0) + 1
            key = f"{prefix}{counters[prefix]:04d}"
            assigned.append((key, rec))
    return assigned


def pin_keys(records: list[Record], key_map: Path) -> tuple[list[tuple[str, Record]], list[str]]:
    """Take final keys from an existing key_map.csv instead of re-assigning them.

    scripts/rebuild.py 用。マニフェストは重複解決後の生存レコードだけを載せるため、
    再取得したレコード集合に対して重複検出・採番をやり直すと、上流の異動ひとつで
    通し番号が総ずれしうる。表に載っている provisional_key だけを、その最終キー
    （art/inp/bok/web + 連番）で出力し、順序も採番時と同じ「プレフィックス順 →
    キー順」に固定する。表にない provisional_key は返り値の第2要素で報告する。

    Returns ([(key, record), ...] in output order, unknown provisional_keys).
    """
    prov2key: dict[str, str] = {}
    with key_map.open(encoding="utf-8", newline="") as fh:
        for row in csv.DictReader(fh):
            prov2key[row["provisional_key"]] = row["key"]
    assigned: list[tuple[str, Record]] = []
    unknown: list[str] = []
    for rec in records:
        key = prov2key.get(rec.provisional_key)
        if key is None:
            unknown.append(rec.provisional_key)
            continue
        assigned.append((key, rec))
    assigned.sort(key=lambda kr: (biblib.PREFIX_ORDER.get(kr[0][:3], 99), kr[0]))
    return assigned, unknown


def to_bib_entry(key: str, rec: Record) -> dict:
    entry = {"ENTRYTYPE": rec.entry_type, "ID": key}
    for fname, fval in rec.bibtex_fields.items():
        if str(fval).strip():
            entry[fname] = str(fval)
    return entry


def write_metadata(assigned: list[tuple[str, Record]], path: Path) -> None:
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=biblib.METADATA_COLUMNS)
        writer.writeheader()
        for key, rec in assigned:
            writer.writerow({
                "key": key,
                "entry_type": rec.entry_type,
                "discipline": rec.discipline,
                "subfield": rec.subfield,
                "difficulty_flags": ";".join(rec.difficulty_flags),
                "source_name": rec.source_name,
                "source_url": rec.source_url,
                "retrieved_at": rec.retrieved_at,
                "notes": rec.notes,
            })


def write_keymap(assigned: list[tuple[str, Record]], path: Path) -> None:
    """final key -> provisional_key map, for joining enrichment tables keyed by
    provisional_key onto the released (final-key) dataset."""
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(["key", "provisional_key", "source", "entry_type"])
        for key, rec in assigned:
            writer.writerow([key, rec.provisional_key, rec.source, rec.entry_type])


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-dir", type=Path, default=Path("data/interim"),
                        help="dir containing <source>/records.jsonl (default: data/interim)")
    parser.add_argument("--output-dir", type=Path, default=Path("dataset"),
                        help="dir for ja_bib_full.bib + metadata.csv (default: dataset)")
    parser.add_argument("--key-map", type=Path, default=None,
                        help="既存の key_map.csv を与えると最終キーを再採番せず固定する "
                             "(rebuild 用; 重複解決は行わない)")
    args = parser.parse_args()

    records = biblib.load_records(args.input_dir)
    unknown: list[str] = []
    if args.key_map:
        assigned, unknown = pin_keys(records, args.key_map)
        dropped = []
    else:
        kept, dropped = resolve(records)
        assigned = assign_keys(kept)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    biblib.write_bib([to_bib_entry(k, r) for k, r in assigned],
                     args.output_dir / "ja_bib_full.bib")
    write_metadata(assigned, args.output_dir / "metadata.csv")
    write_keymap(assigned, args.output_dir / "key_map.csv")

    counts: dict[str, int] = {}
    for key, _ in assigned:
        counts[key[:3]] = counts.get(key[:3], 0) + 1
    print(f"input records: {len(records)}")
    if unknown:
        print(f"not in key map (skipped): {len(unknown)}")
        for prov in unknown:
            print(f"  UNMAPPED {prov}")
    print(f"duplicates dropped: {len(dropped)}")
    for loser, winner_rec, reason in dropped:
        winner_key = next(k for k, r in assigned if r is winner_rec)
        print(f"  DROP {loser.provisional_key} ({loser.source}) "
              f"-> kept {winner_key} [{reason}]")
    print(f"final records: {len(assigned)}")
    for prefix in sorted(counts, key=lambda p: biblib.PREFIX_ORDER.get(p, 99)):
        print(f"  {prefix}: {counts[prefix]}")


if __name__ == "__main__":
    main()
