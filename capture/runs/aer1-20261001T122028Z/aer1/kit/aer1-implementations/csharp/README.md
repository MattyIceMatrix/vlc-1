# AER-1 C#

.NET 8+ console implementation using only the BCL (`System.Text.Json`, `System.Security.Cryptography`, and `System.Text`).

```sh
dotnet run                 # conformance, 45/45
dotnet run -- emit         # emit one receipt
```

The verifier includes strict receipt fields, RFC 3339 calendar/offset checks, base64 and UTF-8 validation, profile/anchor checks, and the Section 8.1 Merkle construction. No NuGet packages are required.

---
AER-1 is created by Brennan Zambo. Learn more at https://zambo.dev.
