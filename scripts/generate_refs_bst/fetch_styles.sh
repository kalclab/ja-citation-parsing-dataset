#!/bin/zsh
# Fetch the .bst styles that are NOT redistributable and therefore not vendored.
#
#   ipsjsort.bst / ipsjunsrt.bst : 情報処理学会 (IPSJ) 配布物。ライセンス上の再配布可否が
#                                  明示されないため同梱せず、公式 zip から取得する。
#   jsai.bst                     : 著作権は人工知能学会 (JSAI)。同上。
#
# Vendored (取得不要): jecon.bst (LPPL 1.3+), scripts/csl/*.csl (CC BY-SA 3.0).
# TeX Live 由来 (取得不要): jplain.bst / junsrt.bst (upbibtex が既定パスで解決)。
#
# Sources / versions (2026-07-17 時点):
#   IPSJ  ipsj_v4-1.zip (2025-02-06)   https://www.ipsj.or.jp/journal/submit/style.html
#   JSAI  jsaiac_tex_ja_utf8lf-2026.zip https://conf.ai-gakkai.or.jp/jsai2026/author-guideline/
set -e
DEST="${0:A:h}/bst"      # scripts/generate_refs_bst/bst
mkdir -p "$DEST"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

IPSJ_URL="https://www.ipsj.or.jp/journal/submit/9faeag0000001nsz-att/ipsj_v4-1.zip"
JSAI_URL="https://conf.ai-gakkai.or.jp/jsai2026/wp-content/uploads/2025/12/jsaiac_tex_ja_utf8lf-2026.zip"

echo "[fetch] IPSJ  -> ipsjsort.bst / ipsjunsrt.bst (UTF-8 variant)"
curl -fsSL -o "$TMP/ipsj.zip" "$IPSJ_URL"
unzip -o -j "$TMP/ipsj.zip" '*/UTF8/ipsjsort.bst' '*/UTF8/ipsjunsrt.bst' -d "$DEST" >/dev/null

echo "[fetch] JSAI  -> jsai.bst"
curl -fsSL -o "$TMP/jsai.zip" "$JSAI_URL"
unzip -o -j "$TMP/jsai.zip" '*/jsai.bst' -d "$DEST" >/dev/null

echo "[done] fetched into $DEST:"
ls -1 "$DEST"
