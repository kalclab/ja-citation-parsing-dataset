#!/usr/bin/env python3
"""Phase 2 (.bst): generate reference strings for BibTeX .bst styles.

Pipeline per style: write a minimal upLaTeX document that \\nocite{*} all entries,
run upLaTeX (to emit the .aux) then upBibTeX (to emit the .bbl), then parse the
.bbl into per-key reference strings. The .bbl carries the formatted output; we
de-TeX it into a plain string rather than compiling to PDF (CJK PDF text
extraction is unreliable, and the spec asks for .bbl extraction).

All candidate .bst call the pTeX-only builtin `is.kanji.str$`, so upBibTeX /
pBibTeX is required -- standard bibtex will not run them.

Output: JSONL, one object per (key x style):
    {"key", "style", "style_impl": "bst", "ref_string", "generation_status"}

Requires TeX Live with upLaTeX/upBibTeX on PATH. If not found, the known
user-space install (~/texlive/2026/bin/*) is auto-added; override with TEXBIN.

Usage:
    uv run python scripts/generate_refs_bst/generate_refs_bst.py \
        --bib scripts/fixtures/test.bib \
        --out data/interim/survey_0b/out/ref_strings_bst.jsonl
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from glob import glob
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
STYLES_JSON = REPO / "scripts" / "styles.json"
BST_DIR = REPO / "scripts" / "generate_refs_bst" / "bst"

sys.path.insert(0, str(REPO / "scripts"))
import biblib  # noqa: E402

# Classic jBibTeX styles ({ff}{ll} formatting). They differ from jecon/CSL in
# two input expectations, both handled in a per-style temp copy (derived .bib
# itself is unchanged):
#   1. Names: they expect the traditional "姓 名" space form. The derived .bib is
#      comma-canonicalised ("姓, 名") for jecon/CSL, which reverses Japanese names
#      to 名姓 under {ff}{ll}. We convert Japanese names back to space form here.
#      Romaji "Last, First" is left as comma (renders correctly as First Last).
#   2. @misc: they read `howpublished`/`note`, not `url`/`urldate`, so we mirror
#      the URL into howpublished=\url{...} (+ note from urldate).
# jecon(-mod) reads `url` directly and handles Japanese names from comma form,
# so it is intentionally excluded from both transforms.
CLASSIC_STYLES = {"jplain", "junsrt", "ipsjsort", "ipsjunsrt", "jsai"}
_NAME_FIELDS = ("author", "editor", "translator")


def prepare_bib(src: Path, dst: Path, style: str) -> None:
    """Copy the bib to dst; for classic styles apply space-form names + @misc URL."""
    if style not in CLASSIC_STYLES:
        shutil.copy(src, dst)
        return
    entries = biblib.load_bib(src)
    for e in entries:
        for fld in _NAME_FIELDS:
            if e.get(fld, "").strip():
                new, n = biblib.to_space_form(e[fld])
                if n:
                    e[fld] = new
        if e.get("ENTRYTYPE", "").lower() == "misc":
            url = e.get("url", "").strip()
            if url and not e.get("howpublished", "").strip():
                e["howpublished"] = f"\\url{{{url}}}"
            urldate = e.get("urldate", "").strip()
            if urldate and not e.get("note", "").strip():
                e["note"] = f"{urldate} 参照"
    biblib.write_bib(entries, dst)


def ensure_texbin() -> str | None:
    """Return the directory holding upbibtex, adding a fallback to PATH if needed."""
    if shutil.which("upbibtex"):
        return None
    cand = os.environ.get("TEXBIN")
    cands = [cand] if cand else glob(str(Path.home() / "texlive" / "*" / "bin" / "*"))
    for d in cands:
        if d and Path(d, "upbibtex").exists():
            os.environ["PATH"] = f"{d}:{os.environ.get('PATH','')}"
            return d
    return None


# --- .bbl -> plain string -------------------------------------------------

_SC = re.compile(r"\{\\(?:sc|bf|it|em|rm|tt|sf)\s+([^{}]*)\}")
_HREF = re.compile(r"\\href\{[^}]*\}\{([^}]*)\}")
_URLLIKE = re.compile(r"\\(?:nolinkurl|url|doi|texttt|path)\{([^}]*)\}")


def detex(s: str) -> str:
    """Reduce .bbl TeX markup to the plain string a reader would see."""
    s = s.replace("\\newblock", " ")
    s = re.sub(r"\\bysame(?:jp)?", "", s)
    s = re.sub(r"\\urlstyle\{[^}]*\}", "", s)   # formatting-only wrapper; drop first
    for _ in range(3):
        # resolve inner url/doi macros before the enclosing \href so its 2nd arg
        # is brace-clean (jecon: \href{doi.org/..}{\urlstyle{tt}\nolinkurl{10..}})
        s = _URLLIKE.sub(r"\1", s)   # \nolinkurl{X} \url{X} \doi{X} \path{X}
        s = _HREF.sub(r"\1", s)      # \href{A}{B} -> B
        s = _SC.sub(r"\1", s)        # {\sc X} -> X
    s = s.replace("~", " ")          # NBSP / name separator in jsai
    s = re.sub(r"\\[\s,;:!]", " ", s)  # spacing macros incl. \<newline> in page ranges
    s = s.replace("\\&", "&").replace("\\%", "%").replace("\\#", "#").replace("\\_", "_")
    s = s.replace("\\/", "")
    s = re.sub(r"\\[a-zA-Z@]+\*?", "", s)     # remaining named control words
    s = re.sub(r"\\([^A-Za-z@])", r"\1", s)   # \<punct> e.g. ipsj's \：  -> keep punct
    s = s.replace("{", "").replace("}", "")
    s = s.replace("---", "—").replace("--", "–")  # TeX en/em dash
    s = re.sub(r"\s+", " ", s).strip()
    return s


def parse_bbl(bbl: str) -> dict[str, str]:
    """Map citation key -> de-TeX'd reference string from a .bbl."""
    m = re.search(r"\\begin\{thebibliography\}\{[^}]*\}(.*?)\\end\{thebibliography\}", bbl, re.S)
    if not m:
        return {}
    region = m.group(1)
    out: dict[str, str] = {}
    parts = re.split(r"(?=\\(?:bibitem|harvarditem))", region)
    for p in parts:
        p = p.strip()
        if p.startswith("\\harvarditem"):
            # natbib (jecon): \harvarditem[short]{full}{year}{key} body
            hm = re.match(r"\\harvarditem(?:\[[^\]]*\])?\{.*?\}\{.*?\}\{([^}]*)\}", p, re.S)
        elif p.startswith("\\bibitem"):
            hm = re.match(r"\\bibitem(?:\[[^\]]*\])?\{([^}]*)\}", p)
        else:
            continue
        if not hm:
            continue
        key = hm.group(1)
        out[key] = detex(p[hm.end():])
    return out


# --- style-specific output fixes ------------------------------------------

_PLAIN_NUM = re.compile(r"[0-9０-９]+")


def fix_jecon_edition(ref: str, edition: str) -> str:
    """Undo jecon's 第…版 wrap when the edition field is already a full phrase.

    jecon renders Japanese-entry editions as 第{edition}版, which is correct
    only for bare-number values (edition={2} -> 第2版). Our records keep the
    source-faithful full designation (第2版, 新装版, 改訂3版, ver.2, POD版 ...),
    so the wrap doubles it (第第2版版) or mis-wraps it (第新装版版, 第ver.2版).
    Replace the wrapped form with the source phrase; bare numbers are left to
    jecon's own (correct) formatting.
    """
    ed = edition.strip()
    if not ed or _PLAIN_NUM.fullmatch(ed):
        return ref
    return ref.replace(f"第{ed}版", ed)


# --- LaTeX doc + run ------------------------------------------------------

def doc_tex(style: str, natbib: bool, bibbase: str) -> str:
    pre = "\\usepackage[numbers]{natbib}\n" if natbib else ""
    return (
        "\\documentclass[uplatex,dvipdfmx]{jsarticle}\n"
        f"{pre}"
        "\\makeatletter\\@ifundefined{doi}{\\newcommand{\\doi}[1]{#1}}{}\\makeatother\n"
        "\\begin{document}\n"
        "\\nocite{*}\n"
        f"\\bibliographystyle{{{style}}}\n"
        f"\\bibliography{{{bibbase}}}\n"
        "\\end{document}\n"
    )


def run_style(bib_path: Path, style: str, natbib: bool) -> tuple[dict[str, str] | None, str]:
    with tempfile.TemporaryDirectory() as td:
        d = Path(td)
        prepare_bib(bib_path, d / "refs.bib", style)
        (d / "doc.tex").write_text(doc_tex(style, natbib, "refs"), encoding="utf-8")
        env = dict(os.environ, BSTINPUTS=f"{BST_DIR}:", BIBINPUTS=f"{d}:")
        up = subprocess.run(["uplatex", "-interaction=nonstopmode", "doc.tex"],
                            cwd=d, env=env, capture_output=True, text=True)
        if not (d / "doc.aux").exists():
            return None, "uplatex produced no .aux"
        bib = subprocess.run(["upbibtex", "doc"], cwd=d, env=env, capture_output=True, text=True)
        bbl = d / "doc.bbl"
        if not bbl.exists():
            tail = (bib.stdout + bib.stderr).strip().splitlines()[-3:]
            return None, "upbibtex produced no .bbl: " + " | ".join(tail)
        refs = parse_bbl(bbl.read_text(encoding="utf-8"))
        if not refs:
            return None, "empty .bbl (no \\bibitem parsed)"
        return refs, ""


def bib_keys(bib_path: Path) -> list[str]:
    try:
        import bibtexparser  # type: ignore

        parser = bibtexparser.bparser.BibTexParser(common_strings=True)
        parser.ignore_nonstandard_types = False
        with bib_path.open(encoding="utf-8") as fh:
            db = bibtexparser.load(fh, parser=parser)
        return [e["ID"] for e in db.entries]
    except Exception:
        return re.findall(r"^@\w+\s*\{\s*([^,\s]+)\s*,", bib_path.read_text(encoding="utf-8"), re.M)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--bib", type=Path, default=REPO / "scripts" / "fixtures" / "test.bib")
    ap.add_argument("--out", type=Path, default=REPO / "data" / "interim" / "survey_0b" / "out" / "ref_strings_bst.jsonl")
    ap.add_argument("--styles", type=Path, default=STYLES_JSON)
    ap.add_argument("--only", nargs="*", help="subset of style names to run")
    args = ap.parse_args()

    if ensure_texbin() is None and not shutil.which("upbibtex"):
        print("upbibtex not found on PATH and no ~/texlive/*/bin/* fallback. "
              "Install TeX Live (langjapanese) or set TEXBIN.", file=sys.stderr)
        return 1

    styles = json.loads(args.styles.read_text(encoding="utf-8"))["bst"]
    if args.only:
        styles = [s for s in styles if s["style"] in set(args.only)]
    keys = bib_keys(args.bib)
    if not keys:
        print(f"no entries found in {args.bib}", file=sys.stderr)
        return 1
    # {key: entry} to flag container-field drops (e.g. jecon 和文 @inproceedings)
    meta = {e["ID"]: e for e in biblib.load_bib(args.bib)}

    args.out.parent.mkdir(parents=True, exist_ok=True)
    n_ok = n_fail = 0
    with args.out.open("w", encoding="utf-8") as out:
        for s in styles:
            if s.get("source") == "fetch" and s.get("file") and not (REPO / s["file"]).exists():
                refs, reason = None, "style file not fetched; run scripts/generate_refs_bst/fetch_styles.sh"
            else:
                refs, reason = run_style(args.bib, s["style"], s.get("natbib", False))
            for key in keys:
                if refs is None:
                    rec = dict(key=key, style=s["style"], style_impl="bst",
                               ref_string="", generation_status=f"failed: {reason}")
                    n_fail += 1
                elif key in refs and refs[key]:
                    ref = refs[key]
                    if s["style"].startswith("jecon"):
                        edition = meta.get(key, {}).get("edition", "")
                        if edition:
                            ref = fix_jecon_edition(ref, edition)
                    # container フィールドが記録にあるのに出力に現れない組は
                    # ok_partial:<field> として識別可能にする（手整形はしない）。
                    missing = biblib.partial_container_fields(meta.get(key, {}), ref)
                    status = "ok_partial:" + ",".join(missing) if missing else "ok"
                    rec = dict(key=key, style=s["style"], style_impl="bst",
                               ref_string=ref, generation_status=status)
                    n_ok += 1
                else:
                    rec = dict(key=key, style=s["style"], style_impl="bst",
                               ref_string="", generation_status="failed: key absent from .bbl")
                    n_fail += 1
                out.write(json.dumps(rec, ensure_ascii=False) + "\n")
            print(f"[bst] {s['style']:<20} {'OK' if refs is not None else 'FAILED: ' + reason}", file=sys.stderr)

    print(f"wrote {args.out}  (ok={n_ok}, failed={n_fail})", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
