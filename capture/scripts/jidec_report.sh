#!/usr/bin/env bash
# jidec_report.sh -- fetch the current JIDEC export + head and grade them with the
# reference checker, for the signed report requested in issue #12.
# BLAST RADIUS: GitHub-hosted runner only; GET requests only; writes only under $OUT/jidec.
set -u
O="$OUT/jidec"; mkdir -p "$O"
note(){ echo "$*" | tee -a "$O/steps.txt"; }
get(){ code=$(curl -sSL -A "vlc-1-capture (github.com/MattyIceMatrix/vlc-1)" -o "$O/$2" -w '%{http_code}' "$1"); note "GET $1 -> $code ($(stat -c %s "$O/$2" 2>/dev/null) bytes)"; [ "$code" = 200 ] || rm -f "$O/$2"; }
L=https://ledger.horizonshield.dev
get $L/ledger/export.jsonl export.jsonl
get $L/ledger/head head.json
[ -f "$O/export.jsonl" ] || { note "no export; abort"; exit 0; }
sha256sum "$O/export.jsonl" "$O/head.json" | tee -a "$O/steps.txt"
note "head body: $(cat "$O/head.json")"
EXPECT_HEAD=$(python3 -c "import json,sys;d=json.load(open('$O/head.json'));print(d.get('head') or d.get('ledger_head') or '')" 2>/dev/null)
note "expect-head: $EXPECT_HEAD"
if [ -n "$EXPECT_HEAD" ]; then
  python3 conformance.py --log "$O/export.jsonl" --adapter adapters/jidec-ledger-chained.json --expect-head "$EXPECT_HEAD" > "$O/grade.txt" 2>&1; note "grade (with --expect-head) exit $?"
else
  python3 conformance.py --log "$O/export.jsonl" --adapter adapters/jidec-ledger-chained.json > "$O/grade.txt" 2>&1; note "grade exit $?"
fi
tail -30 "$O/grade.txt" | tee -a "$O/steps.txt"
note "done $(date -u +%FT%TZ)"
