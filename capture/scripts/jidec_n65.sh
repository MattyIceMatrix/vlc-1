#!/usr/bin/env bash
# jidec_n65.sh -- fetch what is needed to check the JIDEC n 65 stamped head independently.
# BLAST RADIUS: GitHub-hosted runner only; GET requests only; writes only under $OUT/jidec.
set -u
O="$OUT/jidec"; mkdir -p "$O"
note(){ echo "$*" | tee -a "$O/steps.txt"; }
get(){ code=$(curl -sSL -A "vlc-1-capture (github.com/MattyIceMatrix/vlc-1)" -o "$O/$2" -w '%{http_code}' "$1"); note "GET $1 -> $code ($(stat -c %s "$O/$2" 2>/dev/null) bytes)"; [ "$code" = 200 ] || rm -f "$O/$2"; }
L=https://ledger.horizonshield.dev
get $L/ledger/export.jsonl export.jsonl
get $L/ledger/head head.json
for n in 65 66; do get "$L/ledger/$n?format=json" entry-$n.json; done
get "$L/ledger/66/ots" entry-66.ots
get "$L/ledger/66?format=ots" entry-66-b.ots
for h in 969240 969244; do
  get https://blockstream.info/api/block-height/$h bs-$h.hash
  [ -f "$O/bs-$h.hash" ] && get https://blockstream.info/api/block/$(cat "$O/bs-$h.hash") bs-$h.json
  get https://mempool.space/api/block-height/$h mp-$h.hash
  [ -f "$O/mp-$h.hash" ] && get https://mempool.space/api/block/$(cat "$O/mp-$h.hash") mp-$h.json
done
# the operator's survive-v0 drill, for the record of how they check it
git clone -q --depth 1 https://github.com/ogasurfproject-jpg/horizon-shield /tmp/hs 2>&1 | tail -1
echo "horizon-shield commit $(git -C /tmp/hs rev-parse HEAD 2>/dev/null)" >> "$O/steps.txt"
mkdir -p "$O/survive-v0"; cp -r /tmp/hs/workers/hs-ledger/nenrin/survive-v0/. "$O/survive-v0/" 2>/dev/null
find /tmp/hs -iname "*66*.ots" -o -iname "*.ots" | head -20 > "$O/ots-files-in-repo.txt"
for f in $(grep -i "66" "$O/ots-files-in-repo.txt" | head -3); do cp "$f" "$O/repo-$(basename "$f")"; done
pip install -q opentimestamps 2>&1 | tail -1
note "done $(date -u +%FT%TZ)"
