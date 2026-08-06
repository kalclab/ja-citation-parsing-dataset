#!/usr/bin/env python3
"""Plausibility screening for @book records (shared by the NDL and CiNii collectors).

Removes records that would look unnatural in an academic reference list, in two
classes surfaced by manual review of all 250 collected titles (2026-07-17):

A. Non-scholarly material mis-collected as an academic book:
   - Exam-prep / drill / licensing-review books (e.g. TAC出版 のトレーニング経済学,
     ○×問題 quiz books, 社労士試験必携, Medic Media 「病気がみえる」国試レビュー).
   - Consumer how-to / hobby popular books (e.g. ナツメ社「史上最強図解これならわかる!」,
     秀和システム「…の基本と仕組み」, 「図解…やさしい…」).
   - Software / product operation manuals tied to a specific obsolete product
     (e.g. コロナ社「R:BASE PROのすすめ」, 朝倉書店「IBM5550…やさしいBASIC」).
   - Learned-society yearbook (年報) volumes whose "title" is a session / common
     theme heading, ISBN-typed as a book (e.g. 現代書館「共通論題『幸福の経済社会学』」,
     「絆の経済社会学」= 経済社会学会年報 各巻). Detected via series containing 年報.

B. Non-Japanese bibliographies that slipped past the has-Japanese gate because CJK
   kanji overlap (simplified-Chinese, traditional-Chinese/Taiwan, Korean books,
   e.g. 重庆出版社「10新经济学科」, 中華法學會「中華法學」, 一潮閣「韓國親族制度研究」,
   서울大學校出版部「法學通論」). The dataset is for Japanese-language references.

Kept deliberately (NOT screened): translations and classics (訳書・古典全集),
glossaries / handbooks / dictionaries (用語集・便覧・事典・ハンドブック), lab-experiment
and clinical practice texts from academic medical publishers, intro university
textbooks. These are natural in a reference list.

Each predicate returns (excluded: bool, reason: str). Reasons are logged and
summarised in a QC report.
"""
from __future__ import annotations

import re

# --- Class A: non-scholarly -------------------------------------------------

# Publishers that are essentially exam-prep / licensing-review houses.
# "TAC" matches both "TAC出版" and "TAC株式会社出版事業部"; no scholarly JP
# publisher name contains that token.
EXAM_PUBLISHERS = (
    "TAC", "東京リーガルマインド", "早稲田経営出版", "大原出版",
    "Medic Media", "メディックメディア",
    # 法学書院 is a licensing-exam specialist (行政書士/司法書士/弁理士/税理士/裁判所職員 ほか);
    # every record it contributed to the 法学 query is exam-prep, so it is blanket-excluded.
    "法学書院",
)
# General-interest / hobby how-to publishers (their output is not scholarly).
POPULAR_PUBLISHERS = ("ナツメ社", "秀和システム", "ソーテック社", "西東社", "日本文芸社")

# Title markers of exam-prep / drill / licensing material. NOTE: bare 試験 and 検定
# are deliberately excluded -- they hit legitimate scholarly terms (臨床試験 clinical
# trial, (仮説)検定 statistical test). Use specific licensing/drill phrasings only.
EXAM_TITLE = re.compile(
    r"社労士|司法試験|公務員試験|宅建|簿記検定|過去問|○×問題|[×〇○]×?問題集|"
    r"一問一答|試験対策|試験必携|受験|資格ガイダンス|資格ガイド|合格体験|士試験合格"
)
# Title markers of consumer how-to / popular framing.
POPULAR_TITLE = re.compile(
    r"史上最強|図解入門|超図解|マンガでわかる|いちばんやさしい|世界一やさしい|"
    r"図解.{0,12}やさしい|の基本と仕組み$|だれでもわかる|サルでもわかる"
)
# Software / product operation manuals (obsolete product tokens + manual phrasing).
SOFTWARE_TITLE = re.compile(
    r"R:BASE|IBM\s?5550|MS-?DOS|一太郎|Lotus\s?1-2-3|dBASE|"
    r"アプリケーションガイド|コマンドモード操作|ファミリーのためのやさしいBASIC|"
    r"98活用|PC-?9800|PC-?98[^0-9]|ＭＳＸ|MSX|ワープロ活用|マイコン入門"
)


def screen_nonscholarly(title: str, publisher: str, series: str | None) -> tuple[bool, str]:
    pub = publisher or ""
    ser = series or ""
    if any(p in pub for p in EXAM_PUBLISHERS):
        return True, f"exam_prep_publisher:{pub}"
    if EXAM_TITLE.search(title):
        return True, "exam_prep_title"
    if any(p in pub for p in POPULAR_PUBLISHERS):
        return True, f"popular_howto_publisher:{pub}"
    if POPULAR_TITLE.search(title):
        return True, "popular_howto_title"
    if SOFTWARE_TITLE.search(title):
        return True, "software_manual"
    if re.search(r"年報", ser) or title.startswith("共通論題"):
        return True, "society_yearbook_session"  # periodical volume mis-typed as book
    return False, ""


# --- Class B: non-Japanese --------------------------------------------------

# Foreign academic publishers (mainland China / Taiwan / Korea) seen in the data.
FOREIGN_PUBLISHERS = (
    "重庆", "重慶", "人民法院", "人民出版社", "法律出版社", "南开", "南開",
    "大學校出版", "一潮閣", "中華法學會", "台灣法學會", "商务印书馆",
    "北京大学", "清华", "复旦", "高等教育出版社", "中国政法大学",
    # Taiwan / Korea academic-law publishers seen leaking via the CiNii law queries
    "元照", "五南", "三民書局", "新學林", "博英社", "法文社", "中央研究院",
)
HANGUL = re.compile(r"[가-힣]")
# A conservative set of simplified-Chinese-only characters not used in Japanese.
SIMPLIFIED = set("经济证业宪灿产车东习义务华际团应专单极复众邓两对观变价签龙")


def screen_non_japanese(title: str, publisher: str) -> tuple[bool, str]:
    pub = publisher or ""
    if any(p in pub for p in FOREIGN_PUBLISHERS):
        return True, f"foreign_publisher:{pub}"
    if HANGUL.search(title) or HANGUL.search(pub):
        return True, "korean_script"
    hits = [c for c in title if c in SIMPLIFIED]
    if hits:
        return True, "simplified_chinese:" + "".join(sorted(set(hits)))
    return False, ""


def screen_book(title: str, publisher: str, series: str | None = None) -> tuple[bool, str]:
    """Return (excluded, reason). A record is dropped if either class fires."""
    ex, why = screen_non_japanese(title, publisher)
    if ex:
        return True, why
    return screen_nonscholarly(title, publisher, series)
