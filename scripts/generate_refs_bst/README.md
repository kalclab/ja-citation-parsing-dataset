# .bst 生成パイプライン（upLaTeX + upBibTeX）

`.bst` スタイルで参考文献文字列を逆生成する。最小の upLaTeX 文書を組み、`\nocite{*}` で全件を挙げ、upLaTeX（`.aux` 生成）→ upBibTeX（`.bbl` 生成）を実行し、`.bbl` を平文に還元する。

全候補 `.bst`（jecon / ipsjsort / jsai）は pTeX 専用の組み込み関数 `is.kanji.str$`（漢字判定）を呼ぶため、標準 bibtex では動かず **upBibTeX / pBibTeX が必須**。

## スタイルファイルの入手（ライセンス別）

| style | source | 入手 | ライセンス |
|---|---|---|---|
| jecon | vendored | `bst/jecon.bst` 同梱 | LPPL 1.3+ |
| ipsjsort | fetch | `fetch_styles.sh` | IPSJ 配布物・再配布可否不明のため非同梱 |
| jsai | fetch | `fetch_styles.sh` | 著作権 JSAI・非同梱 |
| jplain, junsrt | texlive | TeX Live `pbibtex-base`（`upbibtex` が既定パスで解決） | TeX Live |

fetch 済みファイル（ipsjsort/ipsjunsrt/jsai）は `.gitignore` 済みでコミットしない。

```sh
zsh scripts/generate_refs_bst/fetch_styles.sh   # IPSJ/JSAI 公式 zip から取得
```

取得元 URL・バージョンは `fetch_styles.sh` 冒頭コメントに記録。CSL スタイル（sist02/jpa2022/chicago, いずれも CC BY-SA 3.0）は `scripts/csl/` に同梱。

## TeX Live のセットアップ（~/texlive/2026 の再現）

macOS でユーザ権限のみ（`sudo` 不要）でホーム配下に導入する手順。BasicTeX（Homebrew cask）は管理者インストーラを起動し無人実行で止まるため使わない。

```sh
cd /tmp
curl -fsSLO https://mirror.ctan.org/systems/texlive/tlnet/install-tl-unx.tar.gz
tar xzf install-tl-unx.tar.gz && cd install-tl-2*

cat > /tmp/tl.profile <<'EOF'
selected_scheme scheme-custom
collection-basic 1
collection-latex 1
collection-langjapanese 1
collection-bibtexextra 1
TEXDIR ~/texlive/2026
TEXMFLOCAL ~/texlive/texmf-local
TEXMFSYSVAR ~/texlive/2026/texmf-var
TEXMFSYSCONFIG ~/texlive/2026/texmf-config
TEXMFVAR ~/.texlive2026/texmf-var
TEXMFCONFIG ~/.texlive2026/texmf-config
TEXMFHOME ~/texmf
instopt_adjustpath 0
tlpdbopt_install_docfiles 0
tlpdbopt_install_srcfiles 0
EOF

./install-tl -profile /tmp/tl.profile -no-gui
```

導入後 `~/texlive/2026/bin/universal-darwin/` に `uplatex` `upbibtex` `pbibtex` が入る。`generate_refs_bst.py` は `upbibtex` が PATH になければこのディレクトリを自動追加する（`TEXBIN` 環境変数で上書き可）。`collection-langjapanese` に `pbibtex-base`（jplain/junsrt）が含まれる。

## 実行

```sh
uv run python scripts/generate_refs_bst/generate_refs_bst.py \
    --bib scripts/fixtures/test.bib \
    --out data/interim/survey_0b/out/ref_strings_bst.jsonl \
    [--only jecon ipsjsort ...]
```

出力は 1 行 1 サンプルの JSONL: `{"key","style","style_impl":"bst","ref_string","generation_status"}`。upBibTeX が `.bbl` を出せない組は `generation_status="failed: ..."` として記録し、手整形しない。

## 古典系スタイルへの入力調整（`prepare_bib`）

古典 jBibTeX 系（jplain / junsrt / ipsjsort / jsai）は jecon/CSL と入力規約が異なる。
コンパイル直前の一時 .bib のみで次の 2 点を調整する（派生 .bib 本体は不変。jecon(-mod)
は `url` を直接読み、日本語著者もカンマ形から正しく整形するため対象外）。

1. **著者形式（姓名順）**: 古典系は `{ff}{ll}` 整形で伝統的な「姓 名」空白形入力を前提と
   する（First=姓, Last=名 → 出力 姓名）。派生 .bib は jecon/CSL 用にカンマ形「姓, 名」へ
   正準化しているため、そのまま渡すと日本語著者が「名姓」に反転する（例 `李, 在檍` →
   `在檍李`）。これは**スタイルの挙動ではなく入力規約の相違**であり、`prepare_bib` が
   日本語のみの著者（author/editor/translator）をカンマ形→空白形へ再変換して解消する
   （例 → `李在檍`）。ローマ字「Last, First」は変換しない（`{ff}{ll}` で First Last に正しく出る）。
   境界なし連結形（例 `山本行男`）は単一トークンなのでそのまま。
2. **@misc の URL**: 古典系 @misc 書式は `url`/`urldate` でなく `howpublished`/`note` を読む。
   派生 .bib は URL を `url` に一本化しているため、一時 .bib に `howpublished={\url{...}}`
   （＋ `urldate`→`note`）を補って URL 落ちを防ぐ。

## .bbl → 平文 ref_string の還元規則

`\bibitem` / `\harvarditem`（natbib=jecon）単位で分解してキーを取り、本文を `detex()` で還元する。適用順が重要（内側の URL マクロを先に解決してから外側の `\href` を処理）。

| 対象 | 処理 |
|---|---|
| `\begin/\end{thebibliography}`, jecon の `\newcommand` 前文 | 除去（本文領域のみ抽出） |
| `\bibitem[label]{key}` / `\harvarditem[..]{..}{year}{key}` | キー抽出後、プレフィックスを除去 |
| `\newblock` | 空白（標準 jsarticle の定義に一致） |
| `\urlstyle{..}` | 除去（体裁指定のみ） |
| `\nolinkurl{X}` `\url{X}` `\doi{X}` `\path{X}` | `X`（URL/DOI 文字列） |
| `\href{A}{B}` | `B`（内側マクロ解決後にブレース整合） |
| `{\sc X}` `{\bf X}` 等 | `X` |
| `~` | 空白（jsai の姓名区切り・NBSP） |
| `\ ` `\,` `\;` `\!` `\<改行>` | 空白（ページ範囲の折返し等） |
| `\&` `\%` `\#` `\_` | `&` `%` `#` `_` |
| ipsj の `\：` 等 `\<非英字>` | バックスラッシュ除去し記号を残す |
| 残存 `\controlword` | 除去 |
| `--` / `---` | – / —（TeX の en/em dash） |

注意: `\newblock` を空白とみなす前提のため、`\newblock` を句点等へ再定義する特殊クラスでは差異が出うる（本パイプラインは標準 `jsarticle` を使用）。
