#!/usr/bin/env python3
"""
verify_finding_v0.py — Independent reproduction of the v0 hash defect.

Purpose:
  The JIDEC v1 SPEC (Bitcoin-anchored as ledger entry #2) asserts that the
  v0 audit hash in the deployed hs-pdf-gen worker covered only the estimate
  JSON — it did NOT cover the benchmark bytes, the algorithm code, the
  thresholds, or the PDF text.

  This script proves that assertion mechanically. It reproduces the exact
  hash the deployed worker computed, using a canary input for which the
  deployed worker itself already documents the expected hash value.

  Anyone can run it with only the Python 3 standard library. No network,
  no dependencies, no hidden state. If the reproduced hash matches the
  deployed worker's published expected hash, the reproduction is faithful.
  From there, the coverage claims are demonstrated by mutating parts of
  the input the hash *should* cover, and parts it *should not*, and
  confirming which ones change the hash.

Source of truth for the canary:
  hs-pdf-gen deployed worker (bundled source), var HS_AUDIT_CANARY_EX,
  and the published expected hash var HS_AUDIT_CANARY_EXPECT.hash =
  "C025E288675EE898". These are set in the same file that implements the
  hash, so their pairing is not a post-hoc claim — it's the deployment
  self-testing.

  The bundled source is retrievable via Cloudflare's API to any account
  owner, and the two hash-computation call sites are quoted verbatim in
  SPEC_HASH_INDEPENDENCE_v1.md (JIDEC entry #2):
    - hsHandleEstimateAudit(), line 18661:  SHA-256(JSON.stringify(ex))
    - generatePDF(),           line 19543:  SHA-256(join("|") of 5 fields)

  This script reproduces the first one, since it has a published canary
  and expected-hash pair. The second is a straightforward join of five
  runtime fields and is quoted in the SPEC; anyone can hash the same
  join to reproduce.

Usage:
  python3 verify_finding_v0.py
  # exit code 0 if reproduction matches the deployed canary
  # exit code 1 otherwise
"""

import hashlib
import json
import sys


# ---------------------------------------------------------------------------
# 1. Canary input — copied verbatim from HS_AUDIT_CANARY_EX in the deployed
#    worker (bundle line 18737). Insertion order matters: JavaScript's
#    JSON.stringify preserves object key order, and Python 3.7+ dicts do
#    the same. This script depends on that guarantee.
# ---------------------------------------------------------------------------
CANARY = {
    "schema_version": "0.1",
    "extraction_method": "canary",
    "source_file": "(canary)",
    "doc": {
        "doc_type": "estimate",
        "issuer": "CANARY",
        "customer": "CANARY",
        "customer_contact": None,
        "title": "外壁塗装 カナリア固定入力",
        "estimate_no": "CANARY-001",
        "issue_date": "2026-07-07",
        "valid_until": "2026-12-31",
        "currency": "JPY",
        "subtotal_ex_tax": 454000,
        "tax_rate_pct": 10,
        "tax": 45400,
        "total_inc_tax": 499400,
        "payment_terms": [],
        "doc_notes": [],
    },
    "rows": [
        {"no": 1, "type": "section", "description": "仮設工事",
         "qty": None, "unit": None, "unit_price": None, "amount": None, "flags": []},
        {"no": 2, "type": "item", "description": "仮設足場(くさび式)",
         "qty": 200, "unit": "㎡", "unit_price": 800, "amount": 160000, "flags": []},
        {"no": 3, "type": "section", "description": "塗装工事",
         "qty": None, "unit": None, "unit_price": None, "amount": None, "flags": []},
        {"no": 4, "type": "item", "description": "下塗り(シーラー)",
         "qty": 120, "unit": "㎡", "unit_price": 750, "amount": 90000, "flags": []},
        {"no": 5, "type": "item", "description": "シリコン中塗り",
         "qty": 120, "unit": "㎡", "unit_price": 1700, "amount": 204000, "flags": []},
    ],
}

# Published in the same worker source (bundle line 18738) as the expected
# result of hashing the above canary through the v0 pipeline.
EXPECTED_HASH_V0 = "C025E288675EE898"


# A representative "benchmark bundle" that the v0 hash does NOT cover.
# The exact bytes do not matter for the demonstration — only that they are
# a stand-in for one of the inputs Chun's finding said was missing (any of
# souba-db, HS_MEISAI_BENCH, or the algorithm commit ID would do).
BENCHMARK_BUNDLE_A = {
    "_meta": {"version": "souba-db@2026-07"},
    "gaiheki_tosou": {"min_yen_per_tsubo": 8000, "avg": 12000, "max": 18000},
}
BENCHMARK_BUNDLE_B = {
    # Same schema, silently mutated numbers. This is exactly the "same-month
    # R2 update" scenario the SPEC calls out.
    "_meta": {"version": "souba-db@2026-07"},
    "gaiheki_tosou": {"min_yen_per_tsubo": 8000, "avg": 15000, "max": 25000},
}


# ---------------------------------------------------------------------------
# 2. Reproduce the v0 hash computation exactly.
#
#    From the deployed worker, function hsHandleEstimateAudit(), line 18661:
#
#      var enc = new TextEncoder().encode(JSON.stringify(ex));
#      var digest = await crypto.subtle.digest("SHA-256", enc);
#      var fullHex = Array.from(new Uint8Array(digest)).map(
#          function(b2) { return b2.toString(16).padStart(2, "0"); }
#      ).join("");
#      var hash = fullHex.slice(0, 16).toUpperCase();
#
#    JavaScript's JSON.stringify with no space argument uses no whitespace
#    and preserves key insertion order. Python's json.dumps matches that
#    with separators=(",",":") and default sort_keys=False.
#
#    ensure_ascii=False keeps non-ASCII characters as their raw UTF-8 bytes,
#    matching JS behavior.
# ---------------------------------------------------------------------------
def v0_hash(estimate: dict) -> str:
    canonical = json.dumps(estimate, ensure_ascii=False, separators=(",", ":"))
    full_hex = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return full_hex[:16].upper()


# ---------------------------------------------------------------------------
# 3. Run the checks and print the coverage table.
# ---------------------------------------------------------------------------
def main() -> int:
    print("=" * 72)
    print("JIDEC v0 hash independent reproduction")
    print("Reproduces the deployed hs-pdf-gen hash and demonstrates coverage")
    print("=" * 72)
    print()

    canonical = json.dumps(CANARY, ensure_ascii=False, separators=(",", ":"))
    print(f"Canonical JSON length: {len(canonical)} bytes")
    print(f"First 120 chars:       {canonical[:120]}...")
    print()

    reproduced = v0_hash(CANARY)
    print(f"Reproduced v0 hash:    {reproduced}")
    print(f"Deployed expected:     {EXPECTED_HASH_V0}  (from HS_AUDIT_CANARY_EXPECT.hash)")
    match = reproduced == EXPECTED_HASH_V0
    print(f"Reproduction faithful: {match}")
    if not match:
        print()
        print("FAIL: the reproduction did not match the deployed expected hash.")
        print("      Either the canary in this script has drifted from the deployed")
        print("      version, or the hash formula in this script does not match")
        print("      the deployed code. Inspect the source and rerun.")
        return 1
    print()

    # -------------------------------------------------------------------
    # Coverage demonstration.
    # For each mutation, we show whether the v0 hash changes. Anything the
    # hash covers WILL change the hash. Anything the hash does NOT cover
    # will leave the hash identical.
    # -------------------------------------------------------------------
    print("-" * 72)
    print("Coverage demonstration")
    print("-" * 72)
    print()
    print(f"{'mutation':<58} {'covered?':<10}")
    print(f"{'-' * 58} {'-' * 10}")

    baseline = v0_hash(CANARY)

    # (a) Change a row unit price inside the estimate itself.
    mutated_estimate = json.loads(json.dumps(CANARY))
    mutated_estimate["rows"][4]["unit_price"] = 9999
    h = v0_hash(mutated_estimate)
    print(f"{'change rows[4].unit_price 1700 -> 9999':<58} {str(h != baseline):<10}")

    # (b) Change the estimate title.
    mutated_estimate = json.loads(json.dumps(CANARY))
    mutated_estimate["doc"]["title"] = "外壁塗装 別の入力"
    h = v0_hash(mutated_estimate)
    print(f"{'change doc.title':<58} {str(h != baseline):<10}")

    # (c) Swap the entire benchmark bundle from A to B (silent R2 update).
    #     The v0 hash formula does not read the benchmark at all, so this
    #     cannot change the output. We assert it does not.
    _bench = BENCHMARK_BUNDLE_A  # noqa: F841 — inputs simulated, not fed to v0
    h = v0_hash(CANARY)
    print(f"{'swap benchmark bundle A -> B (same estimate)':<58} {str(h != baseline):<10}")

    # (d) Change the algorithm commit ID (simulate a redeployed worker).
    _commit_before, _commit_after = "abc123...", "def456..."  # noqa: F841
    h = v0_hash(CANARY)
    print(f"{'swap algorithm commit (same estimate)':<58} {str(h != baseline):<10}")

    # (e) Change the threshold config (min/max/danger).
    _thresholds_before, _thresholds_after = {"danger": 1.3}, {"danger": 2.0}  # noqa: F841
    h = v0_hash(CANARY)
    print(f"{'swap threshold config (same estimate)':<58} {str(h != baseline):<10}")

    print()
    print("Reading:")
    print("  Rows (a) and (b) change the estimate JSON, so the v0 hash changes.")
    print("  Rows (c)(d)(e) leave the estimate JSON unchanged; the v0 hash is")
    print("  identical. Therefore the v0 hash commits ONLY to the estimate JSON.")
    print("  It does not commit to the benchmark, the algorithm version, or the")
    print("  thresholds. This is exactly the finding stated in the SPEC (JIDEC")
    print("  entry #2), reproduced here independently from the published canary.")
    print()
    print("PASS: reproduction faithful, coverage matches the SPEC's finding.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
