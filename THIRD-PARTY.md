# Scoring other people's logs

**2026-09-12, revised 2026-09-27.** VLC-1 is only worth something if it can be
applied to logs this project did not produce. This is that exercise, run against
eight formats: six scored from their **open, public documentation**, one (NVIDIA
OpenShell, open source) from a single live capture, and one (the JIDEC ledger)
scored by its own operator. It is not run against closed commercial products, whose
internals cannot be checked and about which this document therefore says
nothing.

Except the OpenShell capture and the JIDEC export, which the table labels as
such, every sample under `examples/third-party/` is **shape-accurate synthetic
data built from the public specification**, not a capture. Field names, structures and
chaining are taken from the sources cited per adapter. If a field name is wrong,
the adapter is wrong and a correction is welcome — that is the point of shipping
the adapters as data.

## A note on which number this is

Every score below is the **structural** level — what the delivered evidence
demonstrates on its own, with nothing taken on anyone's word. That is the fair
number to publish about somebody else's format, because none of these producers
supplied an adapter or an evidence manifest and it would be wrong to score them
on assertions they never made. See `SPEC.md` §8.4.

If any of these vendors wants to supply a declaration, the attested number is
theirs to claim and ours to relay, clearly labelled as relayed.

## Results

| producer | structural level | what it has | what stops it |
|---|---|---|---|
| **OpenTelemetry** (OTLP logs) | **L0** | `droppedAttributesCount` and friends; Collector queue metrics; OTLP `partial_success.rejected_log_records` | No integrity binding of any kind in OTLP. No per-record ordinal. Loss is real and counted — on the **metrics path**, which is a different pipeline that fails independently and is not bound to the data. |
| **Kubernetes audit** (`audit.k8s.io/v1`) | **L0** | rich, well-specified event content; an audit **policy** that is genuine coverage information | `auditID` is a random UID, not an ordinal, so holes are invisible. Full-queue discards raise `apiserver_audit_error_total` and the error string *"audit buffer queue blocked"* — neither of which is in the log. No chain, no signature. |
| **Linux auditd** | **L0** | the kernel **counts** discarded records in `audit_lost` | `audit_log_lost()` writes that count to **dmesg**, not to `audit.log`; it is otherwise readable only over netlink. The counter exists and is on the wrong side of the boundary. No default integrity binding. |
| **AWS CloudTrail** (digest files) — *from the public documentation reviewed* | **L0**, blocked only by **VLC-L1-3** | A real chain: `previousDigestHashValue` over the previous digest **file**, RSA signature in S3 object metadata, and an hour with no activity still emits a digest with `logFiles: []` — a rare explicit *"nothing this interval"* assertion | From the public documentation reviewed: no end marker. Truncating the newest digest is undetectable **from the chain alone**; you need out-of-band knowledge of which hour it should be. Chain is over files, not events; the documentation reviewed describes no dropped-event count; scope is in `EventSelector` config, not in the evidence. |
| **MCP tool calls** (`tools/call` over JSON-RPC 2.0) | **L0** | a request/response correlation `id`; a `tools/list` result that is genuine coverage information | The `id` correlates a call with its reply; it is not an ordinal over the delivered file, and hosts assign it per connection, so absent calls leave no hole. No integrity field, no record counter, no requirement to state which servers were connected. NSA's June 2026 MCP information sheet names *"poor or missing audit logs"* as a risk and recommends logging every invocation — and specifies no mechanism for integrity, loss or coverage. |
| **Fab equipment** (SECS-II/GEM over HSMS, SEMI E5/E30/E37) — *scored from public documentation, not from the paywalled standards; see the adapter's `_basis`* | **L0** | `SMPLN`, a real ordinal over the trace samples of one `TRID`; `S2F23`, which names the SVIDs a trace requested | No per-message digest appears in the public documentation or the open-source implementations, and HSMS is a session protocol over TCP/IP — it protects the hop, not the stored row. The ordinal covers trace samples only, not event reports or alarms. The larger loss needs no standard to establish: the **sampling period itself** is undeclared dead time — at one sample a minute, fifty-nine seconds in sixty go unobserved and no record marks them as unobserved rather than uneventful. Which SVIDs were enabled, and which wafers the sampling plan measured, live in equipment configuration. **Each of these is written in the adapter as a question a clause reference would settle.** |
| **NVIDIA OpenShell** 0.1.2 (Open Agent Safety Platform), the sandbox event stream held by the gateway — *one live run, one driver, 2026-09-29, not confirmed by NVIDIA; see the adapter's `_basis`* | **L0**, blocked by **VLC-L1-1** | In this run: every denial carried a reason; every allow named the policy rule that decided it; policy loads and reloads carried the policy's version and full SHA-256; the record was held **outside the agent** (VLC-L5-1 passes) | In this run: no integrity field, no sequence number and no drop accounting were present, and 7 of 75 adjacent line pairs were out of timestamp order. A decision line did not carry the hash of the policy it was decided under. Removing the six DENIED lines leaves a log that scores identically. **This replaces a documentation-based score made earlier the same day**, which assumed the agent could write its own log; in this run it could not. The OCSF JSON file the documentation describes was not produced in this run, on this driver; other drivers and configurations have not been tried. None of this has been confirmed by NVIDIA. **Sentry is not scored.** Reported upstream with a proposed fix: [NVIDIA/OpenShell#3817](https://github.com/NVIDIA/OpenShell/issues/3817). |
| **agentgateway** 1.5.0 (Linux Foundation), JSON request log — *one live run, 2026-09-29, not confirmed by the agentgateway maintainers; see `examples/third-party/gateways-live/`* | **L0**, blocked by **VLC-L1-1** | every MCP request logged with method, tool name, session and status; held outside the agent (VLC-L5-1 passes) | A call refused by the `mcpAuthorization` rules (allow `echo`, deny `get-sum`; `get-sum` is registered by server-everything 2026.8.31, `dist/tools/index.js`) is logged **identically to a call to a tool that does not exist** — same `Unknown tool` error, same HTTP 400, same `reason: MCP`, no policy field. No integrity field, no ordinal, no drop count; config loaded without a hash. |
| **Docker MCP Gateway** v0.44.1, `--log-calls --verbose` on stderr — *one live run, 2026-09-29, not confirmed by Docker* | **L0**, blocked by **VLC-L1-1** | lists enabled servers and tool count at start-up; held outside the agent | A call outside the `--tools` allow-list is logged as `Calling tool convert_time` — the line an **executed** call gets; a call `--block-secrets` refused leaves an argument scan with no outcome. What separates refused from executed is what is absent: the `Running mcp/time`, `took:` and response-scan lines; and the refused call's lines have the same shape as those of a call to a tool that does not exist. No timestamps; according to the source, Docker's allowed/denied audit events are sent only to Docker Desktop. The first start exited because `mcp/time` was not pinned to a digest; the capture passed `--verify-signatures=false` rather than pinning. |
| **IBM ContextForge** 1.0.11, `structured_log_entries` (served by `/api/logs/search`), every audit switch on — *one live run, 2026-09-29, not confirmed by IBM* | **L0**, blocked by **VLC-L1-1** | rich tables: audit trail, security events, structured logs, traces; held outside the agent | With `AUDIT_TRAIL_ENABLED`, `PERMISSION_AUDIT_ENABLED` and `SECURITY_LOGGING_LEVEL=all`: in `structured_log_entries` the PII-plugin block is an ERROR row, `invocation failed`, `is_security_event` 0, no error message, plus a `POST /rpc - 200` row; the token-scope refusal left only `POST /rpc - 200`. `security_events` holds eight authentication successes — including one for each refused request — and neither refusal; `permission_audit_log` is empty. Both refusals are in the **text** log. |
| **Lasso MCP Gateway** 1.2.1, xetrack trace — *one live run, 2026-09-29, not confirmed by Lasso Security* | **L0**, blocked by **VLC-L1-1** and **VLC-L5-1** | a row per traced response with a call id | The guardrail's masking is stored as if it were the tool's output, with no marker field (only `structuredContent` is null on that row); a call that failed inside the gateway has **no row**; requests are not traced. The gateway is a subprocess of the agent's host and writes where the host tells it. Did not start with the current `mcp` SDK 2.x (run `run-20260929T012350Z` on the capture branch). |
| **Bifrost** 2.2.3 (Maxim AI), `mcp_tool_logs` via `/api/mcp-logs` — *one live run, 2026-09-29, not confirmed by Maxim AI* | **L0**, blocked by **VLC-L1-1** and **VLC-L5-1** | of the five records scored, the only one that states a refusal **as** a refusal, with the reason; an out-of-band dropped-write counter | With no admin authentication configured (the capture also set `disable_auth_on_inference`), `DELETE /api/mcp-logs` on the port that executes tools removed the record of the caller's own refused call — `MCP tool logs deleted successfully` — and `/api/logs/dropped` still read 0. Its documentation describes audit logs with HMAC signing as an Enterprise feature covering admin changes, not tool calls. |
| **OpenAI Agents SDK** 0.22.3, trace and span `export()` payloads from its `BatchTraceProcessor` — *one live run, 2026-09-30, mock model endpoint, not confirmed by OpenAI; see `examples/third-party/agent-sdks-live/`* | **L0**, blocked by **VLC-L1-1** and **VLC-L5-1** | a span per model call, tool call, turn and agent, with parent ids and the tool's input and output | A call refused by a tool input guardrail is an ordinary `function` span with `error: null` and the rejection text as its output; no guardrail span was emitted for the tool input guardrail and its decision is not recorded (the SDK has a `guardrail` span type, but it was not used here). With `max_queue_size=4` the exported file held 4 of the 29 items a witness processor recorded; the other 25 were discarded by `put_nowait` on a full queue (`agents/tracing/processors.py` lines 627-630 in 0.22.3), each logged at WARNING level (printed to stderr as the bare line `Queue is full, dropping span.`) and nothing in the trace. The file with the drops scores exactly as the full one. The default queue (8192) dropped nothing in this run; the load at which it overflows was not measured. Processors run in the agent's process, and `set_trace_processors` replaces them. |
| **OpenTelemetry GenAI** spans (`opentelemetry-instrumentation-openai-v2` 2.4b0, `opentelemetry-util-genai` 1.1b0, SDK 1.45.0; latest experimental conventions opted in) — *one live run, 2026-09-30, mock model endpoint, not confirmed by the OpenTelemetry project* | **L0**, blocked by **VLC-L1-1** and **VLC-L5-1** | `chat` spans with model, token counts and, opted in, the messages including tool calls; `execute_tool` spans with tool name, call id, arguments and result | The openai instrumentation records model calls only; the two `execute_tool` spans were written by the application through util-genai. The refused call is recorded, as status ERROR with the application's message and `error.type: PermissionError`; none of the `execute_tool` attributes util-genai lists after the conventions is a policy field, so a refusal and a tool that failed look alike. No integrity field, no ordinal, no drop count; the batch processor was not exercised. The GenAI conventions are not stable (opt-in flag `gen_ai_latest_experimental`; `_incubating` attributes). instrumentation-openai-v2 2.4b0 does not import against util-genai 1.2b0 (found by reading the source, not recorded in this run); 1.1b0 was pinned. |
| **Agent tool-call transcripts** (every framework) | **L0** | readability | Written by the audited process. Fails **VLC-L5-1** by construction, whatever else is done to them. |
| **Falco** 0.45.0 (falcosecurity), modern_ebpf driver, JSON alert stream (`file_output`, `json_output: true`) — *one live run per configuration scored (a second, unscored run replicated it), 2026-09-30, not confirmed by the Falco maintainers; see `examples/third-party/falco-live/`* | **L0**, blocked by **VLC-L1-1** | the most detailed in-band drop statement scored so far: with `syscall_event_drops` threshold 0 and rate 1, four `Falco internal: syscall event drop` alerts whose `n_drops` summed to 8081, exactly the kernel drop counter; every rule trigger alerted (16 of each of four rules); written by a separate privileged process from kernel events (VLC-L5-1 passes as declared) | The drop statement counts syscalls, not alerts, and nothing states how many alerts were produced, so there is no production count; no integrity field, no sequence number. With `syscall_event_drops` at the image defaults (threshold .1, actions `[log, alert]`, rate .03333, max_burst 1; `falco.yaml` lines 1134-1152), the same load dropped 11694 syscalls and the stream held **no drop alert**: no one-second interval in the side metrics file exceeded 3.9% dropped, and `event_drops.cpp` (0.45.0, line 104) acts only above the threshold; the `log` action logs at DEBUG, below the default `log_level: info`, and Falco's own exit summary, which counts the seconds that crossed the threshold, read `event drop detected: 0 occurrences`. That capture, and one with a rule alert removed, score exactly as the tuned one. In the second, unscored run's default configuration one of 16 `Read sensitive file untrusted` triggers produced no alert, in a one-second side-file interval with 4.7% of syscalls dropped and no drop alert; a causal link was not established. |
| **Trillian Tessera** v1.0.4 tile log (C2SP tlog-tiles, Ed25519-signed checkpoint), the library under Sigstore's Rekor v2 — *positive control, one live run, 2026-09-30, POSIX example, not a Rekor deployment, not confirmed by the Tessera or Sigstore maintainers; see `examples/third-party/tessera-live/`* | **L0**, blocked by **VLC-L1-1** and **VLC-L5-1** — *because the checker has no Merkle-tree mechanism* | RFC 6962 Merkle tree with a signed size and root: inclusion proofs for every entry and a consistency proof from the size-3 to the size-6 checkpoint, built by Tessera's client from the tiles, all verified, and a standard-library verifier (`verify_tlog.py`) reproduces all of it; removing one entry is detected | `conformance.py` can recompute only hash chains, so the adapter declares `none` rather than fake a pass; the file with an entry removed, which the verifier rejects, scores exactly as the full one. **A log clearly stronger on integrity than every agent log here scores with them: a gap in the checker, not in the log.** It fails coverage and policy for real: it binds any bytes it is given. VLC-L5-1 fails because in this capture one job wrote the entries and held the key; no witness was configured. |
| **invinoveritas verdict ledger** (babyblueviper), hash chain from entry 40 with the head broadcast as signed Nostr events — *positive control, scored from public data, three live fetches, 2026-09-30, offered for scoring by the operator on PR #3, who supplied no number; not confirmed by the operator; see `examples/third-party/invinoveritas-ledger-live/`* | **L0**, blocked by **VLC-L1-1** and **VLC-L5-1** — *because the checker has no mechanism for this chain* | 230 entries, 40→269: every `content_hash` recomputed from its full record, every `head_hash` from it and the recomputed predecessor, zero link breaks; the newest head event on the relays (NIP-01 id and BIP-340 signature verified, the key `/ledger` publishes) states entry 269 and the head the recomputation reaches. `verify_ledger.py` (standard library) catches a removed, edited or reordered entry from the chain alone, and a dropped newest entry or a consistently rewritten chain only against the signed head | `conformance.py` cannot recompute `sha256(content_hash + "|" + prev_head)`, so the adapter declares `none` rather than fake a pass; the file with the newest entry dropped, which the verifier rejects, scores exactly as the full one. It fails loss, coverage and policy for real: nothing in the chain states what was issued against what was written, which the ledger's own `completeness` block says in its own words. VLC-L5-1 fails because the operator writes the entries and signs the heads. Head events were found only for entries 264–269, on 2 of the 6 relays queried. |
| **JIDEC ledger, before 2026-09-28** (HORIZON SHIELD), *scored by its own operator; kept as a control* | **L0**, blocked by **VLC-L1-1** and **VLC-L1-3** | a real ordinal `n`; SHA-256 over each entry's canonical bytes; every hash anchored individually to Bitcoin through OpenTimestamps | No predecessor binding: entries verify one at a time, so removing one or truncating the newest leaves every survivor valid. A gap in `n` is visible; the tail is not, because nothing states how many entries exist and there is no end marker. The Bitcoin anchor proves a hash existed by a block time, not that the ledger delivered every hash it anchored. The entries are written by the operator whose own work several of them record. |
| **JIDEC ledger** (HORIZON SHIELD), *live export, scored by its own operator after jidec-chain-v1* | **L0** on the log alone, blocked by **VLC-L1-3** (its `jidec-head-v1` end marker is not itself chained, EXT-022); **L1** against the head stamped in its daily Bitcoin batch; blocked from L2 by **VLC-L2-1** and the rest of L2 | `prev_entry_sha256` and `entry_sha256` on every row by this specification's `sha256-canonical-fields` recipe, derived from fields each entry already carried; a `jidec-head-v1` end marker; the head also written into each daily batch whose bytes are stamped to Bitcoin | No loss accounting: nothing states how many submissions arrived or were dropped, only what was appended. Coverage and policy unchanged. Since 1.4.1-draft an unchained end marker no longer carries L1 on the log alone: the tail could be cut and the marker rewritten without recomputing a hash. The stamped batch head is exactly the independently held value that restores it; chaining the marker itself would restore it on the log alone. |
| this project's kernel journal (live capture) | **L4 structural**, L5 attested | | its L5 rests on a declared trust boundary, and is labelled as such rather than counted as demonstrated |
| this project's journal, **pre-2026-09-12** | **L2** | | failed VLC-L3-1(d); kept as a control |

## Read this the right way

**None of these products is badly engineered.** CloudTrail's digest chain is
careful work and is the best thing in the set. OpenTelemetry's dropped counters
are a genuine loss-accounting primitive. auditd has counted lost records since
before most of this field existed.

The pattern is not incompetence. It is that **integrity was specified and
completeness never was**, so every team built the property someone asked them
for. Four of them are one design decision from L2:

- OpenTelemetry: put `rejected_log_records` in-band, in the stream, instead of
  only on the metrics path and the response.
- Kubernetes: make `auditID` monotonic per epoch, or emit a `dropped: n` event
  when `audit buffer queue blocked` fires.
- auditd: emit the `audit_lost` delta into `audit.log` as a record, not to dmesg.
- MCP: write the connected servers and their exposed tools into the transcript as
  a record, and re-emit on `tools/list_changed`. The host already has the list —
  it is how it routes the call.

None of those is a research problem. They are afternoon-sized changes that nobody
has been asked for, which is precisely the argument for asking in a standard
rather than in a product.

## Reproduce

```sh
python3 conformance.py --log examples/third-party/cloudtrail-digests.jsonl \
                       --adapter adapters/aws-cloudtrail-digest.json
```

The MCP pair is the one to run if you only run one:

```sh
for f in mcp-toolcall mcp-toolcall-partial-host; do
  python3 conformance.py --log examples/third-party/$f.jsonl \
                         --adapter adapters/mcp-toolcall.json --json
done
```

`mcp-toolcall.jsonl` is a session in which the agent called a files server, a
partner order API and a mail server. `mcp-toolcall-partial-host.jsonl` is the
**same session** recorded by a host connected to only the files server: the
outbound `http_post` and the `send_email` left no trace at all. The surviving
`id`s run 3, 4, 5 with no hole, because a host numbers per connection. The two
logs are indistinguishable — same level, same failed requirements — and one of
them is missing an agent posting to a third party and sending mail. That is not a
tamper-evidence problem and no amount of hashing the transcript addresses it.

The OpenShell pair is a single live capture of NVIDIA's agent runtime — one run,
one driver, 2026-09-29, not confirmed by NVIDIA:

```sh
for f in openshell-live-full openshell-live-scrubbed; do
  python3 conformance.py --log examples/third-party/$f.jsonl \
                         --adapter adapters/nvidia-openshell-live.json --json
done
```

`openshell-live-full.jsonl` is one sandbox run on a GitHub-hosted runner, converted line for line from `openshell logs` by `openshell-live/convert.py` (the raw output is beside it). Under the default policy the agent's requests to the GitHub API and to example.com were both denied; under NVIDIA's quickstart policy the GitHub request was allowed and example.com was still denied. `openshell-live-scrubbed.jsonl` is the same capture with the six DENIED lines removed. Both score L0 on the same twelve failed requirements. In this run, OpenShell enforced the policy and kept the record out of the agent's reach; what the record, as captured, cannot do is show, to anyone holding it later, that nothing was taken out.

The five gateways were run the same way, each with at least one allowed call and
one call the gateway refused or altered (`examples/third-party/gateways-live/README.md` has the table and what
each needed to start):

```sh
for g in agentgateway docker-mcp contextforge lasso bifrost; do
  for v in full scrubbed; do
    python3 conformance.py --log examples/third-party/$g-live-$v.jsonl \
                           --adapter adapters/$g-live.json --json
  done
done
```

Each `-scrubbed` file removes the lines for a refused or altered call (the rule is
in `convert.py` and each adapter's integrity note); each scores exactly as its
`-full` file does, and CI checks that requirement by requirement.
Bifrost's scrubbed file was produced by Bifrost: it is the table as served after
the unauthenticated delete. The five fail differently — a refusal that looks like
a typo, a refusal that looks like an execution, a refusal kept out of the audit
tables, an alteration that looks like output, and a correct refusal record that
the refused caller could delete — and in none of the five scored records can the
checker tell that anything is missing.

Two agent-SDK trace formats were captured the same way on 2026-09-30, with no API
key: each SDK ran against a local mock OpenAI-compatible endpoint that asks for one
allowed and one refused tool call (`examples/third-party/agent-sdks-live/README.md`):

```sh
for v in full scrubbed overflow; do
  python3 conformance.py --log examples/third-party/openai-agents-live-$v.jsonl \
                         --adapter adapters/openai-agents-live.json --json
done
for v in full scrubbed; do
  python3 conformance.py --log examples/third-party/otel-genai-live-$v.jsonl \
                         --adapter adapters/otel-genai-live.json --json
done
```

Both score L0 and each `-scrubbed` file scores exactly as its `-full` file. The
OpenAI Agents SDK's `-overflow` file is the same run through a
`BatchTraceProcessor` with `max_queue_size=4`: 25 of 29 items were dropped, the SDK
said so only on stderr, and the file scores exactly as the full one. CI checks all
three comparisons requirement by requirement.

Falco and a Tessera transparency log were captured on 2026-09-30 by
`.github/workflows/falco-rekor-capture.yml` (`examples/third-party/falco-live/README.md`,
`examples/third-party/tessera-live/README.md`):

```sh
for v in full scrubbed default; do
  python3 conformance.py --log examples/third-party/falco-live-$v.jsonl \
                         --adapter adapters/falco-live.json --json
done
for v in full scrubbed; do
  python3 conformance.py --log examples/third-party/tessera-live-$v.jsonl \
                         --adapter adapters/tessera-live.json --json
  python3 examples/third-party/tessera-live/verify_tlog.py jsonl \
          examples/third-party/tessera-live-$v.jsonl examples/third-party/tessera-live/log.vkey
done
```

All five score L0. Falco's `-default` file is the same load with the drop settings
left as shipped: 11694 syscalls dropped, no drop alert, and the file scores exactly as
the tuned one. The Tessera pair is the positive control: `verify_tlog.py` accepts the
full file and rejects the scrubbed one, and `conformance.py` scores the two
identically, because it has no mechanism for a Merkle tree. CI checks both.

The invinoveritas verdict ledger was fetched from its public API and public Nostr
relays on 2026-09-30 by `.github/workflows/ledger-capture.yml`
(`examples/third-party/invinoveritas-ledger-live/README.md`):

```sh
for v in full truncated; do
  python3 conformance.py --log examples/third-party/invinoveritas-ledger-live-$v.jsonl \
                         --adapter adapters/invinoveritas-ledger-live.json --json
  python3 examples/third-party/invinoveritas-ledger-live/verify_ledger.py jsonl \
          examples/third-party/invinoveritas-ledger-live-$v.jsonl --mutations
done
```

A second positive control, and the case `--expect-head` exists for: the chain alone
catches a removed, edited or reordered entry, but not a dropped newest entry or a chain
rewritten consistently from genesis; the signed head held on third-party relays catches
both. `conformance.py` scores both files L0, identically, because it has no mechanism for
`head = sha256(content_hash + "|" + prev_head)`. CI checks the verifier, the mutations
and the identical scores.

The fab pair makes the same point on a production line:

```sh
for f in fab-equipment-full fab-equipment-sampled; do
  python3 conformance.py --log examples/third-party/$f.jsonl \
                         --adapter adapters/fab-equipment-secsgem.json --json
done
```

One overlay excursion, one tool, two records of it. In `fab-equipment-full.jsonl`
the trace was re-initialised inside the window, four SVIDs are collected and three
wafers a lot are measured: the stage-Z drift is visible from **16 April** and wafer
W13 is out of the 3.0 nm action limit the same day. In
`fab-equipment-sampled.jsonl` the trace was initialised before the window opened,
the stage-Z SVID is not in the set, and the sampling plan measures wafers 01 and
25 — the two the thermal gradient reaches last. Its first evidence of anything is
the alarm on **24 April**. Eight days of centre wafers out of spec, and the file
does not know it. Both score L0 on the same twelve failed requirements, so nothing
in either one tells a reader which of the two they are holding.

Each adapter carries its `sources` inline. Disagree with a scoring by editing the
adapter and re-running; that is a shorter argument than an email.

## Caveat

These are **structural** scores of **formats**, from **public documentation**, on
**synthetic samples** — except the OpenShell row (one live run, one driver, not
confirmed by NVIDIA) and the JIDEC rows (scored by their own operator). A deployment can do better than its format allows — sequence numbers
in an attribute, an external signer, an out-of-band coverage statement — and a
vendor who has done so should say which clause they meet and how. That statement
is the deliverable VLC-1 is really asking for.
