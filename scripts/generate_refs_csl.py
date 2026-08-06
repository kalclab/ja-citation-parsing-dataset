#!/usr/bin/env python3
"""Phase 2 (CSL): generate reference strings for CSL styles via pandoc citeproc.

For each style, pandoc renders the whole bibliography to HTML once; each entry
comes out as <div id="ref-KEY" class="csl-entry">, which lets us map the rendered
string back to its citation key reliably (and preserves cross-entry context such
as year-suffix disambiguation).

Output: JSONL, one object per (key x style):
    {"key", "style", "style_impl": "csl", "ref_string", "generation_status"}

generation_status is "ok" on success, or "failed: <reason>" when the style could
not be run or produced no entry for that key. Failed rows are recorded, never
hand-formatted (per the spec: keep the data's non-artificiality).

Usage:
    uv run python scripts/generate_refs_csl.py \
        --bib scripts/fixtures/test.bib \
        --out data/interim/survey_0b/out/ref_strings_csl.jsonl
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import tempfile
from html.parser import HTMLParser
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
STYLES_JSON = REPO / "scripts" / "styles.json"

sys.path.insert(0, str(REPO / "scripts"))
import biblib  # noqa: E402

# Leading enumerator produced by numbered styles (e.g. sist02 -> "(1) ").
_ENUM_RE = re.compile(r"^\s*(?:\(\d+\)|\[\d+\]|\d+[.)])\s+")

# pandoc's BibTeX reader applies LaTeX semantics to field values, so raw
# specials corrupt titles: `%` truncates the rest of the field (comment), `$`
# toggles math (delimiters dropped), `~` -> space, `\` dropped. `& _ # ^` are
# fine but escaping them too is harmless. We escape a COMPILE-ONLY copy fed to
# pandoc; the derived .bib and the .bst path (which reads fields verbatim via
# upBibTeX) are untouched. Ground-truth notation is unchanged — pandoc renders
# `\%`->`%` etc., so ref_strings still carry the literal character.
_ESC_SKIP = {"ID", "ENTRYTYPE", "url", "doi", "urldate", "eprint", "link"}


def _latex_escape(s: str) -> str:
    s = s.replace("\\", r"\textbackslash{}")
    for a, b in (("&", r"\&"), ("%", r"\%"), ("$", r"\$"), ("#", r"\#"),
                 ("_", r"\_"), ("~", r"\textasciitilde{}"), ("^", r"\textasciicircum{}")):
        s = s.replace(a, b)
    return s


def _escaped_bib(src: Path, dst: Path) -> None:
    entries = biblib.load_bib(src)
    for e in entries:
        for k in list(e):
            if k not in _ESC_SKIP:
                e[k] = _latex_escape(e[k])
    biblib.write_bib(entries, dst)


class _RefExtractor(HTMLParser):
    """Collect the plain-text content of each <div id="ref-KEY"> block."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.refs: dict[str, str] = {}
        self._key: str | None = None
        self._depth = 0
        self._buf: list[str] = []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "div" and a.get("id", "").startswith("ref-"):
            self._key = a["id"][len("ref-"):]
            self._depth = 1
            self._buf = []
        elif self._key is not None and tag == "div":
            self._depth += 1

    def handle_endtag(self, tag):
        if self._key is not None and tag == "div":
            self._depth -= 1
            if self._depth == 0:
                text = re.sub(r"\s+", " ", "".join(self._buf)).strip()
                self.refs[self._key] = text
                self._key = None

    def handle_data(self, data):
        if self._key is not None:
            self._buf.append(data)


def bib_keys(bib_path: Path) -> list[str]:
    """Citation keys in document order. Uses bibtexparser if available, else regex."""
    try:
        import bibtexparser  # type: ignore

        parser = bibtexparser.bparser.BibTexParser(common_strings=True)
        parser.ignore_nonstandard_types = False
        with bib_path.open(encoding="utf-8") as fh:
            db = bibtexparser.load(fh, parser=parser)
        return [e["ID"] for e in db.entries]
    except Exception:
        keys = re.findall(r"^@\w+\s*\{\s*([^,\s]+)\s*,", bib_path.read_text(encoding="utf-8"), re.M)
        return keys


def render_style(bib_path: Path, csl_path: Path) -> tuple[dict[str, str] | None, str]:
    """Return ({key: ref_string}, "") on success, or (None, reason) on failure."""
    with tempfile.TemporaryDirectory() as td:
        esc_bib = Path(td) / "refs.bib"
        _escaped_bib(bib_path, esc_bib)
        md = Path(td) / "doc.md"
        md.write_text('---\nnocite: "@*"\nlang: ja-JP\n---\n', encoding="utf-8")
        cmd = [
            "pandoc", str(md), "--citeproc",
            f"--bibliography={esc_bib}", f"--csl={csl_path}",
            "-t", "html",
        ]
        proc = subprocess.run(cmd, capture_output=True, text=True)
        if proc.returncode != 0:
            reason = proc.stderr.strip().splitlines()[-1] if proc.stderr.strip() else "pandoc error"
            return None, reason
        ext = _RefExtractor()
        ext.feed(proc.stdout)
        return ext.refs, ""


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--bib", type=Path, default=REPO / "scripts" / "fixtures" / "test.bib")
    ap.add_argument("--out", type=Path, default=REPO / "data" / "interim" / "survey_0b" / "out" / "ref_strings_csl.jsonl")
    ap.add_argument("--styles", type=Path, default=STYLES_JSON)
    ap.add_argument("--only", nargs="*", help="subset of style names to run")
    ap.add_argument("--keep-enumerator", action="store_true",
                    help="番号スタイルの先頭 (n)/[n]/n. を残す（既定は除去。番号はバッチ順序の人工物で書誌情報を持たないため）")
    args = ap.parse_args()

    styles = json.loads(args.styles.read_text(encoding="utf-8"))["csl"]
    if args.only:
        styles = [s for s in styles if s["style"] in set(args.only)]
    keys = bib_keys(args.bib)
    if not keys:
        print(f"no entries found in {args.bib}", file=sys.stderr)
        return 1
    meta = {e["ID"]: e for e in biblib.load_bib(args.bib)}

    args.out.parent.mkdir(parents=True, exist_ok=True)
    n_ok = n_fail = 0
    with args.out.open("w", encoding="utf-8") as out:
        for s in styles:
            csl_path = REPO / s["file"]
            refs, reason = render_style(args.bib, csl_path)
            for key in keys:
                if refs is None:
                    rec = dict(key=key, style=s["style"], style_impl="csl",
                               ref_string="", generation_status=f"failed: {reason}")
                    n_fail += 1
                elif key in refs and refs[key]:
                    text = refs[key]
                    if not args.keep_enumerator:
                        text = _ENUM_RE.sub("", text)
                    missing = biblib.partial_container_fields(meta.get(key, {}), text)
                    status = "ok_partial:" + ",".join(missing) if missing else "ok"
                    rec = dict(key=key, style=s["style"], style_impl="csl",
                               ref_string=text, generation_status=status)
                    n_ok += 1
                else:
                    rec = dict(key=key, style=s["style"], style_impl="csl",
                               ref_string="", generation_status="failed: no entry in output")
                    n_fail += 1
                out.write(json.dumps(rec, ensure_ascii=False) + "\n")
            status = "OK" if refs is not None else f"FAILED ({reason})"
            print(f"[csl] {s['style']:<20} {status}", file=sys.stderr)

    print(f"wrote {args.out}  (ok={n_ok}, failed={n_fail})", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
