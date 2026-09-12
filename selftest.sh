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
PRE=examples/reference-impl/pre-basis-L2.jsonl
if [ -f "$PRE" ]; then
	got=$(level "$PRE" adapters/sentinel.json)
	[ "$got" = "2" ] && ok "pre-fix capture -> L$got (the gap the checker found was real)" \
	                 || bad "pre-fix capture -> L$got, expected L2: the checker has been loosened"
else
	bad "pre-fix capture missing: the not-rigged control cannot run"
fi
for j in examples/reference-impl/kernel-witness-L5.jsonl examples/reference-impl/kernel-witness-with-loss-L5.jsonl; do
	[ -f "$j" ] || continue
	got=$(level  "$j" adapters/sentinel.json)
	sgot=$(slevel "$j" adapters/sentinel.json)
	if [ "$got" = "5" ] && [ "$sgot" = "4" ]; then
		ok "$(basename $j) -> structural L$sgot, attested L$got"
	else
		bad "$(basename $j) -> structural L$sgot, attested L$got; expected 4 and 5"
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

hr
if [ "$FAIL" = "0" ]; then echo "SELFTEST PASS"; else echo "SELFTEST FAIL"; fi
exit $FAIL
