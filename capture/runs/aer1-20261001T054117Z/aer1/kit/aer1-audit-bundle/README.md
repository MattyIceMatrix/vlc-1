# EU AI Act Article 12 audit-bundle exporter

Run:

```sh
python3 export_audit_bundle.py samples --repo /path/to/zambo --out bundle
python3 test_audit_bundle.py /path/to/zambo
```

The exporter validates every input receipt using the canonical AER-1 core rules and structured anchor checks, copies only valid receipts, writes a field mapping as JSON and Markdown, adds five worked examples, writes a human-readable summary, and records SHA-256 hashes and byte lengths for every bundle file in `manifest.json`.

The mapping cites the official [EUR-Lex Article 12 text](https://eur-lex.europa.eu/eli/reg/2024/1689/oj/eng). It is deliberately careful: Article 12 requires automatic lifetime event logging and specific traceability capabilities, but it does not prescribe the AER-1 eight-field schema. A receipt can provide integrity and traceability evidence without being, by itself, a complete Article 12 compliance determination.

---
AER-1 is created by Brennan Zambo. Learn more at https://zambo.dev.
