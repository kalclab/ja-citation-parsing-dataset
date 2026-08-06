# Licences

This repository combines original code and data with vendored third-party
style files. The applicable licence depends on the path.

## Original code — MIT

Applies to `scripts/**` except the vendored style files listed below.

> MIT License
>
> Copyright (c) 2026 Anonymous Authors (identity withheld for double-blind review)
>
> Permission is hereby granted, free of charge, to any person obtaining a copy
> of this software and associated documentation files (the "Software"), to deal
> in the Software without restriction, including without limitation the rights
> to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
> copies of the Software, and to permit persons to whom the Software is
> furnished to do so, subject to the following conditions:
>
> The above copyright notice and this permission notice shall be included in
> all copies or substantial portions of the Software.
>
> THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
> IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
> FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
> AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
> LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
> OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
> THE SOFTWARE.

## Original data and documentation — CC BY 4.0

Applies to `manifest.csv`, `key_map.csv`, `sample_100.txt`, `annotations/**`,
and `DATASET.md`.

Licensed under the Creative Commons Attribution 4.0 International licence
(<https://creativecommons.org/licenses/by/4.0/>). Attribute to
"Anonymous Authors" until the companion paper is de-anonymised; a citation
will be provided here afterwards.

Provenance notes:

- `annotations/name_boundaries.jsonl` is derived from National Diet Library
  (NDL) authority and bibliographic data via NDL Search. NDL's bibliographic
  data is freely reusable; this file attributes NDL through the recorded
  `authority_url` identifiers (<https://ndlsearch.ndl.go.jp/help/api/provider>).
- `manifest.csv` contains only record identifiers, source URLs, and our own
  classification columns; it embeds no metadata from the source services.

## Vendored third-party style files — their own licences

| Path | Licence | Origin |
|---|---|---|
| `scripts/csl/sist02.csl`, `jpa2022.csl`, `chicago-author-date.csl` | CC BY-SA 3.0 | Citation Style Language project and the authors named in each file header |
| `scripts/generate_refs_bst/bst/jecon.bst` | LPPL 1.3+ | jecon-bst project (author named in the file header) |
| `scripts/generate_refs_bst/bst/jecon-mod.bst` | LPPL 1.3+ | Modified from `jecon.bst`; renamed as LPPL requires, with the modification documented at the top of the file |

`ipsjsort.bst` and `jsai.bst` are **not** redistributed here (society
distributions without redistribution rights). `scripts/generate_refs_bst/fetch_styles.sh`
downloads them from their official sources for local use.

## Re-fetched bibliographic metadata — source services' terms

Running `scripts/rebuild.py` fetches bibliographic metadata directly from the
original services (J-STAGE, CiNii, NDL Search, Crossref, and the web pages
listed in `manifest.csv`). That metadata is **not** covered by the licences
above: it is obtained under each service's own terms of use, which the person
running the script is responsible for observing. In particular, the J-STAGE
WebAPI terms prohibit keeping API-provided information in machine-readable
form for more than 24 hours, which is why the rebuilt files are not
redistributed in this repository (see README).
