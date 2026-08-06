# Phase 1 収集規約（コレクタ間の共通契約）

2026-07-17 に確定した決定事項と、ソース別コレクタが従う共通フォーマットを定める。全コレクタ・検証・マージスクリプトはこの契約に従う。

## 確定した決定（2026-07-17）

- ソース割付: 下表のとおり。ただし **openBD は不使用**（ライセンス上の懸念のため）。openBD に割り付けていた @book 30 件は NDL +15 / CiNii Books +15 に再配分（NDL 145 / CiNii Books 105）。
- 引用スタイル: 7 スタイル（jecon / jpa2022 / sist02 / ipsjsort / jsai / jplain / chicago-author-date）。社会学評論スタイルは見送り。**junsrt は除外**（出力文字列が jplain と完全一致し、差はリスト順序のみで 1 件単位の逆生成データには現れないため）。
- ~~jecon の和文 @inproceedings は booktitle を出力しない挙動を真正出力として収録（ok_partial マーカー付き）~~ → **撤回・解決**: jecon に公式オプションが無いことを確認のうえ、**jecon-mod.bst（1 トークン改変: format.output.in.ed.booktitle の空分岐 → format.btitle）を採用**。会議録名を『』体裁で出力。他タイプはバイト一致（回帰確認済み）。ref_strings.jsonl の style 名は "jecon-mod" とし、改変内容を README に明記して真正 jecon との差を隠さない。
- CiNii は無償 appid の登録を推奨（未登録の間は無鍵＋低頻度で運用）。
- J-Stage は 1 誌あたり取得上限 30 件を目安に分散収集。

## 目標分布（openBD 再配分後）

| タイプ | 目標 | ソース内訳 |
|---|---|---|
| @article | 300 | J-Stage 200 / CrossRef 60 / CiNii 40 |
| @inproceedings | 250 | J-Stage(JSAI等) 130 / 言語処理学会 60 / CiNii 60 |
| @book | 250 | NDL SRU 145 / CiNii Books 105 |
| @misc | 200 | 省庁白書・e-Stat 120 / 規格・学協会文書 80 |

実際の収録件数は `DATASET.md` を参照。

## ディレクトリ契約

以下の `data/` 配下はコレクタの作業ディレクトリで、リポジトリには含まれない（再取得のたびに手元で生成される）。

- `data/raw/<source>/` — API 生レスポンス（再現用に保存。書誌メタデータのみ、本文・抄録は保存しない）
- `data/interim/<source>/records.jsonl` — コレクタの出力（下記スキーマ）
- `dataset/` — マージ・検証後の成果物のみ。コレクタは直接書かない
- `<source>` は `jstage` / `ndl` / `cinii`（図書、books コレクタ） / `cinii_supp`（雑誌・会議論文の補完コレクタ。書き込み衝突回避のため分離） / `crossref` / `anlp` / `webmisc` のいずれか

## 中間レコードスキーマ（records.jsonl、1 行 1 レコード）

```json
{
  "provisional_key": "jstage-000042",
  "entry_type": "article",
  "bibtex_fields": {"author": "山田 太郎 and 鈴木 花子", "title": "...", "journal": "...", "volume": "8", "number": "2", "pages": "32-45", "year": "2015", "doi": "..."},
  "discipline": "理工",
  "subfield": "機械工学",
  "difficulty_flags": ["subtitle", "english_mixed"],
  "source_name": "J-Stage WebAPI",
  "source_url": "https://doi.org/....",
  "retrieved_at": "2026-07-17T10:00:00+09:00",
  "notes": "著者名はソースでは「姓, 名」形式だったため区切りを変換"
}
```

- `provisional_key`: `<source>-<連番6桁>`。**最終キー（art0001 等）はマージ時に scripts/merge_assign_keys.py が付与する**。コレクタは付けない。
- `entry_type`: `article` / `inproceedings` / `book` / `incollection` / `misc`
- `bibtex_fields`: BibTeX フィールド名 → 値。タイプ別必須フィールド（`DATASET.md` 参照）を満たすこと。取得できた任意フィールド（doi, issn, isbn, publisher, address, url, urldate 等）はすべて保持。
- `discipline`: `人文社会` / `理工` / `医学生命` の 3 値。`subfield` は自由記述。
- `source_url`: 実在検証可能な URL（DOI・書誌詳細ページ等）。**全件必須**。

## @misc の URL 規則

- URL は `url` フィールドのみに置く。`howpublished` には組織名等のみ（`\url{}` を入れない — Phase 2 で URL が二重出力されるため）。

## 必須フィールドの例外規定

- @article の `volume` 要件: 通巻表記のみで巻を持たない日本語誌は、`nonstandard_volume` フラグ付きかつ `number` があれば `volume` 欠如を許容する（validate.py 実装済み）。コレクタは通巻をソース表記のまま `number` に格納し、`volume` をでっち上げない。

## difficulty_flags 統制語彙

`subtitle`（副題付き）/ `edited_volume`（編著・監修）/ `translated`（訳書）/ `institutional_author`（機関著者）/ `nonstandard_volume`（通巻等の非標準巻号）/ `page_style`（pp. でないページ表記）/ `wareki`（和暦併記）/ `english_mixed`（欧文混じり）。各タイプで 1 割以上に何らかのフラグが立つことを目標とする。

## 表記・品質の厳守事項

- 捏造禁止。全レコードは実取得データに基づく。
- 全角記号・中黒・波ダッシュ等はソースのまま保持。正規化しない。CrossRef の HTML エンティティ（`&lt;` 等）のみアンエスケープし、notes に記録。
- 著者は ` and ` 区切り、日本語著者名は「姓 名」（間に半角スペース）を基本。ソースが「姓, 名」等の異なる形式の場合は**ソース準拠のまま保持**し、その旨を notes に記録（ソース忠実性を優先。コレクタ側で変換しない）。
- 著者書式と BibTeX 名前パースの不整合（「姓 名」空白形は (u)pBibTeX / citeproc が姓名を誤認する — 予備検証で実証済み）は、**Phase 2 用の派生ファイル ja_bib_derived.bib で機械的に解決**する: 日本語文字のみの著者名「姓 名」→「姓, 名」変換。原本 ja_bib_full.bib には適用しない。
- API 優先、リクエスト間 1〜2 秒ウェイト、robots.txt 尊重。User-Agent にプロジェクト名と連絡先を含める（例: `ja-citation-parsing-dataset (mailto:<連絡先アドレス>)`）。確認結果は `docs/collection_compliance.md` を参照。
- 各ソース最低 20 件のサンプル検査を行い、系統的不良のクリーニングルールをコレクタの docstring と README に記録。

## スクリプト規約

- Python は uv 管理（リポジトリルートの pyproject.toml）。実行は `uv run scripts/collect_<source>.py`。
- コレクタは冪等に（再実行で重複追記しない。provisional_key で dedup）。
- ソース横断の重複（同一 DOI・同一 ISBN・題名+年一致)はマージ時に検出するが、コレクタ内でも既知の重複は避ける。
