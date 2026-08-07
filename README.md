# Japanese Bibliographic Reference Parsing Dataset (manifest release)

Evaluation dataset for bibliographic-information extraction from Japanese
reference strings. It covers **988 real, verified records** (journal
articles, conference papers, books, and web/grey literature) and, for each
record, reference strings reverse-generated in **7 Japanese citation styles**
with authentic BibTeX/CSL processors. This repository is the companion
artefact of a paper under double-blind review; author and affiliation
information is withheld.

**Version: v1.1** (2026-08-07). See `CHANGELOG.md` for what changed since
v1.0; a rebuild run on this revision reproduces the v1.1 artefacts.

## Why this is a manifest, not the data

The terms of use of some source services — most restrictively the J-STAGE
WebAPI, which prohibits keeping API-provided information in machine-readable
form for more than 24 hours — do not permit redistributing the collected
metadata. This repository therefore ships everything needed to **rebuild the
dataset locally, deterministically, from the original sources**:

| Path | What it is |
|---|---|
| `manifest.csv` | 988 rows: record key, entry type, discipline/subfield, difficulty flags, source name, source URL, original retrieval timestamp |
| `key_map.csv` | Mapping from final keys to per-source provisional keys (pins key assignment during rebuild) |
| `sample_100.txt` | Keys of the 100-record evaluation sample used in the paper |
| `annotations/` | Name-boundary annotations: NDL-authority-based splits (`name_boundaries.jsonl`) and manually/web-verified splits (`manual_name_table.jsonl`) applied during rebuild |
| `annotations/field_overrides.jsonl` | Guarded field corrections applied during rebuild: 10 CiNii `@article` records whose source `volume` embeds the issue number, decoded into `volume` + `number`. Each row records the expected source value and only applies if the re-fetched record still carries it |
| `scripts/` | Collection, rebuild, validation, and reference-string generation pipeline |
| `DATASET.md` | Schema and conventions of the rebuilt artefacts |
| `CHANGELOG.md` | Release history |

The rebuilt files (`dataset/ja_bib_full.bib`, `dataset/ja_bib_derived.bib`,
`dataset/metadata.csv`, `dataset/ref_strings.jsonl`) appear locally after
running the pipeline and are intentionally gitignored.

## Rebuilding the dataset

Prerequisites: [uv](https://docs.astral.sh/uv/) (Python 3.12+), and for
reference-string generation additionally pandoc 3.x (CSL styles) and a
TeX Live installation with upLaTeX/upBibTeX (.bst styles; see
`scripts/generate_refs_bst/README.md`).

```sh
uv sync

# 1) Re-fetch metadata from the original sources and rebuild the dataset
#    (dataset/ja_bib_full.bib, metadata.csv, and the annotation-applied
#    dataset/ja_bib_derived.bib in one go). Polite crawling: >=1.5 s between
#    requests per host — please put your own contact address in the
#    User-Agent constants (rebuild.py reads the one in scripts/collect_jstage.py).
#    A full run makes ~1,300 requests and takes on the order of an hour;
#    use --only-source to run it in stages (results accumulate).
uv run python scripts/rebuild.py

# 2) Generate reference strings in the 7 styles
zsh scripts/generate_refs_bst/fetch_styles.sh   # fetches non-redistributable .bst
uv run python scripts/generate_refs_csl.py --bib dataset/ja_bib_derived.bib --out dataset/ref_strings_csl.jsonl
uv run python scripts/generate_refs_bst/generate_refs_bst.py --bib dataset/ja_bib_derived.bib --out dataset/ref_strings_bst.jsonl
```

Because the sources are live services, individual records may have been
corrected upstream since the original retrieval (timestamps are in
`manifest.csv`); `rebuild.py` reports any record it cannot re-fetch or that
no longer matches expectations rather than silently substituting content.

## The 7 citation styles

| Style | Implementation | Field |
|---|---|---|
| jecon-mod | .bst (upBibTeX) | Economics (humanities/social sciences) |
| ipsjsort | .bst | Information Processing Society of Japan |
| jsai | .bst | Japanese Society for Artificial Intelligence |
| jplain | .bst | Classic jBibTeX |
| sist02 | CSL | Cross-disciplinary (SIST02) |
| jpa2022 | CSL | Psychology |
| chicago-author-date | CSL | Contrastive / mixed-script control |

`jecon-mod` is `jecon.bst` (LPPL 1.3+) with two modifications, both
documented at the top of `scripts/generate_refs_bst/bst/jecon-mod.bst`:

1. **Proceedings title restored.** For Japanese `@inproceedings` without an
   editor, the unmodified style omits the proceedings title, making the venue
   unrecoverable; the modification outputs it. This affects `@inproceedings`
   only — when it was introduced, `@article`/`@book`/`@misc` output was
   byte-identical to the unmodified style.
2. **`\bysame` disabled** (v1.1). `jecon`'s own customisation variable
   `bst.use.bysame` is set to `#0`, so a repeated author is printed in full
   instead of being replaced by a dash. The suppression depends on the
   preceding entry in the same bibliography, which is meaningless for
   reference strings that are used one at a time.

`generate_refs_bst.py` additionally post-processes `jecon` output for the
`edition` field; see `scripts/README.md`.

## Collection ethics

Collection was API-first with 1–2 s waits between requests and gathered
bibliographic metadata only (no full texts or abstracts). robots.txt was
checked per domain before collection; the observed Disallow paths are
implemented in `ROBOTS_DISALLOW` in `scripts/collect_webmisc.py`, which
also gates the rebuild.

## Licensing

See `LICENSE.md`: original code MIT, original data and documentation
CC BY 4.0 (attribution: "Anonymous Authors" until de-anonymisation),
vendored citation-style files under their own licences, and re-fetched
metadata under the source services' terms.
