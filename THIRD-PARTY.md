# Scoring other people's logs

**2026-09-12.** VLC-1 is only worth something if it can be applied to logs this
project did not produce. This is that exercise, run against four **open,
publicly documented** formats — not against closed commercial products, whose
internals cannot be checked and about which this document therefore says
nothing.

Every sample under `examples/third-party/` is **shape-accurate synthetic data
built from the public specification**, not a capture. Field names, structures and
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
| **AWS CloudTrail** (digest files) | **L0**, blocked only by **VLC-L1-3** | A real chain: `previousDigestHashValue` over the previous digest **file**, RSA signature in S3 object metadata, and an hour with no activity still emits a digest with `logFiles: []` — a rare explicit *"nothing this interval"* assertion | No end marker. Truncating the newest digest is undetectable **from the chain alone**; you need out-of-band knowledge of which hour it should be. Chain is over files, not events; no dropped-event count exists in the product; scope is in `EventSelector` config, not in the evidence. |
| **Agent tool-call transcripts** (every framework) | **L0** | readability | Written by the audited process. Fails **VLC-L5-1** by construction, whatever else is done to them. |
| this project's kernel journal (live capture) | **L4 structural**, L5 attested | | its L5 rests on a declared trust boundary, and is labelled as such rather than counted as demonstrated |
| this project's journal, **pre-2026-09-12** | **L2** | | failed VLC-L3-1(d); kept as a control |

## Read this the right way

**None of these products is badly engineered.** CloudTrail's digest chain is
careful work and is the best thing in the set. OpenTelemetry's dropped counters
are a genuine loss-accounting primitive. auditd has counted lost records since
before most of this field existed.

The pattern is not incompetence. It is that **integrity was specified and
completeness never was**, so every team built the property someone asked them
for. Three of the four are one design decision from L2:

- OpenTelemetry: put `rejected_log_records` in-band, in the stream, instead of
  only on the metrics path and the response.
- Kubernetes: make `auditID` monotonic per epoch, or emit a `dropped: n` event
  when `audit buffer queue blocked` fires.
- auditd: emit the `audit_lost` delta into `audit.log` as a record, not to dmesg.

None of those is a research problem. They are afternoon-sized changes that nobody
has been asked for, which is precisely the argument for asking in a standard
rather than in a product.

## Reproduce

```sh
python3 conformance.py --log examples/third-party/cloudtrail-digests.jsonl \
                       --adapter adapters/aws-cloudtrail-digest.json
```

Each adapter carries its `sources` inline. Disagree with a scoring by editing the
adapter and re-running; that is a shorter argument than an email.

## Caveat

These are **structural** scores of **formats**, from **public documentation**, on
**synthetic samples**. A deployment can do better than its format allows — sequence numbers
in an attribute, an external signer, an out-of-band coverage statement — and a
vendor who has done so should say which clause they meet and how. That statement
is the deliverable VLC-1 is really asking for.
