# AER-1 MCP server

The server exposes `verify_receipt`, `emit_receipt`, and `explain_receipt` over newline-delimited JSON-RPC MCP stdio. It uses Python's standard library so the smoke test is reproducible without network access; it is compatible with the MCP stdio transport and can be launched by any MCP client. If your client requires the SDK, install `mcp` in the configured environment before launch.

```sh
python3 test_server.py
python3 server.py
```

Configure a client to launch `python3 /absolute/path/mcp-server/server.py`. Example conversations include: “Verify this receipt” → PASS/FAIL and reasons; “Emit a receipt for tool X with these inputs and outputs” → JSON receipt; “What does this receipt prove?” → a bounded explanation that distinguishes recorded bytes from external truth.
