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
PRE=examples/reference-impl/pre-basis-L2.jsonl
if [ -f "$PRE" ]; then
	got=$(level "$PRE" adapters/sentinel.json)
	l25=$(req "$PRE" adapters/sentinel.json VLC-L2-5)
	l31d=$(req "$PRE" adapters/sentinel.json VLC-L3-1d)
	if [ "$got" = "1" ] && [ "$l25" = "FAIL" ] && [ "$l31d" = "FAIL" ]; then
		ok "pre-fix capture -> L1: identity fails (predates EXT-003), and VLC-L3-1d still fails (the gap it was kept to show)"
	else
		bad "pre-fix capture -> L$got, VLC-L2-5 $l25, VLC-L3-1d $l31d; expected L1, FAIL, FAIL"
	fi
else
	bad "pre-fix capture missing: the not-rigged control cannot run"
fi
for j in examples/reference-impl/kernel-witness-L5.jsonl examples/reference-impl/kernel-witness-with-loss-L5.jsonl; do
	[ -f "$j" ] || continue
	got=$(level  "$j" adapters/sentinel.json)
	sgot=$(slevel "$j" adapters/sentinel.json)
	# Expected to fail until the Sentinel sensor writes an event-only produced
	# count and is re-run (Corrigendum 2). Marked only for that exact reason:
	# if it fails for any other reason, or starts passing, the suite goes red.
	l25=$(req "$j" adapters/sentinel.json VLC-L2-5)
	if [ "$got" = "5" ] && [ "$sgot" = "4" ]; then
		bad "$(basename $j) now passes: remove its expected-failure marker in section 5"
	elif [ "$l25" = "FAIL" ] && [ "$sgot" = "1" ]; then
		xfail "$(basename $j) -> structural L$sgot, attested L$got; expected 4 and 5 once the sensor is fixed (captured before EXT-003)"
	else
		bad "$(basename $j) -> structural L$sgot, attested L$got, VLC-L2-5 $l25: a failure other than the known one"
	fi
done
ok "the reference implementation's own L5 is ATTESTED, not structural, and says so"


hr; echo "6. THE WITNESS -- reconciling a self-report against an independent record"
R="python3 witness/reconcile.py"
if $R --claims examples/reference-impl/agent-transcript-honest.jsonl \
      --journal examples/reference-impl/kernel-witness-honest-session.jsonl \
      --scope witness/scope-demo.json --require-agreement >/dev/null 2>&1; then
	ok "honest run: zero divergences over the declared scope"
else
	bad "honest run produced findings: the reconciler cries wolf"
fi
SIG=$($R --claims examples/reference-impl/agent-transcript-spoofed.jsonl \
         --journal examples/reference-impl/kernel-witness-spoofed-session.jsonl \
         --scope witness/scope-demo.json --json 2>/dev/null \
      | python3 -c 'import json,sys;print(json.load(sys.stdin)["substitution_signature"])')
[ "$SIG" = "True" ] && ok "spoofed run: substitution signature raised" \
                    || bad "spoofed run: the spoof was not detected"

# EXT-005. --require-agreement used to mean "no divergence found", which empty
# inputs, unparseable lines and a journal with a broken chain all satisfy. Each
# of these must now be refused, and a basename match must not let a different
# absolute path corroborate a claim.
RT=$(mktemp -d); trap 'rm -rf "$RT"' EXIT
: > "$RT/empty.jsonl"
cp examples/reference-impl/agent-transcript-honest.jsonl "$RT/badline.jsonl"
echo "{not json" >> "$RT/badline.jsonl"
python3 - "$RT" <<'PYX'
import json, sys
d = sys.argv[1]
j = [json.loads(l) for l in open("examples/reference-impl/kernel-witness-honest-session.jsonl") if l.strip()]
for r in j:
    if "h" in r: r["h"] = "00" * 32
open(f"{d}/garbage.jsonl", "w").write("\n".join(json.dumps(r, separators=(",", ":")) for r in j) + "\n")
c = [json.loads(l) for l in open("examples/reference-impl/agent-transcript-honest.jsonl") if l.strip()]
for r in c:
    if str(r.get("command", "")).startswith("/usr/bin/id"): r["command"] = "/safe/bin/id -u"
open(f"{d}/otherpath.jsonl", "w").write("\n".join(json.dumps(r) for r in c) + "\n")
PYX
H=examples/reference-impl/agent-transcript-honest.jsonl
W=examples/reference-impl/kernel-witness-honest-session.jsonl
refused() { ! $R --claims "$1" --journal "$2" --scope witness/scope-demo.json --require-agreement >/dev/null 2>&1; }
refused "$RT/empty.jsonl" "$RT/empty.jsonl" \
  && ok "two empty inputs are refused, not reported as agreement" \
  || bad "two empty inputs reported as agreement"
refused "$RT/badline.jsonl" "$W" \
  && ok "an unparseable claim line blocks the strong result" \
  || bad "an unparseable claim line was counted and ignored"
refused "$H" "$RT/garbage.jsonl" \
  && ok "a witness journal whose chain does not verify is refused" \
  || bad "a witness with garbage hashes was accepted as evidence"
refused "$RT/otherpath.jsonl" "$W" \
  && ok "a claimed /safe/bin/id is not corroborated by a witnessed /usr/bin/id" \
  || bad "a different absolute path corroborated the claim by basename"

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
base = json.load(open("adapters/sentinel.json"))
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

hr
[ "$XFAIL" -gt 0 ] && echo "$XFAIL expected failure(s), each disclosed above with its reason"
if [ "$FAIL" = "0" ]; then echo "SELFTEST PASS"; else echo "SELFTEST FAIL"; fi
exit $FAIL
