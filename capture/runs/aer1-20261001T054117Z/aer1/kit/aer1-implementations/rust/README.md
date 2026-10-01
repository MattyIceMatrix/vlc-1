# AER-1 Rust

Rust implementation of the AER-1 receipt verifier and emitter.

## Run

```sh
cargo run --bin conformance
cargo run --bin emit
```

The conformance command reads `../vectors/index.json` and reports every vector, ending with `CONFORMANCE: 45/45`. `src/lib.rs` exposes `verify`, `profile`, `anchor`, and `emit`.

## Dependencies

- `serde_json` — JSON values and parsing.
- `sha2` — SHA-256 implementation.
- `hex` — lowercase digest encoding.

The verifier performs no network access. The checked-in vector corpus is reproducible offline; updating it is a separate fetch step.
