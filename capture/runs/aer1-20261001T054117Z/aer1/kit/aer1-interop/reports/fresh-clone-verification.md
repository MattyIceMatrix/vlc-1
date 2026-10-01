# Fresh-clone AER-1 verification report

## Scope and qualification

This report was produced from a fresh clone of `https://gitlab.com/rambozambodotdev/zambo` at commit `586dafd8b2458a5a789da1f69c8aaa1d2aaaf11c`. It records a fresh-clone execution result for the repository's checked-in 43-vector corpus. The corpus index identifies version `1.3.0` and spec revision `-03`. It does not claim that the checked-in corpus is already a v1.4.0 or -04 corpus.

## Result

All seven implementations passed every one of the 43 checked-in vectors:

| Implementation | Result |
|---|---|
| Rust | 43/43 |
| Go | 43/43 |
| TypeScript | 43/43 |
| Python | 43/43 |
| Java | 43/43 |
| C# | 43/43 |
| Swift | 43/43 |

## Per-vector result

Every cell below is the native runner result, not a copied result from another implementation.

| Vector | Rust | Go | TypeScript | Python | Java | C# | Swift |
|---|---|---|---|---|---|---|---|
| anchored-bad-leaf-hash | PASS | PASS | PASS | PASS | PASS | PASS | PASS |
| anchored-bad-timestamp | PASS | PASS | PASS | PASS | PASS | PASS | PASS |
| anchored-missing-proof | PASS | PASS | PASS | PASS | PASS | PASS | PASS |
| anchored-valid | PASS | PASS | PASS | PASS | PASS | PASS | PASS |
| missing-inputs | PASS | PASS | PASS | PASS | PASS | PASS | PASS |
| bad-created-at | PASS | PASS | PASS | PASS | PASS | PASS | PASS |
| bad-id | PASS | PASS | PASS | PASS | PASS | PASS | PASS |
| bad-provenance | PASS | PASS | PASS | PASS | PASS | PASS | PASS |
| bytes-not-base64 | PASS | PASS | PASS | PASS | PASS | PASS | PASS |
| hash-bad-format | PASS | PASS | PASS | PASS | PASS | PASS | PASS |
| hash-mismatch | PASS | PASS | PASS | PASS | PASS | PASS | PASS |
| impossible-date | PASS | PASS | PASS | PASS | PASS | PASS | PASS |
| missing-output-hash | PASS | PASS | PASS | PASS | PASS | PASS | PASS |
| non-utf8-bytes | PASS | PASS | PASS | PASS | PASS | PASS | PASS |
| tool-not-object | PASS | PASS | PASS | PASS | PASS | PASS | PASS |
| receipt-01 | PASS | PASS | PASS | PASS | PASS | PASS | PASS |
| receipt-02 | PASS | PASS | PASS | PASS | PASS | PASS | PASS |
| receipt-03-live | PASS | PASS | PASS | PASS | PASS | PASS | PASS |
| aer1-local-valid-01 | PASS | PASS | PASS | PASS | PASS | PASS | PASS |
| aer1-local-valid-02 | PASS | PASS | PASS | PASS | PASS | PASS | PASS |
| aer1-local-valid-03 | PASS | PASS | PASS | PASS | PASS | PASS | PASS |
| aer1-local-valid-04 | PASS | PASS | PASS | PASS | PASS | PASS | PASS |
| aer1-local-valid-05 | PASS | PASS | PASS | PASS | PASS | PASS | PASS |
| aer1-local-invalid-schema | PASS | PASS | PASS | PASS | PASS | PASS | PASS |
| aer1-local-invalid-id | PASS | PASS | PASS | PASS | PASS | PASS | PASS |
| aer1-local-invalid-id-version | PASS | PASS | PASS | PASS | PASS | PASS | PASS |
| aer1-local-invalid-date-day | PASS | PASS | PASS | PASS | PASS | PASS | PASS |
| aer1-local-invalid-date-hour | PASS | PASS | PASS | PASS | PASS | PASS | PASS |
| aer1-local-invalid-date-zone | PASS | PASS | PASS | PASS | PASS | PASS | PASS |
| aer1-local-invalid-tool | PASS | PASS | PASS | PASS | PASS | PASS | PASS |
| aer1-local-invalid-tool-name | PASS | PASS | PASS | PASS | PASS | PASS | PASS |
| aer1-local-invalid-tool-version | PASS | PASS | PASS | PASS | PASS | PASS | PASS |
| aer1-local-invalid-tool-scope | PASS | PASS | PASS | PASS | PASS | PASS | PASS |
| aer1-local-invalid-provenance | PASS | PASS | PASS | PASS | PASS | PASS | PASS |
| aer1-local-invalid-status | PASS | PASS | PASS | PASS | PASS | PASS | PASS |
| aer1-local-invalid-missing-id | PASS | PASS | PASS | PASS | PASS | PASS | PASS |
| aer1-local-invalid-missing-tool | PASS | PASS | PASS | PASS | PASS | PASS | PASS |
| aer1-local-invalid-bytes-format | PASS | PASS | PASS | PASS | PASS | PASS | PASS |
| aer1-local-invalid-bytes-padding | PASS | PASS | PASS | PASS | PASS | PASS | PASS |
| aer1-local-invalid-bytes-utf8 | PASS | PASS | PASS | PASS | PASS | PASS | PASS |
| aer1-local-invalid-hash-format | PASS | PASS | PASS | PASS | PASS | PASS | PASS |
| aer1-local-invalid-hash-mismatch | PASS | PASS | PASS | PASS | PASS | PASS | PASS |
| aer1-local-invalid-missing-hash | PASS | PASS | PASS | PASS | PASS | PASS | PASS |

## Commands

```sh
git clone https://gitlab.com/rambozambodotdev/zambo.git zambo
cd zambo
export PATH=/path/to/swift-6.0.3-RELEASE-ubuntu24.04/usr/bin:$PATH
(cd aer1-implementations/rust && cargo run --quiet --bin conformance)
(cd aer1-implementations/go && go run ./cmd/conformance)
(cd aer1-implementations/typescript && npm run conformance)
(cd aer1-implementations/python && python3 conformance.py)
(cd aer1-implementations/java && mvn -q compile exec:java)
(cd aer1-implementations/csharp && dotnet run)
(cd aer1-implementations/swift && swift run aer1)
```

Each command printed `CONFORMANCE: 43/43`.

## Environment

- OS: Linux-6.18.38+-x86_64-with-glibc2.39
- Python: 3.12.3
- Java: OpenJDK 21.0.12.1
- .NET: 8.0.131
- Go: go1.22.2 linux/amd64
- Rust: rustc 1.75.0
- Node: v22.13.0
- Swift: 6.0.3

## Spec and vector discrepancies

The fetched AER-1 -04 draft at `https://www.ietf.org/archive/id/draft-zambo-aer1-04.txt` describes the core fields, strict UTF-8 commitment checking, provenance, and verification procedure. The repository index remains `1.3.0` with revision `-03`. The draft's Section 5 uses a system-specific `EXECUTED BY ...` class while the vectors exercise concrete implementation names such as `EXECUTED BY PYTHON`, along with the fixed `OBSERVED VIA GATEWAY` and `LOGGED BY AGENT` classes. This is consistent with the draft's statement that the recording-system name is substituted, but it would benefit from an explicit grammar in a future vector revision.

No vector was found that tests every -04 addition, including public URL resolution, chain completeness, signer metadata, or optional batch anchoring. This is a coverage boundary, not a failed conformance result. No separate ambiguity report is filed because the evidence identifies a revision and coverage gap, not a contradictory verdict.
