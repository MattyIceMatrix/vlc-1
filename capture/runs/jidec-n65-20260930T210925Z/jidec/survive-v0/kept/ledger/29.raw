# NENRIN coordinate-v1 addendum: localheaders v3, from genesis, no checkpoint (`nenrin-coordinate-v1-addendum-localheaders-v3`)

This addendum cites the localheaders v2 addendum and, through it, v1, the sources addendum,
the time axis v3 addendum and the v1 spec. It edits none of them and changes no file they
pinned. It closes the limit that v1 and v2 both named and could not close from inside a
window: that the first retarget boundary of the file stayed unverified, and that a lighter
alternative chain was refused only by a checkpoint the operator chose. The header chain is now
pulled from the genesis block, whose eighty bytes the adapter has carried since entry 27,
through every block to the tip, from three full nodes over the peer to peer protocol, and
validated in one streaming pass by consensus rules with no checkpoint supplied. Every
difficulty retarget in the history of the chain is verified from inside the file. The windows
entries 27 and 28 pinned are byte slices of this file. The checkpoints those entries chose
were confirmed by the bytes, not the other way round.

Cited, anchored, unchanged:

    5be2b22e339d8b5c45a272325c49da189f10715b01683025ae903e83bf251df5  NENRIN_COORDINATE_SPEC_v1.md (JIDEC entry 22)
    447bcf4f38cd8099683ccd396467609438aa47399e9bb9b75d7c425900147611  NENRIN_COORDINATE_v1_ADDENDUM_time_v3.md (JIDEC entry 24)
    04908cd53c006ea0ebd24535ab8d3c884317cd2aeeff7a24f136c8a459cf50dc  NENRIN_COORDINATE_v1_ADDENDUM_sources_v1.md (JIDEC entry 26)
    f5512ea3bb476e3356f96979c9a922e102f35d893659d76ad151fed5450f6162  NENRIN_COORDINATE_v1_ADDENDUM_localheaders_v1.md (JIDEC entry 27)
    5ed2027f4ce46a11a35dc065c74b02b81a4289c759225776f9383f4909cdf5f4  NENRIN_COORDINATE_v1_ADDENDUM_localheaders_v2.md (JIDEC entry 28)
    276bc047838ee944bc078f519988d3688d58131318d4da916dad038622e22512  freshness_v3.py (pinned by entry 24, not modified)
    d0dba8267b6deeb72552c18b982aec126e7eb6948bad93ddbf8723464c6c203e  localheaders.py (pinned by entry 27, not modified)
    b7c8ddefff198c865f3e27ec86d6d02d26ff4778158e4380f66d2c97ebaed367  localheaders_mainnet.bin (pinned by entry 27, the explorer built window)
    888151bb1b8b7566132a4e5d9385e34ee3db06651263ce77d6872a2a7fa9f194  localheaders_p2p.bin (pinned by entry 28, the window from three nodes)

## 1. What ran

On 2026-09-04 at 09:32 UTC the operator ran sync_headers_p2p.py in from-genesis mode. The
locator sent to each node was the genesis block hash, computed from the eighty bytes the
adapter holds, not looked up. The client resolved 181 candidate addresses from eight public
DNS seeds and connected to the first three that completed a handshake and answered
getheaders within the timeout:

    136.51.20.119:8333   /Satoshi:28.1.0/   965455 headers   tip 965454
    87.166.205.38:8333   /Satoshi:29.0.0/   965456 headers   tip 965455
    24.126.175.8:8333    /Satoshi:30.2.0/   965457 headers   tip 965456

Two other nodes completed the handshake and were dropped by name for not answering within
thirty seconds; they are recorded in the manifest as failures and supplied no byte. Each
finished node was pulled independently, two thousand headers per message, about 483 messages
per node, six to seven minutes per node. Every message was validated as it arrived, in
constant memory, by the same seven checks localheaders.validate_chain applies: linkage, proof
of work against the encoded target, target within the proof of work limit, the retarget at
every multiple of 2016 recomputed with Bitcoin Core's arithmetic from the first and last
timestamps of the previous period, median time past over the last eleven timestamps, future
drift against the clock, and the genesis hash at height zero. No checkpoint was supplied to
the validator. The three checkpoints of entry 27 were passed with --check-against, which
requires them to sit on the chain at the stated hashes and refuses otherwise; that is a check
the chain had to pass, not a rule the chain was allowed to lean on.

The second and third nodes were compared byte for byte against the first at the same offset
after every message; a mismatch would have ended the run naming the height, and nothing would
have been written. The three runs are byte identical over the 965455 headers they all cover.
The chain grew by two blocks while the run was in progress: the three tips differ by exactly
the blocks mined between each node's final message. That is lag, recorded as three tips, and
the longest agreeing run was written. Read back through the streaming validator as the last
step, the file reports:

    965457 headers, heights 0 through 965456, 77236560 bytes
    tip 00000000000000000001696cecabd47bef0ff322c80a3ae5bb0c9747f902ee57, nTime 1788514729 (09:38:49 UTC)
    478 retarget boundaries verified from inside the file, 2016 through 963648, none unverified
    chainwork 0x144b6257e7f6258de9bd94ff7
    one disclosure: height 0, bits continuity, because the genesis block has no predecessor

That one disclosure is the whole of what the file could not check about itself. The genesis
block's bits are checked against the proof of work limit and its hash against the constant the
adapter carries from bytes; what it cannot have is a previous block to be continuous with.
Every later header has one, and every one was checked.

## 2. What the bytes settle

genesis_window_check.py, pinned below, was run on the file with no checkpoints, no network and
nothing written. Nine checks, all green, on the operator's machine:

The whole file validates without a checkpoint in 2.3 seconds, sha256 d91d6482...3fec, tip
965456, chainwork as above. The 478 boundaries verified are exactly the multiples of 2016 from
2016 to 963648. The only unverified item is the genesis bits continuity. The header at offset
zero hashes to 000000000019d6689c085ae165831e934ff763ae46a2a6c172b3f1b60a8ce26f.

The three windows the earlier entries pinned are byte slices of this file at their heights:
heights 961632 through 965451 hash to b7c8ddef...d367, the value entry 27 pinned for the
blockstream built file; 961632 through 965452 hash to b8803f63...e56b, the mempool built file
entry 27 pinned; 961632 through 965454 hash to 888151bb...9194, the file from three nodes
entry 28 pinned. Eight couriers, two explorers and six full nodes across two entries, one
byte sequence, and the sequence is a slice of a chain that stands on its own work back to
block zero.

The five checkpoint heights the earlier manifests name, 961632, 963648, 965451, 965452 and
965454, were read straight from the bytes at those offsets and match the hashes the operator
chose, though none was given to the validator. Block 965447, which confirmed entry 26 on the
Bitcoin chain, is at its offset with hash 000000000000000000019ecf79e3647d64a626fc3df2c0d71f6fdf63aa411736
and nTime 1788508723, the values entries 27 and 28 reported. The chain that holds the anchor
of the record which admitted the third source was a fixture is now held whole, from the first
block, by the machine that made the admission.

## 3. The judge that streams

localheaders.validate_chain, pinned by entry 27, takes a complete byte string and returns a
report holding every parsed header. That is the right shape for a window and the wrong shape
for the whole chain: validating cumulatively after every network message is quadratic in the
number of headers, and holding every parsed header costs hundreds of megabytes for nothing.
The v1 client pinned by entry 28 did exactly that, which is why it was run on a window.

localheaders_stream.py applies the same seven checks as headers arrive and keeps only what the
next header needs: the previous hash and bits, the last eleven timestamps, the first timestamp
of the current and previous difficulty period, the running chainwork and the bookkeeping
lists. It imports localheaders.py's primitives and changes nothing in that file. It raises
localheaders.Refused with the same reason strings at the same heights.

stream_redteam.py proves the two judges are one. It feeds the same bytes to both, the
streaming one in random chunk sizes from a seeded generator, and requires identical reports:
same fields, same sha, same verdict. Eight checks, all green, identical on the operator's
machine and in a clean container: an honest mined chain reports identically; chunking one
header at a time or all at once changes nothing; all twelve refusals of the v1 red team (bit
flip, unmined header, easy bits at a retarget, bits changed off a boundary, median time past,
future time, checkpoint conflict, duplicate, gap, negative bits, target over the limit, bad
length) are refused by both with the same reason at the same height; a mid period start
discloses the same unverified boundary; a missing previous hash is disclosed identically; the
state stays bounded at eleven timestamps and two period starts however long the chain; the
mainnet genesis and block one validate identically under mainnet rules; and the real 3820
header window of entry 27 produces identical reports from both.

## 4. Superseded files, on record

Entry 28 pinned sync_headers_p2p.py at
9b600f9b7e6ab112be8fd3e84fc4d04cd35381cc1448fe7c1abee95b49c237f9 and p2p_redteam.py at
30bfe3eb07db8cb59e771d41bd786dd8d4ec2ec6bbe3bba42a4db76dd0bcdb7a. Those bytes are unchanged on
the ledger and still reproduce entry 28's result. This addendum pins their successors, which
validate through the streaming judge instead of cumulatively, add the from-genesis mode and
the --check-against flag, and extend the red team to fifteen checks with a from-genesis case
in which fake peers serve a mined chain from height zero and the client verifies every
boundary and matches the checkpoint. A superseded sha is not an edit. It is a new file with a
new hash, and the old one stays where it was, citable by anyone.

## 5. Limits, named

  - The chain file is not in the repository. It is 77 megabytes, and its bytes are the public
    chain, which twenty thousand nodes serve. Its sha256 is pinned here together with the
    sha256 of four prefixes, so a verifier who pulls from genesis to any tip past 965456 can
    compare without holding this copy:

        first 100000 headers, heights 0 through 99999:   0cc5d81131cca61998461e72d3eaac2618faecc2f9522e0b13578464361b9d91
        first 500000 headers, heights 0 through 499999:  ea10f50e4b7eacf10024ec832d1784d025308d78feabbdea235c23b190811768
        first 900000 headers, heights 0 through 899999:  f405cccf0e1d8fccd0a35e857e8252c0759c80693be5760b828975a58b039977
        first 965455 headers, heights 0 through 965454:  981bfb7deca7b23b5ff74d01962a5af57566d2addcc476e846f34f28b5e1097a

    The last is the window all three nodes covered. The operator keeps the file and its
    manifest is in the repository.
  - What refuses a lighter alternative chain is now the work, not a checkpoint. An adversary
    who can outwork the chain from genesis is not an adversary this specification defends
    against, and no specification does. A checkpoint still has one honest use, as a pin the
    operator chooses for a window sync, and v1 and v2 stated that use correctly.
  - The clock for the future drift check was taken at the start of the run, 09:32:11 UTC.
    The tip block was mined at 09:38:49 UTC, 398 seconds later, inside the two hour
    allowance. A run long enough for the chain to move more than two hours past its own
    start would refuse its own tip; the fix is a fresh clock, not a wider allowance.
  - The file is a snapshot. The chain has moved since. Currency is a matter of syncing again
    from the manifest, and freshness_v3 treats a stale file as a stale source, entry 24's v3.3.
  - The connection is plaintext, IPv4 only, discovered through DNS seeds, as v2 said. What an
    adversary on the path can serve is bounded by proof of work, by byte agreement across
    independent nodes, and now by the whole history rather than a window of it.
  - Whether the two explorers of entry 26 share an implementation is still not audited. The
    third source no longer depends on either for anything.

## Files pinned by this addendum

    68a574f23430b530ef747dfc75e1e56440f02b3d4f0f3e3f1961d1e679be5779  localheaders_stream.py
        the same seven checks in one pass and constant memory; imports localheaders.py unchanged
    2feb92d17a7d084f9f2c023939774a76e6abb47d8a30fe10b29f23eba730d240  stream_redteam.py
        two judges fed the same bytes must agree on every report and every refusal; eight checks, deterministic
    b7e5a27f9cf5b4aef151f4361297fa089d3aa8cd7f832fef8542c965dd4c02d8  sync_headers_p2p.py
        the p2p client, v2: streaming validation, from-genesis mode, check-against; supersedes 9b600f9b7e6ab112 pinned by entry 28
    d848b12f63d1473dae316a45c95d4e0a52a01e12e648e28a7dfc16af905abd93  p2p_redteam.py
        fake peers on loopback, fifteen checks including from genesis; supersedes 30bfe3eb07db8cb5 pinned by entry 28
    2c45be77c748b18505c712500490cc723f1812e2b7e2f27ecc2c09321285d0af  genesis_window_check.py
        the whole file without checkpoints, the earlier windows as byte slices, the checkpoints read from bytes; nine checks
    d91d6482cee0763a5200a669852827b65b80ebbb0148dd0fb665631d48eb3fec  localheaders_full.bin
        965457 raw headers, heights 0 through 965456, from three full nodes, byte identical across them over 965455; not in the repository, prefixes above
    c7e8cca8b21e88e347a8fdedf7fe4378d86e8ab0079173b36e1fa7f1c2ca78c2  localheaders_full.manifest.json
        the three nodes by address and user agent, the two dropped, tips, chainwork, the one disclosure, the checkpoints that had to sit on the chain

Run offline and deterministically, from the directory holding these files:

    python3 stream_redteam.py ; python3 p2p_redteam.py ; python3 genesis_window_check.py localheaders_full.bin localheaders_full.manifest.json

The first ends in 8 / 8, the second in 15 / 15, the third in 9 / 9. Without the chain file, the
first two still run and the third reports what is missing. To build the file yourself, run
sync_headers_p2p.py with --from-genesis and --check-against localheaders_mainnet.manifest.json;
any three nodes that agree will hand you the same bytes up to height 965454, the prefix hashes
above will match, and slice_window in localheaders_stream.py will cut the earlier windows out
of your copy at the same hashes.

No trust in the operator is required: fetch the bytes, recompute the hash, check the anchor.
Once this addendum is anchored, a later correction is a new file that cites this one, never an
edit. Entry 26 said the third source was a fixture. Entry 27 made it a chain read through a
courier. Entry 28 removed the courier's name from the path. This entry removes the operator's
choice from the verdict. What is left between the operator and the chain is the work.
