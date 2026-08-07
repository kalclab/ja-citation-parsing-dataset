# Changelog

Versions refer to the artefacts a rebuild produces from this repository, not
to the repository files alone: re-running `scripts/rebuild.py` and the two
reference-string generators on a given revision reproduces that version.

## v1.1 — 2026-08-07

Three corrections. The record set is unchanged (988 records, 7 styles,
6,916 reference strings); what changed is how some of them render and, for
10 records, two field values.

### `jecon-mod`: `\bysame` disabled

`jecon.bst` replaces a repeated author with a dash (`\bysame`) when the same
author heads consecutive entries of a bibliography. That is correct for a
typeset reference list but wrong for this dataset, whose strings are used one
at a time and in arbitrary order: the author was simply missing from the
string once the TeX markup was reduced to plain text. The style's own
customisation variable `bst.use.bysame` is now `#0`.

### `jecon` `edition` post-fix

`jecon` wraps the `edition` of a Japanese entry as `第{edition}版`, which is
right only for a bare number (`2` → `第2版`). This dataset keeps the
source-faithful full designation (`第2版`, `新装版`, `ver.2`, …), so the wrap
doubled it (`第第2版版`) or mangled it (`第新装版版`). `fix_jecon_edition()` in
`scripts/generate_refs_bst/generate_refs_bst.py` removes the wrap for `jecon`
output only. The BibTeX records are untouched — the other six styles print
`edition` verbatim, where the full designation is the correct Japanese form.

### 10 volume/number decodes

CiNii's `prism:volume` sometimes embeds the issue number (`123-8`, `125巻5号`,
`第124編5号`, `41－1`, `46 (4)`, …). Ten `@article` records carried such a value
and were flagged `nonstandard_volume`. Each was checked by hand against its
CiNii record and decoded into `volume` + `number`; one record whose source
states no issue number keeps `volume` alone, with no issue invented.

The decodes live in `annotations/field_overrides.jsonl` as a guard table:
every row records the value observed at collection time under `from`, and
`rebuild.py` applies the correction only if the re-fetched record still
carries exactly that value. If an upstream record has since changed, the
correction is withheld and the record is reported as a rebuild failure
rather than silently overwritten. The `nonstandard_volume` flag was removed
from these 10 rows of `manifest.csv`; the flag now covers 209 records, and
the volumes that remain flagged are ones no decode applies to (issue-number-
only serials, conference identifiers such as `JSAI2017`, volume designations
such as `上`/`下`).

### Effect on the reference strings

| Style | Strings changed (of 988) |
|---|---|
| jecon-mod | 267 |
| ipsjsort, jsai, jplain, sist02, jpa2022 | 10 each |
| chicago-author-date | 9 |

The 267 `jecon-mod` changes are 239 authors restored by disabling `\bysame`,
18 `edition` fixes, and the 10 volume/number decodes. The other styles are
affected only by the 10 decodes (`chicago-author-date` renders one of them
identically before and after).

## v1.0 — 2026-07-17

Initial release: 988 records collected and verified, reference strings
generated in 7 Japanese citation styles, name-boundary annotations, and the
manifest-plus-rebuild-pipeline distribution.
