# NENRIN coordinate-v1 addendum: refusals v1, a refusal is a record (`nenrin-coordinate-v1-addendum-refusals-v1`)

This addendum cites the localheaders v3 addendum and, through it, v2, v1, the sources
addendum, the time axis v3 addendum and the v1 spec. It edits none of them and changes no
file they pinned. It closes a gap that no addendum had named, because the operator had not
seen it. An outside verifier who had independently recomputed entries 26, 27 and 28 asked
whether the red team's case in which two peers serve two valid chains, no checkpoint separates
them, and the client refuses and names both, is logged anywhere a downstream consumer of the
ledger can query directly, or whether someone has to read the addendum text to know that
failure mode exists. The honest answer was no. This entry makes it yes.

Cited, anchored, unchanged:

    5be2b22e339d8b5c45a272325c49da189f10715b01683025ae903e83bf251df5  NENRIN_COORDINATE_SPEC_v1.md (JIDEC entry 22)
    447bcf4f38cd8099683ccd396467609438aa47399e9bb9b75d7c425900147611  NENRIN_COORDINATE_v1_ADDENDUM_time_v3.md (JIDEC entry 24)
    04908cd53c006ea0ebd24535ab8d3c884317cd2aeeff7a24f136c8a459cf50dc  NENRIN_COORDINATE_v1_ADDENDUM_sources_v1.md (JIDEC entry 26)
    f5512ea3bb476e3356f96979c9a922e102f35d893659d76ad151fed5450f6162  NENRIN_COORDINATE_v1_ADDENDUM_localheaders_v1.md (JIDEC entry 27)
    5ed2027f4ce46a11a35dc065c74b02b81a4289c759225776f9383f4909cdf5f4  NENRIN_COORDINATE_v1_ADDENDUM_localheaders_v2.md (JIDEC entry 28)
    937ce7049c1962f9e862af5f124ae31a40ef39c230a5c0937a1a23257a861693  NENRIN_COORDINATE_v1_ADDENDUM_localheaders_v3.md (JIDEC entry 29)
    276bc047838ee944bc078f519988d3688d58131318d4da916dad038622e22512  freshness_v3.py (pinned by entry 24, not modified)
    d0dba8267b6deeb72552c18b982aec126e7eb6948bad93ddbf8723464c6c203e  localheaders.py (pinned by entry 27, not modified)

## 1. The gap, stated exactly

Entries 27, 28 and 29 each said "nothing is written on a refusal". That rule was written for
header bytes: a sync that cannot establish agreement must not leave a file that looks like a
validated chain. The rule was correct and it swallowed too much. The client, on refusing,
raised an exit with a sentence and wrote nothing at all. The manifest, which records dropped
peers in peers_failed, is written only when a sync succeeds. So a refusal on the real network
would have left no file, no ledger entry, and nothing a consumer could query; the only places
the failure mode existed were the red team's printed output and the prose of the addenda. A
refusal that is legible only in prose is a weaker guarantee than one with its own queryable
record. The ledger already holds one published failure, entries 2 and 3, the v0 hash defect,
so the discipline was known; it had not been applied to the courier.

## 2. What changed

sync_headers_p2p.py now writes a refusal record on every refusal, before exiting, and still
writes no header byte. The record is JSON with schema nenrin-localheaders-refusal-1 and
carries: the reason code, one of peers_disagree, below_min_peers, readback_refused,
readback_sha_mismatch; the reason in words; the height when there is one; for a disagreement,
both peers by address and both hashes at that height, and how many headers they agreed on
before it; every peer that finished, with its tip; every peer that was dropped, with why; the
network, stated as bitcoin mainnet only when both the magic and the parameters are mainnet's,
and otherwise stated as a test network with the magic spelled out; the clock; the peer
minimum; and bytes_written false. A disagreement is caught while streaming, so the record
names the peer whose bytes were the reference and the peer that departed from them, and the
two hashes come from the two headers at the first differing offset.

make_refusal_seed.py turns one record into a JIDEC seed, the same shape as every other entry:
the claim is the SHA-256 of the record's exact bytes, the record is the entry's canonical
text, and the work line begins with "NENRIN localheaders refusal" followed by the reason,
the height, the peers and the hashes. It is fail closed: a record whose schema is not the
refusal schema, whose bytes_written is not false, whose reason code the client does not emit,
or whose disagreement names one peer twice or one hash twice, gets no seed.

p2p_redteam.py, sixteen checks, all green, identical on the operator's machine and in a clean
container. The two chains case now also requires the record: reason peers_disagree, height
12, the first peer's hash at 12 and the second peer's, the count of headers agreed before,
the test network named, the fixed clock. The below minimum case requires its record: reason
below_min_peers, the dropped peer named with its reason, the finished peer listed. A new case
feeds the two chains record to the seed maker and requires the claim to equal the record's
sha, then feeds five tampered variants and requires each to be refused with no seed written.
The two chains case binds its fake peers to fixed ports, so with the fixed clock and the
mined chains the record is byte reproducible: the operator's machine and the container
produced the same file, sha256 07830db2...cf26, on every run.

## 3. The refusal on the ledger

That record, refusal_record_redteam_c07.json, is appended to the ledger as the entry
immediately preceding this one, citable by its own id, which is the record's sha256:

    07830db2cf32aaee74b77c3cc563318515d276a505288ae574a3666f7defcf26

jidec_cite on that id returns the record as machine readable JSON with the two peers, the
height and the two hashes, and the ledger's list shows it under a work line that begins
"NENRIN localheaders refusal: peers_disagree at height 12". No prose is needed to learn that
the failure mode exists, what it looks like, or what the client does about it. The record
says on its face that it comes from a test network with fake peers on loopback; it is the
shape of a refusal, published before any real one has happened, so that a consumer can code
against it now.

The operator's rule from this entry on: every refusal record the client writes against the
real network is appended to the ledger the same way, by the same script, whether or not the
operator likes what it says. A contradiction between sources is evidence, and evidence is
published, not chosen away.

## 4. Limits, named

  - The ledger has no typed kind field. A refusal entry is told apart from a claim by the
    schema field inside its record and by the prefix of its work line; a consumer filtering
    the list must read the work line or parse the record. A typed kind is ledger schema
    work, a change to the service, and is named here, not done.
  - The record is written by the same program that refused. A run killed before it reaches
    the refusal point leaves nothing, as before. The record covers refusals the client
    decided, not runs that never decided.
  - The record proves that the client saw a contradiction and what it saw. It does not say
    which peer was honest. That is the point: the client does not choose, and the record
    does not pretend to.
  - The refusal on the ledger today is from the red team. Its clock is the red team's fixed
    clock, its peers are loopback addresses, and its network line says so. No refusal has
    occurred on the real network. When one does, its record will look like this one and go
    where this one went.
  - Everything v3 named stays named: plaintext transport, IPv4 only, DNS seeds for
    discovery, the chain file kept outside the repository, the two explorers' implementation
    independence unaudited.

## Files pinned by this addendum

    dd6c198554c63b8b0844e3463639ea287bef773408249936466f43d87f082271  sync_headers_p2p.py
        the p2p client, v3: every refusal writes its record before exiting, header bytes never written on a refusal; supersedes b7e5a27f9cf5b4ae pinned by entry 29
    0d49d6638c4965bae292d95ffd0eb58ca731f3e942e342e94f80d7bbf833a22e  p2p_redteam.py
        sixteen checks; the two chains and below minimum cases require their records, the seed round trip refuses five tampered records; supersedes d848b12f63d1473d pinned by entry 29
    c5f693225ed8e7de2427aa8bab75236c135b9304e2f51f4d0f87057839b5bde3  make_refusal_seed.py
        one refusal record becomes one ledger seed; fail closed on schema, bytes_written, reason code and a disagreement that names one peer or one hash twice
    07830db2cf32aaee74b77c3cc563318515d276a505288ae574a3666f7defcf26  refusal_record_redteam_c07.json
        the two chains refusal as the client wrote it: peers 127.0.0.1:28901 and 127.0.0.1:28902, height 12, both hashes, test network, bytes_written false; byte reproducible

Entry 29 pinned sync_headers_p2p.py at
b7e5a27f9cf5b4aef151f4361297fa089d3aa8cd7f832fef8542c965dd4c02d8 and p2p_redteam.py at
d848b12f63d1473dae316a45c95d4e0a52a01e12e648e28a7dfc16af905abd93. Those bytes are unchanged
on the ledger and still reproduce entry 29's result. The successors are pinned above. A
superseded sha is not an edit.

Run offline and deterministically, from the directory holding these files:

    python3 p2p_redteam.py --emit-refusal refusal_record_check.json ; python3 make_refusal_seed.py refusal_record_check.json --out seed_check.json

The first ends in 16 / 16 and prints the record's sha256, which is the id above. The second
prints the same sha256 as the claim. Then cite that id against the ledger and compare the
bytes.

No trust in the operator is required: fetch the bytes, recompute the hash, check the anchor.
Once this addendum is anchored, a later correction is a new file that cites this one, never an
edit. Entry 29 removed the operator's choice from the verdict. This entry removes the
operator's silence from a refusal.
