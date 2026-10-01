# AER-1 JSON Schema

The canonical draft-2020-12 schema is `aer1.schema.json`, published by convention at `https://zambo.dev/aer1/schema/0.3/receipt.json`. Version `0.3` is stable for this draft; incompatible future changes receive a new versioned URL rather than silently changing the existing schema.

```sh
python3 validate.py receipt.json
python3 test_schema.py
```

The stdlib validator performs JSON-Schema-shaped structural checks plus the AER-1 semantic checks needed for strict base64/UTF-8, RFC 3339 calendar validity, and the SHA-256 commitment. Unknown receipt fields remain allowed. The schema can be referenced by IDEs and CI tools that support JSON Schema 2020-12.
