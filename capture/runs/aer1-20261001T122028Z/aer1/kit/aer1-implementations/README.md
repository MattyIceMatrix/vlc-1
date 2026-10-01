# AER-1 independent implementations

Seven independent implementations of **AER-1 (AI Agent Execution Receipts)**, draft revision -06: Rust, Go, TypeScript, Python, Java, C#, and Swift.

## Conformance

Each implementation runs the live frozen corpus from `https://zambo.dev/aer1/test-vectors/index.json` using the checked-in fixture snapshot under `vectors/`.

| Language | Command | Result |
|---|---|---|
| Rust | `cd rust && cargo run --bin conformance` | **45/45** |
| Go | `cd go && go run ./cmd/conformance` | **45/45** |
| TypeScript | `cd typescript && npm install && npm run conformance` | **45/45** |
| Python | `cd python && python3 conformance.py` | **45/45** |
| Java | `cd java && javac -d classes src/main/java/dev/aer1/AER1.java && java -cp classes dev.aer1.AER1` | **45/45** |
| C# | `cd csharp && dotnet run` | **45/45** |
| Swift | `cd swift && swift run` | **45/45** |

The runners validate the core receipt rules plus the reference-producer profile boundary and anchored transparency-log tier represented in the corpus.

## Layout

- `rust/` — Cargo library, conformance binary, and emitter binary.
- `go/` — standard-library Go package, conformance command, and emitter command.
- `typescript/` — TypeScript source compiled to native Node.js ESM, conformance command, and emitter command.
- `python/` — standard-library Python verifier, emitter, and conformance runner.
- `java/` — single-file Java verifier with direct JDK conformance runner.
- `csharp/` — .NET console project with conformance runner.
- `swift/` — Swift Package Manager project with conformance runner.
- `vectors/` — 45 frozen fixtures and the live index snapshot used by the runners.

## Implemented rules

- Required receipt members and object shape.
- UUID v4/variant validation used by the frozen corpus.
- RFC 3339 syntax, calendar validity, and timezone-offset bounds.
- Base64 decoding with strict padding and strict UTF-8 validation.
- SHA-256 output commitments using `sha256:` plus lowercase hexadecimal.
- Provenance classes from Section 5.
- Reference-producer payload profile (`inputs`) and optional anchor tier.
- Emitters that preserve exact UTF-8 payload bytes and round-trip through the verifier.

## Spec notes and ambiguities

1. Section 3 describes `receipt_schema_version` as a string and gives `0.3` as the reference value. The frozen adversarial corpus treats values other than `0.3` as invalid, so all seven implementations enforce `0.3`.
2. The core draft says "Stable UUID"; the frozen adversarial corpus rejects a UUID with a non-v4 version nibble. The implementations therefore enforce UUID v4 with the RFC variant bits.
3. The draft permits any non-empty `verification_status`, but the receipt table defines `verified` as the passing value and the frozen corpus rejects `pending`. The implementations enforce `verified` for a conforming receipt.
4. The published index contains 45 vectors, including 26 local adversarial vectors not present in the older reference repository checkout. The local snapshot follows the published index as the conformance authority.
5. The draft says "Stable UUID" without specifying case. RFC 4122 defines lowercase as canonical, and the Merkle leaf (Section 8.1) hashes the receipt_id bytes verbatim, so mixed case would fork roots. The conformance kit and all seven implementations now enforce lowercase UUIDs and reject uppercase. (Closed per independent review, emi-ilands, 2026-09-29; enforced 2026-09-30.)
