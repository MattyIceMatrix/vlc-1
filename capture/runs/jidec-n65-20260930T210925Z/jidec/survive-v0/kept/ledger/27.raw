# NENRIN coordinate-v1 addendum: localheaders, a chain and not a website (`nenrin-coordinate-v1-addendum-localheaders-v1`)

This addendum cites the sources addendum and, through it, the time axis v3 addendum and the
v1 spec. It does not edit any of them and it does not change freshness_v3.py, whose bytes
entry 24 pinned and which are cited below unchanged. What it does is pay a debt those files
wrote in public: entry 24 called a locally synced header set the strongest form of the time
check and entry 26 said plainly that the operator's third source, `localheaders`, was a
fixture and not wired. It is wired now, and this file pins the code, the adversary, the real
header set it was run against, and the verdicts that came out, so that anyone can rerun all
of it offline and get the same bytes.

Cited, anchored, unchanged:

    5be2b22e339d8b5c45a272325c49da189f10715b01683025ae903e83bf251df5  NENRIN_COORDINATE_SPEC_v1.md (JIDEC entry 22)
    447bcf4f38cd8099683ccd396467609438aa47399e9bb9b75d7c425900147611  NENRIN_COORDINATE_v1_ADDENDUM_time_v3.md (JIDEC entry 24)
    04908cd53c006ea0ebd24535ab8d3c884317cd2aeeff7a24f136c8a459cf50dc  NENRIN_COORDINATE_v1_ADDENDUM_sources_v1.md (JIDEC entry 26)
    276bc047838ee944bc078f519988d3688d58131318d4da916dad038622e22512  freshness_v3.py (pinned by entry 24, not modified)

## 1. What changed

The third beacon source now reads raw Bitcoin block headers, eighty bytes each, from a file
the operator synced, and verifies every header against the chain's own consensus rules before
it is allowed to say anything about any block. No API is in the path at verification time.
The two public explorers remain in the quorum as what they are: each one's word about the
chain. The header set is not anyone's word. It is the chain, checked.

Seven checks, on every header, in order: the double SHA-256 hash; linkage to the previous
hash; proof of work, the hash as a 256 bit integer at or below the target its own bits encode
and that target at or below the chain's limit; the difficulty rule, bits unchanged off a
boundary and, on a boundary, equal to what Bitcoin Core's retarget arithmetic produces from
the previous period's first and last timestamps, clamped to a factor of four and capped at
the limit; median time past, the timestamp above the median of the previous eleven; future
drift against a supplied clock, skipped and said so when no clock is supplied so offline runs
stay deterministic; and checkpoints, hashes the operator pins here, which a covered height
must match and an uncovered height reports as unreached, lag and never a veto.

One violation refuses the whole file. A header set with one bad header is evidence of
tampering or corruption, not a shorter chain. The refused source reports itself down with the
reason and the height, and freshness_v3 treats it exactly as it treats any down source. The
emitted shape is the one freshness_v3 already consumes, so freshness_v3.py is untouched:
value is the block hash in display order, time is the header's nTime.

Implementation independence, the axis entry 26 said the operator could not claim, is now
bought by construction for this one source. Two explorers may share a codebase. A header
verified by its own proof of work shares nothing with either of them.

## 2. The adversary mines

The red team does not fake proof of work. It mines real headers at a test difficulty of about
two to the fourteenth hashes per block, deterministic from nonce zero, and it mines its
forgeries too, so the line between what proof of work refuses and what only a checkpoint
refuses is drawn by execution. Twenty five checks, all green, identical on the operator's
machine and in a clean container:

  - a flipped bit, an unmined header, a header mined at the old easier difficulty across a
    retarget whose own proof of work holds, bits drifting off a boundary, a timestamp at or
    below median time past, a future timestamp under a supplied clock, negative and over
    limit targets, a duplicate header, a missing header, a file that is not a multiple of
    eighty bytes, a manifest whose hash does not match the file: all refused, each with its
    reason.
  - a truncated file is lag, not a veto, and inside freshness_v3's quorum the truncated
    source is marked lag while the proof is still affirmed by the others.
  - a heavier alternative chain forked at height twelve passes every consensus check and is
    refused only by the checkpoint. That is the residual made visible rather than described.
    Along the way the adversary recorded a fact worth keeping: its thirty six block fork was
    lighter than the thirty two block honest chain, because the honest chain had retargeted
    harder, and it took thirty two forged blocks to out work twenty honest ones. Block count
    is not work.
  - a file that starts mid period names the boundary it cannot verify instead of pretending.
  - the real mainnet genesis header and block one, written from bytes, hash to the known
    values and pass the mainnet rules. The adapter recognises the chain from bytes, never
    from a name.
  - a lying explorer loses to the header chain plus one honest explorer and the proof fails
    closed; a refused header file becomes a down source with its reason on the record and the
    quorum carries on.

## 3. What ran on the real chain

The operator synced a window from two explorers on 2026-09-04, treating each as a courier and
not as a source: every header was rebuilt from the fields the courier returned, refused if
its hash did not equal the id the courier printed, and then validated by the seven checks
above before a byte was written.

    blockstream.info   heights 961632..965451   3820 headers   305600 bytes
    mempool.space      heights 961632..965452   3821 headers   305680 bytes

The two couriers agree byte for byte on all 3820 headers they both cover: the SHA-256 of the
first 305600 bytes of the mempool file equals the SHA-256 of the blockstream file. The one
extra header mempool returned links to the blockstream tip. Checkpoints, the retarget
boundaries inside the window and the tips, pinned here:

    961632  00000000000000000000d1e01392faa65ceeaed307f0a3159144b84146ff24ba
    963648  00000000000000000001769d9a327f5b455aa8a2dd407b1b63040d2a9f832d32
    965451  00000000000000000000e9f3195446ee74b371312941d73e8fdddab86499b499
    965452  00000000000000000001906f4769930973ed17a5a6916427533f9199cc5705a0

The difficulty boundary at 963648 was verified from inside the file. The boundary at 961632,
the first header, could not be, because the first block of the period before it (959616) is
not in the file; the report names it as unverified. Nothing was assumed.

freshness_v3 was then run offline against three real sources, the header chain and the two
explorer snapshots, with a fixed clock so the run is reproducible. Five proofs, five verdicts:

    f9cc2494ccbfe0f050d49be6a0aae61ce919a2ae68052122640b129fb0073041  honest proof on the real tip: authentic, three sources agree, quorum basis, valid as issued
    f1fd185bd01b0b148630097c183c4daa3734b2555ab0d8aa25290d8e0bfdfc2a  fabricated hash at the real height: forged, refused
    16cb59e0a1f671f275811e9aefed82c5fd999be37d84f6425cdcac5e1a043a12  height beyond the reference tip plus six: bad coordinate, refused, every source honest
    a84f48f38125bbbb9669b956a82b16d4e3a5eca8f012b5b75b050c7dff6f519f  created a week before its own beacon block: beacon authentic, refused as backdated (the v3.1 decoupling, on real data)
    2ddfd0a38a66d1f4c348ebe0afc18cbf72fd1720c182d5ad957b28e20368a033  header chain down, explorers alone: authentic, two agree, degraded tip basis disclosed

Those are record hashes of the full verdict records freshness_v3 emits. They reproduce byte
for byte from the pinned files.

## 4. Limits, named

  - The courier at sync time is still an HTTP explorer. Trust does not rest on it, because a
    forged header fails proof of work and a stale chain is lag, but the form that touches no
    third party at any time, a peer to peer header sync, is not built. Named, not closed.
  - Proof of work bounds an attacker by hashpower, not by identity. A lighter alternative
    chain is refused by the operator's checkpoints and by nothing else the operator can
    verify alone. The checkpoints are pinned here and so anchored in Bitcoin through JIDEC,
    which is the anchor of the anchor, and they are the operator's choice.
  - The header set is a snapshot. Its tip is where the courier was on 2026-09-04. Currency is
    re measured by syncing again on the cadence freshness_v3 already fails closed on.
  - The first boundary of any window is not verifiable from inside the window. The report
    says so every time.
  - The two explorer snapshots are each explorer's word, kept as quorum members and nothing
    more. Whether those two share an implementation is still not audited, as entry 26 said.
    What changed is that the third source no longer depends on either of them.

## Files pinned by this addendum

In fixed order, each with its SHA-256. Clone the repository, take the SHA-256 of each file,
compare it here, and check the time this addendum entered a Bitcoin block.

    d0dba8267b6deeb72552c18b982aec126e7eb6948bad93ddbf8723464c6c203e  localheaders.py
        the adapter: seven consensus checks on raw headers, one violation refuses the file, emits the freshness_v3 shape
    ff3faaaa25318be884f53675d3e0c58ee36ea0c1a737b6465f1fed86c551cc04  localheaders_redteam.py
        the adversary: mines real proof of work at test difficulty, twenty five checks, deterministic, offline
    88f40b8eea10ec0771213f27a40661ce81a53f524cdde8cdd256f6d3dee6ddc5  sync_headers.py
        the only network step, run by the operator: rebuilds headers from a courier's fields, refuses any whose hash disagrees, validates, writes nothing on failure
    78d2aa44210463f48b4be90816f06e53a6bbe6965ef1b32596fc396ee6b33c78  sources_live.py
        assembles the three real sources for freshness_v3 without touching freshness_v3.py
    d2bfb41a5e683f48e1e9f74b5232abf0a1fbe989809d4c4163b2dc5e2e8c5970  freshness_live.py
        the five real chain proofs above, fixed clock, reproducible
    b7c8ddefff198c865f3e27ec86d6d02d26ff4778158e4380f66d2c97ebaed367  localheaders_mainnet.bin
        3820 raw headers 961632..965451 via blockstream.info, validated
    712b679210c38e5f77acb1989a6182cb1d0a95e2e4d097a8973c58cd7609d423  localheaders_mainnet.manifest.json
    b8803f63305640daefeae5f9eda14a7bd10873af023526791cff0662db39e56b  localheaders_mainnet_mempool.bin
        3821 raw headers 961632..965452 via mempool.space, validated; first 305600 bytes identical to the file above
    8a25d65c244e0ff7cc9abf8b333d083ad2a53d7ea85441f6e14c6f65f6c46d62  localheaders_mainnet_mempool.manifest.json
    f5a124354fea409b169e3e7dd5c7195e2849e15fd4d3c46f429500ab470f1ae6  explorer_blockstream_snapshot.json
    6b18c5d40d914e686733c7f5ae3457cff63f23ba9a58d9ce12ab8a02e4e98dbb  explorer_mempool_snapshot.json

Run offline and deterministically, from the directory holding these files:

    python3 localheaders.py --self-check ; python3 localheaders_redteam.py ; python3 freshness_live.py

The first prints the genesis hash from bytes. The second ends in 25 / 25. The third ends in
the five record hashes above. To rebuild the header set yourself, run sync_headers.py against
either explorer with --start 961632 and compare the SHA-256 of its first 305600 bytes to
b7c8ddef...aed367; a different courier producing the same bytes is the point.

No trust in the operator is required: fetch the bytes, recompute the hash, check the anchor.
Once this addendum is anchored, a later correction is a new file that cites this one, never an
edit. The debt entry 26 wrote in public is paid in bytes, which is the only currency the
founding witness accepts, and the right one.
