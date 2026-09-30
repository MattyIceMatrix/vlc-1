# Falco, live, with forced syscall drops

Captured 2026-09-30 on a GitHub-hosted runner (ubuntu-24.04, kernel
6.17.0-1022-azure, 4 CPUs, Docker 28.0.4) by `.github/workflows/falco-rekor-capture.yml`
on branch `capture/falco-rekor`, run `run-20260930T112902Z` (everything the script
kept, including the image's `falco_rules.yaml` and `config.d/`, is under
`capture/runs/` on that branch). Falco 0.45.0 (`falcosecurity/falco:0.45.0`, the
latest release on the day; stderr: `Falco version: 0.45.0 (x86_64)`), modern_ebpf
driver, in a privileged container; alerts written by `file_output` with
`json_output: true`.

## What was done

Rule triggers ran with `docker exec` in an unprivileged `alpine:3.20` container
(`vlc-victim`, no host mounts). One round is: `cat /etc/shadow` (stable rule *Read
sensitive file untrusted*), `echo x > /etc/vlc-<phase>-<n>` (the capture's own rule
*VLC capture write below etc*, `vlc_rules.yaml`; the stable ruleset has no write-below-etc
rule), `docker exec -t ... sh -c ...` (*Terminal shell in container*) and
`ln -sf /etc/shadow ...` (*Create Symlink Over Sensitive Files*). Phase A: 3 rounds,
quiet. Phase B: 10 rounds while four more containers ran `find /` and `/bin/true`
loops, with the ring buffer cut to one 1 MB buffer shared by all CPUs
(`engine.modern_ebpf.buf_size_preset: 1`, `cpus_for_each_buffer: 0`; the image default
is preset 4, 8 MB, one buffer per 2 CPUs). Phase C: 3 rounds after the load stopped.
Timestamps are in `*/triggers.txt`.

Two runs, same load, same buffer; the config changes are in `tuned.diff` and
`default-run.diff` against the image's `falco.default.yaml`:

| run | `syscall_event_drops` | drop alerts in the stream | their `n_drops` sum | kernel drop counter at the end (side file) | Falco's exit summary |
|---|---|---|---|---|---|
| `tuned` -> `falco-live-full.jsonl` | threshold 0, rate 1 (actions `[log, alert]`, max_burst 1: defaults) | 4 | 8081 | `scap.n_drops` 8081 of 9035905 events | `event drop detected: 4 occurrences` |
| `default` -> `falco-live-default.jsonl` | image defaults: threshold .1, actions `[log, alert]`, rate .03333, max_burst 1 | **0** | -- | `scap.n_drops` **11694** of 9131659 events | `event drop detected: 0 occurrences` |

The side file is `metrics.output_file` (`*/metrics.jsonl`), which both runs enabled
so the true drop total is known; it is not part of the alert stream. The tuned run
also had `metrics.output_rule` on (the image default once metrics are enabled), so its
stream carries 15 `Falco internal: metrics snapshot` alerts with the same monotonic
counters. In both runs every trigger alerted: 16 of each of the four rules. The four
drop alerts are stamped 11:26:42 to 11:26:48; the first phase-B round finished at
11:26:48.19. `falco.outputs_queue_num_drops` was 0 at the end of both runs.

## Why the default run has no drop alert

`userspace/falco/event_drops.cpp` at tag 0.45.0: once a second Falco takes the delta
of the kernel counters; `if(delta.n_drops > 0)` (line 98) it computes the ratio of
drops to events and acts only `if(ratio > m_threshold)` (line 104) -- the occurrence
counter behind the exit summary is incremented inside that test (line 105) -- and
then only if the token bucket has a token (line 109). The `log` action logs at DEBUG
(line 147), below the image default `log_level: info` (`falco.default.yaml` line
1029), so neither run printed a drop line to stderr. In the default run the worst
second in the side file dropped 3.9% of its events (7414 of 191251), under the 10%
threshold (the side file's one-second intervals are not aligned with Falco's own
one-second windows; the exit summary's 0, counted inside the threshold test, is the
direct evidence that no window crossed it). So 11694 dropped syscalls left no trace in
the alert stream, in Falco's log or in Falco's own occurrence count. The image's `falco.yaml` says the drop alert is enabled by
default (lines 1120-1121) and the defaults are at lines 1134-1152.

## Score

All three files score **L0** on the same 12 failed requirements (VLC-L1-1/2/3,
L2-1, L2-5, L3-1a, L3-6, L4-1, L5-3/4/5/6); CI checks full vs scrubbed and full vs
default requirement by requirement. VLC-L5-1 passes as declared: the record is
written by a separate privileged process from kernel events, outside the reach of
the container that triggered it (see the adapter's boundary statement for what a
host root can still do). The in-band drop statement does not raise the score: it
counts syscall events, not alert records, it is not integrity-bound, and nothing in
the stream states how many alerts were produced.

## Files

- `convert.py` -- `python3 convert.py {tuned,default}/events.json [--scrub]`;
  re-serializes each alert unchanged, `--scrub` removes the first *Read sensitive
  file untrusted* alert.
- `tuned/`, `default/` -- `events.json` (the alert file), `metrics.jsonl` (side
  file), `falco.stderr.txt`, `triggers.txt`.
- `falco.default.yaml` -- the image's `/etc/falco/falco.yaml`; `tuned.diff`,
  `default-run.diff`; `vlc_rules.yaml`.

```sh
python3 convert.py tuned/events.json           > ../falco-live-full.jsonl
python3 convert.py tuned/events.json --scrub   > ../falco-live-scrubbed.jsonl
python3 convert.py default/events.json         > ../falco-live-default.jsonl
```

## Not established

One run of each configuration, one kernel, one runner. The storm dropped under 4%
of events in any second; a load heavy enough to cross the 10% default threshold was
not tried, so this capture does not show whether the default configuration reports
drops at that level. Whether dropped syscalls cost any rule hit was not
demonstrated: every trigger here alerted. At start-up, in both runs, Falco's libs (libpman) reported
failures to attach the TOCTOU-mitigation programs for connect, creat, open, openat and openat2 (stderr:
"Detection will continue to work, but TOCTOU mitigation may not properly work").
Not confirmed by the Falco maintainers.
