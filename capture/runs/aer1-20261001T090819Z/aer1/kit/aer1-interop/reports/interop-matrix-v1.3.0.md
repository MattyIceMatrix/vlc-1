# AER-1 interoperability matrix report

## Status

This report uses the requested filename `interop-matrix-v1.3.0.md`, but it does not relabel the corpus. The fresh checkout measured here contains **corpus version `1.3.0`** and **spec revision `-03`**, with 43 vectors. No checked-in `v1.4.0` or `-04` corpus was present at commit `586dafd8b2458a5a789da1f69c8aaa1d2aaaf11c`.

Within that actual frozen corpus, all seven implementations are present and every ordered emitter/verifier pair passed: **49/49 PASS**. Differential fuzzing found **0 divergences** across the harness's 200 deterministic cases.

## Methodology

The harness discovers implementations from markers under `aer1-implementations/`. Each implementation emits one receipt using its native emitter. For every emitted receipt, the harness invokes every native verifier, producing a 7 by 7 ordered matrix. An ordered pair means that the receipt emitted by implementation A is verified by implementation B. The reverse pair is tested independently because emitters and verifiers can differ.

A matrix cell is PASS only when the verifier process exits successfully for that concrete receipt. The harness also generates 200 deterministic malformed and adversarial receipts using seed 41. A fuzz divergence is recorded when the boolean verdict differs between languages. The result is PASS only when all observed verdicts agree for that case.

C# and Swift are executed through their built binaries, not through a wrapper that could ignore verifier arguments. Swift's verifier mode is part of the checked-in implementation.

## Results

| Emit \ Verify | python | java | csharp | swift | rust | go | typescript |
|---|---|---|---|---|---|---|---|
| python | PASS | PASS | PASS | PASS | PASS | PASS | PASS |
| java | PASS | PASS | PASS | PASS | PASS | PASS | PASS |
| csharp | PASS | PASS | PASS | PASS | PASS | PASS | PASS |
| swift | PASS | PASS | PASS | PASS | PASS | PASS | PASS |
| rust | PASS | PASS | PASS | PASS | PASS | PASS | PASS |
| go | PASS | PASS | PASS | PASS | PASS | PASS | PASS |
| typescript | PASS | PASS | PASS | PASS | PASS | PASS | PASS |

The machine-readable result is [`matrix-results-v1.3.0.json`](./matrix-results-v1.3.0.json).

## Reproduction

From a fresh clone:

```sh
git clone https://gitlab.com/rambozambodotdev/zambo.git zambo
cd zambo
git checkout 586dafd8b2458a5a789da1f69c8aaa1d2aaaf11c
export PATH=/path/to/swift-6.0.3-RELEASE-ubuntu24.04/usr/bin:$PATH
cd aer1-interop
python3 run_matrix.py --repo .. --out interop-report.html
```

Expected output for this checkout:

```text
AVAILABLE MATRIX: 49/49 PASS; FUZZ DIVERGENCES: 0; MISSING: none
```

Native conformance commands are documented in each implementation README and were also run independently. Environment: Linux-6.18.38+-x86_64-with-glibc2.39; Python 3.12.3; openjdk version "21.0.12.1" 2026-08-18; .NET 8.0.131; go version go1.22.2 linux/amd64; rustc 1.75.0 (82e1608df 2023-12-21) (built from a source tarball); Node v22.13.0; Swift 6.0.3.

## Edge cases and anomalies

The first attempt at the seven-language matrix exposed two harness defects: the C# command path ignored the intended verifier arguments, and Swift lacked a file-verification mode. Both were corrected before this report. The resulting 49/49 run had zero divergences.

The corpus metadata discrepancy is unresolved by design. The repository advertises the requested seven-language proof, but its checked-in index still identifies version `1.3.0` and revision `-03`. This report records that fact so a future v1.4.0/-04 publication can be distinguished from this result.
