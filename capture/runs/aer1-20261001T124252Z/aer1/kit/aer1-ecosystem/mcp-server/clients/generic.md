# Generic MCP client

Register one stdio server with command `python3` and argument `/absolute/path/to/aer1-ecosystem-pack/mcp-server/server.py`. The server advertises three tools: `verify_receipt`, `emit_receipt`, and `explain_receipt`. Use the client’s normal MCP stdio transport; do not send receipt JSON to a third-party network unless your policy permits it.
