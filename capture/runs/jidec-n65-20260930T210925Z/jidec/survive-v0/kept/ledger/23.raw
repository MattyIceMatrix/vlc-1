# NENRIN coordinate-v1 code manifest (`nenrin-coordinate-v1-manifest`)

This manifest pins the exact bytes of the coordinate-integrity harnesses that back NENRIN_COORDINATE_SPEC_v1.md. The SHA-256 of this manifest is appended to the JIDEC ledger and stamped to Bitcoin. Anyone can clone the repository, take the SHA-256 of each file below, compare it to the value here, and check the time this manifest entered a Bitcoin block. No trust in the operator is required: fetch the bytes, recompute the hash, check the anchor.

Spec anchored beside this manifest:
  5be2b22e339d8b5c45a272325c49da189f10715b01683025ae903e83bf251df5  NENRIN_COORDINATE_SPEC_v1.md

Harness files, in fixed order, each with its SHA-256:

  76273d0bd53792bc9470fac6f94956581857b642a3dfd5c04f4d2889d10a0127  nenrin_census.py
      census 実装: 呼べる母集団を CT から数え直す(三集合分解、jidec-path-v1 witness 化)
  1b94e0d200b5526491136c0d08dcacfd7699c1d21e2aaffe5f5568965dcb8e1a  census_redteam.py
      census の敵: 隠し/水増し/改ざん/残余誤名 を10手で fail-closed
  a0971fc15b9d32ea32b47cfd04fd19104aaf3f187e0b1c2d32e90ca324d17a37  join_guard.py
      join 実装: 座標(原価カテゴリ)を明細から導出、prover のラベルを不一致で拒否
  7826a060ef1d68b4d410e8bc6704ea86bff0d5f04b37dc2bf50238806bfa857e  join_redteam.py
      join の敵: 全サブ層を緑に保ったまま座標詐称を8手で拒否
  324728e261cba5a21ab15b92e6def1af0ab8fa6f7b0bda7b81b3b27696527702  time_coordinate_probe.py
      時刻座標 probe: created_at を prover が選べる問題(本物 Ed25519)
  65781879fd510154a8c78fe1dd7a51b92b5ed3590093b707f7f6cc769081047f  time_redteam.py
      時刻の敵: authorship 確認/postdating 拒否/backdating と currency を命名
  2563f7c85fb8c1bbdd2f1d6806a7330d9a323c24de50ff1a349a3aa7cc894431  freshness_v2.py
      freshness v2: backdating をビーコンで閉じ currency を fail-closed に
  25e433759752c8dd36b7f0be8fdef883067b3573420b9004837cc4872759ce3a  freshness_v2_redteam.py
      freshness v2 の敵: 両側の時間箱と fail-closed を9手で確認

All four harnesses run offline and deterministically:
  python3 nenrin_census.py ; python3 census_redteam.py
  python3 join_guard.py ; python3 join_redteam.py
  python3 time_coordinate_probe.py ; python3 time_redteam.py
  python3 freshness_v2.py ; python3 freshness_v2_redteam.py

Once this manifest is anchored, the byte sequence of each harness above is fixed at that Bitcoin block height. A later correction is a new manifest that cites this one, never an edit. The operator is a subject of this rule, not an exception.
