# JCCDB v4.0 リリース宣言 / Release Declaration  2026-08-27

## 宣言
**JCCDB v4.0。95403品目・重複ゼロ。** v3.1(65,520)に全国56自治体の公表単価表(政府PDF131本)から実在確認した **29,883品目** を追加。全件 evidence_url 付きで jccdb-v4-provenance.csv に記録、verified 層。

- 65,520 + 29,883 = **95,403** / Verified 13,207 -> **43,090** / Extended 52,313 / Verified+Extended = 95,403
- 粗粒度カテゴリ 72 -> **97**（新規は26の正規カテゴリに整理、その他は約6パーセント）

## 各ファイルのSHA-256
形式: <SHA-256> <半角スペース2つ> <ファイル名>

1e6eeacbe130c5180e21588d58379a8f22d7f48b001a1d1bd40f3892ecc3ebc4  jccdb-v4-full.csv
97151421fb97decccb94d7db24fd19747702dd04041cb2d3ebcb060eb9c4cf2e  jccdb-v4-verified.csv
a5ea086be7eb84aee0a76d8ac69188a5ed5bc0874a27e0ac68fdad2712f75aa4  jccdb-v4-extended.csv
bd0a4d23fb8fb2441c2292ac52dd56e8d5ccb66b732dd0be75efc7d8ef5ff128  jccdb-v4-provenance.csv
4a419b4d3fed362067ac2a1313b11ba9764130a69e17bf58fba91ca952604098  jccdb-v4-schema.json
ccac323cd45fe4502c3b92429939204c502358dcc89e5243495547c1dd23f951  jccdb-v4-catalog-additions.csv
8e087446fcab632c79bd651df73c2a4bbc6b9d5793848293748e7a418312c894  README.md
6eab9aa58e03b287eb9440bc231322a92568c7b32f83547f4ee9b248160b1668  README.ja.md
b87f71d7bd3f4945e7407cd74f7185382cbc0806c4c405380f59fa21f4f5c993  CITATION.cff

## 検証
shasum -a 256 <ファイル名> の出力が上記と一致すること。jccdb-v4-provenance.csv の evidence_url を開けば、当該自治体の公表単価表PDFに品目の実在を確認できる。

## 正直な注記 ※必読
1. 価格は本カタログに含めない（品目名・カテゴリ・単位のみ、v3.1と同設計）。収録した価格は全て政府「公表」単価（物価資料=有料著作物は除外済み）。
2. カテゴリ正規化済み（原カテゴリ574->26正規）。
3. DOI 10.5281/zenodo.21898745 は現状 v3.1 を指す。v4 は本 deposit で登録。Bitcoin再アンカーは別途。
4. 前橋市126品目は市が複製禁止。外部公開版は除外か許諾。

原則: 政府一次優先・多重照合・確認できないものは未確定・**1件も捏造/推測しない**。
