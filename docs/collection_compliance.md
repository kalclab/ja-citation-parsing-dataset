# 収集時の robots.txt / 利用条件の確認結果

収集は API 優先で行い、API が無いウェブページについてのみ HTTP fetch を用いた。全リクエストでリクエスト間に 1〜2 秒（ウェブページ収集では 1.5 秒）のウェイトを置き、User-Agent にプロジェクト名と連絡先を含めている。各ドメインの robots.txt は収集前（2026-07-17）に実測し、Disallow プレフィックスは収集スクリプト側（`scripts/collect_webmisc.py` の `ROBOTS_DISALLOW`）に実装して回避した。保存するのは書誌メタデータ（タイトル・URL・組織名・年）のみで、本文・PDF の内容は保存しない。

## robots.txt / ToU 確認結果（2026-07-17 実測）

| ドメイン | robots | 判定 |
|---|---|---|
| www.mhlw.go.jp | `Disallow: /cgi-bin/ /images/ /topics/...` のみ | 白書配下は可 |
| www.stat.go.jp | `Disallow: /library/opac/` のみ | 統計 landing は可 |
| www.soumu.go.jp | `ia_archiver` のみ全面禁止（当方 UA 対象外） | 可 |
| www.mext.go.jp | robots.txt なし(404) | 既定で可 |
| www.cao.go.jp / www8.cao.go.jp | robots.txt なし(404) | 可 |
| www.mlit.go.jp | robots.txt なし(404) | 可 |
| www.env.go.jp | `Disallow: /cgi-bin/` のみ | 可 |
| www.meti.go.jp | robots.txt が 403（bot 保護の疑い） | 慎重運用・低頻度、取得不可なら他省で代替 |
| www.ppc.go.jp | `/common /hardcore /hc_config /image /webadmin` のみ | ガイドライン配下は可 |
| www.ipsj.or.jp | `/prms /login...` 等のみ | 倫理綱領等は可 |
| kotobank.jp | `Allow: /`、`Disallow: /search`（GPTBot 等は全面禁止だが当方 UA は対象外） | 個別項目ページ(/word/…)は可。取得は書誌メタデータ（項目名＋辞典名＋URL）のみ |
| www.jisc.go.jp | robots.txt なし(404) | 公開情報ページは可（JIS 本文 DB は対象にしない） |

**ToU 上の運用方針**:

- 収集するのは書誌メタデータ（タイトル・URL・組織名・年）のみ。本文・PDF 中身は保存しない。
- kotobank は個別項目の「見出し語＋出典辞典名」を @misc の title とし、内容は転記しない。robots で当方 UA は許可。件数は控えめ（辞典枠の一部）に留める。
- JIS 規格本文（kikakurui 等の全文 DB）は ToU が厳しいため対象外。JISC 公開ページ／学協会の公開指針を優先。
- meti は robots.txt レスポンスが 403 のため低頻度・少数に留め、取得できなければ経産分を国交・総務・環境で補う（最終的に経産省からの収集は行っていない）。
