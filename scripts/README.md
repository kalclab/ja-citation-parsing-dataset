# Phase 2 生成パイプライン

BibTeX レコードから、承認済み7スタイルの参考文献文字列を逆生成する。スタイル定義は `scripts/styles.json`（単一の真実）。

パイプライン全体:

```
merge_assign_keys.py ─▶ dataset/{ja_bib_full.bib（原本・ソース忠実・不変）, metadata.csv, key_map.csv}
  └─ make_derived_bib.py ─▶ ja_bib_derived.bib   # コンパイル用
       ├─ generate_refs_csl.py ─────▶ ref_strings（csl 3スタイル）
       └─ generate_refs_bst/*.py ───▶ ref_strings（bst 4スタイル）
```

この図の上流（`rebuild.py` の再取得段）で、`annotations/field_overrides.jsonl` のガード付きフィールド置換が当たる。適用点は `rebuild.py` の `stamp()` の末尾、すなわち必須フィールド検査（`check_fields`）より前で、`ja_bib_full.bib` は置換後の値で書き出される。`from` に記した取得時の値と再取得値が食い違うレコードには当てず、他の再取得失敗と同じ経路で報告する（詳細は `rebuild.py` の `apply_overrides`）。

`make_derived_bib.py` の変換（原本は不変）:
1. **典拠 enrichment**（`--names-table`）: NDL 典拠レコード由来の姓名分割（姓, 名）と author 読みの `yomi` を該当レコードに適用。テーブルは `provisional_key` キーなので `key_map.csv`（merge が出力する final↔provisional 対応表）で最終キーへ突合。原本と著者が一致しない件は適用せず stderr にログ。yomi は jecon/ipsjsort の**著者ソートキー**（NDL 図書が持つ題目読みの yomi を上書き）。
2. **手動/Web 確定の姓名分割**（`--manual-table`）: 目視確認＋Web 典拠で確定した名前→分割テーブル（`manual_name_table.jsonl`、名前キー）を、連結形著者に適用（provenance: `manual` / `web-verified`+URL を記録）。既にカンマ形の名は不変。団体・保留名は対象外。
3. **著者カンマ化**: 上記で分割されなかった日本語著者「姓 名」（スペース）→「姓, 名」。原本は BibTeX が姓名を誤認する形のため、必ず派生を各ジェネレータの入力にする。
4. **@misc URL 一本化**: URL を `url` に集約。

`scripts/fixtures/test.bib` は既にカンマ形なので単体で通る。

派生 .bib はカンマ形（姓, 名）で統一するが、古典系 .bst（jplain / ipsjsort / jsai）は
`{ff}{ll}` 整形で「姓 名」空白形を前提とするため、そのままでは日本語著者が名姓に反転する。
これは入力規約の相違であり、`generate_refs_bst.py` の `prepare_bib` がコンパイル直前の一時
.bib のみで日本語著者を空白形へ再変換して解消する（詳細は `generate_refs_bst/README.md`）。

## スタイル一覧（Phase 0-B 承認・2026-07-17、7種）

| style | 実装 | natbib | 分野 |
|---|---|---|---|
| jecon-mod | .bst | 要 | 経済（文系・必須） |
| ipsjsort | .bst | | 情報処理（理工） |
| jsai | .bst | | 人工知能（理工） |
| jplain | .bst | | jBibTeX 古典・整列 |
| sist02 | CSL | | 分野横断 |
| jpa2022 | CSL | | 心理学（文系） |
| chicago-author-date | CSL | | 対照・和欧混在 |

**junsrt は除外（2026-07-17 決定）**: 出力文字列が jplain と per-record で完全一致し、両者の差はリスト（全書誌一覧）の並び順のみ。1 件単位で生成する逆生成データには現れないため、jplain 1 本に集約した。

**jecon-mod.bst — jecon ver.6.6 の改変版（2 箇所）**:

1. **会議録名の出力（2026-07-17 決定）**: 素の jecon.bst は、和文（`is.kanji.entry`）かつ `editor` 空の @inproceedings/@incollection で会議録名（booktitle）を出力しない（`format.output.in.ed.booktitle`, line 2913 の空分岐 `{ }`）。日本の会議録は編者を持たないことが多く、venue が復元不能になるため、当該分岐を `{ format.btitle }` に変更し、会議録名を『…』（`bst.btitle.pre.jp/post.jp`）で題目直後に出力する。公式のカスタマイズ変数・派生版（jecon-a/b/cjk/no-sort/number/reverse/tategaki）にはこの切替が無いことを確認済み。導入時の全件回帰で変化は @inproceedings のみ（会議録名の追加）、@article/@book/@misc はバイト完全一致だった。編者の捏造は一切行わない。
2. **`\bysame` の無効化（v1.1・2026-08-07 決定）**: 公式カスタマイズ変数 `bst.use.bysame` を `#1` → `#0` に変更。同一著者が連続すると横棒（`\bysame`）で著者名を省略する既定挙動は、参照文字列を 1 件単位でシャッフルして使う評価データでは前後文脈依存となり不適当（旧版では省略著者が detex 後に消失していた）。

ref_strings.jsonl の `style` は `jecon-mod`（真正 jecon と区別）。LPPL 1.3+ に従い、改変版はファイル名を変え、冒頭に改変点を明記している。

**jecon の edition 後処理（v1.1）**: jecon は和文エントリの edition を `第{edition}版` で包む（裸の数字 edition のみ正しい）。本データセットの edition はソース忠実な完全表記（`第2版`・`新装版`・`ver.2` 等）のため、`generate_refs_bst.py` の `fix_jecon_edition` が jecon 出力のみ包みを外す。.bib レコード側は不変（他スタイルは edition をそのまま出力するため、`edition = {第2版}` が正しい和文表記になる）。

### generation_status の値

- `ok`: 正常生成。
- `ok_partial:<field>`: 記録に存在する container フィールド（`journal` / `booktitle`）が真正なスタイル挙動で出力に現れない組。ref_string はそのまま採用し、評価側で当該フィールドを除外できるよう識別する（例: jecon の和文・編者なし @inproceedings は booktitle を出力しない → `ok_partial:booktitle`）。判定は空白除去・ASCII 小文字化した部分一致。
- `failed: <理由>`: 生成不可（手整形せず記録のみ）。

## 実行

```sh
# 0) 派生 .bib を生成（原本 → コンパイル用。enrichment 適用は --names-table）
uv run python scripts/make_derived_bib.py --in dataset/ja_bib_full.bib --out dataset/ja_bib_derived.bib \
    --names-table annotations/name_boundaries.jsonl \
    --manual-table annotations/manual_name_table.jsonl   # --key-map 既定: key_map.csv（リポジトリ直下・同梱）

# 1) CSL（pandoc citeproc）。番号は既定で除去、--keep-enumerator で残す
uv run python scripts/generate_refs_csl.py --bib <bib> --out <jsonl> [--only sist02 ...] [--keep-enumerator]

# 2) .bst（upLaTeX + upBibTeX）
uv run python scripts/generate_refs_bst/generate_refs_bst.py --bib <bib> --out <jsonl> [--only jecon ...]
```

デフォルトの `--bib` は `scripts/fixtures/test.bib`（Phase 0-B の実在6レコード）。

## 出力スキーマ（JSONL・1行1サンプル）

```json
{"key": "art0001", "style": "jecon", "style_impl": "bst", "ref_string": "...", "generation_status": "ok"}
```

- `generation_status`: `ok` / `failed: <理由>`。整形失敗の組は記録のみ（手整形しない）。

## 前提

- **pandoc**（CSL 用）: 3.x、citeproc 内蔵。
- **TeX Live（upLaTeX/upBibTeX）**（.bst 用）: 全 .bst が pTeX 専用 `is.kanji.str$` を使うため (u)pBibTeX 必須。導入手順は `scripts/generate_refs_bst/README.md`。`upbibtex` が PATH になければ `~/texlive/*/bin/*` を自動追加、`TEXBIN` で上書き可。
- スタイルファイルのライセンス別入手（詳細は bst README）:
  - 同梱: `scripts/csl/*.csl`（CC BY-SA 3.0）, `bst/jecon.bst`（LPPL 1.3+）
  - 要 fetch（再配布不可のため非同梱・`.gitignore` 済み）: ipsjsort/jsai → `zsh scripts/generate_refs_bst/fetch_styles.sh`
  - TeX Live 由来: jplain/junsrt（`upbibtex` が既定パスで解決）
  - 取得元 URL・バージョンは `fetch_styles.sh` 参照。

## 決定済み事項（2026-07-17）

1. **著者名の書式**: 原本はソース忠実（「姓 名」等をそのまま保持）。BibTeX パース問題は `make_derived_bib.py` が派生 .bib で「姓 名」→「姓, 名」に機械変換して解決。ローマ字・機関著者・カンマ形は不変、判断不能な多空白名は変換せず stderr へログ。
2. **番号スタイルの通し番号**: `generate_refs_csl.py` は既定で先頭の `(1)`／`[1]`／`1.` を除去（番号はバッチ順序の人工物で書誌情報を持たないため）。`--keep-enumerator` で残せる。
3. **@misc の URL 重複**: `make_derived_bib.py` が `url` フィールドへ一本化。`howpublished` は URL を除いた残り（組織名等）のみ保持、URL だけなら削除。

## de-TeX（.bst）の注意

`.bbl` の TeX マークアップをプレーン文字列へ還元している（`\newblock`→空白、`\href/\doi/\nolinkurl`→URL/DOI 文字列、`{\sc }`→本文、`~`→空白、`--`→–、ipsj の `\：`→：）。`\newblock` を空白とみなす前提のため、`\newblock` を句点等に再定義する特殊クラスでは差異が出うる（標準 jsarticle では空白）。
