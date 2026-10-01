# AER-1 Go

Idiomatic Go implementation using the standard library for JSON, base64, SHA-256, UTF-8, and RFC 3339 checks.

## Run

```sh
go run ./cmd/conformance
go run ./cmd/emit
```

The conformance command reads the repository-level `vectors/` snapshot and reports `CONFORMANCE: 45/45`. The `aer1` package exposes `Verify`, `Profile`, `Anchor`, `Emit`, and `Load`.

No third-party dependencies are required.
