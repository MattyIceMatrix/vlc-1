#!/usr/bin/env python3
import base64, hashlib, json, sys, uuid

def emit(tool_name, tool_version, scope, payload, *, receipt_id=None, created_at="2026-01-01T00:00:00Z", provenance="EXECUTED BY PYTHON"):
    raw = payload.encode("utf-8") if isinstance(payload, str) else bytes(payload)
    return {"id": receipt_id or str(uuid.uuid4()), "receipt_schema_version":"0.3", "created_at":created_at, "tool":{"name":tool_name,"version":tool_version,"scope":scope}, "provenance_class":provenance, "canonical_bytes":base64.b64encode(raw).decode(), "output_hash":"sha256:"+hashlib.sha256(raw).hexdigest(), "verification_status":"verified"}

if __name__ == "__main__":
    receipt = emit("demo_tool", "1.0.0", "public", json.dumps({"inputs":{"x":1},"outputs":{"ok":True}}, separators=(",",":")))
    print(json.dumps(receipt, indent=2))
