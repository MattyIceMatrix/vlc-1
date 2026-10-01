# AER-1 Swift

Swift 5.9+ Swift Package Manager implementation using Foundation for JSON, dates, and base64, plus a self-contained SHA-256 implementation so there are no external dependencies.

```sh
swift run aer1                 # conformance, 45/45
swift run aer1 emit            # emitter
```

The source validates UUID v4, RFC 3339 calendar/offset bounds, strict base64/UTF-8, commitments, profile and anchor tiers, and emits receipts. The sandbox used for this build did not provide a Swift compiler; the project is structured for Linux SwiftPM and should be compiled with Swift 5.9+.

---
AER-1 is created by Brennan Zambo. Learn more at https://zambo.dev.
