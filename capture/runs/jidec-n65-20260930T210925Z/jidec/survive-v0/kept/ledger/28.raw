# NENRIN coordinate-v1 addendum: localheaders v2, the courier is the network (`nenrin-coordinate-v1-addendum-localheaders-v2`)

This addendum cites the localheaders v1 addendum and, through it, the sources addendum, the
time axis v3 addendum and the v1 spec. It edits none of them and changes no file they pinned.
It closes the first limit v1 named: that the courier at sync time was still an HTTP block
explorer, a third party in the path even though nothing rested on its word. The courier is
now the Bitcoin peer to peer network itself. Full nodes were asked for headers with
getheaders, answered with headers, and every header was validated by the same seven checks
before a byte was written. There is no website in the path at any time.

Cited, anchored, unchanged:

    5be2b22e339d8b5c45a272325c49da189f10715b01683025ae903e83bf251df5  NENRIN_COORDINATE_SPEC_v1.md (JIDEC entry 22)
    447bcf4f38cd8099683ccd396467609438aa47399e9bb9b75d7c425900147611  NENRIN_COORDINATE_v1_ADDENDUM_time_v3.md (JIDEC entry 24)
    04908cd53c006ea0ebd24535ab8d3c884317cd2aeeff7a24f136c8a459cf50dc  NENRIN_COORDINATE_v1_ADDENDUM_sources_v1.md (JIDEC entry 26)
    f5512ea3bb476e3356f96979c9a922e102f35d893659d76ad151fed5450f6162  NENRIN_COORDINATE_v1_ADDENDUM_localheaders_v1.md (JIDEC entry 27)
    276bc047838ee944bc078f519988d3688d58131318d4da916dad038622e22512  freshness_v3.py (pinned by entry 24, not modified)
    d0dba8267b6deeb72552c18b982aec126e7eb6948bad93ddbf8723464c6c203e  localheaders.py (pinned by entry 27, not modified)
    b7c8ddefff198c865f3e27ec86d6d02d26ff4778158e4380f66d2c97ebaed367  localheaders_mainnet.bin (pinned by entry 27, the explorer built window)

## 1. What ran

On 2026-09-04 the operator ran sync_headers_p2p.py from the manifest of the explorer built
window, so the request to the network was for the same heights, 961632 onward. It resolved
182 candidate addresses from eight public DNS seeds, connected to the first three that
completed a handshake, and pulled the window from each independently:

    45.190.208.56:8333   /Satoshi:31.0.0/   3823 headers   tip 965454
    104.1.125.109:8333   /Satoshi:25.0.0/   3822 headers   tip 965453
    24.105.161.11:8333   /Satoshi:31.0.0/   3823 headers   tip 965454

Each peer's run was validated cumulatively after every headers message: linkage, proof of
work, the retarget at 963648, median time past, future drift against the clock, and the
checkpoints pinned by entry 27. The three runs are byte identical over the 3822 headers they
all cover. The client then compared the longest run against the explorer built file pinned by
entry 27 and found them byte identical over all 3820 headers that file holds: the SHA-256 of
the first 305600 bytes from the network equals b7c8ddef...aed367, the value entry 27 pinned.

That makes five couriers for one byte sequence: two HTTP explorers, three full nodes reached
over the wire protocol, 3820 headers, no disagreement anywhere. The mempool.space run had one
header beyond the blockstream run, at 965452; the network has it too, with the same hash.

One node was one block behind the other two. That is lag. It was recorded as a lower tip, it
did not veto, and the longer agreeing run was written. The rule freshness_v3 applies to a
stale source, entry 24's v3.3, held at the courier level without being written twice.

Block 965447, the block that confirmed entry 26, is inside this set, at the same hash and the
same nTime the v1 addendum reported from the explorer built file. The chain the network handed
over contains the anchor of the record that admitted this source was a fixture.

## 2. The courier, and its adversary

sync_headers_p2p.py speaks the wire protocol directly: version and verack, pong for ping,
getheaders with a locator taken from the manifest, headers messages of up to two thousand,
magic and checksum enforced on every frame, a hard cap on payload size, and no services
advertised so no node sends it anything but what it asked for. A peer that serves one header
failing validation is dropped by name with the reason. Peers that finish must agree byte for
byte over the window they all cover, or the sync refuses and names them; a contradiction
between sources is evidence, and refusing exposes it where choosing would hide it. Nothing is
written on a refusal, and what is written is read back through localheaders.load_source as
the last step.

p2p_redteam.py runs fake peers on loopback that speak the same protocol with a test magic,
serving chains mined by the v1 red team at test difficulty, and points the real client at
them. Fourteen checks, all green, identical on the operator's machine and in a clean
container: two honest peers agree and the bytes written equal the mined chain; a peer serving
one header that fails proof of work is dropped and, below the peer minimum, nothing is written;
with the minimum lowered to one the honest peer's bytes are written and the dropped peer is
recorded in the manifest; a valid fork dies at the checkpoint; a tampered checksum, a wrong
magic, an oversized length, a nonzero transaction count and a stalled peer are each dropped
with the reason; two valid chains that no checkpoint separates make the client refuse and name
both peers; a stale peer is lag and the longer agreeing run is written; a ping in the middle
of getheaders is answered; a peer that does not know the locator returns nothing and is
dropped; the compare flag records byte identity against a reference file.

## 3. Limits, named

  - DNS seeds are a third party for discovery and for nothing else. They choose which nodes
    the client meets; they never see or supply a header. The --peer flag bypasses them.
  - The connection is plaintext. The client does not implement the encrypted transport, so
    an adversary on the network path could substitute a node. What such an adversary can
    serve is bounded by proof of work, by the requirement that independent peers agree byte
    for byte, and by the operator's checkpoints. A sybil set of nodes is bounded the same
    three ways. Named, not closed.
  - Only IPv4 addresses are tried. A node reachable only over IPv6 or Tor is not a peer here.
  - The window still starts at 961632, so the retarget boundary there stays unverified from
    inside the file, exactly as v1 said. The boundary at 963648 is verified.
  - The explorer snapshots remain in the quorum as each explorer's word, and whether the two
    explorers share an implementation is still not audited. What changed in v1 and is now
    complete in v2 is that the third source depends on no explorer for its bytes and no
    explorer for its delivery.

## Files pinned by this addendum

    9b600f9b7e6ab112be8fd3e84fc4d04cd35381cc1448fe7c1abee95b49c237f9  sync_headers_p2p.py
        the courier that is not a website: wire protocol client, cumulative validation, cross peer byte agreement, writes nothing on refusal
    30bfe3eb07db8cb59e771d41bd786dd8d4ec2ec6bbe3bba42a4db76dd0bcdb7a  p2p_redteam.py
        fake peers on loopback speaking the real protocol, fourteen checks, deterministic
    888151bb1b8b7566132a4e5d9385e34ee3db06651263ce77d6872a2a7fa9f194  localheaders_p2p.bin
        3823 raw headers 961632..965454 from three full nodes, byte identical across them, validated; first 305600 bytes equal localheaders_mainnet.bin
    1be415fd42a591c437557cf62587d7400ee99408521a38c2e71292468b471a74  localheaders_p2p.manifest.json
        the three peers by address and user agent, their tips, the comparison result, the checkpoints including the new tip

Run offline and deterministically, from the directory holding these files:

    python3 p2p_redteam.py ; python3 localheaders.py localheaders_p2p.bin localheaders_p2p.manifest.json

The first ends in 14 / 14. The second prints valid, tip 965454, retarget verified at 963648,
checkpoints matched at 961632, 963648, 965451 and 965454. To pull the window from the network
yourself, run sync_headers_p2p.py with --from-manifest localheaders_mainnet.manifest.json and
--compare localheaders_mainnet.bin; any three nodes that agree will hand you the same 3820
headers, and the compare line will say byte identical.

No trust in the operator is required: fetch the bytes, recompute the hash, check the anchor.
Once this addendum is anchored, a later correction is a new file that cites this one, never an
edit. Entry 26 said the third source was a fixture. Entry 27 made it a chain read through a
courier. This entry removes the courier's name from the path. What is left between the
operator and the chain is the chain.
