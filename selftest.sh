#!/bin/sh
# ===========================================================================
# VLC-1 conformance-suite self-test.
#
# A conformance checker that only ever says PASS is a rubber stamp, and one
# that only ever says FAIL is useless.  This asserts BOTH directions:
#
#   positive  every worked example demonstrates EXACTLY its level -- no more
#             (the checker is not generous) and no less (not pedantic);
#   negative  every Annex A mutation LOWERS the level -- the checker cannot be
#             fooled by a log that has been edited after delivery;
#   lattice   two logs of the SAME session, differing only in whether the
#             observation surface was written down, separate at L2/L3;
#   not-rigged the author's own captured journal is reported at the level it
#             actually demonstrates, which today is not the top one.
#
#   ./selftest.sh        exit 0 iff every assertion holds
# ===========================================================================
set -e
cd "$(dirname "$0")"
C="python3 ./conformance.py"
FAIL=0
ok()   { printf '  ok    %s\n' "$*"; }
bad()  { printf '  FAIL  %s\n' "$*"; FAIL=1; }
# A known failure, disclosed and explained. Printed every run so it is never
# silent; does not turn the suite red. If a case marked this way starts
# passing, that is reported as a FAIL so the marker is removed rather than
# left to rot. Any failure not covered by a marker still turns the suite red.
XFAIL=0
xfail() { printf '  xfail %s\n' "$*"; XFAIL=$((XFAIL + 1)); }
req()  { python3 ./conformance.py --log "$1" --adapter "$2" --json 2>/dev/null \
           | python3 -c "import json,sys;print(json.load(sys.stdin)['requirements']['$3']['status'])" \
           | tr -d '\r'; }
hr()   { printf '%s\n' "---------------------------------------------------------------"; }

level() {   # level <log> <adapter>   -> ATTESTED level
	$C --log "$1" --adapter "$2" --json 2>/dev/null | python3 -c \
	  'import json,sys; print(json.load(sys.stdin)["attested_level"])'
}
slevel() {  # slevel <log> <adapter>  -> STRUCTURAL level
	$C --log "$1" --adapter "$2" --json 2>/dev/null | python3 -c \
	  'import json,sys; print(json.load(sys.stdin)["structural_level"])'
}
req() {     # req <log> <adapter> <requirement-id>  -> PASS or FAIL
	$C --log "$1" --adapter "$2" --json 2>/dev/null | python3 -c \
	  "import json,sys; print(json.load(sys.stdin)['requirements'].get('$3',{}).get('status','ABSENT'))"
}
level_m() { # level_m <log> <adapter> <mutation>
	$C --log "$1" --adapter "$2" --mutate "$3" --json 2>/dev/null | python3 -c \
	  'import json,sys; print(json.load(sys.stdin)["level_demonstrated"])'
}

hr; echo "1. POSITIVE -- each worked example sits exactly on its rung"
for row in \
	"examples/L0-plain.jsonl          adapters/plain-jsonl.json            0" \
	"examples/L1-hashchain.jsonl      adapters/generic-appjsonl.json       1" \
	"examples/L2-accounted.jsonl      adapters/generic-appjsonl.json       2" \
	"examples/L2-looks-complete.jsonl adapters/generic-appjsonl.json       2" \
	"examples/L3-coverage.jsonl       adapters/generic-appjsonl.json       3" \
	"examples/L4-policybound.jsonl    adapters/generic-appjsonl-policy.json 4"
do
	set -- $row
	got=$(level "$1" "$2")
	[ "$got" = "$3" ] && ok "$(basename $1) -> L$got" \
	                  || bad "$(basename $1) -> L$got, expected L$3"
done

hr; echo "2. NEGATIVE -- every Annex A mutation must lower the level"
L4=examples/L4-policybound.jsonl
A=adapters/generic-appjsonl-policy.json
base=$(level $L4 $A)
[ "$base" = "4" ] || bad "baseline is L$base, the negative controls below are meaningless"
for m in flip-byte drop-interior truncate-tail drop-loss-decl drop-coverage rebase-policy; do
	got=$(level_m $L4 $A $m)
	if [ "$got" -lt "$base" ]; then ok "A.x $m -> L$got  (was L$base)"
	else bad "A.x $m -> L$got: the checker did not notice"; fi
done

hr; echo "2b. MECHANISMS -- every chain mechanism and produced-count kind, not only the one the examples use"
# Section 2 runs its mutations against one adapter. These run the ones that
# apply against the observer prefix chain, and exercise the chain mechanism and
# produced-count kinds no worked example reaches. Writing them found EXT-013.
KW=examples/reference-impl/kernel-witness-L5.jsonl
if [ -f "$KW" ]; then
  # EXT-022: the observer's end marker is not chained, so on the log alone the
  # journal is L0 and every mutation would "lower" it trivially. The baseline is
  # taken with the journal's own final head supplied as the independent anchor
  # (standing in for a head published elsewhere), which puts it at L1, so each
  # mutation has to be caught by the chain to count.
  KH=$(tail -n 1 "$KW" | python3 -c 'import json,sys;print(json.load(sys.stdin)["h"])' | tr -d '\r')
  kb=$($C --log "$KW" --adapter adapters/observer.json --expect-head "$KH" --json 2>/dev/null \
       | python3 -c 'import json,sys;print(json.load(sys.stdin)["structural_level"])' | tr -d '\r')
  [ "$kb" -ge 1 ] || bad "observer baseline with its head anchored is L$kb; the mutation controls below would be vacuous"
  for m in flip-byte drop-interior truncate-tail drop-coverage; do
    got=$($C --log "$KW" --adapter adapters/observer.json --expect-head "$KH" --mutate $m --json 2>/dev/null \
          | python3 -c 'import json,sys;print(json.load(sys.stdin)["structural_level"])' | tr -d '\r')
    if [ "$got" -lt "$kb" ]; then ok "observer prefix chain, head anchored: $m -> L$got (was L$kb)"
    else bad "observer prefix chain: $m -> L$got, not lowered from L$kb"; fi
  done
fi
MC=$(mktemp -d)
python3 examples/mechanism_cases.py "$MC" | tr -d '\r' > "$MC/cases.txt"
while read -r LOG AD REQ EXPECT MODE; do
  GOT=$($C --log "$LOG" --adapter "$AD" --json 2>/dev/null \
        | python3 -c "import json,sys;print(json.load(sys.stdin)['requirements']['$REQ']['status'])" \
        | tr -d '\r')
  N=$(basename "$LOG" .jsonl)
  if [ "$MODE" = "xfail" ]; then
    if [ "$GOT" = "$EXPECT" ]; then bad "$N: now detected ($REQ $GOT); remove its expected-failure marker"
    else xfail "$N: $REQ $GOT, should be $EXPECT -- disclosed in FINDINGS-EXTERNAL.md"; fi
  elif [ "$GOT" = "$EXPECT" ]; then ok "$N: $REQ $GOT"
  else bad "$N: expected $REQ $EXPECT, got $GOT"; fi
done < "$MC/cases.txt"
rm -rf "$MC"

hr; echo "3. NEGATIVE -- a checker that always fails is also broken"
# Re-run the untouched log after the mutations: it must still reach L4.
got=$(level $L4 $A)
[ "$got" = "4" ] && ok "untouched log still L4 after mutation runs" \
                 || bad "untouched log now L$got: the checker is not stateless"

hr; echo "3b. INDEPENDENCE -- an in-process producer cannot witness itself"
# L4 is the ceiling for a log the audited process writes. Not a slight on the
# producer: a fact about authorship, proved as
# no_check_on_the_self_report_can_see_substitution.
app=$(level examples/L4-policybound.jsonl adapters/generic-appjsonl-policy.json)
[ "$app" = "4" ] && ok "app-layer self-report tops out at L$app" \
                 || bad "app-layer self-report reached L$app"

hr; echo "3c. TRUST BOUNDARY -- a generous adapter must not move the structural level"
# The checker reports two numbers. The attested one includes what the producer
# asserts; the structural one is recomputed from the log. If a fabricated
# adapter could raise the structural number, the distinction would be theatre.
TB="$(mktemp -d)"
trap 'rm -rf "$TB"' EXIT
python3 - "$TB" <<'PYE'
import json, sys
out = sys.argv[1]
a = json.load(open('adapters/generic-appjsonl-policy.json'))
# every attested property claimed as strongly as the schema allows
a['name'] = 'fabricated-optimistic'
a['integrity']['documented'] = True
a['integrity']['primitive_documented'] = True
a['loss']['overflow_behaviour'] = 'block'
a['coverage']['bidirectional_test'] = {'exists': True, 'negative_control': True,
                                       'ref': 'trust me'}
a['policy'] = {'mode': 'chain_root', 'digest_field': 'policy_digest',
               'change_class': 'POLICY',
               'replay': {'deterministic': True, 'reference': 'trust me'}}
a['independence'] = {'mode': 'kernel', 'audited_process_can_write_records': False,
                     'boundary_statement': 'trust me',
                     'reconciliation': {'bidirectional': True, 'scope_declared': True}}
json.dump(a, open(out + '/optimistic.json', 'w'), indent=2)
# and the same adapter with the two documentation declarations REMOVED
b = json.load(open('adapters/generic-appjsonl.json'))
b['name'] = 'silent-on-documentation'
b['integrity'].pop('documented', None)
b['integrity'].pop('primitive_documented', None)
json.dump(b, open(out + '/silent.json', 'w'), indent=2)
PYE
L4=examples/L4-policybound.jsonl
base_s=$(slevel $L4 adapters/generic-appjsonl-policy.json)
base_a=$(level  $L4 adapters/generic-appjsonl-policy.json)
opt_s=$(slevel  $L4 "$TB/optimistic.json")
opt_a=$(level   $L4 "$TB/optimistic.json")
if [ "$opt_s" = "$base_s" ] && [ "$opt_a" -gt "$base_a" ]; then
	ok "fabricated independence: attested L$base_a -> L$opt_a, structural unmoved at L$opt_s"
	ok "the number an adapter can inflate is labelled as the one an adapter can inflate"
else
	bad "expected structural to stay at L$base_s and attested to rise above L$base_a;"
	bad "got structural L$opt_s, attested L$opt_a"
fi

# and silence is not a declaration: the two documentation requirements used to
# pass when the adapter said nothing at all. That was a defect, not a policy.
d1=$(req examples/L1-hashchain.jsonl "$TB/silent.json" VLC-L1-2)
d2=$(req examples/L1-hashchain.jsonl "$TB/silent.json" VLC-L1-4)
if [ "$d1" = "FAIL" ] && [ "$d2" = "FAIL" ]; then
	ok "an adapter silent on documentation fails VLC-L1-2 and VLC-L1-4"
else
	bad "silence still passes: VLC-L1-2=$d1 VLC-L1-4=$d2"
fi

hr; echo "4. LATTICE -- the same session, separated only by a coverage record"
a=$(level examples/L2-looks-complete.jsonl adapters/generic-appjsonl.json)
b=$(level examples/L3-coverage.jsonl       adapters/generic-appjsonl.json)
if [ "$a" = "2" ] && [ "$b" = "3" ]; then
	ok "L2-looks-complete=L$a  L3-coverage=L$b"
	ok "both logs: chain valid, identity closes, zero declared loss"
	ok "one of them was missing 58 inferences and only the other can say so"
else
	bad "separation failed: $a / $b"
fi

hr; echo "5. NOT RIGGED -- the author's own journals, judged by the same rules"
# The suite's first run on 2026-09-12 reported this project's captured journal at
# L2, failing VLC-L3-1(d): the COVERAGE record listed nine hooked syscalls and
# never said how it knew the list was exhaustive.  sensor/govern.c was fixed the
# same day.  BOTH captures are kept, and both assertions are load-bearing:
#
#   the PRE-FIX capture must still come out at L2 -- if a later change makes it
#   pass, the checker has been loosened, not the product improved;
#   the POST-FIX capture must come out at L4 on a live kernel -- claiming L4
#   without a capture that demonstrates it is exactly what this spec forbids.
#
# Corrigendum 2 (EXT-003) moved the pre-fix capture from L2 to L1: its produced
# count includes framing records, so the identity no longer closes. It is a
# historical capture and cannot be regenerated, so it is re-pinned rather than
# marked as an expected failure. What it was kept for is unchanged: VLC-L3-1d
# must still FAIL on it. If that ever passes, the checker has been loosened.
#
# Corrigendum 6 (EXT-022) moves every journal below to L0 on the log alone. The
# observer's HEAD record names the chain head but is not itself chained, so the
# last records of a journal can be dropped and HEAD edited to match with no hash
# recomputed -- the checker now refuses VLC-L1-3 without an independently held
# head, and refuses the produced count (read from HEAD) in every case. These are
# the levels the captures actually demonstrate. They are pinned, so a change
# that restores the old numbers without binding the end marker turns this red.
PRE=examples/reference-impl/pre-basis-L2.jsonl
if [ -f "$PRE" ]; then
	got=$(level "$PRE" adapters/observer-legacy.json)
	l13=$(req "$PRE" adapters/observer-legacy.json VLC-L1-3)
	l31d=$(req "$PRE" adapters/observer-legacy.json VLC-L3-1d)
	if [ "$got" = "0" ] && [ "$l13" = "FAIL" ] && [ "$l31d" = "FAIL" ]; then
		ok "pre-fix capture -> L0: its end marker is unbound (EXT-022), and VLC-L3-1d still fails (the gap it was kept to show)"
	else
		bad "pre-fix capture -> L$got, VLC-L1-3 $l13, VLC-L3-1d $l31d; expected L0, FAIL, FAIL"
	fi
else
	bad "pre-fix capture missing: the not-rigged control cannot run"
fi
for j in examples/reference-impl/pre-EXT-022/kernel-witness-L5.jsonl examples/reference-impl/pre-EXT-022/kernel-witness-with-loss-L5.jsonl; do
	[ -f "$j" ] || continue
	got=$(level  "$j" adapters/observer-legacy.json)
	sgot=$(slevel "$j" adapters/observer-legacy.json)
	JH=$(tail -n 1 "$j" | python3 -c 'import json,sys;print(json.load(sys.stdin)["h"])' | tr -d '\r')
	A=$($C --log "$j" --adapter adapters/observer-legacy.json --expect-head "$JH" --json 2>/dev/null | python3 -c \
	  'import json,sys;r=json.load(sys.stdin);q=r["requirements"];print(r["structural_level"],r["attested_level"],q["VLC-L1-3"]["status"],q["VLC-L2-1"]["status"])' | tr -d '\r')
	if [ "$sgot" = "0" ] && [ "$got" = "0" ] && [ "$A" = "1 1 PASS FAIL" ]; then
		ok "pre-EXT-022/$(basename $j) -> L0 on the log alone; L1 with its head anchored, blocked at VLC-L2-1 (count on an unbound marker)"
	else
		bad "$(basename $j) -> structural L$sgot, attested L$got, anchored [$A]; expected 0, 0, [1 1 PASS FAIL]"
	fi
done
# EXT-022, closed in the sensor (octa-sentinel 269b176): HEAD is chained and
# names the head it closes. Re-captured 2026-09-29 on live eBPF tracepoints.
for j in examples/reference-impl/kernel-witness-L5.jsonl examples/reference-impl/kernel-witness-with-loss-L5.jsonl; do
	[ -f "$j" ] || { bad "re-captured journal missing: $j"; continue; }
	got=$(level  "$j" adapters/observer.json)
	sgot=$(slevel "$j" adapters/observer.json)
	l13=$(req "$j" adapters/observer.json VLC-L1-3)
	if [ "$sgot" = "4" ] && [ "$got" = "5" ] && [ "$l13" = "PASS" ]; then
		ok "$(basename $j) (sealed HEAD) -> structural L4, attested L5 on the log alone; VLC-L1-3 PASS because HEAD is chained"
	else
		bad "$(basename $j) (sealed HEAD) -> structural L$sgot, attested L$got, VLC-L1-3 $l13; expected 4, 5, PASS"
	fi
done
ok "the reference implementation is scored by the same rules: pre-fix captures stay at L0, captures from the fixed sensor earn L4/L5"

hr; echo "6. THE WITNESS -- reconciling a self-report against an independent record"
R="python3 witness/reconcile.py"
SIG=$($R --claims examples/reference-impl/agent-transcript-spoofed.jsonl \
         --journal examples/reference-impl/kernel-witness-spoofed-session.jsonl \
         --scope witness/scope-demo.json --json 2>/dev/null \
      | python3 -c 'import json,sys;print(json.load(sys.stdin)["substitution_signature"])' | tr -d '\r')
[ "$SIG" = "True" ] && ok "spoofed run: substitution signature raised" \
                    || bad "spoofed run: the spoof was not detected"

# EXT-005, EXT-015, EXT-016. Each case must be refused for ITS OWN reason, not
# merely refused: once the reconciler requires an L3 witness, every case built
# on the demo witness is refused anyway while that witness predates EXT-003, and
# a control that only checks the exit code would pass for the wrong reason.
RT=$(mktemp -d); trap 'rm -rf "$RT"' EXIT
python3 - "$RT" > "$RT/results.txt" <<'PYX'
import copy, hashlib, json, subprocess, sys
d = sys.argv[1]
E = "examples/reference-impl"
H, W = f"{E}/agent-transcript-honest.jsonl", f"{E}/kernel-witness-honest-session.jsonl"
canon = lambda o: json.dumps(o, sort_keys=True, separators=(",", ":"))
sha = lambda s: hashlib.sha256(s.encode()).hexdigest()

# EXT-022. No captured journal qualifies as a witness any more: the observer's
# end marker is not chained, so none demonstrates structural L1 on its own, let
# alone L3. The reconciler's gates still need testing against a witness that
# does qualify, so this section RE-SEALS the capture under a chain that binds its
# end marker. The records are the sensor's, unchanged; the seal is this test's,
# not the sensor's, and nothing here is presented as a capture.
def seal(src, dst):
    recs = [json.loads(l) for l in open(src) if l.strip()]
    out, prev = [], None
    for r in recs:
        r = {k: v for k, v in r.items() if k != "h"}
        if prev is None:                      # H0: the root, derived from the policy digest
            prev = sha(r["policy_digest"]); r["hash"] = prev
        else:
            if r["class"] == "HEAD":
                r["head"] = prev
            r["hash"] = sha(prev + canon(r)); prev = r["hash"]
        out.append(r)
    open(dst, "w").write("\n".join(canon(r) for r in out) + "\n")
SA = json.load(open("adapters/observer.json"))
SA["name"] = "observer-resealed-for-test"
SA["integrity"] = {"mechanism": "sha256-chain-canonical", "hash_field": "hash", "primitive": "SHA-256",
                   "documented": True, "primitive_documented": True,
                   "root": {"kind": "field_of_first_record", "field": "policy_digest", "transform": "sha256"},
                   "end_marker": {"class": "HEAD", "head_field": "head", "self_bound": True}}
json.dump(SA, open(f"{d}/sealed.json", "w"))
SW = f"{d}/witness-sealed.jsonl"
seal(W, SW)

open(f"{d}/empty.jsonl", "w").close()
open(f"{d}/badline.jsonl", "w").write(open(H).read() + "{not json\n")
j = [json.loads(l) for l in open(SW) if l.strip()]
for r in j:
    if "hash" in r: r["hash"] = "00" * 32
open(f"{d}/garbage.jsonl", "w").write("\n".join(json.dumps(r, separators=(",", ":")) for r in j) + "\n")
c = [json.loads(l) for l in open(H) if l.strip()]
for r in c:
    if str(r.get("command", "")).startswith("/usr/bin/id"): r["command"] = "/safe/bin/id -u"
open(f"{d}/otherpath.jsonl", "w").write("\n".join(json.dumps(r) for r in c) + "\n")
c = [json.loads(l) for l in open(H) if l.strip()] + [{"t": 1, "type": "tool_call", "tool": "shell_ext", "command": "id"}]
open(f"{d}/unmapped.jsonl", "w").write("\n".join(json.dumps(r) for r in c) + "\n")

def rec(claims, journal, adapter=None):
    extra = ["--journal-adapter", adapter] if adapter else []
    p = subprocess.run(["python3", "witness/reconcile.py", "--claims", claims, "--journal", journal,
                        "--scope", "witness/scope-demo.json", "--json"] + extra, capture_output=True, text=True)
    q = subprocess.run(["python3", "witness/reconcile.py", "--claims", claims, "--journal", journal,
                        "--scope", "witness/scope-demo.json", "--require-agreement"] + extra,
                       capture_output=True, text=True)
    return json.loads(p.stdout), q.returncode
def say(ok, msg): print(("OK" if ok else "BAD") + "|" + msg)

SAP = f"{d}/sealed.json"
# the honest run, re-sealed witness: the records must agree AND the witness must qualify
r, rc = rec(H, SW, SAP)
say(rc == 0, "honest run (witness re-sealed for the test): the records agree and the witness qualifies"
    if rc == 0 else "honest run refused: " + "; ".join(r["evidence_problems"])
    + f" / agreement {r['agreement']}")

def refused_for(claims, journal, needle, label, where="problems", adapter=SAP):
    r, rc = rec(claims, journal, adapter)
    hay = r["evidence_problems"] if where == "problems" else \
          [f["severity"] + " " + f["what"] for f in r["findings"]]
    say(rc != 0 and any(needle in h for h in hay), label)

# EXT-022: the honest run against the pre-fix capture, whose end marker is not
# chained, is refused -- and for that reason. The re-capture from the fixed
# sensor (HEAD chained) is accepted as a witness with the shipped adapter.
refused_for(f"{E}/pre-EXT-022/agent-transcript-honest.jsonl", f"{E}/pre-EXT-022/kernel-witness-honest-session.jsonl",
            "VLC-L1-3", "the pre-fix capture, end marker unchained, is refused as a witness (EXT-022)",
            adapter="adapters/observer-legacy.json")
_r, _rc = rec(H, W, None)
say(_rc == 0, "the re-captured honest session, HEAD chained, is accepted as a witness with the shipped adapter")
refused_for(f"{d}/empty.jsonl", f"{d}/empty.jsonl", "claim record is empty",
            "two empty inputs are refused as empty, not reported as agreement")
refused_for(f"{d}/badline.jsonl", SW, "unparseable line(s) in the claim record",
            "an unparseable claim line blocks the strong result")
refused_for(H, f"{d}/garbage.jsonl", "VLC-L1-1",
            "a witness journal whose chain does not verify is refused for its chain")
refused_for(f"{d}/otherpath.jsonl", SW, "UNCORROBORATED CLAIM /safe/bin/id",
            "a claimed /safe/bin/id is not corroborated by a witnessed /usr/bin/id", where="findings")
refused_for(f"{d}/unmapped.jsonl", SW, "have no mapping",
            "a claimed tool with no mapping blocks the strong result (EXT-016)")
# A genuinely weak witness: the pre-EXT-003 capture of the same session, re-sealed
# the same way, which scores structural L1 under the corrected identity.
P3 = f"{E}/pre-EXT-003"
seal(f"{P3}/kernel-witness-honest-session.jsonl", f"{d}/pre3-sealed.jsonl")
refused_for(f"{P3}/agent-transcript-honest.jsonl", f"{d}/pre3-sealed.jsonl",
            "VLC-L5-4 requires L3",
            "a witness below structural L3 cannot corroborate (EXT-015)")
# VLC-L5-6 (1.4-draft), the sibling of the case above. The SAME honest witness,
# its structural level held fixed, with only the exhaustiveness basis taken
# away: the adapter's basis_field points at a field that does not exist.
a = copy.deepcopy(SA)
a["coverage"]["basis_field"] = "no_such_field"
json.dump(a, open(f"{d}/nobasis.json", "w"))
s_lvl = json.loads(subprocess.run(["python3", "conformance.py", "--log", SW, "--adapter", f"{d}/nobasis.json",
                                   "--json"], capture_output=True, text=True).stdout)["structural_level"]
say(s_lvl >= 3, f"control precondition: removing the basis leaves the witness at structural L{s_lvl}, not below L3")
refused_for(H, SW, "VLC-L5-6",
            "a witness at structural L3+ with no exhaustiveness basis cannot corroborate an absence (VLC-L5-6)",
            adapter=f"{d}/nobasis.json")
PYX
while IFS='|' read -r V M; do
  case "$V" in
    OK)    ok "$M" ;;
    XFAIL) xfail "$M" ;;
    *)     bad "$M" ;;
  esac
done < "$RT/results.txt"

hr; echo "7. PROVENANCE -- the version a report cites must be the version it was checked against"
# Every report carries "spec": <version>, and Annex E manifests are archived
# under it. If the checker stamps a version whose normative text differs from
# the one shipped beside it, a reader reproducing an L4 claim reads the wrong
# clauses -- 1.0-draft had no structural/attested split at all. Three places
# state the version; they must agree, or the citation is wrong somewhere.
PV=$(python3 - <<'PYX'
import json, re, subprocess, sys
rep = json.loads(subprocess.run(
    ["python3", "./conformance.py", "--log", "examples/L1-hashchain.jsonl",
     "--adapter", "adapters/generic-appjsonl.json", "--json"],
    capture_output=True, text=True).stdout)
stamped = rep["spec"].replace("VLC-1 ", "").strip()
spec = re.search(r"^\|\s*Version\s*\|\s*([^|]+?)\s*\|", open("SPEC.md", encoding="utf-8").read(), re.M)
cff  = re.search(r'^version:\s*"?([^"\n]+?)"?\s*$', open("CITATION.cff", encoding="utf-8").read(), re.M)
print(stamped, spec.group(1) if spec else "MISSING", cff.group(1) if cff else "MISSING")
PYX
)
set -- $PV
if [ "$1" = "$2" ] && [ "$2" = "$3" ]; then
	ok "checker stamps $1, SPEC.md says $2, CITATION.cff says $3"
else
	bad "version disagreement: checker=$1 SPEC.md=$2 CITATION.cff=$3"
	bad "a report citing the wrong version points a reproducer at the wrong clauses"
fi

hr; echo "8. ADAPTER INVARIANCE -- an adapter-only change must not alter a structural result"
# EXT-004. A requirement classed structural is recomputed from the log. Its
# result must not depend on anything the adapter merely asserts. VLC-L5-4 was
# classed structural but scored the witness on every requirement, attested
# ones included, so pointing coverage.basis_field at any non-empty field
# flipped it with the log unchanged. This control rewrites only attested
# adapter fields and requires every structural requirement to come out
# identical, on every worked example that has a coverage block.
AI=$(python3 - <<'PYX'
import json, subprocess, copy, tempfile, os
cases = [("examples/L3-coverage.jsonl",   "adapters/generic-appjsonl.json"),
         ("examples/L4-policybound.jsonl", "adapters/generic-appjsonl.json")]
def structural(log, adapter_obj):
    fd, path = tempfile.mkstemp(suffix=".json"); os.close(fd)
    json.dump(adapter_obj, open(path, "w"))
    rep = json.loads(subprocess.run(["python3", "./conformance.py", "--log", log,
                                     "--adapter", path, "--json"],
                                    capture_output=True, text=True).stdout)
    os.unlink(path)
    return {k: v["status"] for k, v in rep["requirements"].items()
            if v.get("class") == "structural"}, rep["structural_level"]
moved = []
for log, ad in cases:
    base = json.load(open(ad))
    if "coverage" not in base: continue
    ref, ref_lv = structural(log, base)
    for field in ("attached_field", "class", "hash"):
        a = copy.deepcopy(base); a["coverage"]["basis_field"] = field
        got, lv = structural(log, a)
        diff = [k for k in ref if got.get(k) != ref[k]]
        if diff or lv != ref_lv:
            moved.append(f"{log.split('/')[-1]} basis_field={field}: {diff or 'level'}")
print("MOVED " + "; ".join(moved) if moved else "OK")
PYX
)
case "$AI" in
  OK) ok "rewriting the adapter's coverage basis moved no structural requirement, on any example" ;;
  *)  bad "an adapter-only change altered a structural result: ${AI#MOVED }"
      bad "a structural requirement must be recomputed from the log, not relayed from the adapter" ;;
esac

hr; echo "9. TYPED OBLIGATIONS -- each fails at the requirement it names, not at L1"
# EXT-006. Seven normative obligations were checked for presence or summed
# totals rather than type, and each could reach L4 while violated. Every mutant
# below is RE-SEALED after editing, so VLC-L1-1 still passes and the mutant can
# only fail where it is aimed. Honest controls must still pass.
TM=$(mktemp -d)
# POSIX sh: the case list goes through a file, not process substitution, and
# not a pipe -- a while-loop at the end of a pipe runs in a subshell and its
# bad() calls would be lost.
python3 examples/typed_mutants.py "$TM" | tr -d '\r' > "$TM/cases.txt"
while read -r LOG AD REQ EXPECT; do
  GOT=$(python3 ./conformance.py --log "$LOG" --adapter "$AD" --json 2>/dev/null \
        | python3 -c "import json,sys;r=json.load(sys.stdin)['requirements'];print(r['$REQ']['status'], r['VLC-L1-1']['status'])" \
        | tr -d '\r')
  set -- $GOT
  N=$(basename "$LOG" .jsonl)
  if [ "$1" = "$EXPECT" ] && [ "$2" = "PASS" ]; then
    ok "$N: $REQ $EXPECT, chain intact"
  else
    bad "$N: expected $REQ $EXPECT with VLC-L1-1 PASS, got $REQ $1 with VLC-L1-1 $2"
  fi
done < "$TM/cases.txt"
rm -rf "$TM"

hr; echo "10. EVIDENCE MANIFEST -- a citation that is not complete is weaker than none (Annex E)"
# EXT-007. A malformed entry was treated as absent, digests were any string,
# and the negative control VLC-E-5 requires was not required.
EVR=$(python3 - <<'PYX'
import json, subprocess, copy, tempfile, os
base = json.load(open("adapters/observer.json"))
log = "examples/reference-impl/kernel-witness-honest-session.jsonl"
def status(ad):
    fd, p = tempfile.mkstemp(suffix=".json"); os.close(fd); json.dump(ad, open(p, "w"))
    r = json.loads(subprocess.run(["python3", "./conformance.py", "--log", log, "--adapter", p,
                                   "--json"], capture_output=True, text=True).stdout)
    os.unlink(p); return r["requirements"]["VLC-L3-4"]["status"]
cases = [("honest entry", base, "PASS")]
a = copy.deepcopy(base); a["evidence"]["VLC-L3-4"] = "see the coverage log"
cases.append(("malformed entry", a, "FAIL"))
a = copy.deepcopy(base); a["evidence"]["VLC-L3-4"]["runner_digest"] = "trust me"
cases.append(("malformed digest", a, "FAIL"))
a = copy.deepcopy(base); a["evidence"]["VLC-L3-4"].pop("negative_control")
cases.append(("no negative control", a, "FAIL"))
for name, ad, want in cases:
    got = status(ad)
    print(f"{'OK' if got == want else 'BAD'}|{name}: VLC-L3-4 {got}, expected {want}")
PYX
)
EVF=$(mktemp)
printf '%s\n' "$EVR" | tr -d '\r' > "$EVF"
while IFS='|' read -r V M; do
  [ "$V" = "OK" ] && ok "$M" || bad "$M"
done < "$EVF"
rm -f "$EVF"

hr; echo "11. LOADER AND ORDINAL MODE -- duplicate names, non-finite numbers, non-objects, undeclared ordinal gaps (vlc-1#1)"
# A duplicate member name is invisible to the canonical-JSON chain (the PARSED record is hashed), NaN/Infinity
# are not canonical JSON, a non-object line crashed the checker, and ordinal mode scored a silent gap as a
# declared loss. Every log below is built with the chain intact, so the only thing that can catch it is the check named.
OR=$(python3 - <<'PYX'
import copy, hashlib, json, os, subprocess, tempfile
d = tempfile.mkdtemp()
canon = lambda o: json.dumps(o, sort_keys=True, separators=(",", ":"))
def build(recs, end_extra):
    prev, out = "00" * 32, []
    for r in recs:
        h = hashlib.sha256(prev.encode() + canon(r).encode()).hexdigest(); out.append(dict(r, hash=h)); prev = h
    end = dict({"class": "END", "head": prev}, **end_extra)
    h = hashlib.sha256(prev.encode() + canon(end).encode()).hexdigest(); out.append(dict(end, hash=h))
    return out
def write(name, lines):
    p = os.path.join(d, name); open(p, "w").write("\n".join(lines) + "\n"); return p
def run(log, ad):
    ap = os.path.join(d, "ad.json"); json.dump(ad, open(ap, "w"))
    p = subprocess.run(["python3", "conformance.py", "--log", log, "--adapter", ap, "--json"], capture_output=True, text=True)
    try:
        r = json.loads(p.stdout)["requirements"]; return p.returncode, {k: v["status"] for k, v in r.items()}
    except Exception:
        return p.returncode, None
base = json.load(open("adapters/generic-appjsonl.json"))
ordn = copy.deepcopy(base)
ordn["loss"] = {"mode": "ordinal", "ordinal_field": "seq", "declaration_class": "DROP", "count_field": "lost",
                "interval_fields": ["from", "to"], "overflow_behaviour": "drop_counted",
                "produced": {"kind": "max_ordinal", "field": "seq",
                             "high_water_field": "last_seq", "start": 0}}
ev = [{"class": "EPOCH_START", "producer": "x"}] + [{"class": "inference", "seq": i, "verdict": "allow"} for i in range(10) if i != 4]
def emit(tag, name, want):
    print(("OK" if want else "BAD") + "|" + name)
# 1. silent ordinal gap: must fail L2-2 with the chain intact; the same gap DECLARED must pass (positive control)
lines = [json.dumps(r) for r in build(ev, {"lost_total": 0, "records": 10, "last_seq": 9})]
rc, st = run(write("gap.jsonl", lines), ordn)
emit("", "ordinal mode: an undeclared gap fails VLC-L2-2 with VLC-L1-1 intact", st and st["VLC-L2-2"] == "FAIL" and st["VLC-L1-1"] == "PASS")
decl = [{"class": "EPOCH_START", "producer": "x"}] + [{"class": "inference", "seq": i, "verdict": "allow"} for i in range(10) if i != 4] + [{"class": "DROP", "lost": 1, "from": 4, "to": 4}]
lines = [json.dumps(r) for r in build(decl, {"lost_total": 1, "records": 10, "last_seq": 9})]
rc, st = run(write("gapdecl.jsonl", lines), ordn)
emit("", "ordinal mode: the same gap declared by the producer passes VLC-L2-2 and VLC-L2-5", st and st["VLC-L2-2"] == "PASS" and st["VLC-L2-5"] == "PASS")
bad = [{"class": "EPOCH_START", "producer": "x"}] + [{"class": "inference", "seq": i, "verdict": "allow"} for i in range(10) if i != 4] + [{"class": "DROP", "lost": 2, "from": 4, "to": 4}]
lines = [json.dumps(r) for r in build(bad, {"lost_total": 2, "records": 10, "last_seq": 9})]
rc, st = run(write("gapbad.jsonl", lines), ordn)
emit("", "ordinal mode: a declaration whose interval size differs from its count fails VLC-L2-2", st and st["VLC-L2-2"] == "FAIL")
# 2. duplicate member name inserted into one record, chain not recomputed: refused, not scored
src = open("examples/L2-accounted.jsonl").read().splitlines()
i = next(k for k, l in enumerate(src) if '"class":"inference"' in l and k > 3)
src[i] = src[i].replace('"verdict":"allow"', '"verdict":"deny","verdict":"allow"', 1)
rc, st = run(write("dup.jsonl", src), base)
emit("", "a duplicate member name is unreadable at VLC-L1-1 and scores L0, not L2", st is not None and st["VLC-L1-1"] == "FAIL")
# 3. NaN, with the chain RE-SEALED over it (json.dumps hashes NaN happily), so only the loader can refuse it
nanev = copy.deepcopy(ev); nanev[1]["x"] = float("nan")
lines = [json.dumps(r) for r in build(nanev, {"lost_total": 0, "records": 10, "last_seq": 9})]
rc, st = run(write("nan.jsonl", lines), ordn)
emit("", "a NaN literal in a re-sealed log is unreadable at VLC-L1-1, not scored", st is not None and st["VLC-L1-1"] == "FAIL")
# 4. non-object line
src = open("examples/L2-accounted.jsonl").read().splitlines() + ["1"]
rc, st = run(write("nonobj.jsonl", src), base)
emit("", "a non-object line is reported at VLC-L1-1 instead of crashing the checker", st is not None and st["VLC-L1-1"] == "FAIL")
# 5. the shipped L2 example is unaffected
rc, st = run("examples/L2-accounted.jsonl", base)
emit("", "the shipped L2 example still passes VLC-L2-5", st and st["VLC-L2-5"] == "PASS")
PYX
)
ORF=$(mktemp)
printf '%s\n' "$OR" | tr -d '\r' > "$ORF"
while IFS='|' read -r V M; do
  [ "$V" = "OK" ] && ok "$M" || bad "$M"
done < "$ORF"
rm -f "$ORF"

hr; echo "12. ANCHORED ROOT AND HEAD -- a re-rooted, re-sealed log is caught only by a value held outside the log (Annex A.13)"
# The in-place rebase-policy mutation breaks the chain, so VLC-L1-1 kills it for the wrong reason. A log that is
# re-rooted under another policy digest AND re-sealed is internally consistent; only a root/head the verifier holds
# independently can refute it (EXT-008). --expect-root / --expect-head are that input.
AR=$(python3 - <<'PYX'
import importlib.util, json, os, subprocess, sys, tempfile
sys.path.insert(0, "examples")
import make_examples as mk
AD = "adapters/generic-appjsonl-policy.json"
def run(log, *extra):
    p = subprocess.run(["python3", "conformance.py", "--log", log, "--adapter", AD, "--json", *extra], capture_output=True, text=True)
    return json.loads(p.stdout)
orig_root = mk.sha(mk.POLICY)
d = tempfile.mkdtemp()
mk.HERE = d
mk.POLICY = "dead" + mk.POLICY[4:]
import contextlib, io
with contextlib.redirect_stdout(io.StringIO()):
    mk.l4()
re = os.path.join(d, "L4-policybound.jsonl")
def emit(name, cond): print(("OK" if cond else "BAD") + "|" + name)
r = run(re)
emit("a re-rooted, re-sealed log scores structural L4 on its own (the gap, stated)", r["structural_level"] == 4)
r = run(re, "--expect-root", orig_root)
emit("--expect-root: the same log fails VLC-L1-1 against the original root", r["requirements"]["VLC-L1-1"]["status"] == "FAIL" and r["structural_level"] == 0)
r = run("examples/L4-policybound.jsonl", "--expect-root", orig_root)
q = r["requirements"]["VLC-L1-1"]
emit("--expect-root: the genuine log passes, and the note says the root was anchored", q["status"] == "PASS" and "supplied independently" in q["note"] and r["structural_level"] == 4)
head = None
r0 = run("examples/L4-policybound.jsonl")
lines = [l for l in open("examples/L4-policybound.jsonl") if l.strip()]
head = json.loads(lines[-1])["hash"]
r = run("examples/L4-policybound.jsonl", "--expect-head", head)
emit("--expect-head: the genuine head passes", r["requirements"]["VLC-L1-1"]["status"] == "PASS" and r["structural_level"] == 4)
r = run("examples/L4-policybound.jsonl", "--expect-head", "ab" * 32)
emit("--expect-head: a wrong head fails VLC-L1-1", r["requirements"]["VLC-L1-1"]["status"] == "FAIL")
# truncate-tail: the adapter DOES declare an end marker; the note must not blame the adapter
p = subprocess.run(["python3", "conformance.py", "--log", "examples/L4-policybound.jsonl", "--adapter", AD, "--mutate", "truncate-tail", "--json"], capture_output=True, text=True)
n = json.loads(p.stdout)["requirements"]["VLC-L1-3"]["note"]
emit("truncate-tail: VLC-L1-3 names the log's missing end marker, not the adapter", "adapter declares no end marker" not in n and "expected 'END'" in n)
PYX
)
ARF=$(mktemp)
printf '%s\n' "$AR" | tr -d '\r' > "$ARF"
while IFS='|' read -r V M; do
  [ "$V" = "OK" ] && ok "$M" || bad "$M"
done < "$ARF"
rm -f "$ARF"

hr
echo "13. Annex K: committed findings ledger (findings.py)"
JR=$(python3 - <<'PYJ'
import json, os, shutil, subprocess, sys, tempfile
sys.path.insert(0, ".")
import findings as f
D = "examples/findings"
A = json.load(open(os.path.join(D, "anchors.json")))
BASE = [json.loads(l) for l in open(os.path.join(D, "ledger.jsonl")) if l.strip()]
T = tempfile.mkdtemp()
def emit(msg, cond): print(("OK" if cond else "NO") + "|" + msg)
def rehash(recs):
    prev = f.GENESIS
    for i, r in enumerate(recs):
        r["seq"] = i; r["prev"] = prev; r.pop("hash", None); r["hash"] = f.record_hash(r); prev = r["hash"]
    return recs
def write(name, recs=None, text=None):
    p = os.path.join(T, name)
    with open(p, "w") as fh:
        fh.write(text if text is not None else "".join(f.canon(r) + "\n" for r in recs))
    return p
def run(ledger, *extra):
    p = subprocess.run(["python3", "findings.py", "verify", "--ledger", ledger, "--json", *extra],
                       capture_output=True, text=True)
    return json.loads(p.stdout)
def st(r, rid): return r["requirements"][rid]["status"]
def copy(): return [dict(r) for r in BASE]
try:
    both = ["--anchor", "subject=" + A["subject"], "--anchor", "tester=" + A["tester"]]
    r = run(os.path.join(D, "ledger.jsonl"), "--docs", os.path.join(D, "docs"), "--as-of", "2026-11-26", *both)
    emit("worked example: conformant, both anchors hold",
         r["conformant"] and all(st(r, k) == "PASS" for k in r["requirements"]))
    emit("worked example: F-002 critical is reported overdue, F-001 revealed, F-003 withdrawn",
         r["findings"]["F-002"]["status"] == "overdue" and r["findings"]["F-002"]["class"] == "critical"
         and r["findings"]["F-001"]["status"] == "revealed" and r["findings"]["F-003"]["status"] == "withdrawn")
    emit("worked example: unanchored tail is counted from the earlier anchor", r["unanchored_tail"] == 3)
    r = run(os.path.join(D, "ledger.jsonl"), "--as-of", "2026-10-10")
    emit("status is dated: before its due date F-002 is open, not overdue", r["findings"]["F-002"]["status"] == "open")

    drop = rehash([x for x in copy() if x["finding_id"] != "F-002"])
    p = write("drop.jsonl", drop)
    r = run(p)
    emit("F-002 erased and chain re-hashed: with no anchor, VLC-K-6 is NOT_TESTED, never PASS",
         st(r, "VLC-K-6") == "NOT_TESTED")
    emit("the same erasure fails VLC-K-6 against the subject's anchor alone",
         st(run(p, "--anchor", "subject=" + A["subject"]), "VLC-K-6") == "FAIL")

    down = copy(); down[1]["class"] = "low"; rehash(down)
    emit("undisclosed critical F-002 quietly downgraded to low: caught by the subject's anchor",
         st(run(write("down.jsonl", down), "--anchor", "subject=" + A["subject"]), "VLC-K-6") == "FAIL")
    down = copy(); down[0]["class"] = "low"; rehash(down)
    emit("revealed F-001 downgraded to low after the fact: its opening no longer matches (VLC-K-4)",
         st(run(write("down2.jsonl", down)), "VLC-K-4") == "FAIL")

    tail = copy(); tail[5]["at"] = "2026-11-27T09:00:00Z"; rehash(tail)
    p = write("tail.jsonl", tail)
    r = run(p, "--anchor", "subject=" + A["subject"], "--anchor", "tester=" + A["tester"])
    emit("a record after the subject's anchor is edited: subject's anchor still holds, tester's catches it",
         "subject" in r["anchors"] and "tester" not in r["anchors"] and st(r, "VLC-K-6") == "FAIL")

    d = os.path.join(T, "docs"); shutil.copytree(os.path.join(D, "docs"), d)
    with open(os.path.join(d, "F-001.md"), "a") as fh: fh.write("Severity reassessed.\n")
    emit("disclosed document edited after reveal fails VLC-K-5",
         st(run(os.path.join(D, "ledger.jsonl"), "--docs", d), "VLC-K-5") == "FAIL")

    two = copy() + [dict(copy()[5])]; rehash(two)
    emit("a second reveal for an already revealed finding fails VLC-K-3", st(run(write("two.jsonl", two)), "VLC-K-3") == "FAIL")
    back = copy(); back[3]["due"] = "2026-10-20"; rehash(back)
    emit("a defer that moves the due date earlier fails VLC-K-3", st(run(write("back.jsonl", back)), "VLC-K-3") == "FAIL")
    order = copy(); order[2]["at"] = "2026-10-01T00:00:00Z"; rehash(order)
    emit("a backdated record fails VLC-K-2", st(run(write("order.jsonl", order)), "VLC-K-2") == "FAIL")

    first = f.canon(BASE[0])
    emit("a non-integer number fails VLC-K-1",
         st(run(write("float.jsonl", text=first.replace('"seq":0', '"seq":0.0') + "\n")), "VLC-K-1") == "FAIL")
    emit("a duplicate member fails VLC-K-1",
         st(run(write("dup.jsonl", text=first[:-1] + ',"class":"info"}\n')), "VLC-K-1") == "FAIL")
    na = copy(); na[3]["reason"] = "fix-in-progr\u00e9s"; rehash(na)
    emit("a non-ASCII string fails VLC-K-1", st(run(write("na.jsonl", na)), "VLC-K-1") == "FAIL")
    print("DONE|section 13 ran to completion")
except Exception as e:
    emit("section 13 aborted: %s: %s" % (type(e).__name__, e), False)
finally:
    shutil.rmtree(T)
PYJ
)
JRF=$(mktemp)
printf '%s\n' "$JR" | tr -d '\r' > "$JRF"
# A crash inside the block must not read as a pass: require the completion line.
grep -q '^DONE|' "$JRF" || bad "section 13 did not run to completion (checker crashed or produced invalid JSON)"
while IFS='|' read -r V M; do
  case "$V" in DONE) ;; OK) ok "$M" ;; *) bad "$M" ;; esac
done < "$JRF"
rm -f "$JRF"

hr
echo "14. L3i: interval attestation, and the two attacks EXT-002 left open"
L3D=$(mktemp -d)
python3 examples/l3i_cases.py "$L3D" >/dev/null 2>&1 || bad "l3i fixtures did not build"
l3i_worst() {
  python3 conformance.py --log "$L3D/$1.jsonl" --adapter "$L3D/l3i.adapter.json" --json 2>/dev/null \
  | python3 -c 'import sys,json
try: r=json.load(sys.stdin)["requirements"]
except Exception: print("CRASH"); raise SystemExit
v=[x["status"] for k,x in r.items() if k.startswith("VLC-L3i")]
print("CRASH" if not v else ("FAIL" if "FAIL" in v else "PASS"))'
}
for spec in "l3i-honest PASS a complete window, each tick binding a later producer record" \
            "l3i-producer-died FAIL the producer stopped mid-interval: the absent ticks are the evidence (EXT-002)" \
            "l3i-attestor-dropped FAIL attestor traffic dropped wholesale -- EXT-002 reporter question 1" \
            "l3i-anchor-replayed FAIL one anchor replayed across every tick -- EXT-002 reporter question 2 (EXT-018)" \
            "l3i-self-anchored FAIL a witness set anchored to itself binds no producer record (EXT-018)" \
            "l3i-reversed-binding FAIL ticks bound in reverse: observation order contradicts tick order (EXT-018)"; do
  set -- $spec; CASE=$1; WANT=$2; shift 2
  GOT=$(l3i_worst "$CASE")
  if [ "$GOT" = "$WANT" ]; then ok "$CASE -> $WANT: $*"; else bad "$CASE expected $WANT, got $GOT"; fi
done
rm -rf "$L3D"

hr
echo "15. NEGATIVE CONTROLS -- every requirement must be able to fail"
# An audit over 1512 scorings (72 logs x 21 adapters) found six requirements
# that passed everywhere and had never been observed to fail. A requirement
# that cannot be made to fail is indistinguishable from one that is not
# checked, which is how EXT-018 survived: L3i passed every log for two weeks
# by never running. Each control below flips one requirement and nothing else.
N15=$(mktemp -d)
mut() {  # mut <out> <python expr over `a`>
  python3 -c "
import json,sys
a=json.load(open('adapters/generic-appjsonl-policy.json'))
$2
json.dump(a,open('$N15/$1.json','w'))"
}
L4=examples/L4-policybound.jsonl
base_l23=$(req $L4 adapters/generic-appjsonl-policy.json VLC-L2-3)
[ "$base_l23" = "PASS" ] || bad "control precondition: L4 example should start with VLC-L2-3 PASS, got $base_l23"

mut nointeg  "a['integrity']['mechanism']='none'"
mut silent   "a['loss']['overflow_behaviour']='silent'"
mut noob     "a['loss'].pop('overflow_behaviour',None)"
mut cvevent  "a['non_event_classes']=[c for c in a['non_event_classes'] if c!=a['coverage']['declaration_class']]"
mut noreplay "a['policy']['replay'].pop('reference',None)"

for spec in "nointeg  VLC-L2-3 a loss declaration with no integrity binding is removable" \
            "silent   VLC-L2-4 a producer that discards silently cannot claim L2" \
            "noob     VLC-L2-4 overflow behaviour undeclared is not overflow behaviour declared" \
            "cvevent  VLC-L3-5 a coverage declaration counted as an event inflates the identity" \
            "noreplay VLC-L4-3 a policy digest with no retrievable artefact is not re-evaluable"; do
  set -- $spec; M=$1; R=$2; shift 2
  G=$(req $L4 "$N15/$M.json" "$R")
  if [ "$G" = "FAIL" ]; then ok "$R fails when $*"; else bad "$R should FAIL under mutation '$M', got $G"; fi
done

# VLC-L3i-4 is attested: the reader relays that the attestor is independent.
python3 examples/l3i_cases.py "$N15" >/dev/null 2>&1 || bad "l3i fixtures did not build for section 15"
python3 -c "
import json
a=json.load(open('$N15/l3i.adapter.json'))
a['interval']['trusted_attestors']=['someone.else.example']
json.dump(a,open('$N15/l3i-untrusted.json','w'))"
G=$(req "$N15/l3i-honest.jsonl" "$N15/l3i-untrusted.json" VLC-L3i-4)
if [ "$G" = "FAIL" ]; then ok "VLC-L3i-4 fails when the declared attestor is not one the reader accepts"; else bad "VLC-L3i-4 should FAIL for an unaccepted attestor, got $G"; fi

# VLC-L3-1b has no failure path ON PURPOSE: it is the attested half of the
# coverage declaration (EXT-001) and a reader cannot recompute it. The
# invariant that matters is that it never stands alone -- it is only ever
# emitted alongside a well-formed declaration, so it can never carry a level
# by itself.
A1=$(req $L4 adapters/generic-appjsonl-policy.json VLC-L3-1a)
B1=$(req $L4 adapters/generic-appjsonl-policy.json VLC-L3-1b)
if [ "$A1" = "PASS" ] && [ "$B1" = "PASS" ]; then
  ok "VLC-L3-1b is attested-only and rides with VLC-L3-1a, which is recomputed"
else
  bad "VLC-L3-1b/1a invariant broken: 1a=$A1 1b=$B1"
fi
rm -rf "$N15"

hr
echo "16. CITED ARTEFACTS -- a reference to a file that is not here is a claim"
# EXT-019. The CI proof step globs proofs/*.v: it compiles what is present and
# cannot notice that something CITED is absent. proofs/sentinel_interval.v is
# referenced in six places, including a normative sentence in SPEC.md and the
# fix claim for EXT-002, and is not in this tree. This check reads the
# citations rather than the directory, so the gap cannot close silently.
CIT=$(python3 - <<'PYC'
import os, re, glob
cited = {}
for p in (glob.glob("*.md") + glob.glob("*.py") + glob.glob("examples/*.py")
          + glob.glob("proofs/*.v") + glob.glob("adapters/*.json")):
    try:
        s = open(p, encoding="utf-8", errors="replace").read()
    except OSError:
        continue
    for m in re.findall(r"(?:proofs/)?([A-Za-z0-9_]+\.v)\b(?! \(not in this repository)", s):
        if p.endswith(".v") and m == os.path.basename(p):
            continue
        cited.setdefault(m, set()).add(p)
for f in sorted(cited):
    state = "present" if os.path.exists(os.path.join("proofs", f)) else "ABSENT"
    print("%s|%s|%d" % (state, f, len(cited[f])))
PYC
)
[ -n "$CIT" ] || bad "section 16: no proof citations found at all, which cannot be right"
printf '%s\n' "$CIT" | while IFS='|' read -r STATE F N; do
  [ -z "$F" ] && continue
  if [ "$STATE" = "present" ]; then
    printf '  ok    proofs/%s is cited in %s place(s) and is in the tree\n' "$F" "$N"
  else
    printf '  xfail proofs/%s is cited in %s place(s) and is NOT in this tree (EXT-019)\n' "$F" "$N"
  fi
done
# The xfail above runs in a subshell, so count it here.
MISSING=$(printf '%s\n' "$CIT" | grep -c '^ABSENT|' || true)
XFAIL=$((XFAIL + MISSING))

hr
echo "17. UNBOUND END MARKER -- a tail cut with the marker rewritten, and no hash recomputed (EXT-022)"
# The observer's HEAD record names the chain head but is not chained itself, and
# the produced count was read from it. Dropping the last records and copying the
# new last hash into HEAD, with the counts lowered to match, passed VLC-L1-3 and
# the L2 identity -- structural L4, attested L5 on the reference journal -- with
# no hash computed at all. Every case below is built from the shipped capture.
U17=$(python3 - <<'PYU'
import json, os, subprocess, tempfile
d = tempfile.mkdtemp()
KW = "examples/reference-impl/pre-EXT-022/kernel-witness-L5.jsonl"
LEG = "adapters/observer-legacy.json"
src = [l.rstrip("\n") for l in open(KW) if l.strip()]
head = json.loads(src[-1]); H = head["h"]
k = 5
cut = json.loads(src[-1]); cut["h"] = json.loads(src[-2 - k])["h"]
cut["records"] -= k; cut["chained"] -= k
T = os.path.join(d, "truncated.jsonl")
open(T, "w").write("\n".join(src[:-1 - k] + [json.dumps(cut, separators=(",", ":"))]) + "\n")
def run(log, ad=LEG, *extra):
    p = subprocess.run(["python3", "conformance.py", "--log", log, "--adapter", ad, "--json", *extra],
                       capture_output=True, text=True)
    return json.loads(p.stdout)
def st(r, rid): return r["requirements"].get(rid, {}).get("status", "ABSENT")
def emit(msg, cond): print(("OK" if cond else "BAD") + "|" + msg)
r = run(T)
emit("5 records cut from the reference journal's tail, HEAD rewritten: VLC-L1-3 FAIL, structural L0 "
     "(was structural L4, attested L5)", st(r, "VLC-L1-3") == "FAIL" and r["structural_level"] == 0)
r = run(T, LEG, "--expect-head", H)
emit("the same cut against the journal's independently held head: VLC-L1-1 FAIL", st(r, "VLC-L1-1") == "FAIL")
r = run(KW, LEG, "--expect-head", H)
emit("the untouched journal with its head anchored: VLC-L1-3 PASS -- the anchor establishes the tail",
     st(r, "VLC-L1-3") == "PASS" and st(r, "VLC-L1-1") == "PASS")
emit("...and VLC-L2-1 still FAIL: an anchored head does not bind the counts on an unchained marker",
     st(r, "VLC-L2-1") == "FAIL")
# the same attack on a capture from the fixed sensor: HEAD is chained, so the
# rewrite breaks the chain and nothing above L0 survives
NK = "examples/reference-impl/kernel-witness-L5.jsonl"
ns = [l.rstrip("\n") for l in open(NK) if l.strip()]
nh = json.loads(ns[-1]); nh["head"] = json.loads(ns[-2 - k])["h"]
nh["records"] -= k; nh["chained"] -= k
NT = os.path.join(d, "sealed-truncated.jsonl")
open(NT, "w").write("\n".join(ns[:-1 - k] + [json.dumps(nh, separators=(",", ":"))]) + "\n")
r = run(NT, "adapters/observer.json")
emit("the same cut on a sealed-HEAD capture: structural L0 on the log alone, no anchor needed", r["structural_level"] == 0)
r = run(NK, "adapters/observer.json")
emit("the untouched sealed-HEAD capture: VLC-L1-3 PASS and VLC-L2-5 PASS on the log alone",
     st(r, "VLC-L1-3") == "PASS" and st(r, "VLC-L2-5") == "PASS")
r = run("examples/L1-hashchain.jsonl", "adapters/generic-appjsonl.json")
emit("positive control: a chained end marker still establishes VLC-L1-3 on the log alone", st(r, "VLC-L1-3") == "PASS")
# self_bound defaults to true, and a marker declared bound that carries no hash
# used to be skipped silently rather than refused
L = [l for l in open("examples/L1-hashchain.jsonl") if l.strip()]
e = json.loads(L[-1]); e.pop("hash")
N = os.path.join(d, "nohash.jsonl"); open(N, "w").write("".join(L[:-1]) + json.dumps(e) + "\n")
r = run(N, "adapters/generic-appjsonl.json")
emit("an end marker declared self-bound that carries no binding: VLC-L1-3 FAIL", st(r, "VLC-L1-3") == "FAIL")
print("DONE|")
PYU
) || true
U17F=$(mktemp); printf '%s\n' "$U17" | tr -d '\r' > "$U17F"
# a crash inside the block must not read as a pass
grep -q '^DONE|' "$U17F" || bad "section block U17 did not run to completion (a crash, or an API the checker lacks)"
while IFS='|' read -r V M; do case "$V" in DONE) ;; OK) ok "$M" ;; *) bad "$M" ;; esac; done < "$U17F"; rm -f "$U17F"

hr
echo "18. THE ADAPTER CANNOT RAISE THE STRUCTURAL LEVEL -- VLC-V-3, by attack (EXT-025)"
# The attack from the 2026-09-29 review, verbatim: the log is L2-looks-complete,
# unchanged; only the adapter moves. It relabels the epoch record as a coverage
# declaration and points the per-record policy digest at the chain's own hash
# field. The 1.4-draft checker scored it structural L4.
U18=$(python3 - <<'PYU'
import copy, hashlib, json, os, subprocess, tempfile
d = tempfile.mkdtemp()
canon = lambda o: json.dumps(o, sort_keys=True, separators=(",", ":"))
sha = lambda s: hashlib.sha256(s.encode()).hexdigest()
def run(log, adobj, *extra):
    ap = os.path.join(d, "ad.json"); json.dump(adobj, open(ap, "w"))
    p = subprocess.run(["python3", "conformance.py", "--log", log, "--adapter", ap, "--json", *extra],
                       capture_output=True, text=True)
    return json.loads(p.stdout)
def st(r, rid): return r["requirements"].get(rid, {}).get("status", "ABSENT")
def emit(msg, cond, xfail=None):
    if xfail is not None and not cond:
        print("XFAIL|" + xfail); return
    print(("OK" if cond else "BAD") + "|" + msg)
def reseal(recs, root="00" * 32, first_is_root=False):
    prev, out = root, []
    for i, r in enumerate(recs):
        r = {k: v for k, v in r.items() if k != "hash"}
        if i == 0 and first_is_root:
            r["hash"] = prev
        else:
            if r["class"] == "END": r["head"] = prev
            r["hash"] = sha(prev + canon(r)); prev = r["hash"]
        out.append(r)
    return out
def write(name, recs):
    p = os.path.join(d, name); open(p, "w").write("\n".join(canon(r) for r in recs) + "\n"); return p
base = json.load(open("adapters/generic-appjsonl.json"))
LC = "examples/L2-looks-complete.jsonl"

atk = copy.deepcopy(base)
atk["coverage"].update({"declaration_class": "EPOCH_START", "attached_field": "producer",
                        "unattached_field": "buffer", "by_design_field": "on_full", "basis_field": "producer"})
atk["policy"] = {"mode": "per_record", "digest_field": "hash", "change_class": "NOPE",
                 "replay": {"deterministic": True, "reference": "x"}}
r = run(LC, atk)
emit("the review's attack adapter on L2-looks-complete, log unchanged: structural L2 (1.4-draft: L4)",
     r["structural_level"] == 2)
emit("...refused where it lies: VLC-L3-1a (a relabelled record) and VLC-L4-1 (the chain's hash is no policy digest)",
     st(r, "VLC-L3-1a") == "FAIL" and st(r, "VLC-L4-1") == "FAIL")
# the residual, disclosed: the same relabelling with the epoch class also taken
# out of marker_classes. The bytes of a relabelled record whose class claims no
# other role are the bytes of a genuine declaration; only the mapping differs,
# and the report pins the mapping with adapter_sha256. Expected to fail.
atk2 = copy.deepcopy(atk); atk2["marker_classes"] = ["END"]
r = run(LC, atk2)
emit("residual closed?! relabelling with marker_classes also edited stays at structural L2 -- remove the xfail marker",
     r["structural_level"] == 2,
     xfail=f"relabelling a record no other role claims still reaches structural L{r['structural_level']} "
           f"(not L4: the policy half is refused) -- a mapping, pinned by adapter_sha256; disclosed in EXT-025")
emit("every report pins the mapping its levels are relative to (adapter_sha256)",
     isinstance(r.get("adapter_sha256"), str) and len(r["adapter_sha256"]) == 64)

# per_record: a constant field that is not a digest, on an honest L3 log
pr = copy.deepcopy(base)
pr["policy"] = {"mode": "per_record", "digest_field": "model", "change_class": "POLICY",
                "replay": {"deterministic": True, "reference": "x"}}
r = run("examples/L3-coverage.jsonl", pr)
emit("per_record pointed at a constant non-digest field (model): VLC-L4-1 FAIL, structural L3 (1.4-draft: L4)",
     st(r, "VLC-L4-1") == "FAIL" and r["structural_level"] == 3)
# per_record: digests that change with no change record between them
recs = [json.loads(l) for l in open("examples/L3-coverage.jsonl") if l.strip()]
k = 0
for x in recs:
    if x["class"] == "inference":
        x["policy_digest"] = ("aa" if k < 30 else "bb") * 32; k += 1
pd = copy.deepcopy(pr); pd["policy"]["digest_field"] = "policy_digest"
r = run(write("switch.jsonl", reseal(recs)), pd)
emit("per_record digests that switch mid-log with no policy change record: VLC-L4-2 FAIL",
     st(r, "VLC-L4-2") == "FAIL")

# chain_root: rooted at a field that is not a digest
recs = [json.loads(l) for l in open("examples/L3-coverage.jsonl") if l.strip()]
root = sha(recs[0]["producer"])
cr = copy.deepcopy(base)
cr["integrity"]["root"] = {"kind": "field_of_first_record", "field": "producer", "transform": "sha256"}
cr["policy"] = {"mode": "chain_root", "digest_field": "producer", "change_class": "POLICY",
                "replay": {"deterministic": True, "reference": "x"}}
r = run(write("producer-rooted.jsonl", reseal(recs, root, first_is_root=True)), cr)
emit("chain_root on a field that is not a digest (producer name): VLC-L4-1 FAIL (1.4-draft: PASS, structural L4)",
     st(r, "VLC-L4-1") == "FAIL" and st(r, "VLC-L1-1") == "PASS")
r = run("examples/L4-policybound.jsonl", json.load(open("adapters/generic-appjsonl-policy.json")))
emit("positive control: the policy-rooted example still passes VLC-L4-1 and scores structural L4",
     st(r, "VLC-L4-1") == "PASS" and r["structural_level"] == 4)

oo = copy.deepcopy(base); oo["policy"] = {"mode": "observation_only"}
r = run("examples/L3-coverage.jsonl", oo)
emit("observation_only no longer passes the structural VLC-L4-1 on the adapter's word", st(r, "VLC-L4-1") == "FAIL")
ne = json.load(open("adapters/aws-cloudtrail-digest.json"))
r = run("examples/third-party/cloudtrail-digests.jsonl", ne)
emit("non_enumerable no longer passes the structural VLC-L3-6 on the adapter's word", st(r, "VLC-L3-6") == "FAIL")
r = run("examples/L3-coverage.jsonl", base)
emit("VLC-L3-5 reads only the adapter's non-event list and is reported attested",
     r["requirements"]["VLC-L3-5"]["class"] == "attested")
recs = [json.loads(l) for l in open("examples/L3-coverage.jsonl") if l.strip()]
next(x for x in recs if x["class"] == "COVERAGE")["unattached_here"] = "/v1/chat"
r = run(write("twocats.jsonl", reseal(recs)), base)
emit("a source declared both attached and unattached: VLC-L3-1a FAIL", st(r, "VLC-L3-1a") == "FAIL" and st(r, "VLC-L1-1") == "PASS")
print("DONE|")
PYU
) || true
U18F=$(mktemp); printf '%s\n' "$U18" | tr -d '\r' > "$U18F"
# a crash inside the block must not read as a pass
grep -q '^DONE|' "$U18F" || bad "section block U18 did not run to completion (a crash, or an API the checker lacks)"
while IFS='|' read -r V M; do
  case "$V" in DONE) ;; OK) ok "$M" ;; XFAIL) xfail "$M" ;; *) bad "$M" ;; esac
done < "$U18F"; rm -f "$U18F"

hr
echo "19. VERDICTS, NOT CRASHES -- and exit codes that mean one thing each (EXT-023, EXT-024)"
# 0: a report was produced (and every --expect was met); 1: an --expect was not
# met; 2: no verdict was possible (usage or adapter error). A log that is empty,
# not UTF-8 or not JSON is a verdict -- L0, with the reason -- not a crash.
U19=$(python3 - <<'PYU'
import hashlib, json, os, subprocess, sys, tempfile
d = tempfile.mkdtemp()
canon = lambda o: json.dumps(o, sort_keys=True, separators=(",", ":"))
sha = lambda s: hashlib.sha256(s.encode()).hexdigest()
G = "adapters/generic-appjsonl.json"
def run(log, ad=G, *extra):
    p = subprocess.run(["python3", "conformance.py", "--log", log, "--adapter", ad, "--json", *extra],
                       capture_output=True, text=True)
    try: return p.returncode, json.loads(p.stdout)
    except Exception: return p.returncode, None
def st(r, rid): return (r or {}).get("requirements", {}).get(rid, {}).get("status", "ABSENT")
def emit(msg, cond): print(("OK" if cond else "BAD") + "|" + msg)
def reseal(recs):
    prev, out = "00" * 32, []
    for r in recs:
        r = {k: v for k, v in r.items() if k != "hash"}
        if r["class"] == "END": r["head"] = prev
        r["hash"] = sha(prev + canon(r)); prev = r["hash"]; out.append(r)
    return out
def write(name, text):
    p = os.path.join(d, name); open(p, "wb").write(text if isinstance(text, bytes) else text.encode()); return p

rc, r = run(write("empty.jsonl", ""))
emit("an empty log is a verdict: L0, VLC-L1-1 FAIL, exit 0 (1.4-draft: IndexError)",
     rc == 0 and r and r["structural_level"] == 0 and st(r, "VLC-L1-1") == "FAIL")
recs = [json.loads(l) for l in open("examples/L2-accounted.jsonl") if l.strip()]
recs[-1]["records"] = 40.0
rc, r = run(write("float.jsonl", "\n".join(canon(x) for x in reseal(recs)) + "\n"))
emit("a produced count of 40.0 is not an integer: VLC-L2-1 FAIL, identity not computed (1.4-draft: read as 40, L2 PASS)",
     rc == 0 and st(r, "VLC-L2-1") == "FAIL" and st(r, "VLC-L2-5") == "FAIL")
recs[-1]["records"] = "forty"
rc, r = run(write("str.jsonl", "\n".join(canon(x) for x in reseal(recs)) + "\n"))
emit("a produced count of \"forty\": VLC-L2-1 FAIL and a report, exit 0 (1.4-draft: ValueError)",
     rc == 0 and st(r, "VLC-L2-1") == "FAIL")
# EXT-024: two logs differing only in an invalid byte used to hash identically,
# because both bytes decoded to U+FFFD. The chain below is sealed over U+FFFD.
L1 = [json.loads(l) for l in open("examples/L1-hashchain.jsonl") if l.strip()]
L1[3]["model"] = "acme-�"
body = "\n".join(canon(x) for x in reseal(L1)) + "\n"
raw = body.encode().replace("acme-\\ufffd".encode(), b"acme-\xff")
rc, r = run(write("badutf8.jsonl", raw))
emit("an undecodable byte is not replaced and hashed: L0, VLC-L1-1 FAIL naming UTF-8 (1.4-draft: L1 PASS)",
     rc == 0 and st(r, "VLC-L1-1") == "FAIL" and "UTF-8" in r["requirements"]["VLC-L1-1"]["note"])
rc, r = run("examples/L1-hashchain.jsonl", write("bad.json", "{"))
emit("an adapter that is not JSON: exit 2, JSON error object (1.4-draft: traceback, exit 1)",
     rc == 2 and r and r.get("error") == "adapter")
a = json.load(open(G)); a["integrity"]["mechanism"] = "sha512-imaginary"
rc, r = run("examples/L1-hashchain.jsonl", write("mech.json", json.dumps(a)))
emit("an unknown integrity mechanism: exit 2 (1.4-draft: exit 1)", rc == 2 and r and r.get("error") == "adapter")
a = json.load(open(G)); a["loss"]["produced"] = {"kind": "sum_of_end_marker_fields"}
rc, r = run("examples/L2-accounted.jsonl", write("nofields.json", json.dumps(a)))
emit("a produced kind with no fields: exit 2 (1.4-draft: KeyError)", rc == 2)
rc, r = run(os.path.join(d, "no-such-log.jsonl"))
emit("a log file that does not exist: exit 2 (1.4-draft: scored L0, exit 0)", rc == 2 and r and r.get("error") == "usage")
rc, r = run("examples/L1-hashchain.jsonl", G, "--expect-head", "not-hex")
emit("an anchor that is not 64 hex characters: exit 2", rc == 2)
rc, r = run("examples/L1-hashchain.jsonl", G, "--expect", "3")
emit("an --expect that is not met: exit 1, report still printed", rc == 1 and r and r["attested_level"] == 1)
rc, r = run("examples/L1-hashchain.jsonl", G, "--expect", "1")
emit("an --expect that is met: exit 0", rc == 0)
before = set(os.listdir("examples"))
run("examples/L4-policybound.jsonl", "adapters/generic-appjsonl-policy.json", "--mutate", "flip-byte")
emit("--mutate writes nothing beside the log", set(os.listdir("examples")) == before)
# the programmatic entry point: same dict as --json, no state between calls
sys.path.insert(0, ".")
import conformance as C
H = json.loads(open("examples/L4-policybound.jsonl").read().splitlines()[-1])["hash"]
a1 = C.check("examples/L4-policybound.jsonl", "adapters/generic-appjsonl-policy.json", expect_head="ab" * 32)
a2 = C.check("examples/L4-policybound.jsonl", "adapters/generic-appjsonl-policy.json")
rc, cli = run("examples/L4-policybound.jsonl", "adapters/generic-appjsonl-policy.json")
emit("check() returns the object --json prints", a2 == cli)
emit("check() keeps no state between calls: a wrong anchor fails one call and not the next",
     a1["structural_level"] == 0 and a2["structural_level"] == 4)
try:
    C.check("examples/L1-hashchain.jsonl", os.path.join(d, "bad.json")); raised = False
except C.AdapterError:
    raised = True
emit("check() raises AdapterError for a malformed adapter", raised)
print("DONE|")
PYU
) || true
U19F=$(mktemp); printf '%s\n' "$U19" | tr -d '\r' > "$U19F"
# a crash inside the block must not read as a pass
grep -q '^DONE|' "$U19F" || bad "section block U19 did not run to completion (a crash, or an API the checker lacks)"
while IFS='|' read -r V M; do case "$V" in DONE) ;; OK) ok "$M" ;; *) bad "$M" ;; esac; done < "$U19F"; rm -f "$U19F"

hr
[ "$XFAIL" -gt 0 ] && echo "$XFAIL expected failure(s), each disclosed above with its reason"
if [ "$FAIL" = "0" ]; then echo "SELFTEST PASS"; else echo "SELFTEST FAIL"; fi
exit $FAIL
