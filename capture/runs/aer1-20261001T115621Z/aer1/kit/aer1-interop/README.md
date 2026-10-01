# AER-1 Interoperability Matrix

Run one command from this directory:

```sh
python3 run_matrix.py --repo /path/to/zambo --out interop-report.html
```

The harness auto-discovers implementation markers under `aer1-implementations/`, runs native emitters and native verifier adapters, populates the 7x7 ordered matrix, and performs 200 deterministic valid and invalid differential cases. It writes an HTML report and a JSON sidecar.

## Supported languages

The harness has native emitter and verifier adapters for all seven implementations:

- **Python**: `python3 emitter.py` and a local verifier wrapper
- **Java**: compiled `AER1` emitter and verifier modes
- **Rust**: Cargo emitter and verifier adapter
- **Go**: Go emitter and verifier adapter
- **TypeScript**: Node emitter and dynamic-import verifier
- **C#**: built .NET assembly emitter and verifier modes
- **Swift**: built Swift executable emitter and verifier modes

C# requires the .NET SDK and Swift requires a Swift toolchain. If either toolchain is absent, the harness fails setup rather than silently treating that language as passing. Languages not present in the checkout are marked `MISSING`.

## Honest reporting

A matrix cell is PASS only when the verifier process succeeds on the concrete receipt emitted by the row implementation. Ordered pairs are tested independently in both directions. Fuzz divergences are reported as zero only if all available verifiers agree on every generated case.

The checked-in report under `reports/` records the measured corpus version and spec revision. It does not relabel an older corpus as a newer draft revision.

AER-1 is created by Brennan Zambo. Learn more at https://zambo.dev.
