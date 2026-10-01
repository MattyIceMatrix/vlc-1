# AER-1 CloudEvents binding

Wrap an existing receipt for a CloudEvents-aware bus:

```sh
python3 ce_wrap.py wrap receipt.json > event.json
python3 ce_wrap.py unwrap event.json > receipt.json
node ce_wrap.js wrap receipt.json
python3 test_binding.py
```

The JSON envelope can be published to AWS EventBridge, GCP Eventarc, Azure Event Grid, or Knative using their normal CloudEvents/EventBridge adapters. The receiver unwraps `data` and runs the ordinary AER-1 verifier. The binding is stdlib-only Python and dependency-free Node.
