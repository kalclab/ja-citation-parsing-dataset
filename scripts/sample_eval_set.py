"""Stratified sampling of the 100-record evaluation candidate set.

Produces dataset/sample_100.txt (one citation key per line) from
dataset/metadata.csv, stratified by entry_type × discipline × difficulty.

Constraints (in priority order):
1. entry_type ratio 3:2.5:2.5:2 -> article 30 / inproceedings 25 / book 25 /
   misc 20 (book includes incollection, matching the bok key family).
2. disciplines (人文社会 / 理工 / 医学生命) as even as availability allows within
   each type.
3. difficulty: aim ~35% flagged per discipline cell where both flagged and
   unflagged records exist. Some cells are inherently all-flagged in the corpus
   (ministry/statistics @misc, most @book), so the achieved flagged fraction is
   reported rather than forced — the target is a floor of hard cases, not a cap.

Deterministic (fixed seed) and idempotent. Prints a self-check of the achieved
stratification to stdout.
"""

from __future__ import annotations

import argparse
import csv
import random
from collections import Counter, defaultdict
from pathlib import Path

SEED = 20260807
TYPE_QUOTA = {"article": 30, "inproceedings": 25, "book": 25, "misc": 20}
DISCIPLINES = ["人文社会", "理工", "医学生命"]
FLAG_FRACTION = 0.35


def sample_type(pool: list[dict], quota: int, rng: random.Random) -> list[dict]:
    """Pick `quota` records: even over disciplines, ~FLAG_FRACTION flagged."""
    cells: dict[tuple[str, bool], list[dict]] = defaultdict(list)
    for r in pool:
        cells[(r["discipline"], bool(r["difficulty_flags"]))].append(r)
    for v in cells.values():
        v.sort(key=lambda r: r["key"])

    # discipline targets: even split, remainder to the largest-availability discs
    avail = {d: sum(len(cells[(d, f)]) for f in (True, False)) for d in DISCIPLINES}
    base, rem = divmod(quota, len(DISCIPLINES))
    disc_target = {d: base for d in DISCIPLINES}
    for d in sorted(DISCIPLINES, key=lambda x: (-avail[x], x))[:rem]:
        disc_target[d] += 1

    chosen: list[dict] = []
    for d in DISCIPLINES:
        need = min(disc_target[d], avail[d])
        want_flag = round(need * FLAG_FRACTION)
        flagged, unflagged = cells[(d, True)], cells[(d, False)]
        take_f = min(want_flag, len(flagged))
        take_u = min(need - take_f, len(unflagged))
        take_f = min(need - take_u, len(flagged))  # backfill flagged if unflagged short
        chosen += rng.sample(flagged, take_f) + rng.sample(unflagged, take_u)

    # backfill any global shortfall (rare) from the type's remaining records
    if len(chosen) < quota:
        picked = {r["key"] for r in chosen}
        rest = sorted((r for r in pool if r["key"] not in picked), key=lambda r: r["key"])
        chosen += rng.sample(rest, min(quota - len(chosen), len(rest)))
    return chosen


def sample_type_of(r: dict) -> str:
    return "book" if r["entry_type"] in ("book", "incollection") else r["entry_type"]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dataset-dir", type=Path, default=Path("dataset"))
    ap.add_argument("--out", type=Path, default=Path("dataset/sample_100.txt"))
    args = ap.parse_args()

    rows = list(csv.DictReader((args.dataset_dir / "metadata.csv").open(encoding="utf-8")))
    by_type: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        by_type[sample_type_of(r)].append(r)

    rng = random.Random(SEED)
    selected: list[dict] = []
    for etype in ["article", "inproceedings", "book", "misc"]:
        selected += sample_type(by_type[etype], TYPE_QUOTA[etype], rng)

    keys = sorted(r["key"] for r in selected)
    args.out.write_text("\n".join(keys) + "\n", encoding="utf-8")

    # --- self-check ---
    sel = {r["key"]: r for r in selected}
    print(f"wrote {len(keys)} keys -> {args.out}\n")
    tc = Counter(sample_type_of(r) for r in selected)
    print("entry_type (target 30/25/25/20):")
    for t in ["article", "inproceedings", "book", "misc"]:
        print(f"  {t:<14} {tc[t]:>3} / {TYPE_QUOTA[t]}")
    print("\ntype × discipline:")
    for t in ["article", "inproceedings", "book", "misc"]:
        dc = Counter(r["discipline"] for r in selected if sample_type_of(r) == t)
        print(f"  {t:<14} " + "  ".join(f"{d}:{dc[d]}" for d in DISCIPLINES))
    print("\ndifficulty-flagged fraction:")
    for t in ["article", "inproceedings", "book", "misc"]:
        grp = [r for r in selected if sample_type_of(r) == t]
        f = sum(1 for r in grp if r["difficulty_flags"])
        print(f"  {t:<14} {f}/{len(grp)} ({f / len(grp) * 100:.0f}%)")
    total_f = sum(1 for r in selected if r["difficulty_flags"])
    print(f"  {'OVERALL':<14} {total_f}/{len(selected)} ({total_f / len(selected) * 100:.0f}%)")

    ok = (tc == Counter(TYPE_QUOTA) and len(keys) == 100 and len(set(keys)) == 100)
    print("\nSELF-CHECK:", "PASS" if ok else "CHECK — type quota or uniqueness off")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
