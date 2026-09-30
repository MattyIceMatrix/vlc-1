# JCCDB v3.1 Release Declaration

**Issued:** 2026-07-27 (JST) by Toshikatsu Oga (大賀俊勝), The HORIZONs Inc., ORCID 0009-0000-9180-903X.
**Dataset:** Japan Construction Cost Database (JCCDB), version 3.1.
**Repository:** https://github.com/ogasurfproject-jpg/japan-construction-cost-database
**Commit:** `1c9b9de` on branch `main`.

This document declares the exact bytes of JCCDB v3.1. Its SHA-256 is appended to the JIDEC
public ledger and timestamped into the Bitcoin blockchain through OpenTimestamps. A third
party can therefore establish, without asking the author for anything and without being able
to be deceived by the author, that the files listed below had these contents at or before the
anchored time.

---

## 1. What changed in v3.1

v3.0 separated verified items from unverified ones and removed 608 items proven not to exist.
v3.1 continues in the same direction: it removes duplication and adds real items, and it
records both operations in full so that either can be checked.

**Duplicates removed: 589 rows.** Every removed row was identical to an earlier row in all
three published fields — `category`, `item_name` and `unit`. Each removal is listed in
`jccdb-v3-duplicates-removed.csv` together with the row number of the surviving entry it
duplicated, so a reader can confirm that nothing was lost.

**Rows deliberately kept: 105.** These share an `item_name` with another row but differ in
`category` or `unit`. A worked example: `バックホウ（0.45m3 1日）` appears under both
`RC・コンクリート工事` and `仮設・足場資材`. A catalogue organised by trade is meant to list
shared plant under each trade that uses it. Collapsing these on name alone would have removed
functioning data, and it was not done.

**Items added: 543.** Real items not previously present in the dataset, drawn from the
project's own cost files: insurance and permit fees, labour day-rates, steel sections, rebar
by diameter, electrical conduit and boxes, ground improvement, and surcharge coefficients.
Each is listed in `jccdb-v3-added-20260727.csv` with the source file it came from.

**Additions rejected: 28.** During verification, 28 of the harvested candidates were found to
match entries that v3.0 had already proven not to exist, with evidence URLs. They were
rejected rather than added. They are: domestic 28-go gas water heaters from Noritz, Rinnai,
Paloma and Panasonic (the domestic range is 16, 20 and 24 only); Corona "Eco Jozu" models (Eco
Jozu is a gas condensing technology and Corona does not make gas water heaters); the Corona
UIB-NX46RY 46-go (the real forms are UIB-NX46R(MS) and (FF)); and the Noritz GT-C6052SAWX
60-go (a fabricated extrapolation). The source file predated the v3.0 retraction. Each
rejection is listed in `jccdb-v3-rejected-readd-20260727.csv` with the original retraction
reason. **This is stated plainly because a dataset that removes false items and then quietly
adds them back is worse than one that never removed them.**

**Arithmetic:** 65,566 − 589 + 543 = **65,520**.

---

## 2. Composition, as measured

| Property | Value |
|---|---|
| Total rows | 65,520 |
| Unique rows (category + item_name + unit) | 65,520 — zero duplicates |
| Verified tier | 13,207 |
| Extended tier | 52,313 |
| Verified + Extended | 65,520 — exactly equal to the total |
| Categories, coarse (`category` column of the CSVs) | 72 |
| Categories, fine (`jccdb-v3-schema.json`) | 402 |
| Retracted (held separately, not in the totals) | 608 |
| Licence | CC BY 4.0, single licence across all tiers since v2.1 |

The dataset records item names, categories and units. **It contains no prices.** Price data
lives in a separate layer (`souba-db`) and is not part of this declaration.

**On category granularity.** JCCDB carries two, and both are real. The `category` column of the
CSV files is coarse: 63 categories in v2 and v3.0, **72** in v3.1. The schema file is
fine-grained: `jccdb-v2-schema.json` had **398** categories over the 65,729 items of v2, and
`jccdb-v3-schema.json` has **402** over the 65,520 items of v3.1. In each file the declared
`_meta.total_categories` and `_meta.total_items` match the file's own contents exactly, and the
v3.1 schema contains one entry per CSV row, so the two files describe the same 65,520 items.
A statement citing "398 categories" refers to the schema granularity of v2 and is correct for
v2; the corresponding v3.1 figure is 402. **The coarse and fine numbers describe the same data
at different resolutions; neither supersedes the other.**

---

## 3. File digests

SHA-256 of each published file at commit `1c9b9de`:

```
807009770bd19181902dc4be22356526fdfa4593b100dd9b364982d7ab848503  jccdb-v3-full.csv
ea57f6205156c64982f56d681215477a5baa8a85242650b2e9ed8e5680f86b0a  jccdb-v3-verified.csv
6568eea6d3392b059b24ea62ae6fc93bad9ec762c3526a376bc4b09b55836eb6  jccdb-v3-extended.csv
5d3451c303720e41c379ac4c166da28bb8269c62b2e86ebbebbdbad34118c199  jccdb-v3-retracted.csv
1ccc53764f075b10995be8a5ffea1b1bcade6f39fae8b52e643404f0ff134640  jccdb-v3-schema.json
32c8039f9681da186d26b97606d752bcfd4f80fdd19e4115943d511c09d3b91a  jccdb-v3-provenance.csv
f106da6cc8dd2e13d2d9377b0ab1850c249d679091eb991ffaa71dea1802d751  jccdb-v3-duplicates-removed.csv
e65dae3b23402bc1c666bdd523f1940fc3bd1b48cd07920623a2cab5adc28d5a  jccdb-v3-added-20260727.csv
a3f8d7a2edc7909eee43908633ac273f77e4cc534a36fc07f63bd8dc1069ee37  jccdb-v3-rejected-readd-20260727.csv
```

## 4. How to verify this without trusting the author

Clone the repository at the declared commit and hash the files:

```
git clone https://github.com/ogasurfproject-jpg/japan-construction-cost-database.git
cd japan-construction-cost-database && git checkout 1c9b9de
shasum -a 256 jccdb-v3-full.csv
```

That must print `807009770bd19181902dc4be22356526fdfa4593b100dd9b364982d7ab848503`.

Recount the composition yourself:

```
python3 -c "import csv;L=lambda p:list(csv.DictReader(open(p,encoding='utf-8-sig')));f=L('jccdb-v3-full.csv');v=L('jccdb-v3-verified.csv');e=L('jccdb-v3-extended.csv');print(len(f),len(v),len(e),len(v)+len(e)==len(f),len(set(r['category'] for r in f)))"
```

That must print `65520 13207 52313 True 72`.

Then fetch this declaration's anchored bytes from the JIDEC ledger, hash them, and check the
OpenTimestamps proof. If the digest matches and the proof verifies, these contents existed at
or before the anchored time and have not been altered since.

---

## 5. What this declaration does not claim

It does not claim that every item in the Extended tier has been confirmed to exist. That is
the entire point of separating Extended from Verified: 52,313 rows are **not** verified, and
the dataset says so rather than implying otherwise.

It does not claim that 65,520 is a complete enumeration of construction items in Japan. It is
what this project has collected and can account for.

**It does not claim that the published, DOI-bearing release has been updated.** As of the date
of this declaration, the Zenodo record and the DOIs cited in the author's papers still point
to **v2.1 (65,729 items)**. v3.0 and v3.1 exist in the repository and are anchored here, but a
reader resolving the DOI will receive v2.1. That difference is stated rather than left for the
reader to discover. It is resolved by publishing a new Zenodo version, which has not been done
at the time of writing.

It does not claim that the author's other published surfaces have been synchronised. At the
time of writing they cite different versions, and each is correct for the version it cites.

---

## 日本語要約

**JCCDB v3.1 を宣言する。65,520品目・重複ゼロ・カテゴリ72（CSVの粒度）。**
会計は 65,566 − 589（重複除去） + 543（実在品目の追加） = 65,520。
verified 13,207 ＋ extended 52,313 が総数と厳密に一致する。**価格は含まない。**

**重複除去589行**は、カテゴリ・品名・単位が**すべて一致**する行のみ。残した行番号とともに
`jccdb-v3-duplicates-removed.csv` に全件記録した。**品名だけ一致する105行は残した。**
`バックホウ` が「RC・コンクリート工事」と「仮設・足場資材」の両方にある類で、工種別カタログ
として同じ重機が各工種に出るのは設計として正しい。名前だけで潰せば機能が壊れる。

**追加543件**は保険・申請費、労務単価、鉄骨形鋼、鉄筋、電線管、地盤改良、割増率など。
出典ファイルを品目ごとに記録した。

**そして28件を差し戻した。**取り込み候補のうち28件が、v3.0 で証拠URL付きで**非実在と証明済み**
の品目と一致した（家庭用28号給湯器＝実在は16/20/24号のみ、コロナのエコジョーズ＝ガス技術で
コロナ非該当、GT-C6052SAWX 60号＝架空の外挿）。素材ファイルが v3.0 の除去より古かった。
**偽物を消したデータセットに偽物を黙って戻すのは、最初から消さないより悪い。**だから
差し戻し理由とともに全件記録し、ここに明記する。

**カテゴリの粒度は2系統ある。**CSV の `category` 列は粗く、v2/v3.0 で63、**v3.1 で72**。
schema ファイルは細かく、`jccdb-v2-schema.json` が v2 の65,729品目に対して**398**、
`jccdb-v3-schema.json` が v3.1 の65,520品目に対して**402**。いずれも宣言値と実データが一致し、
v3.1 の schema は CSV の1行につき1件を持つ。**「398カテゴリ」は v2 の schema 粒度として正しく、
v3.1 の対応値は402である。**粗い数と細かい数は同じデータの異なる解像度であって、
どちらかが他方を上書きするものではない。

**本宣言が主張しないこと。**Extended 52,313件は実在確認済みではない（だから分離してある）。
そして**DOI 付きの公開版はいまも v2.1（65,729品目）である。**DOI を辿った読者には v2.1 が届く。
この差は隠さず書く。解消には Zenodo 新版の公開が要り、本宣言の時点では行われていない。
