#!/usr/bin/env bash
# Falco (falcosecurity) with the modern_ebpf driver, in a privileged container on the
# runner. Three phases per run: rule triggers in an unprivileged container (quiet),
# the same triggers under a syscall storm with a 1 MB ring buffer (to force drops),
# then quiet again. Two runs:
#   tuned    json_output, syscall_event_drops {threshold 0, actions [log, alert],
#            rate 1, max_burst 1}, metrics snapshots as alerts every 5s
#   default  json_output only; syscall_event_drops and metrics.output_rule left as the
#            image's falco.yaml has them
# Both runs also write metrics to a side file (metrics.output_file, not in the alert
# stream) as a witness of the true drop totals: every second in the default run, every
# 5s in the tuned run (its metrics.interval also drives the snapshot alerts).
# BLAST RADIUS: GitHub-hosted runner only; writes $OUT/falco and mktemp dirs; removes
# only the containers it names (vlc-falco, vlc-victim, vlc-load*).
GW=falco; . "$(dirname "$0")/lib.sh"
FV="${FALCO_VERSION:-}"
[ -z "$FV" ] && FV=$(curl -s https://api.github.com/repos/falcosecurity/falco/releases/latest | python3 -c 'import json,sys;print(json.load(sys.stdin)["tag_name"])' 2>/dev/null)
FV="${FV:-latest}"; IMG="falcosecurity/falco:$FV"; note "image: $IMG"
run docker pull "$IMG"
docker image inspect "$IMG" --format '{{.Id}} {{json .RepoDigests}}' >> "$O/steps.txt"
note "kernel: $(uname -r); cpus: $(nproc); page size: $(getconf PAGESIZE)"
cid=$(docker create "$IMG"); docker cp "$cid:/etc/falco/falco.yaml" "$O/falco.default.yaml"
docker cp "$cid:/etc/falco/falco_rules.yaml" "$O/falco_rules.yaml"
docker cp "$cid:/etc/falco/config.d" "$O/config.d.default" 2>/dev/null; docker rm "$cid" >/dev/null
sha256sum "$O/falco.default.yaml" "$O/falco_rules.yaml" >> "$O/steps.txt"
note "image defaults (falco.default.yaml):"
grep -n -A12 '^syscall_event_drops:' "$O/falco.default.yaml" | grep -v '^\S*-\s*#' | tee -a "$O/steps.txt"
grep -n '^json_output:\|^priority:\|^  kind:\|buf_size_preset:\|cpus_for_each_buffer:' "$O/falco.default.yaml" | tee -a "$O/steps.txt"

# Our one custom rule, so there is a "write below /etc" hit (the stable ruleset has none).
cat > "$O/vlc_rules.yaml" <<'YAML'
- rule: VLC capture write below etc
  desc: A file under /etc/vlc- opened for writing (added by the VLC-1 capture; not a Falco rule)
  condition: open_write and fd.name startswith /etc/vlc-
  output: "File below /etc opened for writing (file=%fd.name command=%proc.cmdline)"
  priority: ERROR
  tags: [vlc_capture]
YAML

base() { # $1 = output config file
  cp "$O/falco.default.yaml" "$1"
  yq -i '.json_output = true | .file_output.enabled = true | .file_output.keep_alive = true
    | .file_output.filename = "/out/events.json" | .engine.kind = "modern_ebpf"
    | .engine.modern_ebpf.buf_size_preset = 1 | .engine.modern_ebpf.cpus_for_each_buffer = 0
    | .metrics.enabled = true | .metrics.interval = "1s" | .metrics.output_rule = false
    | .metrics.output_file = "/out/metrics.jsonl" | .metrics.kernel_event_counters_enabled = true
    | .rules_files += ["/vlc/vlc_rules.yaml"]' "$1"
}
base "$O/falco.default-run.yaml"
base "$O/falco.tuned.yaml"
yq -i '.syscall_event_drops.threshold = 0 | .syscall_event_drops.actions = ["log","alert"]
  | .syscall_event_drops.rate = 1 | .syscall_event_drops.max_burst = 1
  | .metrics.interval = "5s" | .metrics.output_rule = true' "$O/falco.tuned.yaml"
diff "$O/falco.default.yaml" "$O/falco.default-run.yaml" > "$O/default-run.diff"
diff "$O/falco.default.yaml" "$O/falco.tuned.yaml" > "$O/tuned.diff"

cleanup_c() { docker rm -f vlc-falco vlc-victim vlc-load1 vlc-load2 vlc-load3 vlc-load4 >/dev/null 2>&1; }
trap 'cleanup_c; cleanup' EXIT

triggers() { # $1 = phase tag, $2 = repeats
  local i
  for i in $(seq 1 "$2"); do
    docker exec vlc-victim cat /etc/shadow > /dev/null
    docker exec vlc-victim sh -c "echo x > /etc/vlc-$1-$i"
    docker exec -t vlc-victim sh -c "echo shell-$1-$i" > /dev/null
    docker exec vlc-victim ln -sf /etc/shadow "/tmp/shadow-$1-$i"
    echo "$1 $i $(date -u +%FT%T.%NZ)" >> "$R/triggers.txt"
  done
}

for m in tuned default; do
  R="$O/$m"; mkdir -p "$R"; cleanup_c
  cfg="$O/falco.tuned.yaml"; [ "$m" = default ] && cfg="$O/falco.default-run.yaml"
  note "=== run $m ($(basename "$cfg"))"
  docker run -d --name vlc-falco --privileged \
    -v /var/run/docker.sock:/host/var/run/docker.sock -v /proc:/host/proc:ro -v /etc:/host/etc:ro \
    -v "$cfg:/etc/falco/falco.yaml:ro" -v "$O/vlc_rules.yaml:/vlc/vlc_rules.yaml:ro" -v "$R:/out" \
    "$IMG" >> "$O/steps.txt" 2>&1
  for i in $(seq 1 60); do docker logs vlc-falco 2>&1 | grep -q "Starting health webserver\|Loaded event sources\|Enabled event sources" && break; sleep 1; done
  sleep 5
  docker run -d --name vlc-victim alpine:3.20 sleep 900 >> "$O/steps.txt" 2>&1
  sleep 2
  triggers A 3
  sleep 3
  for j in 1 2 3 4; do
    docker run -d --name vlc-load$j alpine:3.20 sh -c 'for k in 1 2 3 4; do (while :; do find / -xdev > /dev/null 2>&1; done) & done; while :; do /bin/true; cat /etc/hostname > /dev/null; done' >> "$O/steps.txt" 2>&1
  done
  sleep 5
  triggers B 10
  sleep 30
  docker rm -f vlc-load1 vlc-load2 vlc-load3 vlc-load4 >/dev/null 2>&1
  sleep 5
  triggers C 3
  sleep 8
  docker stop -t 20 vlc-falco >/dev/null 2>&1
  docker logs vlc-falco > "$R/falco.stdout.txt" 2> "$R/falco.stderr.txt"
  sudo chown -R "$(id -u):$(id -g)" "$R"
  note "$m: events.json lines $(wc -l < "$R/events.json" 2>/dev/null); metrics.jsonl lines $(wc -l < "$R/metrics.jsonl" 2>/dev/null)"
  python3 - "$R" <<'PY' | tee -a "$O/steps.txt"
import json, sys, collections
r = sys.argv[1]
c = collections.Counter(); drops = 0
try:
    for l in open(r + "/events.json"):
        if not l.strip(): continue
        o = json.loads(l); c[o.get("rule")] += 1
        if o.get("rule") == "Falco internal: syscall event drop":
            drops += int((o.get("output_fields") or {}).get("n_drops", 0))
except Exception as e: print("events.json:", e)
for k, v in sorted(c.items()): print(f"  {v:5d}  {k}")
print("  sum of n_drops over drop alerts:", drops)
last = None
try:
    for l in open(r + "/metrics.jsonl"):
        if l.strip(): last = json.loads(l)
except Exception as e: print("metrics.jsonl:", e)
if last:
    f = last.get("output_fields", last)
    print("  last side-file metrics:", {k: v for k, v in f.items() if k.endswith("n_drops") or k.endswith("n_evts") or "outputs_queue" in k})
PY
done
docker rm -f vlc-victim >/dev/null 2>&1
