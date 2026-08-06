"""Validate the release dataset (dataset/ja_bib_full.bib + metadata.csv).

Checks (per ja_bibtex_collection_prompt.md 検証チェックリスト):
  - whole .bib parses with bibtexparser, no errors;
  - citation keys unique, and .bib IDs == metadata keys (same set);
  - per-type required fields present (see biblib.REQUIRED_FIELDS);
    a `nonstandard_volume`-flagged @article/@incollection may satisfy the
    `volume` requirement with `number`;
  - every metadata row has a non-empty source_url;
  - difficulty_flags drawn only from the controlled vocabulary.
Prints distribution tables (by type / discipline / difficulty flag) to stdout.
Exit code 0 on success, 1 on any failure.
"""

from __future__ import annotations

import argparse
import csv
import sys
from collections import Counter
from pathlib import Path

import bibtexparser
from bibtexparser.bparser import BibTexParser

import biblib


def load_bib(path: Path):
    parser = BibTexParser(common_strings=True)
    parser.ignore_nonstandard_types = False
    return bibtexparser.loads(path.read_text(encoding="utf-8"), parser)


def load_metadata(path: Path) -> dict[str, dict]:
    rows: dict[str, dict] = {}
    with path.open(encoding="utf-8", newline="") as fh:
        for row in csv.DictReader(fh):
            rows[row["key"]] = row
    return rows


def _has(entry: dict, requirement) -> bool:
    names = requirement if isinstance(requirement, tuple) else (requirement,)
    return any(str(entry.get(n, "")).strip() for n in names)


def check_required(entry: dict, flags: set[str]) -> list[str]:
    etype = entry.get("ENTRYTYPE", "")
    missing = []
    for req in biblib.REQUIRED_FIELDS.get(etype, []):
        if _has(entry, req):
            continue
        if (req == "volume" and biblib.NONSTANDARD_VOLUME_FLAG in flags
                and str(entry.get("number", "")).strip()):
            continue  # documented exception: 通巻表記のみ
        missing.append(req if isinstance(req, str) else "|".join(req))
    return missing


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset-dir", type=Path, default=Path("dataset"))
    args = parser.parse_args()

    bib_path = args.dataset_dir / "ja_bib_full.bib"
    meta_path = args.dataset_dir / "metadata.csv"
    errors: list[str] = []

    try:
        db = load_bib(bib_path)
    except Exception as exc:  # noqa: BLE001 - report any parse failure as a check result
        print(f"FAIL: BibTeX parse error: {exc}")
        return 1
    metadata = load_metadata(meta_path)

    entries = db.entries
    bib_keys = [e["ID"] for e in entries]

    # key uniqueness + bib/metadata correspondence
    dup_bib = [k for k, n in Counter(bib_keys).items() if n > 1]
    if dup_bib:
        errors.append(f"duplicate keys in .bib: {sorted(dup_bib)}")
    dup_meta = [k for k, n in Counter(metadata.keys()).items() if n > 1]
    if dup_meta:
        errors.append(f"duplicate keys in metadata.csv: {sorted(dup_meta)}")
    only_bib = set(bib_keys) - set(metadata)
    only_meta = set(metadata) - set(bib_keys)
    if only_bib:
        errors.append(f"keys in .bib but not metadata: {sorted(only_bib)}")
    if only_meta:
        errors.append(f"keys in metadata but not .bib: {sorted(only_meta)}")

    # per-entry checks
    for entry in entries:
        key = entry["ID"]
        row = metadata.get(key, {})
        flags = {f for f in (row.get("difficulty_flags", "") or "").split(";") if f}
        for missing in [check_required(entry, flags)]:
            if missing:
                errors.append(f"{key} ({entry.get('ENTRYTYPE')}): missing required {missing}")
        etype_meta = row.get("entry_type", "")
        if row and etype_meta and etype_meta != entry.get("ENTRYTYPE"):
            errors.append(f"{key}: entry_type mismatch bib={entry.get('ENTRYTYPE')} meta={etype_meta}")

    # metadata-level checks
    for key, row in metadata.items():
        if not (row.get("source_url", "") or "").strip():
            errors.append(f"{key}: empty source_url")
        bad = {f for f in (row.get("difficulty_flags", "") or "").split(";") if f} - biblib.DIFFICULTY_VOCAB
        if bad:
            errors.append(f"{key}: unknown difficulty_flags {sorted(bad)}")

    # --- distribution stats ---
    by_type = Counter(e.get("ENTRYTYPE", "?") for e in entries)
    by_disc = Counter(metadata[k].get("discipline", "?") for k in bib_keys if k in metadata)
    flag_counts: Counter = Counter()
    flagged_by_type: Counter = Counter()
    for entry in entries:
        row = metadata.get(entry["ID"], {})
        flags = [f for f in (row.get("difficulty_flags", "") or "").split(";") if f]
        for f in flags:
            flag_counts[f] += 1
        if flags:
            flagged_by_type[entry.get("ENTRYTYPE", "?")] += 1

    print(f"=== dataset: {len(entries)} records ===\n")
    print("by entry_type:")
    for t, n in sorted(by_type.items()):
        flagged = flagged_by_type.get(t, 0)
        pct = (flagged / n * 100) if n else 0
        print(f"  {t:<14} {n:>4}   flagged: {flagged} ({pct:.0f}%)")
    print("\nby discipline:")
    for d, n in sorted(by_disc.items()):
        print(f"  {d:<14} {n:>4}")
    print("\nby difficulty_flag:")
    for f in sorted(biblib.DIFFICULTY_VOCAB):
        print(f"  {f:<22} {flag_counts.get(f, 0):>4}")

    print()
    if errors:
        print(f"FAIL: {len(errors)} problem(s):")
        for e in errors:
            print(f"  - {e}")
        return 1
    print("PASS: all checks satisfied.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
