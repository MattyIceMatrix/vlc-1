# NENRIN coordinate-v1 addendum: sources and the quorum rule (`nenrin-coordinate-v1-addendum-sources-v1`)

This addendum cites the time axis v3 addendum and the founding witness's state record. It does
not edit either one, and it changes no code. The harness bytes pinned by entry 24 are unchanged
and this file pins none of its own. What it adds is a decision that was left open in public, and
two limits that a quorum of sources cannot close no matter how the rule is written.

Cited, anchored, unchanged:

    5be2b22e339d8b5c45a272325c49da189f10715b01683025ae903e83bf251df5  NENRIN_COORDINATE_SPEC_v1.md (JIDEC entry 22)
    447bcf4f38cd8099683ccd396467609438aa47399e9bb9b75d7c425900147611  NENRIN_COORDINATE_v1_ADDENDUM_time_v3.md (JIDEC entry 24)
    950edfee4e57835f7bdf7f22e07c54392fad692ad88f5c89aacfee5cdf8a64b4  NENRIN_WITNESS_STATE_0001.md (JIDEC entry 25)

Entry 25 says of the operator's choice of rule: recorded in the addendum that cites entry 24,
not here. This is that file.

## 1. Operator independence is what a quorum buys. Implementation independence is not.

The one rule of coordinate integrity is that the coordinate comes from a source the prover does
not own. A quorum of such sources buys independence of ownership: different operators, different
hosts, different incentives, different failures of goodwill. It does not buy independence of
implementation. Two sources running the same codebase are one bug away from two simultaneous
faults, and the single fault model that entry 24 rests on does not hold there.

The founding witness found this on his own set first. Two of his three live sources,
mempool.space and mempool.emzy.de, run the same explorer codebase. He named it in his source
list beside the sources themselves rather than engineering around it, which is the correct move:
a limit written next to the thing it limits is worth more than a limit fixed quietly.

The operator's set is `mempool`, `blockstream` and `localheaders`, with QUORUM 2. The honest
statement about it is narrower than three source names suggest. The operator has not audited the
codebase lineage of the two public explorers, so it does not claim they are independent
implementations; it claims only that they are independently operated. The third source,
`localheaders`, is the one that would be a different implementation by construction, reading a
locally synced header set and depending on no third party API at all, and **it is a fixture in
the harness and is not wired to a real header store.** Entry 24 already names that shape as the
strongest form of the check. It is still the strongest form, and it is still not built.

So on this axis the operator is not ahead of the witness and says so. Three names in `SOURCES`
do not make three implementations, and this file exists partly so that nobody, including the
operator, can later read the count as if they did.

The fix here is not a rule. It is a source. Wiring `localheaders` to a real header store is the
single piece of work that moves this section and section 3 at the same time, and it is the next
thing the operator owes on this axis.

## 2. Corroboration from outside the quorum is evidence of a different kind, not a vote.

An OpenTimestamps anchor, or a second protocol reading the same chain, is sometimes offered as
another source to count toward a quorum. It is not, and folding it in would be a category error.
An anchor binds bytes to a block. A source reports what a block contains. They answer different
questions, and a strong proof of the first spent as a weak vote about the second buys confidence
that was never measured.

So corroboration from outside the quorum sits beside the quorum and never inside it. It cannot
lift a mismatch, and it cannot complete a quorum that the sources did not reach on their own.
Any mismatch between sources still fails closed, exactly as entry 24 states, because a
contradiction between sources is evidence in itself and refusing exposes the liar where
averaging would hide it.

Recorded on both sides. Built on neither. When either side builds it, it will be a new record,
not a reinterpretation of this one.

## 3. The rule for authentic: a fork, chosen, with the number written next to it.

Entry 24 fixed the quorum at two of three and left the choice of rule described rather than
argued. The witness closed the argument, so it is settled here in the open.

**Two of three, the operator's choice.** Tolerates one source down or lying. Opens to two
colluding sources.

**Full unanimity, the witness's choice.** Tolerates two colluding sources. Stops affirming the
moment one honest source is unreachable.

**A dissent rule, the apparent third way, rejected by both sides.** It sits between the two by
treating an explicit contradiction differently from a silence, and it gives up the single outage
guarantee without closing what it claims to close.

The reason there is no third rule that dodges both costs is that the two states are
indistinguishable from where the verifier stands. "One honest source has not confirmed yet" and
"two colluders plus one honest source" look identical until the chain moves. Every rule from two
of three up to unanimity is a point on that one line, and all any of them chooses is what counts
as the third source not having spoken: down, lagging beyond the margin, or lagging at all. None
of them spends neither coin.

**The window, and its number.** Found by the founding witness, Federico Blanco Sanchez-Llanos,
in his analysis of the dissent rule, and recorded here with his name on it. `MARGIN_BLOCKS` is
6 on the operator's side, Bitcoin's own confirmation depth, roughly an hour at the average block
time. Under a dissent rule, two colluding sources matching a fabricated height inside that
margin, with the honest third still below it, would hold `authentic` for up to those six blocks,
and then flip to `forged` when the real block lands with a different hash. Unanimity has no such
window and pays for it in liveness.

**What that window can actually buy an attacker, stated so the choice is not flattered.** It
cannot help backdating: any real historical block would serve a backdater better and costs
nothing. It cannot help postdating: a future creation time fails the clock check independently
of the beacon. It buys a wrong `current` for under an hour, on a proof that then turns `forged`
on the record rather than being erased, and currency is re measured on a cadence, so the verdict
lives until the earlier of the next measurement and the real block. The operator takes that over
one explorer outage silencing `authentic` across the board. That is a preference about which
failure is worse in this use, not a proof that the other choice is wrong. The witness's set and
the witness's use make unanimity the right answer for him, and both rules are on the record with
their prices beside them.

**Held, not built.** A strict mode, unanimity behind a flag, default off, with the mode disclosed
in the verdict so a reader can see which rule produced it, is the shape a future change would
take. The operator is not building it now, because building a second rule before anyone has shown
an environment where two colluding sources are realistic would be adding a switch to answer a
question nobody has asked. If the witness, or anyone else, brings that environment with a concrete
case, the flag gets built and this file gets a successor that cites it.

## 4. What this addendum does not do

It does not change `freshness_v3.py` or `freshness_v3_redteam.py`. The bytes pinned by entry 24
are the current bytes, and the twenty two red team checks that back them are unchanged. It pins
no new files, because nothing new was written.

It does not close the shared implementation axis, the outside corroboration axis, or the
collusion path. It names all three, gives the number for the one that has a number, and says
which piece of work moves them.

It does not settle which rule is correct in general. It settles which rule this operator runs and
what that costs, next to what the witness runs and what that costs.

## How to check this

Clone the repository, take the SHA-256 of the three files cited at the top, compare them to the
values written here, and check the time this addendum entered a Bitcoin block. The claims in
sections 1 and 3 about the harness are checkable in the same repository: `SOURCES`, `QUORUM` and
`MARGIN_BLOCKS` are named constants in `freshness_v3.py`, and the fixture nature of
`localheaders` is visible in the same file.

    python3 freshness_v3.py ; python3 freshness_v3_redteam.py

No trust in the operator is required: fetch the bytes, recompute the hash, check the anchor.
Once this addendum is anchored, a later correction is a new file that cites this one, never an
edit.
