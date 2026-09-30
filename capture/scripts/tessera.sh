#!/usr/bin/env bash
# Positive control: a tile-based transparency log built with Trillian Tessera's POSIX
# example (cmd/examples/posix-oneshot), the library Sigstore's Rekor v2 (rekor-tiles)
# is built on. Appends entries in two rounds, keeps the signed checkpoint after each,
# then has Tessera's own client build inclusion proofs for every entry and a consistency
# proof between the two checkpoints, and checks them (capture/scripts/tlogcap.go).
# The signing key is generated here and only the verifier key is kept.
# BLAST RADIUS: GitHub-hosted runner only; writes $OUT/tessera and mktemp dirs.
GW=tessera; . "$(dirname "$0")/lib.sh"
go version | tee -a "$O/steps.txt"
V="${TESSERA_VERSION:-latest}"
run go install "github.com/transparency-dev/tessera/cmd/examples/posix-oneshot@$V"
BIN="$(go env GOPATH)/bin/posix-oneshot"
go version -m "$BIN" > "$O/posix-oneshot.buildinfo.txt" 2>&1
TV=$(awk '$1=="mod" && $2=="github.com/transparency-dev/tessera"{print $3}' "$O/posix-oneshot.buildinfo.txt")
note "tessera module version: ${TV:-unknown}"

# helper: genkey + verify, built against the same tessera version
B=$(mktemp -d); cp "$HERE/tlogcap.go" "$B/main.go"
( cd "$B" && go mod init tlogcap >/dev/null 2>&1 \
  && go get "github.com/transparency-dev/tessera@${TV:-latest}" golang.org/x/mod/sumdb/note \
     github.com/transparency-dev/formats/log github.com/transparency-dev/merkle >>"$O/steps.txt" 2>&1 \
  && go mod tidy >>"$O/steps.txt" 2>&1 && go build -o tlogcap . >>"$O/steps.txt" 2>&1 )
note "[tlogcap build exit $?]"; cp "$B/go.mod" "$O/tlogcap.go.mod" 2>/dev/null
T="$B/tlogcap"

ORIGIN="vlc-1.capture/tessera-live"
K=$(mktemp -d); "$T" genkey "$ORIGIN" > "$K/keys" 2>>"$O/steps.txt"
export LOG_PRIVATE_KEY=$(sed -n 1p "$K/keys"); VKEY=$(sed -n 2p "$K/keys")
echo "$VKEY" > "$O/log.vkey"; note "verifier key: $VKEY (the signing key is not kept)"

LOG=$(mktemp -d)/log; E=$(mktemp -d)
# Each entry is one audit statement, the kind an agent gateway would log.
mk() { printf '%s\n' "$2" > "$E/$1"; }
mkdir -p "$E/r1" "$E/r2"
mk r1/a '{"event":"session_start","agent":"capture-agent","ts":"'"$(date -u +%FT%TZ)"'"}'
mk r1/b '{"event":"tool_call","tool":"read_file","args":{"path":"notes.txt"},"decision":"allow","rule":"allow-read"}'
mk r1/c '{"event":"tool_call","tool":"delete_file","args":{"path":"notes.txt"},"decision":"deny","rule":"no-delete"}'
mk r2/d '{"event":"tool_call","tool":"read_file","args":{"path":"todo.txt"},"decision":"allow","rule":"allow-read"}'
mk r2/e '{"event":"tool_call","tool":"http_post","args":{"url":"https://example.com"},"decision":"deny","rule":"no-egress"}'
mk r2/f '{"event":"session_end","agent":"capture-agent","ts":"'"$(date -u +%FT%TZ)"'"}'
cp -r "$E" "$O/entry-files"

note "\$ posix-oneshot round 1"
"$BIN" --storage_dir="$LOG" --entries="$E/r1/*" > "$O/round1.stdout.txt" 2> "$O/round1.stderr.txt"; note "[exit $?]"
cp "$LOG/checkpoint" "$O/checkpoint.round1"
sleep 1   # posix-oneshot publishes a checkpoint at most every 100ms; let the first one age
note "\$ posix-oneshot round 2"
"$BIN" --storage_dir="$LOG" --entries="$E/r2/*" > "$O/round2.stdout.txt" 2> "$O/round2.stderr.txt"; note "[exit $?]"
cp -r "$LOG" "$O/log"
note "checkpoint.round1:"; cat "$O/checkpoint.round1" >> "$O/steps.txt"
note "checkpoint:"; cat "$LOG/checkpoint" >> "$O/steps.txt"
(cd "$O/log" && find . -type f | sort) > "$O/log-files.txt"

note "\$ tlogcap verify"
"$T" verify "$LOG" "$VKEY" "$O/checkpoint.round1" > "$O/verify.jsonl" 2> "$O/verify.stderr.txt"; note "[exit $?]"

# Negative control: flip one byte of the refused call's entry in a copy of the log.
N=$(mktemp -d)/log; cp -r "$LOG" "$N"
BUNDLE=$(cd "$N" && find tile/entries -type f | sort | tail -1)
python3 - "$N/$BUNDLE" <<'PY'
import sys; p=sys.argv[1]; b=bytearray(open(p,'rb').read())
i=b.find(b'"deny"'); b[i+2]^=0x20; open(p,'wb').write(bytes(b))
print("flipped byte", i+2, "of", p)
PY
note "\$ tlogcap verify (tampered copy: $BUNDLE)"
"$T" verify "$N" "$VKEY" "$O/checkpoint.round1" > "$O/verify-tampered.jsonl" 2> "$O/verify-tampered.stderr.txt"; note "[exit $?]"
