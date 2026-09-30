# NENRIN coordinate-v1 addendum: time axis v3 (`nenrin-coordinate-v1-addendum-time-v3`)

This addendum cites NENRIN_COORDINATE_SPEC_v1 and supersedes the beacon check of its time
axis. It does not edit v1. A correction is a new file that cites the old, the same rule the
v1 manifest states, applied to the operator rather than carved around it.

Cited, anchored, unchanged:

    5be2b22e339d8b5c45a272325c49da189f10715b01683025ae903e83bf251df5  NENRIN_COORDINATE_SPEC_v1.md

## What v3 changes

freshness_v2 closed backdating with a public beacon and made currency fail-closed. Two seams
stayed open in v2. The cross-build with the founding witness made both concrete on a live
system (a single explorer, mempool.space, on his /verify-proof), so the operator closes them
on its own harness rather than only naming them to someone else.

Seam 1, single source. v2 checked the beacon against one source. One source the prover does
not own is still one point of failure: it can go dark, or lie, and decide the not-before
bound alone. v3 checks the beacon against two or more independent sources and requires a
quorum of agreement before it affirms. One reachable source below quorum cannot vouch for a
proof, because a lone source you cannot cross-check is trusted, not verified.

Seam 2, forged versus unverifiable. v2 collapsed two different failures into one bucket: a
height that provably does not exist on the chain, and a height that cannot be checked right
now because the source is down. Both came back not-authentic and both refused the proof,
which punishes an honest prover for an outage. v3 separates them:

  - a structurally impossible height is a bad coordinate. Fail closed, always, even if other
    sources are down. A provable lie does not become truer because a second source is
    unreachable.
  - a height no reachable source can affirm, and none structurally reject, is unverifiable
    now. The honest proof is not refused, but the not-before bound is not established, so it
    is not asserted not-backdated and not current. Named, retryable, never folded into valid.

Fail closed on the adversary, fail open on the outage. The same one rule as everywhere in the
ledger: the coordinate must come from a source the prover does not own, and no single such
source going dark may open or close the gate. The strongest form of the check reads a locally
synced header set and depends on no third-party API at all.

## Discrepancy record (v3.1, pre-anchor correction)

Found by: the founding witness, Federico Blanco Sanchez-Llanos, while porting v3 to his own
two-source production shape, through his independent second-opinion review. Reported to the
operator directly. Reproduced by the operator on the superseded bytes before any change.

Superseded bytes, kept on record (git commit e296dec5 holds them):

    d59c3385c17e3a8212a5df7d36d236479a3c122c45a069d91ae7301477cf532d  freshness_v3.py (v3, superseded)
    f17d3ee5d52f0cc0bb2a85f81be3eb2ef31a043fde18a2366e2e1409118c4a93  freshness_v3_redteam.py (v3, superseded)

The defect. v3 coupled the backdating check to the quorum. On a lone confirming read it set
not_backdated to None along with beacon_authentic, and only a hard False refuses, so a
genuinely backdated proof carrying a real historical block passed as indeterminate whenever
only one source was reachable. Reproduction on the superseded bytes: created_at long before
an authentic beacon, two of three sources down, one confirming; result unverifiable_now,
refused False, time_indeterminate True. A silent pass, the worst kind, because it leaves no
trace.

The correction. The two checks are decoupled. Corroboration (beacon_authentic) still needs a
quorum to affirm. The backdating check (not_backdated) runs against any confirmed read, even
a lone one below quorum, because a single independently fetched source is real data. The
asymmetry is deliberate: one honest witness is enough to refuse, corroboration is required to
vouch. A red-team case, backdated_lone_source, fails on the superseded bytes and passes on
the corrected ones. Residual, named: a lone corrupt source can cause a false refusal. That is
a recoverable fail-closed error, exposed when the other sources return, unlike the silent pass
it replaces.

## Seam 3, the veto, made explicit (v3.2, pre-anchor)

Prompted by the witness porting the tip discriminator to his live system and asking whether
v3 carries the near-tip residual. It does, and v3.2 makes the tip explicit so the residual is
shown and bounded rather than described.

Superseded bytes, kept on record (git commit 538fc75d holds them):

    e8300274a30f1fdf6d289243b2df8a73d6b9f0ef60e5ca94cfa2deb6643640b9  freshness_v3.py (v3.1, superseded)
    307429a92134206377e100dd723b4ce65c454d19e81093b58948218a4d48f701  freshness_v3_redteam.py (v3.1, superseded)

The veto, derived from data. v3.1 modeled a structural rejection as a fixture flag. v3.2
derives it: each source reports its own tip, and a height is structurally impossible, and
vetoes, only if it is malformed or beyond the HIGHEST tip among all reachable sources plus a
margin of six blocks, Bitcoin's own confirmation depth. A height a source lacks, just above
that source's tip (lag) or in a gap below it (fault), is evidence about that source and not
about the chain. It never vetoes; it degrades that source to cannot-confirm.

Why the highest reachable tip and not each source's own. Compared against its own tip, a
source lagging more than the margin behind the chain would veto a real block that another
source has already confirmed, and one honest source ten blocks behind would refuse the
current tip of the chain. One source's tip is never the whole set's tip. Two cases pin it:
stale_source_no_veto (ten behind, two confirm: authentic) and stale_source_lone_confirm (ten
behind, one confirms: unverifiable, not refused). The boundary is pinned exactly at tip plus
six (lag) and tip plus seven (structural) by margin_boundary_exact.

The near-tip residual, carried and bounded. Inside the margin, a fabricated height carrying a
random hash and an honest block no source has indexed yet look identical: both are
unverifiable_now. Nothing can break that tie at that moment, because nothing can confirm a
block that does not exist yet. The chain breaks it. When the height is mined, every honest
source returns the real hash: the fabricated claim mismatches and flips to forged, refused;
the honest claim matches and flips to authentic. The unknown bucket is a waiting room that
empties in the direction the truth points, within the confirmation depth. A forgery can never
be vouched for in the meantime, because no honest source will ever match a random hash, so
quorum stays structurally unreachable for it. advance_chain() models the chain moving, and
two cases test the convergence instead of asserting it: forged_near_tip_converges and
honest_fresh_converges.

Residual, named: with only one reachable tip, "beyond every reachable tip" rests on that one
source, so a stale lone source can cause a false refusal of a real far-ahead block.
Recoverable, exposed when the others return. Same class as the v3.1 residual.

## Seam 3, the tip itself under quorum (v3.3, pre-anchor)

Prompted by the witness's reviewer probing the v3.2 fix itself, not the honest case, and
finding that a compromised sibling can suppress a legitimate reject. Reproduced on the v3.2
bytes before any change: a ghost height far beyond the chain, all sources honest, refused;
one source inflating its reported tip, unverifiable, not refused.

Superseded bytes, kept on record (git commit 94651217 holds them):

    6ba29b273011e736dece2d9fe4eb2102c18f3355284b30daaf23eba5e895fabb  freshness_v3.py (v3.2, superseded)
    9e59daa94e668aa69108a001e88d36929cecf68c081ea29f879b6596add2842f  freshness_v3_redteam.py (v3.2, superseded)

The residual on the highest tip. Comparing against the highest reachable tip closed the
liveness hole and opened this one: a compromised or MITM'd source inflates its own tip to
cover a ghost height, and the honest sources' structural reject downgrades to unverifiable.
The liar cannot reach authentic, because quorum still needs the real hash at two sources and
a wrong hash loses to any mismatch. But refusing a fabricated height is the point of the
veto, and one liar could switch it off.

Why three sources change the shape. At two sources there is no third value between the
highest and lowest tip, so one chooses which single fault to tolerate: the highest tip and a
liar can suppress a reject, the lowest and a stale source can veto a real block. That is the
witness's irreducible two-source residual, and he named it rather than engineering it away,
correctly. At three sources the choice dissolves. The reference tip is the QUORUM-th highest
reachable tip, the highest height that at least a quorum of sources vouch for. A single liar
inflating its tip becomes the highest and is ignored. A single stale source becomes the
lowest and is ignored. One fault of either kind cannot move it. The same one rule, applied
to the tip: a tip reported by one source is one source.

Degraded mode, named. With exactly a quorum of sources reachable there is no slack, so the
reference tip falls back to the highest and the two-source residual returns for that call,
disclosed as tip_basis max_degraded with the residual on the record. With more than one
fault the single-fault model is out of scope: two stale sources of three cause a recoverable
false refusal of a fresh block, two liars can reach authentic. Neither is claimed closed;
both are pinned so the limit is visible. Four cases: liar_tip_refused_at_three (refused,
fails on the v3.2 bytes), liar_tip_at_two_named (unverifiable, residual disclosed, never
authentic), liar_match_never_authentic (one match is below quorum; against a real block the
fake hash is forged), two_stale_named (the documented false refusal).

Not changed on purpose: any mismatch still fails closed. Two honest matches could outvote one
wrong hash under the same quorum logic, but a contradiction between sources is evidence in
itself, and refusing exposes the liar where averaging would hide it. Held open for the
witness rather than decided alone.

These corrections are applied in place because v3 was pushed but not yet anchored. Once
anchored, any further correction is a new file that cites this one.

## Harness files pinned by this addendum

In fixed order, each with its SHA-256. Clone the repository, take the SHA-256 of each file,
compare it here, and check the time this addendum entered a Bitcoin block. No trust in the
operator is required: fetch the bytes, recompute the hash, check the anchor.

    276bc047838ee944bc078f519988d3688d58131318d4da916dad038622e22512  freshness_v3.py
        time v3.3 implementation: multi-source quorum beacon, forged vs unverifiable split, backdating
        check decoupled from quorum, veto derived from the quorum tip plus a six-block margin so neither a
        stale source nor an inflated tip can move it, near-tip residual bounded by chain convergence,
        degraded mode disclosed, real Ed25519
    1876bff826b598faa03ae8646a0eb8b9c5f010494f0d6322eea288757ac55e0a  freshness_v3_redteam.py
        the adversary: twenty-two checks. one honest witness refuses, a stale source cannot veto, one
        inflated tip cannot suppress a reject, a liar buys unknown at most and never authentic, the
        margin boundary is exact, near-tip claims converge with the chain, the two-source and two-fault
        limits are pinned, honest outage not punished. offline, deterministic.

Run offline and deterministically:

    python3 freshness_v3.py ; python3 freshness_v3_redteam.py

Once this addendum is anchored, the byte sequence of both files above is fixed at that Bitcoin
block height. A later correction is a new addendum that cites this one, never an edit. v3 gets
its own anchor and its own adversarial review before it is treated as current, the same rule
turned on the operator. The witness's review has already run three times and found one
defect and two residuals; all three records stay here.
