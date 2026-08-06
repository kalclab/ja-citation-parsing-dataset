"""Shared helpers for the Phase 1 merge/validate pipeline.

Single source of truth for: the intermediate-record schema contract
(see DATASET.md), type->key-prefix mapping, required-field
policy (ja_bibtex_collection_prompt.md), difficulty-flag vocabulary,
dedup normalisation, and verbatim BibTeX writing.

Design rules encoded here:
- Output preserves source notation. Normalisation (NFKC fold, punctuation
  strip) is used ONLY for internal duplicate detection, never written out.
- BibTeX is written with bibtexparser's verbatim writer: values go inside
  braces with no LaTeX escaping, so full-width symbols / 中黒 / 波ダッシュ
  survive intact (UTF-8).
"""

from __future__ import annotations

import json
import re
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path

from bibtexparser.bibdatabase import BibDatabase
from bibtexparser.bwriter import BibTexWriter

# --- type / key-prefix contract -------------------------------------------

# entry_type -> final-key prefix. incollection shares the @book (bok) counter;
# the true entry_type is preserved in metadata to keep the two distinguishable.
TYPE_PREFIX: dict[str, str] = {
    "article": "art",
    "inproceedings": "inp",
    "book": "bok",
    "incollection": "bok",
    "misc": "web",
}

# Deterministic ordering of the four key families in the merged outputs.
PREFIX_ORDER: dict[str, int] = {"art": 0, "inp": 1, "bok": 2, "web": 3}

# --- required-field policy (prompt "BibTeX の品質基準") --------------------
# A required entry is either a field name (str) or a tuple of alternatives
# (at least one must be present), e.g. author-or-editor for @book.
REQUIRED_FIELDS: dict[str, list] = {
    "article": ["author", "title", "journal", "volume", "pages", "year"],
    "inproceedings": ["author", "title", "booktitle", "year"],
    "book": [("author", "editor"), "title", "publisher", "year"],
    "incollection": [("author", "editor"), "title", "booktitle", "publisher", "year"],
    "misc": ["title", "url", "urldate"],
}

# Narrow, documented exception: a @article/@incollection flagged
# `nonstandard_volume` (通巻表記のみ 等) may satisfy the `volume` requirement
# with `number`. Keeps validation meaningful without rejecting legitimately
# volume-less Japanese periodicals. Surfaced in reports for ratification.
NONSTANDARD_VOLUME_FLAG = "nonstandard_volume"

DIFFICULTY_VOCAB: set[str] = {
    "subtitle",
    "edited_volume",
    "translated",
    "institutional_author",
    "nonstandard_volume",
    "page_style",
    "wareki",
    "english_mixed",
}

# Canonical field emission order for readability + deterministic output.
# Fields not listed are appended alphabetically by the writer.
FIELD_ORDER: tuple[str, ...] = (
    "author", "editor", "translator",
    "title", "booktitle", "journal",
    "publisher", "address", "series", "edition",
    "volume", "number", "pages", "year",
    "issn", "isbn", "doi", "url", "urldate",
    "howpublished", "organization", "note",
)

METADATA_COLUMNS: tuple[str, ...] = (
    "key", "entry_type", "discipline", "subfield",
    "difficulty_flags", "source_name", "source_url", "retrieved_at", "notes",
)


@dataclass
class Record:
    """One intermediate record (data/interim/<source>/records.jsonl)."""

    provisional_key: str
    entry_type: str
    bibtex_fields: dict[str, str]
    source: str  # directory name under interim/ (jstage, cinii, ...)
    discipline: str = ""
    subfield: str = ""
    difficulty_flags: list[str] = field(default_factory=list)
    source_name: str = ""
    source_url: str = ""
    retrieved_at: str = ""
    notes: str = ""

    @classmethod
    def from_json(cls, obj: dict, source: str) -> "Record":
        return cls(
            provisional_key=obj["provisional_key"],
            entry_type=obj["entry_type"],
            bibtex_fields={k: str(v) for k, v in obj.get("bibtex_fields", {}).items()},
            source=source,
            discipline=obj.get("discipline", ""),
            subfield=obj.get("subfield", ""),
            difficulty_flags=list(obj.get("difficulty_flags", [])),
            source_name=obj.get("source_name", ""),
            source_url=obj.get("source_url", ""),
            retrieved_at=obj.get("retrieved_at", ""),
            notes=obj.get("notes", ""),
        )

    def completeness(self) -> int:
        """Number of non-empty BibTeX fields (dedup keep-decision score)."""
        return sum(1 for v in self.bibtex_fields.values() if str(v).strip())


def load_records(input_dir: Path) -> list[Record]:
    """Read every <source>/records.jsonl under input_dir.

    Idempotent within a source: later duplicates of the same
    provisional_key overwrite earlier ones (last wins).
    """
    records: list[Record] = []
    for jsonl in sorted(input_dir.glob("*/records.jsonl")):
        source = jsonl.parent.name
        seen: dict[str, int] = {}
        for line in jsonl.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            rec = Record.from_json(json.loads(line), source)
            if rec.provisional_key in seen:
                records[seen[rec.provisional_key]] = rec
            else:
                seen[rec.provisional_key] = len(records)
                records.append(rec)
    return records


# --- dedup normalisation (internal only) ----------------------------------

def norm_doi(fields: dict[str, str]) -> str | None:
    doi = fields.get("doi", "").strip()
    if not doi:
        return None
    doi = re.sub(r"^https?://(dx\.)?doi\.org/", "", doi, flags=re.I)
    return doi.lower().rstrip("/") or None


def norm_isbn(fields: dict[str, str]) -> str | None:
    isbn = fields.get("isbn", "").strip()
    if not isbn:
        return None
    isbn = re.sub(r"[\s-]", "", isbn).lower()
    return isbn or None


def norm_title_year(fields: dict[str, str]) -> str | None:
    title = fields.get("title", "")
    year = fields.get("year", "").strip()
    if not title or not year:
        return None
    t = unicodedata.normalize("NFKC", title).lower()
    t = re.sub(r"\s+", "", t)
    # drop punctuation / symbols (Unicode P* and S* categories)
    t = "".join(c for c in t if not unicodedata.category(c)[0] in ("P", "S"))
    if not t:
        return None
    return f"{t}::{year}"


def dedup_keys(fields: dict[str, str]) -> list[tuple[str, str]]:
    """Namespaced match keys for a record: (kind, value)."""
    keys: list[tuple[str, str]] = []
    if (d := norm_doi(fields)) is not None:
        keys.append(("doi", d))
    if (i := norm_isbn(fields)) is not None:
        keys.append(("isbn", i))
    if (ty := norm_title_year(fields)) is not None:
        keys.append(("title_year", ty))
    return keys


# --- BibTeX writing (verbatim) --------------------------------------------

def make_writer() -> BibTexWriter:
    w = BibTexWriter()
    w.indent = "  "
    w.add_trailing_comma = False
    w.display_order = FIELD_ORDER
    w.order_entries_by = None  # caller pre-sorts entries
    w.contents = ["entries"]
    return w


def write_bib(entries: list[dict], path: Path) -> None:
    """Write BibTeX entries verbatim (no escaping) as UTF-8.

    `entries` are bibtexparser-style dicts already carrying ID/ENTRYTYPE.
    Caller controls order; the writer preserves it.
    """
    db = BibDatabase()
    db.entries = entries
    path.write_text(make_writer().write(db), encoding="utf-8")


def load_bib(path: Path) -> list[dict]:
    """Load a .bib file into bibtexparser-style entry dicts (ID/ENTRYTYPE + fields).

    Values are kept verbatim (no @string interpolation, non-standard types kept)
    so full-width symbols / 中黒 / 波ダッシュ survive round-trips via write_bib.
    """
    import bibtexparser
    from bibtexparser.bparser import BibTexParser

    parser = BibTexParser(common_strings=True)
    parser.ignore_nonstandard_types = False
    parser.interpolate_strings = False
    with Path(path).open(encoding="utf-8") as fh:
        return bibtexparser.load(fh, parser=parser).entries


# --- Japanese author-name handling (Phase 2 派生 .bib) ---------------------
# BibTeX parses "姓 名" (single space, no comma) as given="姓" family="名",
# reversing/dropping the surname in (u)pBibTeX and citeproc (see style_survey).
# The fix lives ONLY in the derived .bib: convert Japanese-only "姓 名" -> "姓, 名"
# (BibTeX's Last, First). Romaji / institutional / already-comma names are left
# untouched. Source ja_bib_full.bib is never modified.

# Hiragana, Katakana (+ phonetic ext / halfwidth), CJK ideographs (+ ext A),
# iteration marks, chouon. A name is "Japanese-only" if every non-space char is
# in one of these ranges.
_JP_CHAR = re.compile(
    r"[々〆〻"          # 々 〆 〻 iteration marks
    r"぀-ゟ"                # Hiragana
    r"゠-ヿ"                # Katakana (incl. ・ ー)
    r"ㇰ-ㇿｦ-ﾝ"   # Katakana phonetic ext / halfwidth
    r"㐀-䶿一-鿿"   # CJK ext A / CJK Unified
    r"]"
)
_WS_SPLIT = re.compile(r"[ 　]+")   # half-width or full-width space
_AND_SPLIT = re.compile(r"\s+and\s+")


def _is_japanese_only(name: str) -> bool:
    core = _WS_SPLIT.sub("", name)
    return bool(core) and all(_JP_CHAR.match(c) for c in core)


def japanese_name_to_comma(name: str) -> tuple[str, bool, str]:
    """One personal name -> (converted, changed, reason).

    Converts a Japanese-only "姓 名" (exactly one internal space) to "姓, 名".
    reason in: converted / already-comma / no-space / multi-space / not-japanese.
    Non-converting reasons leave the name verbatim.
    """
    n = name.strip()
    if "," in n:
        return n, False, "already-comma"
    parts = _WS_SPLIT.split(n)
    if len(parts) == 1:
        return n, False, "no-space"
    if not _is_japanese_only(n):
        return n, False, "not-japanese"
    if len(parts) != 2:
        return n, False, "multi-space"
    return f"{parts[0]}, {parts[1]}", True, "converted"


# --- container-field completeness (Phase 2 ok_partial marker) -------------
# Fields that carry recoverable venue/container info and should appear in the
# rendered string. If present in the record but absent from the output (e.g.
# jecon drops 和文 @inproceedings booktitle by design), the row is flagged
# ok_partial:<field> so the evaluator can exclude that field per style.
CONTAINER_FIELDS: dict[str, tuple[str, ...]] = {
    "article": ("journal",),
    "inproceedings": ("booktitle",),
    "incollection": ("booktitle",),
}


def norm_for_match(s: str) -> str:
    """Whitespace-insensitive, ASCII-case-insensitive form for substring tests.
    Also drops backslashes so a source `\\&` matches the rendered `&` (styles
    vary full/half-width spacing and lowercase embedded ASCII)."""
    return re.sub(r"[\s\\]+", "", s).lower()


def partial_container_fields(entry: dict, ref_string: str) -> list[str]:
    """Container fields present in `entry` but missing from `ref_string`."""
    et = entry.get("ENTRYTYPE", "").lower()
    return [f for f in CONTAINER_FIELDS.get(et, ())
            if entry.get(f, "").strip() and norm_for_match(entry[f]) not in norm_for_match(ref_string)]


def convert_author_field(value: str) -> tuple[str, list[tuple[str, str]], list[str]]:
    """Convert every name in an ` and `-joined author/editor field.

    Returns (new_value, changes[(before, after)], ambiguous[names left as-is
    that look Japanese but were not safely convertible]).
    """
    names = _AND_SPLIT.split(value.strip())
    out: list[str] = []
    changes: list[tuple[str, str]] = []
    ambiguous: list[str] = []
    for nm in names:
        conv, changed, reason = japanese_name_to_comma(nm)
        out.append(conv)
        if changed:
            changes.append((nm, conv))
        elif reason == "multi-space" and _JP_CHAR.search(nm):
            ambiguous.append(nm)
    return " and ".join(out), changes, ambiguous


# Inverse of the above, for the classic jBibTeX {ff}{ll} styles (jplain /
# ipsjsort / jsai). They expect the traditional "姓 名" space form (First=姓,
# Last=名 -> {ff}{ll} = 姓名). Feeding them the comma-canonicalised derived .bib
# ("姓, 名" = Last=姓, First=名) reverses Japanese names to 名姓. Romaji
# "Last, First" is left as comma (it renders correctly as First Last).
def _comma_to_space_name(name: str) -> tuple[str, bool]:
    n = name.strip()
    if "," not in n:
        return n, False
    parts = [p.strip() for p in n.split(",")]
    if len(parts) != 2 or not parts[0] or not parts[1]:
        return n, False
    if not (_is_japanese_only(parts[0]) and _is_japanese_only(parts[1])):
        return n, False
    return f"{parts[0]} {parts[1]}", True


def to_space_form(value: str) -> tuple[str, int]:
    """Comma-form Japanese names -> space form. Returns (new_value, n_changed)."""
    names = _AND_SPLIT.split(value.strip())
    out: list[str] = []
    n = 0
    for nm in names:
        conv, changed = _comma_to_space_name(nm)
        out.append(conv)
        n += changed
    return " and ".join(out), n
