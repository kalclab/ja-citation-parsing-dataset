#!/usr/bin/env python3
"""マニフェストから書誌メタデータを再取得し、dataset/ を手元で復元する。

    manifest.csv + key_map.csv
      --(this script: 出典ごとに再取得)-->  <workdir>/<source>/records.jsonl
      --(merge_assign_keys.py --key-map)-->  dataset/{ja_bib_full.bib, metadata.csv}
      --(make_derived_bib.py)------------->  dataset/ja_bib_derived.bib

このリポジトリは書誌メタデータ本体を再配布しない（J-STAGE / コトバンク の利用条件による）。
配布するのは「どのレコードが、どの URL の、いつ時点の記述か」を示すマニフェストと、
それを書誌データへ戻すための収集コードだけであり、実データは利用者が自分で取得する。

参照文字列の生成（Phase 2）はこの先の話で、本スクリプトの守備範囲外:
`dataset/ja_bib_derived.bib` ができた時点で `scripts/generate_refs_csl.py`（CSL 3
スタイル）と `scripts/generate_refs_bst/generate_refs_bst.py`（.bst 4 スタイル）が
そのまま引き継げる。

再現性のための約束
------------------
* **キーは再採番しない。** `key_map.csv` の provisional_key→最終キー対応で固定する
  （`merge_assign_keys.py --key-map`）。上流の 1 件が消えても通し番号は総ずれしない。
* **人手で付けた属性は再計算しない。** discipline / subfield / difficulty_flags /
  source_name / source_url / retrieved_at はマニフェストの値をそのまま使う
  （difficulty_flags は収集時のヒューリスティックに人手の是正が入っている）。
  書誌値そのものへの人手の是正は `annotations/field_overrides.jsonl` の
  ガード付き置換だけで、上流の値が置換の前提と一致するときにしか当たらない。
* **日付は実行日ではなく取得日から導く。** @misc の `urldate` はマニフェストの
  `retrieved_at` の日付部分。今日の日付を書き込むと原本と食い違う。
* **取れなかったものは捏造しない。** 取得失敗・同定失敗・必須フィールド欠落は
  (key, 理由) を報告して当該レコードを落とす。欠落を埋めた出力は作らない。

フィールドの対応づけは各コレクタ（`collect_*.py`）の関数をそのまま呼ぶ。本スクリプトが
足すのは「1 件を識別子で引く」取得経路だけで、API 応答→BibTeX フィールドの変換規則は
収集時と同一。

礼儀
----
同一ホストへの連続リクエストは 1.5 秒以上あける。連絡先つき User-Agent を送る。
webmisc は収集時に観測した robots.txt の Disallow を尊重する（`collect_webmisc.robots_ok`）。

実行
----
    uv run python scripts/rebuild.py                        # 全 988 件
    uv run python scripts/rebuild.py --only-source jstage   # 出典を限定
    uv run python scripts/rebuild.py --keys art0098,bok0001 # キーを限定（動作確認向け）
    uv run python scripts/rebuild.py --workdir data/interim --no-merge

全件は数千リクエスト・数時間かかる。出典単位で分けて流し、`<workdir>/<source>/records.jsonl`
に貯めていくのが現実的（マージ段は毎回すべての records.jsonl を読み直す）。
"""
from __future__ import annotations

import argparse
import collections
import csv
import html as html_mod
import json
import re
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urljoin, urlparse
from xml.etree.ElementTree import ParseError

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))

import collect_anlp as anlp  # noqa: E402
import collect_cinii_books as cinii_books  # noqa: E402
import collect_cinii_supp as cinii_supp  # noqa: E402
import collect_crossref as crossref  # noqa: E402
import collect_jstage as jstage  # noqa: E402
import collect_ndl as ndl  # noqa: E402
import collect_webmisc as webmisc  # noqa: E402
import fix_webmisc  # noqa: E402
import refine_titles_webmisc as refine_titles  # noqa: E402
import validate  # noqa: E402

REPO = Path(__file__).resolve().parent.parent
# 連絡先つき User-Agent はコレクタ側の定数を使い回す（利用者が自分の連絡先に
# 差し替える場所を collect_*.py の一箇所に留めるため）。
UA = jstage.USER_AGENT
MIN_WAIT_SEC = 1.5
SOURCES = ("jstage", "crossref", "cinii", "cinii_supp", "ndl", "anlp", "webmisc")


# --------------------------------------------------------------------------- #
# マニフェスト
# --------------------------------------------------------------------------- #

@dataclass
class Target:
    """再取得する 1 件。マニフェストと key_map の同一キー行を束ねたもの。"""

    key: str
    provisional_key: str
    source: str
    entry_type: str
    discipline: str
    subfield: str
    difficulty_flags: list[str]
    source_name: str
    source_url: str
    retrieved_at: str
    overrides: list[dict] = field(default_factory=list)

    @property
    def urldate(self) -> str:
        """@misc の urldate。取得日の日付部分（実行日ではない）。"""
        return self.retrieved_at[:10]


@dataclass
class Failure:
    key: str
    source: str
    reason: str


def load_overrides(path: Path) -> dict[str, list[dict]]:
    """`field_overrides.jsonl` を最終キー別に読む。無ければ空。

    1 行が「`from` の各フィールドが再取得値と一致したときに限り `to` を当てる」
    という条件付きの置換。上流の記述そのものが誤っている（CiNii の prism:volume
    が巻に号を埋め込んでいる等）ものを、出典で人手確認したうえで直すための層。
    """
    by_key: dict[str, list[dict]] = {}
    if not path.exists():
        return by_key
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        ov = json.loads(line)
        by_key.setdefault(ov["key"], []).append(ov)
    return by_key


def load_targets(manifest: Path, key_map: Path,
                 overrides: Path | None = None) -> list[Target]:
    prov: dict[str, dict] = {}
    with key_map.open(encoding="utf-8", newline="") as fh:
        for row in csv.DictReader(fh):
            prov[row["key"]] = row
    ov_by_key = load_overrides(overrides) if overrides else {}
    targets: list[Target] = []
    with manifest.open(encoding="utf-8", newline="") as fh:
        for row in csv.DictReader(fh):
            km = prov.get(row["key"])
            if km is None:
                raise SystemExit(f"{row['key']}: key_map.csv に対応行がない")
            targets.append(Target(
                key=row["key"],
                provisional_key=km["provisional_key"],
                source=km["source"],
                entry_type=row["entry_type"],
                discipline=row["discipline"],
                subfield=row["subfield"],
                difficulty_flags=[f for f in row["difficulty_flags"].split(";") if f],
                source_name=row["source_name"],
                source_url=row["source_url"],
                retrieved_at=row["retrieved_at"],
                overrides=ov_by_key.get(row["key"], []),
            ))
    if unknown := set(ov_by_key) - {t.key for t in targets}:
        raise SystemExit(f"field_overrides.jsonl にマニフェスト外のキー: {sorted(unknown)}")
    return targets


def apply_overrides(rec: dict, t: Target) -> str | None:
    """`field_overrides.jsonl` のガード付き置換を当てる。当たらなければ理由を返す。

    `from` に挙げたフィールドが**すべて**再取得値と一致したときだけ `to` を当てる。
    一つでも食い違えば当てずに理由を返し、呼び出し側が他の再取得失敗と同じ経路で
    報告する（上流が既に直った、あるいは別の値に変わったのに黙って人手の値で
    上書きすると、確認済みという前提が崩れたことが見えなくなるため）。
    """
    if not t.overrides:
        return None
    fields = rec["bibtex_fields"]
    notes: list[str] = []
    for ov in t.overrides:
        stale = [(f, v) for f, v in ov["from"].items()
                 if str(fields.get(f, "")).strip() != v]
        if stale:
            detail = ", ".join(f"{f} が {v!r} でなく {fields.get(f, '')!r}"
                               for f, v in stale)
            return f"field_override の前提と一致しない: {detail}"
        before = " / ".join(f"{f}={v!r}" for f, v in ov["from"].items())
        after = " / ".join(f"{f}={v}" for f, v in ov["to"].items())
        fields.update(ov["to"])
        notes.append(f"field_override: 原文 {before} → {after}"
                     f"（{ov['provenance']}・{ov['verified_against']} で確認）")
    rec["notes"] = "; ".join(n for n in [rec.get("notes", ""), *notes] if n)
    return None


def stamp(rec: dict, t: Target) -> str | None:
    """コレクタが組んだレコードに、マニフェスト側の確定値を被せる。

    人手が入りうる属性（discipline / subfield / difficulty_flags / source_name /
    source_url / retrieved_at）は再取得結果で上書きしない。provisional_key も
    key_map の値に合わせる（cinii_supp などは連番で、URL から復元できないため）。

    bibtex_fields は原則そのまま通すが、`field_overrides.jsonl` に該当行がある
    レコードだけはガード付きで書き換える（`apply_overrides`）。当たらなかった
    場合はその理由を返すので、check_fields と同じ経路で報告する。
    """
    rec["provisional_key"] = t.provisional_key
    rec["entry_type"] = t.entry_type
    rec["discipline"] = t.discipline
    rec["subfield"] = t.subfield or None
    rec["difficulty_flags"] = list(t.difficulty_flags)
    rec["source_name"] = t.source_name
    rec["source_url"] = t.source_url
    rec["retrieved_at"] = t.retrieved_at
    rec.pop("_doi", None)
    rec.pop("_crid", None)
    rec.pop("_sort", None)
    return apply_overrides(rec, t)


def check_fields(rec: dict, t: Target) -> str | None:
    """必須フィールドを満たさないレコードの理由文字列。満たしていれば None。"""
    entry = {"ENTRYTYPE": rec["entry_type"], **rec["bibtex_fields"]}
    missing = validate.check_required(entry, set(t.difficulty_flags))
    if missing:
        return f"必須フィールド欠落: {', '.join(missing)}"
    return None


# --------------------------------------------------------------------------- #
# HTTP（ホスト単位のウェイト付き）
# --------------------------------------------------------------------------- #

class Fetcher:
    def __init__(self, wait: float = MIN_WAIT_SEC, timeout: int = 60) -> None:
        self.wait = wait
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": UA})
        self._last: dict[str, float] = {}
        self.n_requests = 0

    def get(self, url: str, params: dict | None = None) -> requests.Response:
        host = urlparse(url).netloc
        elapsed = time.time() - self._last.get(host, 0.0)
        if elapsed < self.wait:
            time.sleep(self.wait - elapsed)
        self._last[host] = time.time()
        self.n_requests += 1
        resp = self.session.get(url, params=params, timeout=self.timeout,
                                allow_redirects=True)
        # リダイレクト先のホストにも次回分のウェイトを課す（doi.org → 出版社サイト）
        self._last[urlparse(resp.url).netloc] = time.time()
        return resp


# --------------------------------------------------------------------------- #
# J-Stage
# --------------------------------------------------------------------------- #

_JSTAGE_ARTICLE = re.compile(r"/article/([^/]+)/([^/]+)/([^/]+)/")


def _doi_from_url(url: str) -> str:
    m = re.match(r"https?://(?:dx\.)?doi\.org/(.+)$", url, re.I)
    return m.group(1).rstrip("/") if m else ""


_JSTAGE_PAGE = 1000  # 検索 API の 1 リクエスト上限


def _jstage_issue(cdj: str, vol: str, no: str, fetch: Fetcher) -> list[dict]:
    """1 巻号ぶんの Atom エントリを全件返す。

    JSAI 全国大会のように 1 号が 700 件を超える予稿集があるため、
    `opensearch:totalResults` を見て取り切るまでページを繰る。
    """
    raws: list[dict] = []
    total = None
    start = 1
    while total is None or len(raws) < total:
        resp = fetch.get(jstage.API_ENDPOINT, params={
            "service": 3, "cdjournal": cdj, "vol": vol, "no": no,
            "start": start, "count": _JSTAGE_PAGE})
        resp.raise_for_status()
        if total is None:
            m = re.search(r"<opensearch:totalResults>(\d+)", resp.text)
            total = int(m.group(1)) if m else 0
        batch = jstage.parse_entries(resp.text)
        if not batch:
            break
        raws.extend(batch)
        start += len(batch)
    return raws


def rebuild_jstage(targets: list[Target], fetch: Fetcher) -> tuple[list[dict], list[Failure]]:
    """DOI から論文ページへ降り、その巻号を検索 API で引き直して 1 件を同定する。

    検索 API（service=3）は誌 ID + 巻 + 号でしか絞れないので、まず DOI を解決して
    論文ページ URL から cdjournal/巻/号を読む。同じ号の他レコードとはフィードを
    使い回すため、1 号あたりの API 呼び出しは 1 回で済む。著者・副題の補完
    （`fix_missing_authors` / `enrich_subtitles`）は、その解決で既に手元にある
    論文ページ HTML から作った citation_* メタで行い、追加取得はしない。
    """
    records: list[dict] = []
    failures: list[Failure] = []
    feeds: dict[tuple[str, str, str], list[dict]] = {}

    for t in targets:
        try:
            resp = fetch.get(t.source_url)
        except requests.RequestException as exc:
            failures.append(Failure(t.key, t.source, f"論文ページ取得失敗: {exc}"))
            continue
        if resp.status_code != 200:
            failures.append(Failure(t.key, t.source, f"論文ページ HTTP {resp.status_code}"))
            continue
        m = _JSTAGE_ARTICLE.search(resp.url)
        if not m:
            failures.append(Failure(t.key, t.source, f"J-Stage 論文 URL として解釈できない: {resp.url}"))
            continue
        cdj, vol, no = m.groups()

        if (cdj, vol, no) not in feeds:
            try:
                feeds[(cdj, vol, no)] = _jstage_issue(cdj, vol, no, fetch)
            except (requests.RequestException, ParseError) as exc:
                failures.append(Failure(t.key, t.source, f"検索 API 失敗 ({cdj}/{vol}/{no}): {exc}"))
                continue
        raws = feeds[(cdj, vol, no)]

        doi = _doi_from_url(t.source_url).lower()
        raw = next((r for r in raws if doi and r["doi"].lower() == doi), None)
        if raw is None:
            raw = next((r for r in raws if r["link"] and r["link"].rstrip("/") == resp.url.rstrip("/")), None)
        if raw is None:
            failures.append(Failure(t.key, t.source,
                                    f"該当記事が {cdj} {vol}({no}) のフィードに無い（上流で移動・削除の可能性）"))
            continue

        cfg = {"entry_type": t.entry_type, "discipline": t.discipline, "subfield": t.subfield}
        rec = jstage.build_record(raw, cfg, 0)
        if rec is None:
            failures.append(Failure(t.key, t.source, "日本語タイトルまたは日本語著者が消えた"))
            continue

        # 収集時と同じ補完を、取得済み HTML から作ったメタで適用する。
        meta = {k: v for k, v in jstage._extract_meta(resp.text).items()
                if k in jstage._META_KEEP}
        cache = {rec["source_url"]: meta}
        jstage.fix_missing_authors([rec], cache)
        jstage.enrich_subtitles([rec], cache)

        if (why := stamp(rec, t) or check_fields(rec, t)):
            failures.append(Failure(t.key, t.source, why))
            continue
        records.append(rec)
    return records, failures


# --------------------------------------------------------------------------- #
# Crossref
# --------------------------------------------------------------------------- #

def rebuild_crossref(targets: list[Target], fetch: Fetcher) -> tuple[list[dict], list[Failure]]:
    """DOI 1 件を /works/{doi} で引く。フィールド対応は収集時と同じ build_record。"""
    records: list[dict] = []
    failures: list[Failure] = []
    for t in targets:
        doi = _doi_from_url(t.source_url)
        if not doi:
            failures.append(Failure(t.key, t.source, f"source_url から DOI を取り出せない: {t.source_url}"))
            continue
        try:
            resp = fetch.get(f"https://api.crossref.org/works/{doi}",
                             params={"mailto": crossref.MAILTO})
            resp.raise_for_status()
            item = resp.json()["message"]
        except (requests.RequestException, ValueError, KeyError) as exc:
            failures.append(Failure(t.key, t.source, f"Crossref 取得失敗: {exc}"))
            continue
        if item.get("DOI", "").lower() != doi.lower():
            failures.append(Failure(t.key, t.source,
                                    f"DOI 不一致 (要求 {doi} / 応答 {item.get('DOI')})"))
            continue
        rec = crossref.build_record(item, t.discipline, t.subfield)
        if rec is None:
            failures.append(Failure(t.key, t.source, "title/author/journal のいずれかが欠けた"))
            continue
        if (why := stamp(rec, t) or check_fields(rec, t)):
            failures.append(Failure(t.key, t.source, why))
            continue
        records.append(rec)
    return records, failures


# --------------------------------------------------------------------------- #
# CiNii Research（図書 / 雑誌・会議論文）
# --------------------------------------------------------------------------- #

def _crid(url: str) -> str:
    m = re.search(r"/crid/(\d+)", url)
    return m.group(1) if m else ""


def _cinii_item(endpoint: str, crid: str, fetch: Fetcher, extra: dict | None = None) -> dict | None:
    """CRID を全文検索に投げ、その CRID の 1 件を返す。

    OpenSearch には ID 指定の取得口が無いが、CRID を `q` に渡すと当該レコードだけが
    返る。JSON-LD 版（/crid/<id>.json）はスキーマが別物で、コレクタの parse_item /
    build_record をそのまま使えないため採らない。
    """
    params = {"q": crid, "format": "json", "count": 5}
    if extra:
        params.update(extra)
    resp = fetch.get(endpoint, params=params)
    resp.raise_for_status()
    for item in resp.json().get("items", []):
        if _crid(str(item.get("@id", ""))) == crid:
            return item
    return None


def rebuild_cinii(targets: list[Target], fetch: Fetcher) -> tuple[list[dict], list[Failure]]:
    records: list[dict] = []
    failures: list[Failure] = []
    for t in targets:
        crid = _crid(t.source_url)
        try:
            item = _cinii_item(cinii_books.ENDPOINT, crid, fetch)
        except (requests.RequestException, ValueError) as exc:
            failures.append(Failure(t.key, t.source, f"CiNii Books 取得失敗: {exc}"))
            continue
        if item is None:
            failures.append(Failure(t.key, t.source, f"CRID {crid} が検索結果に無い"))
            continue
        rec = cinii_books.parse_item(item, t.discipline)
        if rec is None:
            failures.append(Failure(t.key, t.source,
                                    "図書判定・日本語タイトル・ISBN・年・出版者・著者のいずれかが失われた"))
            continue
        if rec["provisional_key"] != t.provisional_key:
            failures.append(Failure(t.key, t.source,
                                    f"別レコードを引いた ({rec['provisional_key']} != {t.provisional_key})"))
            continue
        if (why := stamp(rec, t) or check_fields(rec, t)):
            failures.append(Failure(t.key, t.source, why))
            continue
        records.append(rec)
    return records, failures


def rebuild_cinii_supp(targets: list[Target], fetch: Fetcher) -> tuple[list[dict], list[Failure]]:
    records: list[dict] = []
    failures: list[Failure] = []
    for t in targets:
        crid = _crid(t.source_url)
        try:
            item = _cinii_item(cinii_supp.ENDPOINT, crid, fetch, {"lang": "ja"})
        except (requests.RequestException, ValueError) as exc:
            failures.append(Failure(t.key, t.source, f"CiNii Research 取得失敗: {exc}"))
            continue
        if item is None:
            failures.append(Failure(t.key, t.source, f"CRID {crid} が検索結果に無い"))
            continue
        if not (item.get("title") or "").strip():
            failures.append(Failure(t.key, t.source, "タイトルが空"))
            continue
        rec = cinii_supp.build_record(item, t.entry_type, t.discipline, t.subfield, t.retrieved_at)
        if (why := stamp(rec, t) or check_fields(rec, t)):
            failures.append(Failure(t.key, t.source, why))
            continue
        records.append(rec)
    return records, failures


# --------------------------------------------------------------------------- #
# NDL Search
# --------------------------------------------------------------------------- #

_NDL_RECORD = re.compile(r"<recordData>(.*?)</recordData>", re.S)


def rebuild_ndl(targets: list[Target], fetch: Fetcher) -> tuple[list[dict], list[Failure]]:
    """SRU を `anywhere="<書誌ID>"` で引く。応答は収集時と同じ dcndl の recordData。"""
    records: list[dict] = []
    failures: list[Failure] = []
    for t in targets:
        m = re.search(r"/books/([^/?#]+)", t.source_url)
        if not m:
            failures.append(Failure(t.key, t.source, f"source_url から書誌 ID を取り出せない: {t.source_url}"))
            continue
        bib_id = m.group(1)
        try:
            resp = fetch.get(ndl.SRU, params={
                "operation": "searchRetrieve", "version": "1.2",
                "recordSchema": "dcndl", "maximumRecords": "5", "startRecord": "1",
                "query": f'anywhere="{bib_id}"'})
            resp.raise_for_status()
        except requests.RequestException as exc:
            failures.append(Failure(t.key, t.source, f"SRU 取得失敗: {exc}"))
            continue

        rec = None
        for chunk in _NDL_RECORD.findall(resp.text):
            parsed = ndl.parse_record(html_mod.unescape(chunk), t.discipline)
            if parsed and parsed["provisional_key"] == t.provisional_key:
                rec = parsed
                break
        if rec is None:
            failures.append(Failure(t.key, t.source,
                                    f"書誌 ID {bib_id} の図書レコードを取得できない"
                                    "（削除・品質ゲート不通過の可能性）"))
            continue
        if (why := stamp(rec, t) or check_fields(rec, t)):
            failures.append(Failure(t.key, t.source, why))
            continue
        records.append(rec)
    return records, failures


# --------------------------------------------------------------------------- #
# 言語処理学会年次大会
# --------------------------------------------------------------------------- #

def rebuild_anlp(targets: list[Target], raw_dir: Path,
                 refresh: bool) -> tuple[list[dict], list[Failure]]:
    """年次大会のプログラム索引を年ごとに 1 回取り、PDF URL で当該発表を突き止める。"""
    records: list[dict] = []
    failures: list[Failure] = []
    by_year: dict[int, list[Target]] = {}
    for t in targets:
        m = re.search(r"/annual_meeting/(\d{4})/", t.source_url)
        if not m:
            failures.append(Failure(t.key, t.source, f"source_url から年を取り出せない: {t.source_url}"))
            continue
        by_year.setdefault(int(m.group(1)), []).append(t)

    for year in sorted(by_year):
        try:
            page, _ = anlp.fetch_index(year, raw_dir, refresh)
            kai, page_year, papers = anlp.parse_papers(page)
        except (requests.RequestException, ValueError) as exc:
            for t in by_year[year]:
                failures.append(Failure(t.key, t.source, f"{year} 年のプログラム索引を読めない: {exc}"))
            continue
        base = anlp.BASE.format(year=page_year)
        by_url = {urljoin(base, p["pdf_path"]): p for p in papers}
        for t in by_year[year]:
            paper = by_url.get(t.source_url)
            if paper is None:
                failures.append(Failure(t.key, t.source, "PDF URL が索引に無い（上流で改稿の可能性）"))
                continue
            rec = anlp.build_record(paper, kai, page_year, t.source_url, t.retrieved_at)
            if (why := stamp(rec, t) or check_fields(rec, t)):
                failures.append(Failure(t.key, t.source, why))
                continue
            records.append(rec)
    return records, failures


# --------------------------------------------------------------------------- #
# webmisc（省庁白書・統計・ガイドライン・辞典項目）
# --------------------------------------------------------------------------- #

_OG_TITLE = (r'<meta[^>]+property=["\']og:title["\'][^>]+content=["\']([^"\']+)',
             r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']og:title["\']')
_MLIT_HEADING = re.compile(r"(令和|平成)\s*[\d元]+\s*年版国土交通白書")


@dataclass
class _WebPage:
    """1 ページ分の抽出結果。3 段階の整形をここから再生する。"""

    target: Target
    raw_title: str
    og: str
    h1s: list[str] = field(default_factory=list)
    mlit_heading: str = ""


def rebuild_webmisc(targets: list[Target], fetch: Fetcher) -> tuple[list[dict], list[Failure]]:
    """1 ページ 1 リクエストで、収集 → タイトル整形 → 後処理の 3 段を再生する。

    原本の webmisc レコードは `collect_webmisc.py`（生 <title>）→
    `refine_titles_webmisc.py --apply`（見出し優先のタイトルに差し替え）→
    `fix_webmisc.py`（国土交通白書の年版見出し・フラグ再計算）の順に作られている。
    最終的な title / year / difficulty_flags はこの順序に依存するため、
    同じ順序で適用する。3 段とも同じ HTML から作れるので取得は 1 回で足りる。

    タイトル衝突回避（`refine_titles_webmisc.do_apply` が、整形後タイトルが他と
    衝突する場合は生 <title> 側に差し戻す）だけは全件の集合に依存する。
    `--keys` や `--only-source` で対象を絞ると母集合が変わるため、ここでは
    「今回再取得した集合」の中で判定する。全件実行なら原本と同じ判定になる。
    """
    src_by_name = {s.name: s for s in webmisc.SOURCES}
    pages: list[_WebPage] = []
    failures: list[Failure] = []

    for t in targets:
        if not webmisc.robots_ok(t.source_url):
            failures.append(Failure(t.key, t.source, "robots.txt の Disallow 配下"))
            continue
        try:
            fetch.n_requests += 1
            resp = webmisc.polite_get(t.source_url)
        except requests.RequestException as exc:
            failures.append(Failure(t.key, t.source, f"ページ取得失敗: {exc}"))
            continue
        if resp.status_code != 200:
            failures.append(Failure(t.key, t.source, f"HTTP {resp.status_code}"))
            continue
        resp.encoding = resp.apparent_encoding
        text = resp.text
        raw_title = webmisc.get_title(text)
        if not raw_title:
            failures.append(Failure(t.key, t.source, "<title>/<h1> からタイトルを取れない"))
            continue
        og = ""
        for pat in _OG_TITLE:
            if (m := re.search(pat, text, re.I)):
                og = refine_titles.cleanhtml(m.group(1))
                break
        mlit = _MLIT_HEADING.search(text)
        pages.append(_WebPage(target=t, raw_title=raw_title, og=og,
                              h1s=re.findall(r"<h1[^>]*>(.*?)</h1>", text, re.S | re.I),
                              mlit_heading=mlit.group(0) if mlit else ""))

    # 第 2 段のタイトル整形は衝突判定のため全件をまとめて決める。
    refined = {p.target.key: refine_titles.pick_base(
        {"raw_title": p.raw_title, "og": p.og, "h1s": p.h1s}) for p in pages}
    collisions = {t for t, n in collections.Counter(refined.values()).items() if n > 1}

    records: list[dict] = []
    for p in pages:
        t = p.target
        src = src_by_name.get(t.source_name)
        org = src.org if src else ""
        # 第 1 段: 生 <title> のまま。urldate は取得日（実行日ではない）。
        fields: dict[str, str] = {"title": p.raw_title, "url": t.source_url,
                                  "urldate": t.urldate}
        if org:
            fields["author"] = org
        if (yr := webmisc.derive_year(p.raw_title)):
            fields["year"] = yr
        notes: list[str] = []

        # 第 2 段: 見出し優先のタイトルへ。衝突する場合は生 <title> に差し戻す。
        nt = refined[t.key]
        if nt in collisions:
            nt = p.raw_title
        if nt != fields["title"]:
            notes.append(f"raw_title: {p.raw_title}")
            fields["title"] = nt
        if (yr := refine_titles.derive_year(nt)):
            fields["year"] = yr

        # 第 3 段: 国土交通白書は <title> が年版を含まないのでページ見出しを採る。
        if t.source_name == "国土交通白書" and p.mlit_heading:
            fields["title"] = p.mlit_heading
            notes.append("title taken from page heading (<title> is generic)")
        if (yr := fix_webmisc.derive_year(fields["title"])):
            fields["year"] = yr

        rec = {"provisional_key": t.provisional_key, "entry_type": "misc",
               "bibtex_fields": fields, "notes": "; ".join(notes)}
        if (why := stamp(rec, t) or check_fields(rec, t)):
            failures.append(Failure(t.key, t.source, why))
            continue
        records.append(rec)
    return records, failures


# --------------------------------------------------------------------------- #
# 実行
# --------------------------------------------------------------------------- #

def write_interim(workdir: Path, source: str, records: list[dict],
                  replace: bool) -> Path:
    """<workdir>/<source>/records.jsonl を書く。

    provisional_key 順に並べる（マージ側の順序はキーで固定されるので出力順は
    結果に影響しないが、差分を読みやすくするため）。`replace` が False のときは
    既存行を読み、同じ provisional_key を差し替えて残りを保つ（キー限定実行を
    重ねて全件に近づけられるように）。
    """
    out_dir = workdir / source
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / "records.jsonl"
    merged: dict[str, dict] = {}
    if path.exists() and not replace:
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                old = json.loads(line)
                merged[old["provisional_key"]] = old
    for rec in records:
        merged[rec["provisional_key"]] = rec
    with path.open("w", encoding="utf-8") as fh:
        for key in sorted(merged):
            fh.write(json.dumps(merged[key], ensure_ascii=False) + "\n")
    return path


def run_merge(workdir: Path, out_dir: Path, key_map: Path) -> int:
    cmd = [sys.executable, str(Path(__file__).resolve().parent / "merge_assign_keys.py"),
           "--input-dir", str(workdir), "--output-dir", str(out_dir),
           "--key-map", str(key_map)]
    print(f"\n$ {' '.join(cmd)}")
    return subprocess.call(cmd)


def run_derived(out_dir: Path, annotations: Path) -> int:
    cmd = [sys.executable, str(Path(__file__).resolve().parent / "make_derived_bib.py"),
           "--in", str(out_dir / "ja_bib_full.bib"),
           "--out", str(out_dir / "ja_bib_derived.bib"),
           "--key-map", str(out_dir / "key_map.csv"),
           "--names-table", str(annotations / "name_boundaries.jsonl"),
           "--manual-table", str(annotations / "manual_name_table.jsonl")]
    print(f"\n$ {' '.join(cmd)}")
    return subprocess.call(cmd)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--manifest", type=Path, default=REPO / "manifest.csv")
    ap.add_argument("--key-map", type=Path, default=REPO / "key_map.csv")
    ap.add_argument("--annotations", type=Path, default=REPO / "annotations")
    ap.add_argument("--workdir", type=Path, default=REPO / "data" / "interim",
                    help="records.jsonl の置き場 (既定: data/interim)")
    ap.add_argument("--raw-dir", type=Path, default=REPO / "data" / "raw",
                    help="生応答のキャッシュ置き場 (既定: data/raw)")
    ap.add_argument("--out-dir", type=Path, default=REPO / "dataset",
                    help="ja_bib_full.bib / metadata.csv の出力先 (既定: dataset)")
    ap.add_argument("--only-source", default="", help=f"出典を限定 ({'/'.join(SOURCES)})")
    ap.add_argument("--keys", default="", help="最終キーをカンマ区切りで限定")
    ap.add_argument("--replace", action="store_true",
                    help="records.jsonl を今回取得分だけで置き換える (既定は追記マージ)")
    ap.add_argument("--refresh", action="store_true",
                    help="キャッシュ済みの索引ページも取り直す (anlp)")
    ap.add_argument("--no-merge", action="store_true",
                    help="records.jsonl まででマージ・派生生成を行わない")
    args = ap.parse_args()

    targets = load_targets(args.manifest, args.key_map,
                           args.annotations / "field_overrides.jsonl")
    if args.only_source:
        wanted = set(args.only_source.split(","))
        if unknown := wanted - set(SOURCES):
            raise SystemExit(f"未知の出典: {sorted(unknown)}")
        targets = [t for t in targets if t.source in wanted]
    if args.keys:
        wanted_keys = [k.strip() for k in args.keys.split(",") if k.strip()]
        by_key = {t.key: t for t in targets}
        if missing := [k for k in wanted_keys if k not in by_key]:
            raise SystemExit(f"マニフェストに無いキー: {missing}")
        targets = [by_key[k] for k in wanted_keys]
    if not targets:
        raise SystemExit("対象が 0 件")

    by_source: dict[str, list[Target]] = {}
    for t in targets:
        by_source.setdefault(t.source, []).append(t)
    partial = bool(args.only_source or args.keys)
    if partial and "webmisc" in by_source:
        print("NOTE: webmisc のタイトル衝突回避は再取得した集合の中で判定する "
              "(全件実行時と結果が変わりうる)", file=sys.stderr)

    fetch = Fetcher()
    all_failures: list[Failure] = []
    for source in SOURCES:
        group = by_source.get(source)
        if not group:
            continue
        print(f"[{source}] {len(group)} 件を再取得 ...", file=sys.stderr)
        if source == "jstage":
            records, failures = rebuild_jstage(group, fetch)
        elif source == "crossref":
            records, failures = rebuild_crossref(group, fetch)
        elif source == "cinii":
            records, failures = rebuild_cinii(group, fetch)
        elif source == "cinii_supp":
            records, failures = rebuild_cinii_supp(group, fetch)
        elif source == "ndl":
            records, failures = rebuild_ndl(group, fetch)
        elif source == "anlp":
            records, failures = rebuild_anlp(group, args.raw_dir / "anlp", args.refresh)
        else:
            records, failures = rebuild_webmisc(group, fetch)
        path = write_interim(args.workdir, source, records, args.replace)
        all_failures.extend(failures)
        print(f"[{source}] 成功 {len(records)} / 失敗 {len(failures)} -> {path}",
              file=sys.stderr)

    if all_failures:
        report = args.workdir / "rebuild_failures.csv"
        report.parent.mkdir(parents=True, exist_ok=True)
        with report.open("w", encoding="utf-8", newline="") as fh:
            w = csv.writer(fh)
            w.writerow(["key", "source", "reason"])
            for f in all_failures:
                w.writerow([f.key, f.source, f.reason])
        print(f"\n再取得できなかった {len(all_failures)} 件 (-> {report}):", file=sys.stderr)
        for f in all_failures:
            print(f"  SKIP {f.key} [{f.source}] {f.reason}", file=sys.stderr)

    print(f"\nHTTP リクエスト数: {fetch.n_requests}", file=sys.stderr)
    if args.no_merge:
        return 0
    if (rc := run_merge(args.workdir, args.out_dir, args.key_map)):
        return rc
    return run_derived(args.out_dir, args.annotations)


if __name__ == "__main__":
    raise SystemExit(main())
