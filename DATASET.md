# 日本語文献 BibTeX データセット

日本語の参考文献文字列（reference string）からの書誌情報抽出を評価するためのデータセット。正解となる BibTeX レコードを実在文献から収集し（Phase 1）、日本国内で実際に用いられる複数の引用スタイルで参考文献文字列を逆生成する（Phase 2）ことで、文字列 → 書誌情報の復元精度を測る評価データを構成する。

全レコードは実在する文献・ウェブページに基づき、1 件ごとに出典 URL を記録して検証可能にしている。書誌メタデータのみを収集し、本文・抄録は保存しない。

## 配布形態と再構築

収集元（J-Stage・コトバンク等）の利用条件により、**収集した書誌値そのものは本リポジトリで再配布しない**。リポジトリが配布するのは次の 4 つで、書誌値を含む成果物は利用者が手元で再構築する。

| 配布物 | 内容 |
|---|---|
| `manifest.csv` | 全 988 レコードの引用キー・文献タイプ・分野・細分野・難易度フラグ・取得元・出典 URL・取得日時（書誌値そのものは含まない） |
| `scripts/` | 収集・マージ・検証・参考文献文字列生成の全スクリプト |
| `annotations/` | 人手で作成したアノテーション（著者の姓名境界の分割テーブル等） |
| `annotations/field_overrides.jsonl` | 出典の記述自体が誤っているフィールドの、ガード付き置換テーブル（v1.1。取得時の値を `from` に記録し、再取得値が一致するときだけ当てる） |
| `key_map.csv` / `sample_100.txt` | 最終キーとコレクタ側の暫定キーの対応表／評価用 100 件サンプルのキーリスト |

`scripts/rebuild.py` を実行すると、`manifest.csv` の出典 URL から書誌を再取得し、下表の成果物を `dataset/` 以下に生成する。`dataset/` は `.gitignore` 済みで、リポジトリには含まれない。実行手順はルート README を参照。

| ファイル | 内容 | 生成段階 |
|---|---|---|
| `dataset/ja_bib_full.bib` | 全 988 レコードの BibTeX 原本（ソース忠実・UTF-8） | Phase 1 |
| `dataset/metadata.csv` | レコードごとの分野・難易度・出典情報（`manifest.csv` に、ソース固有の処理内容を記す `notes` 列を加えたもの） | Phase 1 |
| `dataset/ja_bib_derived.bib` | .bst 系スタイル用の派生ファイル（著者姓名分割等） | Phase 2 |
| `dataset/ref_strings.jsonl` | スタイル別の参考文献文字列（key × style） | Phase 2 |

本文書の以降の記述は、この再構築後の成果物を対象とする。

## 収録レコードと分布

全 988 レコード。文献タイプ比率はおおむね 3 : 2.5 : 2.5 : 2 を維持している。

### 文献タイプ別

| タイプ | BibTeX entry type | 件数 | 難ケース率 |
|---|---|---|---|
| 雑誌論文 | `@article` | 296 | 55% |
| 会議論文 | `@inproceedings` | 249 | 54% |
| 図書 | `@book` / `@incollection` | 249 | 82% |
| ウェブサイト | `@misc` | 194 | 70% |

### 分野別

| 分野 | 件数 |
|---|---|
| 人文社会 | 341 |
| 理工 | 390 |
| 医学生命 | 257 |

### 難易度フラグ別

意図的に含めた「難しい」書誌の種類と件数。1 レコードが複数のフラグを持つことがある。

| フラグ | 意味 | 件数 |
|---|---|---|
| `nonstandard_volume` | 通巻表記等の非標準な巻号 | 209 |
| `institutional_author` | 機関・団体名の著者 | 210 |
| `english_mixed` | 欧文混じり（英語題目・ローマ字著者等） | 196 |
| `subtitle` | 副題付きタイトル | 186 |
| `page_style` | `pp.` でない非標準なページ表記 | 93 |
| `wareki` | 和暦併記 | 85 |
| `edited_volume` | 編著・監修 | 49 |
| `translated` | 訳書 | 24 |

## スキーマ

### 引用キー

`{タイプ略号}{連番4桁}` で統一する。`art0001`（雑誌論文）、`inp0001`（会議論文）、`bok0001`（図書。`@incollection` を含む）、`web0001`（ウェブサイト）。図書のうち `@incollection` は `bok` 連番に混ぜ、`manifest.csv` / `metadata.csv` の `entry_type` で区別する。

### manifest.csv / metadata.csv の列

| 列 | 内容 |
|---|---|
| `key` | 引用キー（`ja_bib_full.bib` と対応） |
| `entry_type` | `article` / `inproceedings` / `book` / `incollection` / `misc` |
| `discipline` | `人文社会` / `理工` / `医学生命` |
| `subfield` | 細分野（自由記述） |
| `difficulty_flags` | 難易度フラグ（`;` 区切り。上表の統制語彙） |
| `source_name` | 取得元 |
| `source_url` | 実在検証可能な出典 URL（全件記入） |
| `retrieved_at` | 取得日時 |
| `notes` | ソース固有の処理内容（書式変換・補完等）の記録。`metadata.csv` のみ |

### BibTeX の必須フィールド

- `@article`: author, title, journal, volume, pages, year（通巻のみで巻を持たない誌は `nonstandard_volume` フラグ付きで `number` が volume を代替する）
- `@inproceedings`: author, title, booktitle, year
- `@book`: author または editor, title, publisher, year
- `@misc`: title, url, urldate

取得できたフィールドは必須以外（doi, issn, isbn, publisher, address, series 等）もすべて保持する。

## 収集ソースと手順

各ソースは API またはエクスポートを優先して取得し、リクエスト間に 1〜2 秒の待機を置いた。robots.txt と利用条件は収集前（2026-07-17）にドメインごとに確認し、観測した Disallow パスは `scripts/collect_webmisc.py` の `ROBOTS_DISALLOW` として実装している。

| ソース | 主なタイプ | 件数 | 収集スクリプト |
|---|---|---|---|
| J-Stage WebAPI | article / inproceedings | 329 | `scripts/collect_jstage.py` |
| NDL Search SRU | book | 144 | `scripts/collect_ndl.py` |
| CiNii Research（Books） | book | 105 | `scripts/collect_cinii_books.py` |
| CiNii Research（OpenSearch） | article / inproceedings | 99 | `scripts/collect_cinii_supp.py` |
| 言語処理学会年次大会アーカイブ | inproceedings | 60 | `scripts/collect_anlp.py` |
| コトバンク（辞典項目） | misc | 58 | `scripts/collect_webmisc.py` |
| Crossref REST API | article | 57 | `scripts/collect_crossref.py` |
| 省庁白書・統計・ガイドライン等 | misc | 136 | `scripts/collect_webmisc.py` |

各ソースについて、取得後に最低 20 件のサンプルを出典ページと突き合わせる検査を行った（`scripts/collect_jstage.py qc`、`scripts/qc_books_sample.py`、`scripts/qc_webmisc.py` 等）。ソース固有のクリーニング規則の詳細は各コレクタの docstring に記録している。

`@misc` のうち省庁系は、白書・統計・ガイドラインの公開ページを列挙し、取得時にページの実在とタイトルを確認して構成した（総務省統計局・厚生労働省・内閣府・国土交通省・環境省・個人情報保護委員会・各学協会の公開文書等）。

## クリーニング規則の要約

表記の正規化（全角記号・中黒・波ダッシュ等）は行わず、**ソースのまま保持する**（正規化は評価側の役割）。ソース固有の系統的な不良にのみ、以下の限定的な処理を施し、各レコードの `notes` に記録する。

- **著者名の区切り**: 著者は ` and ` 区切り。日本語著者名は基本形「姓 名」（半角スペース区切り）とするが、ソースが異なる形式（「姓, 名」等）の場合はソース準拠のまま保持し `notes` に記録する。NDL・言語処理学会の一部は姓名が連結（境界なし）で提供されるため、その連結形のまま保持する（後述の既知の制限を参照）。
- **HTML エンティティ / タグ**: Crossref・J-Stage の題目に残る HTML 実体参照（`&lt;` 等）はアンエスケープし、表示用の埋め込みタグ（`<I>`、`<SUB>` 等）は除去して `notes` に記録する。
- **巻号の復号**: CiNii の `123(6)` 形式は volume=123 / number=6 に分解する（同一情報の復号であり改変ではない）。v1.1 では、CiNii の `prism:volume` が巻に号を埋め込んでいた @article 10 件（`123-8`・`125巻5号`・`第124編5号`・`41－1`・`46 (4)` 等）についても、出典レコードを 1 件ずつ人手で確認したうえで volume / number へ復号し、`nonstandard_volume` を外した（`annotations/field_overrides.jsonl`。ソースに号の記載が無い 1 件は volume のみとし、号は補わない）。復号のしようがない非標準な巻号（通巻表記・`JSAI2017` のような会議 ID・`上`/`下` 等）は引き続きソース表記のまま保持し `nonstandard_volume` を付与する。
- **ページ**: 開始・終了ページから構成する。非数値ページ（会議発表番号等）は原表記のまま保持し `page_style` を付与する。
- **出版者と出版地**: 「東京 : 電気学会」のように出版地が混入する場合は分割し、地名を `address`、社名を `publisher` に振り分ける。
- **図書の選別**: 学術出版社名での検索を主軸とし、ISBN を持つ和書に限定、児童書・非学術書を除外して近現代の学術書に寄せている。

## 参考文献スタイル（Phase 2）

参考文献文字列は、著者表記・年の位置・巻号ページ表記・和欧混在処理が互いに異なる 7 スタイルで生成する。人文社会系スタイルを複数含む。

| スタイル | 実装 | 想定分野 |
|---|---|---|
| jecon-mod | .bst | 経済学（人文社会）。jecon ver.6.6 の改変版（和文会議録名を出力、`\bysame` を無効化の 2 箇所）。`scripts/README.md` 参照 |
| ipsjsort | .bst | 情報処理学会（理工） |
| jsai | .bst | 人工知能学会（理工） |
| jplain | .bst | jBibTeX 古典・整列系 |
| sist02 | CSL | 分野横断（SIST 02） |
| jpa2022 | CSL | 心理学（人文社会） |
| chicago-author-date | CSL | 対照・和欧混在検証 |

同一レコードの出力例（`bok0068`）:

```
jecon-mod           山本行男 (2005) 『クリック!有機化学』，化学同人．
sist02              山本行男. クリック!有機化学. 化学同人, 2005, ISBN4759809937.
jpa2022             山本行男. (2005). クリック!有機化学. 化学同人.
chicago-author-date 山本行男. 2005年. クリック!有機化学. 化学同人.
ipsjsort            山本行男：クリック!有機化学，化学同人 (2005).
jsai                山本 行男：クリック!有機化学, 化学同人 (2005)
jplain              山本行男. クリック!有機化学. 化学同人, 2005.
```

スタイル×文献タイプごとに、どのフィールドが文字列に現れるかの実測対応表は、再構築した `ref_strings` に対して `scripts/analyze_field_rendering.py` を実行すると得られる。

## 品質保証

- 全体が `bibtexparser` でエラーなくパースでき、引用キーの重複がなく、タイプ別必須フィールドを 100% 充足することを `scripts/validate.py` で検査している。
- `source_url` は全件記入。ランダム 3%（30 件、タイプ層化）を再取得して実在を確認した結果、リンク切れ・書誌不一致は 0 件だった。
- 評価用サンプル候補 `sample_100.txt` は、タイプ比率 30/25/25/20 を保ち、各タイプ内で分野を均等に近づけ、難ケースを含む層化条件で生成している（`scripts/sample_eval_set.py`、乱数シード固定）。
- 生成後の突き合わせとして、スタイルごとのランダム 20 件の目視照合とスタイル間の出力同一率の検査を実施済み（照合表は `scripts/verify_refs.py` で再生成できる）。

## 既知の制限

- **著者の姓名境界**: 一部のソース（NDL 図書の可読著者表示・言語処理学会予稿・CiNii Books）は著者を姓名区切りなしの連結形で提供する。Phase 2 派生ファイルでは、NDL 典拠レコード（`annotations/name_boundaries.jsonl`）と、目視確認および Web 典拠による手動分割テーブル（`annotations/manual_name_table.jsonl`、240 名＝目視確認 229・Web 典拠 11）で姓名境界を復元している（原本 `ja_bib_full.bib` は不変。推測での分割は書誌の捏造にあたるため行わない）。この結果、姓と名からなる著者名の連結形はすべて解消した。連結のまま残るのは**単一名 4 件のみ**（`ピウス二世`＝regnal name、`国際膵臓学会ワーキンググループ`・`電通美術回路`＝団体名、`ホクソエム`＝筆名）。これらは「姓名境界が不明」なのではなく、**書誌的に「姓名の分割」という操作が定義されない単一名**であり、著者フィールドの難ケースとして意図的に保持している。
- **`english_mixed` の分野の偏り**: 欧文混じり書誌（和文題目＋ローマ字著者等）は、著者名をローマ字化する医学・工学系の誌に集中する。人文社会系の誌は表記が一貫（漢字著者＋和文題目）で欧文混じりが生じにくいため、`english_mixed` レコードは理工・医学生命に偏る。
- **書評の `@article`**: 一部の雑誌論文は書評であり、題目が「X 著『Y』」の形式をとる（被評図書の書名を含む）。実在する書誌であり、複雑なケースとして意図的に残している。
- **スタイル実装に由来する挙動**: jplain は題目中の英字を小文字化する（`AI` → `ai`）。これは各スタイルの真正な挙動であり、評価設計時に考慮する。
- **jecon の edition 後処理（v1.1）**: jecon は和文エントリの edition を `第{edition}版` で包むが、これは裸の数字 edition（`2` → `第2版`）にしか正しくない。本データセットの edition はソース忠実な完全表記（`第2版`・`新装版`・`ver.2` 等）なので、そのままでは `第第2版版`・`第新装版版` になる。`generate_refs_bst.py` の `fix_jecon_edition` が jecon 出力に限って包みを外す。これはスタイル本来の出力からの逸脱であり、edition を含むレコードの jecon 文字列を評価に使う際は考慮する（.bib 側は不変で、他 6 スタイルは edition をそのまま出力する）。
- **jecon の `\bysame`（v1.1）**: 素の jecon は同一著者が連続すると 2 件目以降の著者名を横棒（`\bysame`）で省略する。参照文字列を 1 件単位で扱う本データセットでは前後文脈依存の省略が意味を持たないため、公式カスタマイズ変数で無効化した（v1.0 では省略された著者が detex 後に脱落していた）。したがって jecon-mod の著者表記は、リストとして組版した真正 jecon の出力とは一部のレコードで異なる。
- **古典系 .bst の著者形式**: jplain / ipsjsort / jsai は `{ff}{ll}` 整形で伝統的な「姓 名」（空白形）入力を前提とする。派生 .bib は jecon/CSL 用にカンマ形「姓, 名」へ正準化しているため、そのまま渡すと日本語著者が「名姓」に反転する。これはスタイルの挙動ではなく入力規約の相違であり、`generate_refs_bst.py` の `prepare_bib` がコンパイル直前の一時 .bib のみで日本語著者をカンマ形→空白形へ再変換して解消している（ローマ字「Last, First」は変換せず、`{ff}{ll}` で正しく First Last に出力）。会議録名は jecon-mod で出力される（素の jecon の booktitle 欠落は解消済み）。
