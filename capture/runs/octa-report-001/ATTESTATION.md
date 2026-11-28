# OCTA gateway — signed-report capture (report 002)

Export produced 2026-11-28 ~07:28 UTC on the operator's machine by
`sealAndExportAuditChain()` of MattyIceMatrix/OCTA, signed with the DURABLE
ledger key (OCTA_AUDIT_PRIVATE_KEY set; key_is_ephemeral false).

Attestation trace, verified before this capture was pushed:
1. `export-meta.json` marker_signature: Ed25519 over sha256(JSON of marker)
   under public_key_pem — VERIFIED.
2. sha256(public_key_pem) = 0577dcaebe4881dc5c94f8d7255ed0a13fc65dffdda12c731c44a72a3107da61,
   equal to ledger_public_key_sha256 in keys/matthew-moore-operator-statement.json,
   whose own signature verifies under keys/matthew-moore-operator.pub.pem — VERIFIED.
3. All entries: chain links + Ed25519 under the same ledger key; final head
   equals the marker head — VERIFIED.

The checker's anchors (expect_root / expect_head) are the marker's genesis and
head, independent of the log by (1)-(3). Grade at capture: structural 4,
attested 4; VLC-L5 fails as it must for a self-reported log (L4 ceiling).
