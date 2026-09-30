# JIDEC 台帳 v1 スキーマ — ハッシュ独立性・データ版固定

**Anchor target:** このドキュメント自身のSHA-256をJIDEC台帳の次エントリ #2 として刻印し、Bitcoinに固定する。刻印後、変更不可。

**Feedback source:** Pang-jo Chun (全 邦釘), Ph.D., The University of Tokyo, Institute of Engineering Innovation. 2026-07-25 メール指摘。

---

## 1. 認めた欠陥

現在の HORIZON SHIELD のハッシュ実装（`hs-pdf-gen`）には、以下の欠陥がある。全先生の指摘は正確である。

### 欠陥A: ハッシュの独立性が成立していない

`generatePDF()` (line 19543) では
```
_hsrc = [params.koji_type, params.teiji_kingaku, params.region, orderId, d2.adj{Min,Avg,Max}].join("|")
```
を SHA-256 化して `d2.auditHash` としている。

これは「二つの実装が独立に同じ結果を計算した」ことを示すものではなく、`params.*` (上流入力) と `d2.adj*` (下流計算結果) を単に連結しているだけである。上流に不正な値が入ってもハッシュはそのまま「正式な監査ハッシュ」として印字される。

`hsHandleEstimateAudit()` (line 18661) も同様に `JSON.stringify(ex)` のみをハッシュ化しており、監査結果・ベンチマーク版・参照データを含まない。

### 欠陥B: ハッシュに含まれていない要素

現在のハッシュは以下を含まない：
- 価格DB（souba-db）そのもののSHA-256
- 明細ベンチマーク（HS_MEISAI_BENCH）そのものの内容SHA
- WPCのバージョン・入力データ
- Workerコードのコミットハッシュ
- しきい値設定（最小・最大・危険）
- 生成されたPDF全文のSHA

したがって、参照データや算出ロジックを事後に変更しても、ハッシュ値だけでは検出できない。

### 欠陥C: バージョン識別子の不十分性

`HS_MEISAI_BENCH.schema_version = "meisai-layer v0.3"` および `souba-db` の `_meta.version = "YYYY-MM"` は**セマンティック**な識別子であって、**内容ハッシュ**ではない。同じ月内に R2 上のJSONを更新すれば、同じ利用者入力でも算出結果が変わりうるが、`schema_version` は変わらない。

論文の「R2のstrong consistencyにより同じデータセットが読まれる」という記述は誤り。strong consistency が保証するのは**更新後の読み取り整合性**であって、**データの不変性**ではない。

---

## 2. 修正: 正規クレームレコード v1

これ以降、JIDEC 台帳に append される `record_canonical` は以下の JSON 形式を必須とする。UTF-8、キーは辞書順、余分な空白なし。

```json
{
  "schema": "jidec-claim-v1",
  "issued_at": "2026-07-25T09:52:00Z",
  "work_id": "外壁塗装 30坪 一式（シリコン）",
  "input_sha256":              "<64hex — 利用者入力見積JSONのSHA-256>",
  "reference_bundle_sha256":   "<64hex — 参照データ束の内容SHA-256>",
  "reference_bundle_version":  "souba-db@2026-07,meisai-bench@v0.3",
  "algorithm_commit":          "<40hex — hs-pdf-gen リポジトリのgit SHA>",
  "algorithm_url":             "https://github.com/ogasurfproject-jpg/horizon-shield/tree/<commit>/workers/hs-pdf-gen",
  "thresholds_sha256":         "<64hex — しきい値設定のSHA-256>",
  "result_sha256":             "<64hex — 監査結果JSONのSHA-256>",
  "pdf_sha256":                "<64hex — 発行PDFファイルのSHA-256>",
  "verifier_recipe_url":       "https://hs-ledger.oga-surf-project.workers.dev/verify/{n}"
}
```

**このレコード全体のSHA-256が `claim_sha256` となり、Bitcoinに刻まれる。**

したがって、Bitcoin に刻まれたハッシュは以下すべてに同時にコミットする：
- 利用者の入力
- 使用した参照データの内容（バージョン名ではなく実データSHA）
- 実行したアルゴリズムのコード版
- 適用したしきい値
- 出力した結果
- 発行したPDF

これらのいずれか一つでも改変すれば、`claim_sha256` は一致しない。

---

## 3. 独立検証レシピ v1

任意の第三者が、HORIZON SHIELD を一切信頼せずに監査主張を検証できる：

```bash
N=<エントリ番号>
BASE=https://hs-ledger.oga-surf-project.workers.dev

# 1. 正規レコードを取得
curl -s "$BASE/ledger/$N?format=raw" > claim.json

# 2. Bitcoin 刻印を検証
curl -s "$BASE/ledger/$N/ots" > claim.ots
ots verify claim.ots        # 要 opentimestamps-client + Bitcoin node
# または https://opentimestamps.org にドロップ

# 3. 各構成要素のSHAを独立に確認
jq -r .reference_bundle_sha256 claim.json > ref.sha
curl -s "$BASE/reference/$(jq -r .reference_bundle_sha256 claim.json)" > ref.json
shasum -a 256 ref.json      # ref.shaと一致することを確認

jq -r .algorithm_commit claim.json > algo.sha
git clone https://github.com/ogasurfproject-jpg/horizon-shield
cd horizon-shield && git checkout $(cat ../algo.sha)  # 同じコードを取得

# 4. 同じ入力+参照+アルゴリズムで再計算し、result_sha256 と一致することを確認
```

---

## 4. 参照束のBitcoin事前固定 (pre-anchoring)

**新規エンドポイント:** `POST /reference/pin`（要 admin token）

参照データ束（souba-db + meisai-bench + thresholds）の全JSONを受け取り、内容SHA-256を計算し、専用のクレームとして即座に台帳に append する。以降のすべての監査クレームは、この pinned reference bundle SHA を `reference_bundle_sha256` として参照しなければならない。

**運用ルール:**
- 参照データを更新する際は、必ず `/reference/pin` に投入し、新しいSHAを取得してからでないと、監査発行に使えない。
- pinning されたバンドルは content-addressed で保存され（key = `ref:<sha>`）、以降不変。
- 過去の監査クレームが参照するSHAは、常に取得可能でなければならない。

これにより「R2の同月内更新でこっそり変わる」問題が根絶される。

---

## 5. 過去エントリの取り扱い

- **Entry #1** (`9a40b981...`) は v0 スキーマである。参照データSHA・commit ID・result SHA を含まないため、v1 の独立検証水準を満たさない。
- Entry #1 の Bitcoin 刻印自体は有効（当該時刻に当該JSONが存在した証拠）。
- 論文および公開文書では、Entry #1 は「概念実証・PTKAアプローチの時刻証拠」であって「独立検証可能な監査記録」ではないと明記する。
- 独立検証可能な監査記録は v1 スキーマ以降とする。

---

## 6. 論文修正事項（MANUSCRIPT v2 に向けて）

- 「R2 strong consistency により同じデータセットが読まれる」の記述を削除し、「参照束のcontent-addressed pinning により、同じSHAを参照する限り同じデータが読まれる」に修正する。
- 「二つの実装が独立にハッシュを計算」の記述を削除し、「Bitcoin にコミットされた canonical record が、入力・参照・アルゴリズム・結果・PDF のすべてに同時にコミットする」に修正する。
- Method セクションに Verifier Recipe (§3) を追加する。
- Limitations セクションに、Entry #1 が v0 スキーマであること、v1 以降が独立検証水準を満たすことを明記する。

---

## 7. 謝辞

本設計変更は、Pang-jo Chun (全 邦釘) Ph.D. の 2026-07-25 の指摘を受けて行った。上流ハッシュのコピー問題、ハッシュ入力の欠落、バージョン識別子の不十分性の三点について、指摘は正確であった。感謝する。

---

**このドキュメントのSHA-256は、JIDEC 台帳エントリ #2 として Bitcoin に刻印される。刻印以降、本ドキュメントの主張は改変不可能である。**
