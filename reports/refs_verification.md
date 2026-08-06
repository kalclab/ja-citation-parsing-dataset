# Phase 2 生成後検証（突き合わせ＋スタイル多様性）

対象: 988 レコード × 7 スタイル。random seed = 20260717。

## スタイル間 出力同一率

- 1 レコードあたりの相異なる文字列数: 平均 7.00 / 7
- いずれか 2 スタイルが同一文字列になるレコード: **0 / 988（0.0%）**
- 全スタイル同一のレコード: 0

スタイル対の同一出力: なし（全対で相違）。

## generation_status 内訳（スタイル別）

| style | ok | ok_partial | failed |
|---|---|---|---|
| chicago-author-date | 988 | 0 | 0 |
| ipsjsort | 988 | 0 | 0 |
| jecon-mod | 988 | 0 | 0 |
| jpa2022 | 988 | 0 | 0 |
| jplain | 988 | 0 | 0 |
| jsai | 988 | 0 | 0 |
| sist02 | 988 | 0 | 0 |

## chicago-author-date: ランダム 20 件 突き合わせ

| key | type | status | 原 BibTeX（圧縮） | ref_string |
|---|---|---|---|---|
| art0028 | article | ok | author=耳塚 寛明 / title=学校組織と生往文化・進路形成 / journal=教育社会学研究 / publisher=一般社団法人　日本教育社会学会 / volume=37 / number=0 / pages=34-46,en234 / year=1982 / doi=10.11151/eds1951.37.34 | 耳塚寛明. 1982年. 「学校組織と生往文化・進路形成」. 教育社会学研究 37 (0): 34–46, en234. https://doi.org/10.11151/eds1951.37.34. |
| art0110 | article | ok | author=山中 速人 / title=石原俊著『近代日本と小笠原諸島――移動民の島々と帝国』 / journal=社会学評論 / volume=59 / number=2 / pages=436-438 / year=2008 / doi=10.4057/jsr.59.436 | 山中速人. 2008年. 「石原俊著『近代日本と小笠原諸島――移動民の島々と帝国』」. 社会学評論 59 (2): 436–38. https://doi.org/10.4057/jsr.59.436. |
| art0114 | article | ok | author=正村 俊之 / title=石井和平著『社会情報学――情報技術と社会の共変』 / journal=社会学評論 / volume=59 / number=4 / pages=830-831 / year=2009 / doi=10.4057/jsr.59.830 | 正村俊之. 2009年. 「石井和平著『社会情報学――情報技術と社会の共変』」. 社会学評論 59 (4): 830–31. https://doi.org/10.4057/jsr.59.830. |
| art0186 | article | ok | author=百武 幸子 / title=やりがいのある仕事へ(<シリーズ>"ポスドク"問題その20) / journal=日本物理学会誌 / volume=64 / number=12 / pages=945-947 / year=2009 / doi=10.11316/butsuri.64.12_945 | 百武幸子. 2009年. 「やりがいのある仕事へ(<シリーズ>"ポスドク"問題その20)」. 日本物理学会誌 64 (12): 945–47. https://doi.org/10.11316/butsuri.64.12_945. |
| art0223 | article | ok | author=碇 醇 / title=エタノール水溶液の単蒸留における微量成分の挙動について / journal=化学工学 / volume=34 / number=11 / pages=1185-1192,a1 / year=1970 / doi=10.1252/kakoronbunshu1953.34.1185 | 碇醇. 1970年. 「エタノール水溶液の単蒸留における微量成分の挙動について」. 化学工学 34 (11): 1185–92, a1. https://doi.org/10.1252/kakoronbunshu1953.34.1185. |
| art0233 | article | ok | author=荒木 賢二 and 大橋 克洋 and 山崎 俊司 and 廣瀬 康行 and 山下 芳範 and 山本 隆一 and 皆川 和史 and 坂本 憲広 and 吉原 博幸 / title=Medical Markup Language (MML) バージョン 2.21　－XML を用いた医療情報交換規約－ / journal=医療情報学 / volume=20 / number=2 / pages=79-85 / year=2000 / doi=10.14948/jami.20.79 | 荒木賢二, 大橋克洋, 山崎俊司, ほか. 2000年. 「Medical Markup Language (MML) バージョン 2.21 －XML を用いた医療情報交換規約－」. 医療情報学 20 (2): 79–85. https://doi.org/10.14948/jami.20.79. |
| art0295 | article | ok | author=小林 裕美 and 森山 美知子 / title=在宅で親や配偶者の看取りを行う介護者の情緒体験と予期悲嘆 / journal=日本看護科学会誌 / volume=30 / number=4 / pages=4_6-4_16 / year=2010 / doi=10.5630/jans.30.4_6 | 小林裕美, と 森山美知子. 2010年. 「在宅で親や配偶者の看取りを行う介護者の情緒体験と予期悲嘆」. 日本看護科学会誌 30 (4): 4_6–16. https://doi.org/10.5630/jans.30.4_6. |
| bok0065 | book | ok | author=伊藤, 明子 / title=基礎看護技術 / publisher=医学書院 / year=2001 | 伊藤明子. 2001年. 基礎看護技術. 新看護学, 7 . 基礎看護\|\|キソ カンゴ ; 2. 医学書院. |
| bok0117 | book | ok | author=角淳一 and 吉田脩二 / title=愛のおしゃべりクリニック : ラジオからのメッセージ / publisher=ミネルヴァ書房 / year=1986 | 角淳一, と 吉田脩二. 1986年. 愛のおしゃべりクリニック : ラジオからのメッセージ. ミネルヴァ書房. |
| bok0125 | book | ok | author=加藤幹郎 / title=愛と偶然の修辞学 / publisher=勁草書房 / year=1990 | 加藤幹郎. 1990年. 愛と偶然の修辞学. 勁草書房. |
| bok0147 | book | ok | editor=東京大学綜合研究会 / title=相性 / publisher=東京大学出版会 / year=2001 | 東京大学綜合研究会, 編. 2001年. 相性. 東京大学公開講座 ; 72. 東京大学出版会. |
| bok0219 | book | ok | author=佐藤喜和 / title=アーバン・ベア = Conservation and Management of Urban Bears : となりのヒグマと向き合う / publisher=東京大学出版会 / year=2021 | 佐藤喜和. 2021年. アーバン・ベア = Conservation and Management of Urban Bears : となりのヒグマと向き合う. 東京大学出版会. |
| inp0057 | inproceedings | ok | author=五藤巧 and 渡辺太郎 / title=文法誤り訂正における参照なし評価尺度を用いた分析的評価法 / booktitle=言語処理学会第30回年次大会発表論文集 / year=2024 / url=https://www.anlp.jp/proceedings/annual_meeting/2024/pdf_dir/D8-5.pdf | 五藤巧., と 渡辺太郎. 2024年. 「文法誤り訂正における参照なし評価尺度を用いた分析的評価法」. 言語処理学会第30回年次大会発表論文集. https://www.anlp.jp/proceedings/annual_meeting/2024/pdf_dir/D8-5.pdf. |
| inp0082 | inproceedings | ok | author=秋山 元秀 / title=西安市における城中村について / booktitle=日本地理学会発表要旨集 69 / pages=194 / year=2006 | 秋山元秀. 2006年. 「西安市における城中村について」. 日本地理学会発表要旨集 69, 194. |
| inp0128 | inproceedings | ok | author=三宅 雅矩 and 池上 高志 and 岡 瑞起 and 橋本 康弘 / title=Hawkes Processと最適区間幅推定を用いたWeb Dataの解析 / booktitle=人工知能学会全国大会論文集 / volume=JSAI2017 / pages=4I25 / year=2017 / doi=10.11517/pjsai.JSAI2017.0_4I25 | 三宅雅矩, 池上高志, 岡瑞起, と 橋本康弘. 2017年. 「Hawkes Processと最適区間幅推定を用いたWeb Dataの解析」. 人工知能学会全国大会論文集 JSAI2017: 4I25. https://doi.org/10.11517/pjsai.JSAI2017.0_4I25. |
| inp0165 | inproceedings | ok | author=笠松 美歩 and 上原 宏 and 宇津呂 武仁 and 齋藤 有 / title=絵本に対する子どもの認知発達的反応に着目した絵本レビュー・発達心理学文献の比較 / booktitle=人工知能学会全国大会論文集 / volume=JSAI2018 / pages=1J105 / year=2018 / doi=10.11517/pjsai.JSAI2018.0_1J105 | 笠松美歩, 上原宏., 宇津呂武仁, と 齋藤有. 2018年. 「絵本に対する子どもの認知発達的反応に着目した絵本レビュー・発達心理学文献の比較」. 人工知能学会全国大会論文集 JSAI2018: 1J105. https://doi.org/10.11517/pjsai.JSAI2018.0_1J105. |
| inp0205 | inproceedings | ok | author=鎌田 基司 and 村上 克介 and 松本 隆仁 and 村瀬 治比古 and 諸見里 聰 and 増田 篤稔 and 洞口 公俊 and 向阪 信一 / title=オキナワモズクの光合成特性の測定 / booktitle=照明学会　全国大会講演論文集 / volume=35 / pages=159 / year=2002 / doi=10.11515/ieijac.35.0.159.0 | 鎌田基司, 村上克介, 松本隆仁, ほか. 2002年. 「オキナワモズクの光合成特性の測定」. 照明学会 全国大会講演論文集 35: 159. https://doi.org/10.11515/ieijac.35.0.159.0. |
| web0083 | misc | ok | author=総務省統計局 / title=世界の統計 / url=https://www.stat.go.jp/data/sekai/index.html | 総務省統計局. 日付なし-b. 世界の統計. 参照 2026年7月17日. https://www.stat.go.jp/data/sekai/index.html. |
| web0132 | misc | ok | author=人工知能学会 / title=人工知能学会倫理委員会設立の趣旨 / url=https://www.ai-gakkai.or.jp/ai-elsi/about/purpose | 人工知能学会. 日付なし-b. 人工知能学会倫理委員会設立の趣旨. 参照 2026年7月17日. https://www.ai-gakkai.or.jp/ai-elsi/about/purpose. |
| web0153 | misc | ok | author=コトバンク / title=風早公紀 / url=https://kotobank.jp/word/%E9%A2%A8%E6%97%A9%E5%85%AC%E7%B4%80-16005 | コトバンク. 日付なし-bd. 風早公紀. 参照 2026年7月17日. https://kotobank.jp/word/%E9%A2%A8%E6%97%A9%E5%85%AC%E7%B4%80-16005. |

## ipsjsort: ランダム 20 件 突き合わせ

| key | type | status | 原 BibTeX（圧縮） | ref_string |
|---|---|---|---|---|
| art0077 | article | ok | author=浅田, 侑樹 / title=The 12th IAGG Master Class on Ageing in Asiaに参加して / journal=Nippon Ronen Igakkai Zasshi. Japanese Journal of Geriatrics / publisher=The Japan Geriatrics Society / volume=61 / number=4 / pages=495-496 / year=2024 / doi=10.3143/geriatrics.61.495 / url=https://doi.org/10.3143/geriatrics.61.495 | 浅田侑樹：The 12th IAGG Master Class on Ageing in Asiaに参加して，Nippon Ronen Igakkai Zasshi. Japanese Journal of Geriatrics, Vol. 61, No. 4, pp. 495–496（オンライン），10.3143/geriatrics.61.495 (2024). |
| art0129 | article | ok | author=太幡 直也 / title=気づかれたくない理由が懸念的被透視感を感じた際の言語的方略に与える影響 / journal=心理学研究 / volume=80 / number=3 / pages=199-206 / year=2009 / doi=10.4992/jjpsy.80.199 | 太幡直也：気づかれたくない理由が懸念的被透視感を感じた際の言語的方略に与える影響，心理学研究， Vol. 80, No. 3, pp. 199–206（オンライン），10.4992/jjpsy.80.199 (2009). |
| art0209 | article | ok | author=森川 邦彦 and 永原 幹雄 and 熊谷 幸司 and 小森 雅晴 and 松本 將 / title=コニカルギヤのかみ合い効率解析 / journal=日本機械学会論文集 / volume=80 / number=815 / pages=DSM0211 / year=2014 / doi=10.1299/transjsme.2014dsm0211 | 森川邦彦，永原幹雄，熊谷幸司，小森雅晴，松本將：コニカルギヤのかみ合い効率解析，日本機械学会論文集， Vol. 80, No. 815, p. DSM0211（オンライン），10.1299/transjsme.2014dsm0211 (2014). |
| art0234 | article | ok | author=別府 文隆 and 木内 貴弘 and 大江 和彦 and 櫻井 恒太郎 / title=UMIN（大学病院医療情報ネットワーク）における文部省文書広報システムの運用と評価 / journal=医療情報学 / volume=20 / number=3 / pages=231-236 / year=2000 / doi=10.14948/jami.20.231 | 別府文隆，木内貴弘，大江和彦，櫻井恒太郎：UMIN（大学病院医療情報ネットワーク）における文部省文書広報システムの運用と評価，医療情報学， Vol. 20, No. 3, pp. 231–236（オンライン），10.14948/jami.20.231 (2000). |
| art0292 | article | ok | author=深田 順子 and 北池 正 and 石垣 和子 / title=訪問看護における摂食・嚥下障害看護の質評価指標改訂版の妥当性と信頼性の検討 / journal=日本看護科学会誌 / volume=30 / number=1 / pages=1_80-1_90 / year=2010 / doi=10.5630/jans.30.1_80 | 深田順子，北池正，石垣和子：訪問看護における摂食・嚥下障害看護の質評価指標改訂版の妥当性と信頼性の検討，日本看護科学会誌， Vol. 30, No. 1, pp. 1_80–1_90（オンライン），10.5630/jans.30.1_80 (2010). |
| bok0037 | book | ok | author=情報科学技術協会 / title=21世紀初頭の情報科学技術予測 : アンケート調查報告書 / publisher=情報科学技術協会 / year=1990 | 情報科学技術協会：21世紀初頭の情報科学技術予測 : アンケート調查報告書，情報科学技術協会 (1990). |
| bok0056 | book | ok | author=情報科学技術協会 / title=情報検索の基礎知識 / publisher=情報科学技術協会 / year=2003 | 情報科学技術協会：情報検索の基礎知識，情報科学技術協会 (2003). |
| bok0147 | book | ok | editor=東京大学綜合研究会 / title=相性 / publisher=東京大学出版会 / year=2001 | 東京大学綜合研究会（編）：相性，東京大学出版会，東京 (2001). |
| bok0170 | book | ok | editor=早川弘一 and 髙野照夫 and 高島尚美 / title=ICU・CCU看護 = Nursing care in ICU & CCU / publisher=医学書院 / year=2013 | 早川弘一，髙野照夫，高島尚美（編）：ICU・CCU看護 = Nursing care in ICU & CCU，医学書院，東京 (2013). |
| bok0193 | book | ok | author=古田克利 / title=IT技術者の能力限界の研究 : ケイパビリティ・ビリーフの観点から / publisher=日本評論社 / year=2017 | 古田克利：IT技術者の能力限界の研究 : ケイパビリティ・ビリーフの観点から，日本評論社，東京 (2017). |
| bok0242 | book | ok | author=Abel, Niels Henrik and Galois, Évariste and 高瀬, 正仁 / title=アーベル/ガロア楕円関数論 / publisher=朝倉書店 / year=1998 | Abel, N. H.，Galois, É.，高瀬正仁：アーベル/ガロア楕円関数論，朝倉書店 (1998). |
| bok0249 | book | ok | author=大津, 政康 / title=アコースティック・エミッションの特性と理論 : 構造物の診断と破壊現象解析 / publisher=森北出版 / year=2022 | 大津政康：アコースティック・エミッションの特性と理論 : 構造物の診断と破壊現象解析，森北出版，第2版pod版 edition (2022). |
| inp0154 | inproceedings | ok | author=福田 直樹 / title=合意形成過程の蓄積・知識化のためのLOD技術に基づく議論過程クラウドの設計と課題 / booktitle=人工知能学会全国大会論文集 / volume=JSAI2018 / pages=1D3OS28b05 / year=2018 / doi=10.11517/pjsai.JSAI2018.0_1D3OS28b05 | 福田直樹：合意形成過程の蓄積・知識化のためのLOD技術に基づく議論過程クラウドの設計と課題，人工知能学会全国大会論文集，Vol. JSAI2018, p. 1D3OS28b05（オンライン），10.11517/pjsai.JSAI2018.0_1D3OS28b05 (2018). |
| inp0155 | inproceedings | ok | author=川崎 樹 and 高橋 和子 / title=論理型言語PROLEGから双極議論フレームワークへの変換 / booktitle=人工知能学会全国大会論文集 / volume=JSAI2018 / pages=1E104 / year=2018 / doi=10.11517/pjsai.JSAI2018.0_1E104 | 川崎樹，高橋和子：論理型言語PROLEGから双極議論フレームワークへの変換，人工知能学会全国大会論文集，Vol. JSAI2018, p. 1E104（オンライン），10.11517/pjsai.JSAI2018.0_1E104 (2018). |
| inp0214 | inproceedings | ok | author=中村 俊之 and 川島 浄子 / title=ガラス管の組成が環形蛍光ランプの特性に及ぼす影響 / booktitle=照明学会　全国大会講演論文集 / volume=35 / pages=7 / year=2002 / doi=10.11515/ieijac.35.0.7.0 | 中村俊之，川島浄子：ガラス管の組成が環形蛍光ランプの特性に及ぼす影響，照明学会 全国大会講演論文集，Vol. 35, p. 7（オンライン），10.11515/ieijac.35.0.7.0 (2002). |
| inp0222 | inproceedings | ok | author=シャザダ&middot;ナイヤール ジハン / title=会計情報システムの形成: ベンチャー投資家とベンチャー企業の関係 —相互関係アプローチ / booktitle=日本経営システム学会全国研究発表大会講演論文集 / volume=28 / pages=121-124 / year=2002 / doi=10.11559/jams.28.0.121.0 | ジハン：会計情報システムの形成: ベンチャー投資家とベンチャー企業の関係 —相互関係アプローチ，日本経営システム学会全国研究発表大会講演論文集，Vol. 28, pp. 121–124（オンライン），10.11559/jams.28.0.121.0 (2002). |
| web0017 | misc | ok | author=内閣府男女共同参画局 / title=男女共同参画白書 令和6年版 全体版（HTML形式） / year=2024 / url=https://www.gender.go.jp/about_danjo/whitepaper/r06/zentai/index.html | 内閣府男女共同参画局：男女共同参画白書 令和6年版 全体版（HTML形式），https://www.gender.go.jp/about_danjo/whitepaper/r06/zentai/index.html (2024). 2026-07-17 参照. |
| web0102 | misc | ok | author=総務省統計局 / title=サービス産業動態統計調査 / url=https://www.stat.go.jp/data/mbss/index.html | 総務省統計局：サービス産業動態統計調査，https://www.stat.go.jp/data/mbss/index.html. 2026-07-17 参照. |
| web0124 | misc | ok | author=個人情報保護委員会 / title=特定個人情報保護評価 / url=https://www.ppc.go.jp/legal/assessment/ | 個人情報保護委員会：特定個人情報保護評価，https://www.ppc.go.jp/legal/assessment/. 2026-07-17 参照. |
| web0145 | misc | ok | author=コトバンク / title=子宮口 / url=https://kotobank.jp/word/%E5%AD%90%E5%AE%AE%E5%8F%A3-14084 | コトバンク：子宮口，https://kotobank.jp/word/%E5%AD%90%E5%AE%AE%E5%8F%A3-14084. 2026-07-17 参照. |

## jecon-mod: ランダム 20 件 突き合わせ

| key | type | status | 原 BibTeX（圧縮） | ref_string |
|---|---|---|---|---|
| art0038 | article | ok | author=兼子 勝 / title=故望月教授の「地学」について / journal=地学雑誌 / publisher=東京 : 東京地学協会 / volume=73 / number=2 / pages=121-124 / year=1964 | 兼子勝 (1964) 「故望月教授の「地学」について」，『地学雑誌』，第73巻，第2号，121–124頁． |
| art0100 | article | ok | author=森 真一 / title=片桐雅隆著『認知社会学の構想――カテゴリー・自己・社会』 / journal=社会学評論 / volume=58 / number=2 / pages=254-255 / year=2007 / doi=10.4057/jsr.58.254 | 森真一 (2007) 「片桐雅隆著『認知社会学の構想――カテゴリー・自己・社会』」，『社会学評論』，第58巻，第2号，254–255頁，DOI: 10.4057/jsr.58.254． |
| art0172 | article | ok | author=物理学史資料委員会　学会150年史連載編集グループ / title=欧文誌の電子化，定款の改定，男女共同参画への取り組み，分科・領域委員会設置：2000-2002 / journal=日本物理学会誌 / volume=81 / number=4 / pages=186 / year=2026 / doi=10.11316/butsuri.81.4_186 | (2026b) 「欧文誌の電子化，定款の改定，男女共同参画への取り組み，分科・領域委員会設置：2000-2002」，『日本物理学会誌』，第81巻，第4号，186頁，DOI: 10.11316/butsuri.81.4_186． |
| art0177 | article | ok | author=播磨 尚朝 / title=JPSJの最近の注目論文から：2月の編集委員会より / journal=日本物理学会誌 / volume=81 / number=6 / pages=304-306 / year=2026 / doi=10.11316/butsuri.81.6_304 | (2026c) 「JPSJの最近の注目論文から：2月の編集委員会より」，『日本物理学会誌』，第81巻，第6号，304–306頁，DOI: 10.11316/butsuri.81.6_304． |
| art0218 | article | ok | author=宝沢 光紀 and 只木 槙力 and 前田 四郎 / title=単一孔から生成する液滴の大きさについて / journal=化学工学 / volume=33 / number=9 / pages=893-898,a1 / year=1969 / doi=10.1252/kakoronbunshu1953.33.893 | 宝沢光紀・只木槙力・前田四郎 (1969) 「単一孔から生成する液滴の大きさについて」，『化学工学』，第33巻，第9号，893–898,a1頁，DOI: 10.1252/kakoronbunshu1953.33.893． |
| art0220 | article | ok | author=小川 政英 and 菅原 勇次郎 and 国井 大蔵 / title=移流動層による湿潤ヒドロゲル乾燥プロセスの開発研究 / journal=化学工学 / volume=34 / number=1 / pages=87-93,a1 / year=1970 / doi=10.1252/kakoronbunshu1953.34.87 | 小川政英・菅原勇次郎・国井大蔵 (1970) 「移流動層による湿潤ヒドロゲル乾燥プロセスの開発研究」，『化学工学』，第34巻，第1号，87–93,a1頁，DOI: 10.1252/kakoronbunshu1953.34.87． |
| art0225 | article | ok | author=森山 昭 / title=固定層による流体・固体等温反応操作の解析法 / journal=化学工学 / volume=34 / number=12 / pages=1308-1314,a1 / year=1970 / doi=10.1252/kakoronbunshu1953.34.1308 | 森山昭 (1970) 「固定層による流体・固体等温反応操作の解析法」，『化学工学』，第34巻，第12号，1308–1314,a1頁，DOI: 10.1252/kakoronbunshu1953.34.1308． |
| bok0009 | book | ok | author=西村, 和雄 / title=ミクロ経済学 / publisher=岩波書店 / year=1996 | 西村和雄 (1996) 『ミクロ経済学』，現代経済学入門，岩波書店． |
| bok0023 | book | ok | author=機械工学実験編集委員会 / title=大学・高専機械工学実験 / publisher=産業図書 / year=1982 | 機械工学実験編集委員会 (1982) 『大学・高専機械工学実験』，産業図書． |
| bok0054 | book | ok | author=歴史学研究会 / title=新自由主義時代の歴史学 / publisher=績文堂出版 / year=2017 | (2017) 『新自由主義時代の歴史学』，現代歴史学の成果と課題 / 歴史学研究会編, 第4次第1巻，績文堂出版． |
| bok0060 | book | ok | author=歴史学研究会 / title=歴史学のアクチュアリティ / publisher=東京大学出版会 / year=2013 | (2013) 『歴史学のアクチュアリティ』，東京大学出版会． |
| bok0068 | book | ok | author=山本, 行男 / title=クリック!有機化学 / publisher=化学同人 / year=2005 | 山本行男 (2005) 『クリック!有機化学』，化学同人． |
| bok0083 | book | ok | author=加藤, 明彦 / title=CKD患者の薬物治療 : 最初の一手と次の一手 / publisher=文光堂 / year=2018 | 加藤明彦 (2018a) 『CKD患者の薬物治療 : 最初の一手と次の一手』，文光堂． |
| bok0096 | book | ok | author=哲学会 / title=日本語の哲学 / publisher=有斐閣 / year=2008 | (2008) 『日本語の哲学』，哲学雑誌, 第123巻第795号，有斐閣． |
| bok0112 | book | ok | author=寺町優子 / title=新しい循環器疾患の看護 / publisher=南山堂 / year=1983 | 寺町優子 (1983) 『新しい循環器疾患の看護』，東京，南山堂． |
| bok0113 | book | ok | author=J.M.Neutze / title=ICU呼吸と循環の管理 / publisher=医学書院 / year=1984 | J.M.Neutze (1984) 『ICU呼吸と循環の管理』，島田康弘・田中一彦訳，第第2版版，東京，医学書院． |
| bok0127 | book | ok | author=川島紘一郎 / title=アセチルコリンの超高感度ラジオイムノアッセイ : 基礎から応用まで / publisher=南山堂 / year=1991 | 川島紘一郎 (1991) 『アセチルコリンの超高感度ラジオイムノアッセイ : 基礎から応用まで』，東京，南山堂． |
| bok0153 | book | ok | author=田崎晴明 and 久我隆弘 and 中村卓史 and 杉山直 and 小林誠 and 白田耕蔵 and 清水明 and 牧島一夫 and 夏梅誠 and 磯暁 / editor=日本物理学会 / title=アインシュタインと21世紀の物理学 / publisher=日本評論社 / year=2005 | 田崎晴明・久我隆弘・中村卓史他 (2005) 『アインシュタインと21世紀の物理学』，東京，日本評論社． |
| bok0245 | book | ok | author=井川, 洋二 / title=新しい生物学に挑戦する気鋭の研究者たち 続 / publisher=羊土社 / volume=続 / year=2000 | 井川洋二 (2000) 『新しい生物学に挑戦する気鋭の研究者たち 続』，第続巻，羊土社． |
| inp0150 | inproceedings | ok | author=早矢仕 晃章 and 大澤 幸生 / title=データ3.0時代のデータランドスケープ / booktitle=人工知能学会全国大会論文集 / volume=JSAI2018 / pages=1C2OS8a04 / year=2018 / doi=10.11517/pjsai.JSAI2018.0_1C2OS8a04 | 早矢仕晃章・大澤幸生 (2018) 「データ3.0時代のデータランドスケープ」，『人工知能学会全国大会論文集』，第JSAI2018巻，1C2OS8a04頁，DOI: 10.11517/pjsai.JSAI2018.0_1C2OS8a04． |

## jpa2022: ランダム 20 件 突き合わせ

| key | type | status | 原 BibTeX（圧縮） | ref_string |
|---|---|---|---|---|
| art0004 | article | ok | author=谷口 雄太 / title=書評　木下昌規『戦国期足利将軍家の権力構造』 / journal=史学雑誌 / volume=125-3 / pages=66-75 / year=2016 | 谷口雄太. (2016). 書評 木下昌規『戦国期足利将軍家の権力構造』. 史学雑誌, 125-3, 66–75. |
| art0005 | article | ok | author=小野 賢一 / title=回顧と展望ヨーロッパ中世（一般） / journal=史学雑誌 / volume=第124編5号 / pages=312-313 / year=2015 | 小野賢一. (2015). 回顧と展望ヨーロッパ中世（一般）. 史学雑誌, 第124編5号, 312–313. |
| art0047 | article | ok | author=仁平, 典宏 / title=原田峻著 『ロビイングの政治社会学―NPO 法制定・改正をめぐる政策過程と社会運動』 / journal=Japanese Sociological Review / publisher=The Japan Sociological Society / volume=73 / number=1 / pages=67-68 / year=2022 / doi=10.4057/jsr.73.67 / url=https://doi.org/10.4057/jsr.73.67 | 仁平典宏. (2022). 原田峻著 『ロビイングの政治社会学―NPO 法制定・改正をめぐる政策過程と社会運動』. Japanese Sociological Review, 73(1), 67–68. https://doi.org/10.4057/jsr.73.67 |
| art0166 | article | ok | author=野尻 美保子 / title=日独物理学会の“Declaration for Future”に思う / journal=日本物理学会誌 / volume=81 / number=2 / pages=51 / year=2026 / doi=10.11316/butsuri.81.2_51 | 野尻美保子. (2026). 日独物理学会の「Declaration for Future」に思う. 日本物理学会誌, 81(2), 51. https://doi.org/10.11316/butsuri.81.2_51 |
| art0191 | article | ok | author=草野 和也 and 古川 雅人 and 山田 和豊 / title=半開放形プロペラファンにおける翼端渦の三次元構造 / journal=日本機械学会論文集 / volume=80 / number=810 / pages=FE0024 / year=2014 / doi=10.1299/transjsme.2014fe0024 | 草野和也., 古川雅人., & 山田和豊. (2014). 半開放形プロペラファンにおける翼端渦の三次元構造. 日本機械学会論文集, 80(810), FE0024. https://doi.org/10.1299/transjsme.2014fe0024 |
| bok0023 | book | ok | author=機械工学実験編集委員会 / title=大学・高専機械工学実験 / publisher=産業図書 / year=1982 | 機械工学実験編集委員会. (1982). 大学・高専機械工学実験. 産業図書. |
| bok0108 | book | ok | editor=斎藤 稔男 and 加賀 精一 / title=アーク溶接実技テキスト 講義編 / publisher=オーム社 / volume=講義編 / year=1989 | 斎藤稔男., & 加賀精一. (編). (1989). アーク溶接実技テキスト 講義編: Vol. 講義編. オーム社. |
| bok0111 | book | ok | editor=日本小児科学会 and 臨床小児医学懇話会 / title=新しい小児の抗生物質療法 : 現状と今後のあり方 / publisher=南山堂 / year=1982 | 日本小児科学会, & 臨床小児医学懇話会 (編). (1982). 新しい小児の抗生物質療法 : 現状と今後のあり方. 南山堂. |
| bok0149 | book | ok | editor=鈴森薫 and 吉村泰典 and 堤治 / title=新しい産科学 : 生殖医療から周産期医療まで / publisher=名古屋大学出版会 / year=2002 | 鈴森薫., 吉村泰典., & 堤治. (編). (2002). 新しい産科学 : 生殖医療から周産期医療まで. 名古屋大学出版会. |
| bok0190 | book | ok | editor=日比紀文 and 横山薫 and 齊藤詠子 and 新井勝大 and 清水泰岳 and 前本篤男 and 髙津典孝 and 内野基 and 国崎玲子 / title=IBD診療ビジュアルテキスト : チーム医療につなげる! / publisher=羊土社 / year=2016 | 日比紀文., 横山薫., 齊藤詠子., 新井勝大., 清水泰岳., 前本篤男., 髙津典孝., 内野基., & 国崎玲子. (編). (2016). IBD診療ビジュアルテキスト : チーム医療につなげる! 羊土社. |
| bok0215 | book | ok | author=田中立二 and 大谷哲夫 / editor=天雨徹 / title=IEC 61850を適用した電力ネットワーク = The Electric Power Network Applying IEC 61850 : スマートグリッドを支える変電所自動化システム / publisher=コロナ社 / year=2020 | 田中立二., & 大谷哲夫. (2020). IEC 61850を適用した電力ネットワーク = The Electric Power Network Applying IEC 61850 : スマートグリッドを支える変電所自動化システム (天雨徹., 編). コロナ社. |
| inp0013 | inproceedings | ok | author=Nann Kavdavid and 的場隆一 / title=Extractive Text Summarization Implemented with SKG Formula / booktitle=言語処理学会第23回年次大会発表論文集 / year=2017 / url=https://www.anlp.jp/proceedings/annual_meeting/2017/pdf_dir/A1-1.pdf | Kavdavid, N., & 的場隆一. (2017). Extractive Text Summarization Implemented with SKG Formula. 言語処理学会第23回年次大会発表論文集. https://www.anlp.jp/proceedings/annual_meeting/2017/pdf_dir/A1-1.pdf |
| inp0057 | inproceedings | ok | author=五藤巧 and 渡辺太郎 / title=文法誤り訂正における参照なし評価尺度を用いた分析的評価法 / booktitle=言語処理学会第30回年次大会発表論文集 / year=2024 / url=https://www.anlp.jp/proceedings/annual_meeting/2024/pdf_dir/D8-5.pdf | 五藤巧., & 渡辺太郎. (2024). 文法誤り訂正における参照なし評価尺度を用いた分析的評価法. 言語処理学会第30回年次大会発表論文集. https://www.anlp.jp/proceedings/annual_meeting/2024/pdf_dir/D8-5.pdf |
| inp0104 | inproceedings | ok | author=鈴木 伸夫 and 紺野 信弘 and 堀口 兵剛 and 金成 由美子 and 杉浦 ミドリ and 福島 匡昭 / title=乳幼児の頭囲及び胸囲判定表示用パーソナルコンピュータシステムの開発の試み / booktitle=日本公衆衛生学会総会抄録集 / volume=54 / pages=252 / year=1995 | 鈴木伸夫., 紺野信弘., 堀口兵剛., 金成由美子., 杉浦ミドリ., & 福島匡昭. (1995). 乳幼児の頭囲及び胸囲判定表示用パーソナルコンピュータシステムの開発の試み. 日本公衆衛生学会総会抄録集, 54, 252. |
| inp0174 | inproceedings | ok | author=大塚 俊之 and 後藤 厳寛 and 杉田 幹夫 and 中島 崇文 and 池口 仁 / title=富士北麓剣丸尾溶岩流上のアカマツ林の起源 / booktitle=日本生態学会大会講演要旨集 / volume=ESJ50 / pages=110 / year=2003 / doi=10.14848/esj.ESJ50.0_110_3 | 大塚俊之., 後藤厳寛., 杉田幹夫., 中島崇文., & 池口仁. (2003). 富士北麓剣丸尾溶岩流上のアカマツ林の起源. 日本生態学会大会講演要旨集, ESJ50, 110. |
| inp0243 | inproceedings | ok | author=山田 卓 and 兵動 正幸 and 中田 幸男 and 吉本 憲正 and 村田 秀一 / title=土の動的変形特性に与える塑性指数の影響 / booktitle=地震工学研究発表会 梗概集 / volume=27 / pages=207 / year=2003 / doi=10.11532/proee2003.27.207 | 山田卓., 兵動正幸., 中田幸男., 吉本憲正., & 村田秀一. (2003). 土の動的変形特性に与える塑性指数の影響. 地震工学研究発表会 梗概集, 27, 207. |
| web0082 | misc | ok | author=総務省統計局 / title=日本の統計 / url=https://www.stat.go.jp/data/nihon/index1.html | 総務省統計局. (日付なし-m). 日本の統計. 読み込み 2026年7月17日, から https://www.stat.go.jp/data/nihon/index1.html |
| web0106 | misc | ok | author=総務省統計局 / title=統計でみる都道府県・市区町村のすがた / url=https://www.stat.go.jp/data/ssds/index.html | 総務省統計局. (日付なし-x). 統計でみる都道府県・市区町村のすがた. 読み込み 2026年7月17日, から https://www.stat.go.jp/data/ssds/index.html |
| web0171 | misc | ok | author=コトバンク / title=横溝正史 / url=https://kotobank.jp/word/%E6%A8%AA%E6%BA%9D%E6%AD%A3%E5%8F%B2-22098 | コトバンク. (日付なし-ak). 横溝正史. 読み込み 2026年7月17日, から https://kotobank.jp/word/%E6%A8%AA%E6%BA%9D%E6%AD%A3%E5%8F%B2-22098 |
| web0186 | misc | ok | author=コトバンク / title=アビシニア国際アフリカ友好協会 / url=https://kotobank.jp/word/%E3%81%82%E3%81%B3%E3%81%97%E3%81%AB%E3%81%82%E5%9B%BD%E9%9A%9B%E3%81%82%E3%81%B5%E3%82%8A%E3%81%8B%E5%8F%8B%E5%A5%BD%E5%8D%94%E4%BC%9A-26590 | コトバンク. (日付なし-q). アビシニア国際アフリカ友好協会. 読み込み 2026年7月17日, から https://kotobank.jp/word/%E3%81%82%E3%81%B3%E3%81%97%E3%81%AB%E3%81%82%E5%9B%BD%E9%9A%9B%E3%81%82%E3%81%B5%E3%82%8A%E3%81%8B%E5%8F%8B%E5%A5%BD%E5%8D%94%E4%BC%9A-26590 |

## jplain: ランダム 20 件 突き合わせ

| key | type | status | 原 BibTeX（圧縮） | ref_string |
|---|---|---|---|---|
| art0087 | article | ok | author=北村, 美渚 / title=The 13th IAGG Master Class on Ageing in Asiaでの学びと出会い / journal=Nippon Ronen Igakkai Zasshi. Japanese Journal of Geriatrics / publisher=The Japan Geriatrics Society / volume=62 / number=3 / pages=335-336 / year=2025 / doi=10.3143/geriatrics.62.335 / url=https://doi.org/10.3143/geriatrics.62.335 | 北村美渚. The 13th iagg master class on ageing in asiaでの学びと出会い. Nippon Ronen Igakkai Zasshi. Japanese Journal of Geriatrics, Vol. 62, No. 3, pp. 335–336, 2025. |
| art0119 | article | ok | author=安達 智史 / title=ポスト多文化主義における社会統合について 戦後イギリスにおける政策の変遷との関わりのなかで / journal=社会学評論 / volume=60 / number=3 / pages=433-448 / year=2009 / doi=10.4057/jsr.60.433 | 安達智史. ポスト多文化主義における社会統合について 戦後イギリスにおける政策の変遷との関わりのなかで. 社会学評論, Vol. 60, No. 3, pp. 433–448, 2009. |
| art0150 | article | ok | author=梅崎 高行 / title=サッカー指導における相互的なバイアス構成の検討 / journal=教育心理学研究 / volume=58 / number=3 / pages=298-312 / year=2010 / doi=10.5926/jjep.58.298 | 梅崎高行. サッカー指導における相互的なバイアス構成の検討. 教育心理学研究, Vol. 58, No. 3, pp. 298–312, 2010. |
| art0156 | article | ok | author=東海林 渉 and 安達 知郎 and 高橋 恵子 and 三船 奈緒子 / title=中学生用コミュニケーション基礎スキル尺度の作成 / journal=教育心理学研究 / volume=60 / number=2 / pages=137-152 / year=2012 / doi=10.5926/jjep.60.137 | 東海林渉, 安達知郎, 高橋恵子, 三船奈緒子. 中学生用コミュニケーション基礎スキル尺度の作成. 教育心理学研究, Vol. 60, No. 2, pp. 137–152, 2012. |
| art0218 | article | ok | author=宝沢 光紀 and 只木 槙力 and 前田 四郎 / title=単一孔から生成する液滴の大きさについて / journal=化学工学 / volume=33 / number=9 / pages=893-898,a1 / year=1969 / doi=10.1252/kakoronbunshu1953.33.893 | 宝沢光紀, 只木槙力, 前田四郎. 単一孔から生成する液滴の大きさについて. 化学工学, Vol. 33, No. 9, pp. 893–898,a1, 1969. |
| art0222 | article | ok | author=永田 進治 and 西川 正史 and 五嶋 慎治 and 中島 正豊 / title=寄書 / journal=化学工学 / volume=34 / number=10 / pages=1115-1121,a1 / year=1970 / doi=10.1252/kakoronbunshu1953.34.1115 | 永田進治, 西川正史, 五嶋慎治, 中島正豊. 寄書. 化学工学, Vol. 34, No. 10, pp. 1115–1121,a1, 1970. |
| art0258 | article | ok | author=赤羽 正章 / title=3．MRI診断 / journal=日本内科学会雑誌 / volume=103 / number=1 / pages=61-69 / year=2014 / doi=10.2169/naika.103.61 | 赤羽正章. 3．mri診断. 日本内科学会雑誌, Vol. 103, No. 1, pp. 61–69, 2014. |
| bok0007 | book | ok | author=情報科学技術協会 / title=情報管理入門 / publisher=情報科学技術協会 / year=1999 | 情報科学技術協会. 情報管理入門. 情報科学技術協会, 1999. |
| bok0083 | book | ok | author=加藤, 明彦 / title=CKD患者の薬物治療 : 最初の一手と次の一手 / publisher=文光堂 / year=2018 | 加藤明彦. CKD患者の薬物治療 : 最初の一手と次の一手. 文光堂, 2018. |
| bok0134 | book | ok | author=World Health Organization / title=ICD-10精神および行動の障害. DCR研究用診断基準 / publisher=医学書院 / volume=DCR研究用診断基準 / year=1994 | World Health Organization. ICD-10精神および行動の障害. DCR研究用診断基準, DCR研究用診断基準. 医学書院, 東京, 1994. |
| bok0146 | book | ok | author=感染症・食中毒集団発生対策研究会 / title=アウトブレイクの危機管理 : 感染症・食中毒集団発生事例に学ぶ / publisher=医学書院 / year=2000 | 感染症・食中毒集団発生対策研究会. アウトブレイクの危機管理 : 感染症・食中毒集団発生事例に学ぶ. 医学書院, 東京, 2000. |
| inp0031 | inproceedings | ok | author=宮内拓也 and 影浦峡 / title=翻訳におけるQA記述の分析: 言語学的カテゴリーを手掛かりに / booktitle=言語処理学会第26回年次大会発表論文集 / year=2020 / url=https://www.anlp.jp/proceedings/annual_meeting/2020/pdf_dir/G2-1.pdf | 宮内拓也, 影浦峡. 翻訳におけるqa記述の分析: 言語学的カテゴリーを手掛かりに. 言語処理学会第26回年次大会発表論文集. 言語処理学会, 2020. |
| inp0099 | inproceedings | ok | author=谷 静香 and 市村 久美子 and 三浦 康司 and 梁 洋子 and 許 鳴 / title=メンタルフィットネス・プログラムの実践(第二報) : 自己評価の向上を重視した体重管理プログラムの事例報告 / booktitle=日本公衆衛生学会総会抄録集 / volume=55 / number=2 / pages=225 / year=1996 | 谷静香, 市村久美子, 三浦康司, 梁洋子, 許鳴. メンタルフィットネス・プログラムの実践(第二報) : 自己評価の向上を重視した体重管理プログラムの事例報告. 日本公衆衛生学会総会抄録集, 第55巻, p. 225, 1996. |
| inp0170 | inproceedings | ok | author=山本 進一 / title=長期モニタリングサイトの現状と分子生態遺伝研究におけるメリット / booktitle=日本生態学会大会講演要旨集 / volume=ESJ50 / pages=100 / year=2003 / doi=10.14848/esj.ESJ50.0.100.1 | 山本進一. 長期モニタリングサイトの現状と分子生態遺伝研究におけるメリット. 日本生態学会大会講演要旨集, 第ESJ50巻, p. 100, 2003. |
| inp0188 | inproceedings | ok | author=内藤 由香子 and 大舘 智氏 / title=マイクロサテライトDNAを用いたオオアシトガリネズミとバイカルトガリネズミ個体群の遺伝構造解析 / booktitle=日本生態学会大会講演要旨集 / volume=ESJ50 / pages=137 / year=2003 / doi=10.14848/esj.ESJ50.0_137_2 | 内藤由香子, 大舘智氏. マイクロサテライトdnaを用いたオオアシトガリネズミとバイカルトガリネズミ個体群の遺伝構造解析. 日本生態学会大会講演要旨集, 第ESJ50巻, p. 137, 2003. |
| web0091 | misc | ok | author=総務省統計局 / title=全国単身世帯収支実態調査 / url=https://www.stat.go.jp/data/tanshin/2024/index.html | 総務省統計局. 全国単身世帯収支実態調査. https://www.stat.go.jp/data/tanshin/2024/index.html. 2026-07-17 参照. |
| web0097 | misc | ok | author=総務省統計局 / title=令和8年経済センサス‐活動調査 / year=2026 / url=https://www.stat.go.jp/data/e-census/2026/index-2.html | 総務省統計局. 令和8年経済センサス‐活動調査. https://www.stat.go.jp/data/e-census/2026/index-2.html, 2026. 2026-07-17 参照. |
| web0120 | misc | ok | author=個人情報保護委員会 / title=関係法令一覧 / url=https://www.ppc.go.jp/legal/laws/ | 個人情報保護委員会. 関係法令一覧. https://www.ppc.go.jp/legal/laws/. 2026-07-17 参照. |
| web0127 | misc | ok | author=個人情報保護委員会 / title=監視・監督方針、検査計画 / url=https://www.ppc.go.jp/legal/supervision/ | 個人情報保護委員会. 監視・監督方針、検査計画. https://www.ppc.go.jp/legal/supervision/. 2026-07-17 参照. |
| web0190 | misc | ok | author=コトバンク / title=アラフラ海真珠貝漁業事件 / url=https://kotobank.jp/word/%E3%81%82%E3%82%89%E3%81%B5%E3%82%89%E6%B5%B7%E7%9C%9F%E7%8F%A0%E8%B2%9D%E6%BC%81%E6%A5%AD%E4%BA%8B%E4%BB%B6-27850 | コトバンク. アラフラ海真珠貝漁業事件. https://kotobank.jp/word/%E3%81%82%E3%82%89%E3%81%B5%E3%82%89%E6%B5%B7%E7%9C%9F%E7%8F%A0%E8%B2%9D%E6%BC%81%E6%A5%AD%E4%BA%8B%E4%BB%B6-27850. 2026-07-17 参照. |

## jsai: ランダム 20 件 突き合わせ

| key | type | status | 原 BibTeX（圧縮） | ref_string |
|---|---|---|---|---|
| art0009 | article | ok | author=草野 篤子 / title=世代間交流に向けてのプレリュード-現状と今後の課題 / journal=老年社会科学 / volume=33巻 / pages=81-89 / year=2011 | 草野 篤子：世代間交流に向けてのプレリュード-現状と今後の課題, 老年社会科学, 33巻, pp. 81–89 (2011) |
| art0053 | article | ok | author=KIMURA, Yuko and TSURUTA, Maki and SUETSUGU, Yuka and SATO, Takanori / title=障害児教育に関する社会学的研究の動向 / journal=The Journal of Educational Sociology / publisher=The Japan Society for Educational Sociology / volume=113 / number=0 / pages=73-107 / year=2023 / doi=10.11151/eds.113.73 / url=https://doi.org/10.11151/eds.113.73 | KIMURA, Y., TSURUTA, M., SUETSUGU, Y., and SATO, T.: 障害児教育に関する社会学的研究の動向, The Journal of Educational Sociology, Vol. 113, No. 0, pp. 73–107 (2023) |
| art0116 | article | ok | author=高橋 章子 / title=相互行為論のデュルケム デュルケム，パーソンズ，ガーフィンケルの秩序形成の論理を比較して / journal=社会学評論 / volume=60 / number=2 / pages=209-224 / year=2009 / doi=10.4057/jsr.60.209 | 高橋 章子：相互行為論のデュルケム デュルケム，パーソンズ，ガーフィンケルの秩序形成の論理を比較して, 社会学評論, Vol. 60, No. 2, pp. 209–224 (2009) |
| art0120 | article | ok | author=浜 日出夫 / title=記憶と場所 近代的時間・空間の変容 / journal=社会学評論 / volume=60 / number=4 / pages=465-480 / year=2010 / doi=10.4057/jsr.60.465 | 浜 日出夫：記憶と場所 近代的時間・空間の変容, 社会学評論, Vol. 60, No. 4, pp. 465–480 (2010) |
| art0131 | article | ok | author=塚脇 涼太 and 越 良子 and 樋口 匡貴 and 深田 博己 / title=なぜ人はユーモアを感じさせる言動をとるのか？──ユーモア表出動機の検討── / journal=心理学研究 / volume=80 / number=5 / pages=397-404 / year=2009 / doi=10.4992/jjpsy.80.397 | 塚脇 涼太, 越 良子, 樋口 匡貴, 深田 博己：なぜ人はユーモアを感じさせる言動をとるのか？──ユーモア表出動機の検討──, 心理学研究, Vol. 80, No. 5, pp. 397–404 (2009) |
| art0168 | article | ok | author=佐藤 勝彦 / title=佐藤文隆先生を偲んで / journal=日本物理学会誌 / volume=81 / number=2 / pages=96 / year=2026 / doi=10.11316/butsuri.81.2_96 | 佐藤 勝彦：佐藤文隆先生を偲んで, 日本物理学会誌, Vol. 81, No. 2, p. 96 (2026) |
| art0202 | article | ok | author=下田 昌利 and 下出 健介 / title=閉空間の音圧低減を目的としたシェル構造のノンパラメトリック形状最適化 / journal=日本機械学会論文集 / volume=80 / number=813 / pages=DSM0137 / year=2014 / doi=10.1299/transjsme.2014dsm0137 | 下田 昌利, 下出 健介：閉空間の音圧低減を目的としたシェル構造のノンパラメトリック形状最適化, 日本機械学会論文集, Vol. 80, No. 813, p. DSM0137 (2014) |
| art0205 | article | ok | author=新井 健太郎 and 高村 英雅 and 小野 雅裕 and 足立 修一 / title=オンボードカメラによる火星飛行機の位置推定アルゴリズム / journal=日本機械学会論文集 / volume=80 / number=814 / pages=DR0171 / year=2014 / doi=10.1299/transjsme.2014dr0171 | 新井 健太郎, 高村 英雅, 小野 雅裕, 足立 修一：オンボードカメラによる火星飛行機の位置推定アルゴリズム, 日本機械学会論文集, Vol. 80, No. 814, p. DR0171 (2014) |
| bok0008 | book | ok | author=足立, 暁生 / title=情報科学の基礎 / publisher=東京電機大学出版局 / year=1990 | 足立 暁生：情報科学の基礎, 情報科学, 東京電機大学出版局 (1990) |
| bok0157 | book | ok | author=桜井邦朋 / title=アカデミック・ライティング : 日本文・英文による論文をいかに書くか / publisher=朝倉書店 / year=2007 | 桜井 邦朋：アカデミック・ライティング : 日本文・英文による論文をいかに書くか, 朝倉書店, 東京 (2007) |
| bok0161 | book | ok | author=石井由香 and 関根政美 and 塩原良和 / title=アジア系専門職移民の現在 : 変容するマルチカルチュラル・オーストラリア / publisher=慶應義塾大学出版会 / year=2009 | 石井 由香, 関根 政美, 塩原 良和：アジア系専門職移民の現在 : 変容するマルチカルチュラル・オーストラリア, 慶應義塾大学出版会, 東京 (2009) |
| inp0001 | inproceedings | ok | author=井上絢翔 and 韓東力 / title=論文間参照情報のアノテーションにおけるクラウドソーシングの利用検討 / booktitle=言語処理学会第21回年次大会発表論文集 / pages=736-739 / year=2015 / url=https://www.anlp.jp/proceedings/annual_meeting/2015/pdf_dir/B5-1.pdf | 井上 絢翔, 韓 東力：論文間参照情報のアノテーションにおけるクラウドソーシングの利用検討, 言語処理学会第21回年次大会発表論文集, pp. 736–739言語処理学会 (2015) |
| inp0016 | inproceedings | ok | author=福原優太 and 阪本浩太郎 and 渋木英潔 and 森辰則 / title=世界史論述問題における模範解答-知識源の対応を表すアノテーションの検討 / booktitle=言語処理学会第23回年次大会発表論文集 / year=2017 / url=https://www.anlp.jp/proceedings/annual_meeting/2017/pdf_dir/P10-7.pdf | 福原 優太, 阪本 浩太郎, 渋木 英潔, 森 辰則：世界史論述問題における模範解答-知識源の対応を表すアノテーションの検討, 言語処理学会第23回年次大会発表論文集言語処理学会 (2017) |
| inp0108 | inproceedings | ok | author=岡本 和士 and 白井 みどり and 田中 陽子 and 中山 和弘 and 柳堀 朗子 and 白石 知子 / title=介護者の健康状態とそれに関連する要因の検討 / booktitle=日本公衆衛生学会総会抄録集 / volume=55 / number=3 / pages=455 / year=1996 | 岡本 和士, 白井 みどり, 田中 陽子, 中山 和弘, 柳堀 朗子, 白石 知子：介護者の健康状態とそれに関連する要因の検討, 日本公衆衛生学会総会抄録集, 第55巻, p. 455 (1996) |
| inp0135 | inproceedings | ok | author=高橋 達二 and 大用 庫智 and 玉造 晃弘 and 横川 純貴 / title=稀少性仮定の下での非独立性の判断としての人間の観察的因果推論 / booktitle=人工知能学会全国大会論文集 / volume=JSAI2017 / pages=4M11in1 / year=2017 / doi=10.11517/pjsai.JSAI2017.0_4M11in1 | 高橋 達二, 大用 庫智, 玉造 晃弘, 横川 純貴：稀少性仮定の下での非独立性の判断としての人間の観察的因果推論, 人工知能学会全国大会論文集, 第JSAI2017巻, p. 4M11in1 (2017) |
| inp0208 | inproceedings | ok | author=東海林 弘靖 / title=新光源を用いた新照明手法による照明デザイン / booktitle=照明学会　全国大会講演論文集 / volume=35 / pages=185 / year=2002 / doi=10.11515/ieijac.35.0.185.0 | 東海林 弘靖：新光源を用いた新照明手法による照明デザイン, 照明学会 全国大会講演論文集, 第35巻, p. 185 (2002) |
| web0078 | misc | ok | author=総務省統計局 / title=労働力調査 / url=https://www.stat.go.jp/data/roudou/index.html | 総務省統計局：労働力調査, https://www.stat.go.jp/data/roudou/index.html：2026-07-17 参照 |
| web0105 | misc | ok | author=総務省統計局 / title=通信・放送業等投入調査 / url=https://www.stat.go.jp/data/tuushin/index.html | 総務省統計局：通信・放送業等投入調査, https://www.stat.go.jp/data/tuushin/index.html：2026-07-17 参照 |
| web0134 | misc | ok | author=人工知能学会 / title=倫理委員会の開催 / url=https://www.ai-gakkai.or.jp/ai-elsi/report/committee | 人工知能学会：倫理委員会の開催, https://www.ai-gakkai.or.jp/ai-elsi/report/committee：2026-07-17 参照 |
| web0153 | misc | ok | author=コトバンク / title=風早公紀 / url=https://kotobank.jp/word/%E9%A2%A8%E6%97%A9%E5%85%AC%E7%B4%80-16005 | コトバンク：風早公紀, https://kotobank.jp/word/%E9%A2%A8%E6%97%A9%E5%85%AC%E7%B4%80-16005：2026-07-17 参照 |

## sist02: ランダム 20 件 突き合わせ

| key | type | status | 原 BibTeX（圧縮） | ref_string |
|---|---|---|---|---|
| art0132 | article | ok | author=藤 桂 and 吉田 富二雄 / title=オンラインゲーム上の対人関係が現実生活の社会性および攻撃性に及ぼす影響 / journal=心理学研究 / volume=80 / number=6 / pages=494-503 / year=2010 / doi=10.4992/jjpsy.80.494 | 藤桂., 吉田富二雄. オンラインゲーム上の対人関係が現実生活の社会性および攻撃性に及ぼす影響. 心理学研究. 2010, vol. 80, no. 6, p. 494–503. |
| art0206 | article | ok | author=濱田 直巳 and 丸山 雅弘 and 梅田 洋 / title=二軸応力下のMod.9Cr1Mo鋼のクリ－プ強度 / journal=日本機械学会論文集 / volume=80 / number=814 / pages=SMM0146 / year=2014 / doi=10.1299/transjsme.2014smm0146 | 濱田直巳, 丸山雅弘, 梅田洋. 二軸応力下のMod.9Cr1Mo鋼のクリ－プ強度. 日本機械学会論文集. 2014, vol. 80, no. 814, p. SMM0146. |
| art0250 | article | ok | author=葛西 圭子 and 貝瀬 友子 and 坂本 すが and 石原 照夫 / title=看護情報システムの有効性と効果的な構築方法の検討　―看護情報システム構築事例から― / journal=医療情報学 / volume=23 / number=1 / pages=45-53 / year=2003 / doi=10.14948/jami.23.45 | 葛西圭子, 貝瀬友子, 坂本すが, 石原照夫. 看護情報システムの有効性と効果的な構築方法の検討 ―看護情報システム構築事例から―. 医療情報学. 2003, vol. 23, no. 1, p. 45–53. |
| art0258 | article | ok | author=赤羽 正章 / title=3．MRI診断 / journal=日本内科学会雑誌 / volume=103 / number=1 / pages=61-69 / year=2014 / doi=10.2169/naika.103.61 | 赤羽正章. 3．MRI診断. 日本内科学会雑誌. 2014, vol. 103, no. 1, p. 61–69. |
| bok0049 | book | ok | author=情報科学技術協会 / title=サーチャー入門 / publisher=情報科学技術協会 / year=1989 | 情報科学技術協会. サーチャー入門. 情報科学技術協会, 1989, ISBN4889510214. |
| bok0213 | book | ok | author=若林宏保 and 大西浩志 and 和佐野有紀 and 上原拓真 and 東成樹 / editor=電通美術回路 / title=アート・イン・ビジネス = Art in Business : ビジネスに効くアートの力 / publisher=有斐閣 / year=2019 | 若林宏保, 大西浩志, 和佐野有紀, 上原拓真, 東成樹. アート・イン・ビジネス = Art in Business : ビジネスに効くアートの力. 東京, 有斐閣, 2019, ISBN978-4-641-16558-8. |
| bok0220 | book | ok | author=山下武志 / title=ARNIとSGLT2阻害薬についてシンプルにまとめてみました = Essentials of ARNI and SGLT2 inhibitor for heart failure treatment : 新時代の心不全治療に向けて / publisher=南江堂 / year=2021 | 山下武志. ARNIとSGLT2阻害薬についてシンプルにまとめてみました = Essentials of ARNI and SGLT2 inhibitor for heart failure treatment : 新時代の心不全治療に向けて. 東京, 南江堂, 2021, ISBN978-4-524-23229-1. |
| bok0242 | book | ok | author=Abel, Niels Henrik and Galois, Évariste and 高瀬, 正仁 / title=アーベル/ガロア楕円関数論 / publisher=朝倉書店 / year=1998 | Abel, Niels Henrik, Galois, Évariste, 高瀬正仁. アーベル/ガロア楕円関数論. 朝倉書店, 1998, ISBN4254114591. |
| inp0008 | inproceedings | ok | author=平田亜衣 and 小町守 / title=Factorization Machines を用いた未知の固有表現分類 / booktitle=言語処理学会第22回年次大会発表論文集 / year=2016 / url=https://www.anlp.jp/proceedings/annual_meeting/2016/pdf_dir/A5-4.pdf | 平田亜衣, 小町守. “Factorization Machines を用いた未知の固有表現分類”. 言語処理学会第22回年次大会発表論文集. 言語処理学会, 2016. https://www.anlp.jp/proceedings/annual_meeting/2016/pdf_dir/A5-4.pdf. |
| inp0011 | inproceedings | ok | author=山本和英 and 髙橋寛治 and 桾澤優希 / title=日本語支援動詞構文の述部に対するサ変動詞への換言 / booktitle=言語処理学会第22回年次大会発表論文集 / year=2016 / url=https://www.anlp.jp/proceedings/annual_meeting/2016/pdf_dir/P17-2.pdf | 山本和英, 髙橋寛治, 桾澤優希. “日本語支援動詞構文の述部に対するサ変動詞への換言”. 言語処理学会第22回年次大会発表論文集. 言語処理学会, 2016. https://www.anlp.jp/proceedings/annual_meeting/2016/pdf_dir/P17-2.pdf. |
| inp0022 | inproceedings | ok | author=上垣外英剛 and 林克彦 and 平尾努 and 永田昌明 / title=依存構造の連鎖を考慮したニューラル文圧縮 / booktitle=言語処理学会第24回年次大会発表論文集 / year=2018 / url=https://www.anlp.jp/proceedings/annual_meeting/2018/pdf_dir/P11-3.pdf | 上垣外英剛, 林克彦, 平尾努., 永田昌明. “依存構造の連鎖を考慮したニューラル文圧縮”. 言語処理学会第24回年次大会発表論文集. 言語処理学会, 2018. https://www.anlp.jp/proceedings/annual_meeting/2018/pdf_dir/P11-3.pdf. |
| inp0035 | inproceedings | ok | author=菊地晏南 and 高崎環 and 中本圭 / title=楽曲の歌詞をもとにした曲名生成 / booktitle=言語処理学会第26回年次大会発表論文集 / year=2020 / url=https://www.anlp.jp/proceedings/annual_meeting/2020/pdf_dir/P3-36.pdf | 菊地晏南, 高崎環., 中本圭. “楽曲の歌詞をもとにした曲名生成”. 言語処理学会第26回年次大会発表論文集. 言語処理学会, 2020. https://www.anlp.jp/proceedings/annual_meeting/2020/pdf_dir/P3-36.pdf. |
| inp0046 | inproceedings | ok | author=大谷直輝 / title=better off構文の定着過程に関する認知言語学的考察 / booktitle=言語処理学会第28回年次大会発表論文集 / year=2022 / url=https://www.anlp.jp/proceedings/annual_meeting/2022/pdf_dir/D2-1.pdf | 大谷直輝. “better off構文の定着過程に関する認知言語学的考察”. 言語処理学会第28回年次大会発表論文集. 言語処理学会, 2022. https://www.anlp.jp/proceedings/annual_meeting/2022/pdf_dir/D2-1.pdf. |
| inp0135 | inproceedings | ok | author=高橋 達二 and 大用 庫智 and 玉造 晃弘 and 横川 純貴 / title=稀少性仮定の下での非独立性の判断としての人間の観察的因果推論 / booktitle=人工知能学会全国大会論文集 / volume=JSAI2017 / pages=4M11in1 / year=2017 / doi=10.11517/pjsai.JSAI2017.0_4M11in1 | 高橋達二, 大用庫智, 玉造晃弘, 横川純貴. “稀少性仮定の下での非独立性の判断としての人間の観察的因果推論”. 人工知能学会全国大会論文集. 2017, p. 4M11in1. |
| inp0241 | inproceedings | ok | author=張 至鎬 and 濱田 政則 and 樋口 俊一 / title=杭基礎に作用する側方流動の外力特性に関する研究 / booktitle=地震工学研究発表会 梗概集 / volume=27 / pages=181 / year=2003 / doi=10.11532/proee2003.27.181 | 張至鎬, 濱田政則, 樋口俊一. “杭基礎に作用する側方流動の外力特性に関する研究”. 地震工学研究発表会 梗概集. 2003, p. 181. |
| inp0242 | inproceedings | ok | author=塩崎 禎郎 and 菅野 高弘 and 小濱 英司 and 白石 悟 and 中瀬 仁 and 三木 隆之 and 亀井 幸雄 and 有岡 謙一 and 岩田 肇 and 兵頭 武志 and 熊本 直樹 and 畑 英也 / title=大水深領域に建設されるL型ブロック式係船岸の地震時安定性について / booktitle=地震工学研究発表会 梗概集 / volume=27 / pages=195 / year=2003 / doi=10.11532/proee2003.27.195 | 塩崎禎郎, 菅野高弘, 小濱英司, 白石悟., 中瀬仁., 三木隆之, 亀井幸雄, 有岡謙一, 岩田肇., 兵頭武志, 熊本直樹, 畑英也. “大水深領域に建設されるL型ブロック式係船岸の地震時安定性について”. 地震工学研究発表会 梗概集. 2003, p. 195. |
| inp0244 | inproceedings | ok | author=加納 誠二 and 佐々木 康 and 秦 吉弥 and 榎野 光 / title=堤防湾曲部の地震時応答に関する実験的検討 / booktitle=地震工学研究発表会 梗概集 / volume=27 / pages=220 / year=2003 / doi=10.11532/proee2003.27.220 | 加納誠二, 佐々木康., 秦吉弥, 榎野光. “堤防湾曲部の地震時応答に関する実験的検討”. 地震工学研究発表会 梗概集. 2003, p. 220. |
| web0048 | misc | ok | author=厚生労働省 / title=令和６年版厚生労働白書－こころの健康と向き合い、健やかに暮らすことのできる社会に－（本文） / year=2024 / url=https://www.mhlw.go.jp/stf/wp/hakusyo/kousei/23/index.html | 厚生労働省. 令和６年版厚生労働白書－こころの健康と向き合い、健やかに暮らすことのできる社会に－（本文）. 2024. https://www.mhlw.go.jp/stf/wp/hakusyo/kousei/23/index.html, (参照 2026-07-17). |
| web0157 | misc | ok | author=コトバンク / title=三島中洲 / url=https://kotobank.jp/word/%E4%B8%89%E5%B3%B6%E4%B8%AD%E6%B4%B2-16819 | コトバンク. 三島中洲. https://kotobank.jp/word/%E4%B8%89%E5%B3%B6%E4%B8%AD%E6%B4%B2-16819, (参照 2026-07-17). |
| web0165 | misc | ok | author=コトバンク / title=住友吉左衛門 / url=https://kotobank.jp/word/%E4%BD%8F%E5%8F%8B%E5%90%89%E5%B7%A6%E8%A1%9B%E9%96%80-18599 | コトバンク. 住友吉左衛門. https://kotobank.jp/word/%E4%BD%8F%E5%8F%8B%E5%90%89%E5%B7%A6%E8%A1%9B%E9%96%80-18599, (参照 2026-07-17). |
