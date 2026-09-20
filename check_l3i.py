# ===========================================================================
# LEVEL 3i -- interval coverage, witnessed by an attestor the producer does
# not control.  (Corrigendum 1, finding EXT-002, Shahab K., 2026-09-13.)
#
# WHY. L3 declares coverage at a POINT (VLC-L3-3: before any event). L2 accounts
# for loss the producer survived to declare. Neither reaches the case where the
# PRODUCER is what failed: proofs/sentinel_interval.v proves
# producer_death_is_invisible -- a checker's verdict on a renumbered truncation
# is EQUAL to its verdict on the renumbered whole.
#
# L3i is the repair. The producer declares an interval; an attestor it cannot
# write to witnesses every tick of it. A producer that dies stops emitting
# ticks, and the absent ticks are the evidence its own silence cannot supply.
#
# CORRESPONDENCE TO THE PROOF. sentinel_interval.v parameterises as
# l3i_ok start k l = ticks_present start k l, covering start .. start+k.
# This checker reads first_tick and last_tick, so k = last - first. The
# translation is stated here because a differential will need it written down
# rather than assumed.
#   ticks_present  <-> the missing-tick scan below
#   missing_start_tick_fails <-> a missing first tick fails VLC-L3i-2
#   full_window_passes       <-> a complete window passes it
# ===========================================================================


def check_l3i(recs, ad, res):
    """Score interval coverage. Returns a summary dict, or None if L3i is not
    claimed by this adapter.

    Adapter shape, under ad["interval"]:
        mode                 "none" to decline the level
        declaration_class    record class carrying the interval declaration
        tick_class           record class carrying one witnessed tick
        first_field          field on the declaration: first tick index
        last_field           field on the declaration: last tick index
        interval_id_field    field naming the interval, on both record kinds
        tick_index_field     field on a tick: its index
        attestor_field       field naming the attestor, on both record kinds
        witness_field        field on a tick: the attestor's signature
        bound_field          field on a tick: the chain position it binds
        trusted_attestors    list the READER accepts; absent means the reader
                             has no list and independence is unestablished
    """
    iv = ad.get("interval")
    if not iv or iv.get("mode") == "none":
        # Not claimed is not failed. The corrigendum is explicit: "A deployment
        # without one gains nothing from it and should report L3i as
        # unestablished, not failed."
        _na(res, "VLC-L3i-1", "adapter declares no interval attestation; L3i "
                              "is not claimed by this producer")
        for rid in ("VLC-L3i-2", "VLC-L3i-3", "VLC-L3i-4"):
            _na(res, rid, "no interval declared")
        return None

    dc = iv.get("declaration_class")
    tc = iv.get("tick_class")
    decls = [r for r in recs if r.cls == dc]

    # ------------------------------------------------ L3i-1  the declaration
    if not decls:
        res.fail("VLC-L3i-1", f"adapter claims interval attestation but no {dc!r} "
                              f"record is in the delivered set")
        for rid in ("VLC-L3i-2", "VLC-L3i-3", "VLC-L3i-4"):
            _na(res, rid, "no interval declaration to score against")
        return None

    d0 = decls[0]
    ivid = _dig(d0, iv.get("interval_id_field"))
    first = _int(_dig(d0, iv.get("first_field")))
    last = _int(_dig(d0, iv.get("last_field")))

    if ivid is None or first is None or last is None:
        res.fail("VLC-L3i-1", "interval declaration lacks an identifier or integer "
                              "first/last tick indices")
        for rid in ("VLC-L3i-2", "VLC-L3i-3", "VLC-L3i-4"):
            _na(res, rid, "interval declaration is malformed")
        return None

    if last < first:
        res.fail("VLC-L3i-1", f"interval runs backwards: {first}..{last}")
        for rid in ("VLC-L3i-2", "VLC-L3i-3", "VLC-L3i-4"):
            _na(res, rid, "interval declaration is malformed")
        return None

    dup = [r for r in decls[1:] if _dig(r, iv.get("interval_id_field")) == ivid]
    if dup:
        res.fail("VLC-L3i-1", f"interval {ivid!r} is declared more than once: which "
                              f"bounds apply is ambiguous")
        for rid in ("VLC-L3i-2", "VLC-L3i-3", "VLC-L3i-4"):
            _na(res, rid, "interval declaration is ambiguous")
        return None

    expected = last - first + 1
    res.ok("VLC-L3i-1", f"interval {ivid!r} declared over ticks {first}..{last} "
                        f"({expected} tick{'s' if expected != 1 else ''})")

    # ------------------------------------------- L3i-3  each witness is bound
    # Structural: recomputed from the log alone. Does a tick name this interval,
    # sit inside the declared bounds, appear once, and bind a chain position
    # that occurs here? None of that requires the attestor to be honest.
    ticks = [r for r in recs if r.cls == tc]
    mine, foreign = [], []
    for t in ticks:
        (mine if _dig(t, iv.get("interval_id_field")) == ivid else foreign).append(t)

    heads = {r.hash for r in recs if r.hash}
    seen, problems = {}, []
    for t in mine:
        n = _int(_dig(t, iv.get("tick_index_field")))
        if n is None:
            problems.append("a tick carries no integer index")
            continue
        if n < first or n > last:
            problems.append(f"tick {n} lies outside the declared interval")
            continue
        if n in seen:
            problems.append(f"tick {n} appears more than once")
            continue
        if not t.hash:
            problems.append(f"tick {n} is not integrity-bound")
            continue
        bf = iv.get("bound_field")
        if bf:
            b = _dig(t, bf)
            if b is None:
                # An unbound witness is liftable: it names no position, so it
                # verifies equally in any log. Annex J.4. Found by the fuzz
                # loop, which passed 136 incomplete windows before this branch
                # existed -- the earlier code accepted a missing binding.
                problems.append(f"tick {n} binds no position: an unbound witness "
                                f"can be lifted from any other log")
                continue
            if b not in heads:
                problems.append(f"tick {n} binds a position absent from this log: "
                                f"a witness lifted from elsewhere")
                continue
        if iv.get("witness_field") and _dig(t, iv.get("witness_field")) is None:
            problems.append(f"tick {n} carries no witness")
            continue
        seen[n] = t

    if foreign:
        problems.append(f"{len(foreign)} tick(s) name a different interval and were "
                        f"not counted toward this one")
    if problems:
        res.fail("VLC-L3i-3", "; ".join(problems[:4]))
    else:
        res.ok("VLC-L3i-3", f"{len(seen)} witness(es) bound to {ivid!r} and to a "
                            f"position in this log")

    # -------------------------------------------- L3i-4  attestor independence
    # ATTESTED, always. The reader relays that this attestor is independent of
    # the producer; nothing in the log establishes it.
    trusted = iv.get("trusted_attestors")
    declared = _dig(d0, iv.get("attestor_field"))
    if trusted is None:
        _na(res, "VLC-L3i-4", "the reader supplied no list of accepted attestors: "
                              "independence cannot be established from the log")
    else:
        named = {_dig(t, iv.get("attestor_field")) for t in mine}
        named.discard(None)
        if declared is None:
            res.fail("VLC-L3i-4", "the declaration names no attestor")
        elif declared not in trusted:
            res.fail("VLC-L3i-4", f"the declaration names attestor {declared!r}, "
                                  f"which the reader does not accept")
        elif named - {declared}:
            res.fail("VLC-L3i-4", f"tick(s) name an attestor other than the declared "
                                  f"{declared!r}: {sorted(named - {declared})}")
        else:
            res.ok("VLC-L3i-4", f"attestor {declared!r} accepted by the reader "
                                f"(attested: independence is relayed, not recomputed)")

    # ------------------------------------------------ L3i-2  every tick present
    # ATTESTED. This is the requirement the proof speaks to.
    missing = [n for n in range(first, last + 1) if n not in seen]
    if missing:
        head = missing[0]
        res.fail("VLC-L3i-2",
                 f"{len(missing)} of {expected} tick(s) absent, first at {head}"
                 f"{' (the declared start)' if head == first else ''}: the interval "
                 f"is unwitnessed there, and a producer that stopped is "
                 f"indistinguishable from one that never started")
    else:
        res.ok("VLC-L3i-2", f"all {expected} tick(s) of {ivid!r} present and witnessed "
                            f"(attested: the attestor's honesty is relayed)")

    return {"interval": ivid, "first": first, "last": last,
            "expected": expected, "present": len(seen), "missing": len(missing)}


# --------------------------------------------------------------------- helpers
def _int(v):
    if isinstance(v, bool) or not isinstance(v, int):
        try:
            return int(v)
        except (TypeError, ValueError):
            return None
    return v


def _na(res, rid, why):
    """Report a requirement as unestablished. The corrigendum requires this be
    distinct from failure; if the result collector has no such channel, fall
    back to ok() with the reason, never fail(), so an honest absence is never
    scored as a defect."""
    fn = getattr(res, "unestablished", None) or getattr(res, "na", None)
    if fn:
        fn(rid, why)
    else:
        res.ok(rid, f"unestablished: {why}")
