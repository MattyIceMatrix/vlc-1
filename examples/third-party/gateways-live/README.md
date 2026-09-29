# Five MCP / agent gateways, live

Captured 2026-09-29 on GitHub-hosted runners by `.github/workflows/gateway-capture.yml`
on branch `capture/gateways` (run `run-20260929T013114Z`; the earlier runs on that
branch show the attempts that failed and what was changed). Each gateway ran with one MCP
server behind it and a rule that allowed at least one tool call and refused or
altered another. Every call was made with plain `curl` or a short stdio client, so nothing in
the record comes from an agent framework.

| gateway | version | refused how | what its record says about the refusal |
|---|---|---|---|
| agentgateway (Linux Foundation) | 1.5.0 | `mcpAuthorization` rules (allow `echo`, deny `get-sum`) | the same line as a call to a tool that does not exist: `Unknown tool`, HTTP 400, `reason: MCP` |
| Docker MCP Gateway | v0.44.1 | `--tools` allow-list; `--block-secrets` | `Calling tool convert_time` -- the line an executed call gets -- and, for the blocked secret, a scan with no outcome |
| IBM ContextForge | 1.0.11 | PII filter plugin; token without `tools.execute` | in the audit database, `invocation failed` (not flagged as security) and `POST /rpc - 200` rows; the refusals are stated only in the text log |
| Lasso MCP Gateway | 1.2.1 | basic guardrail (masks, does not block) | the masked text, stored as the tool's output, no marker field; a call that failed inside the gateway has no row |
| Bifrost (Maxim AI) | 2.2.3 | `tools_to_execute` allow-list | a correct refusal record -- which the same caller then deleted through `DELETE /api/mcp-logs`, unauthenticated, with the dropped counter still at 0 |

All five score **L0**. For each, `<gateway>-live-scrubbed.jsonl` is the record with the
lines of a refused or altered call removed (rule per gateway in `convert.py`), and scores exactly as the full record does; CI asserts that.
For Bifrost the scrubbed file is not an edit: it is what Bifrost served after the delete.

## Files

- `convert.py` -- one mode per gateway; `python3 convert.py GATEWAY DIR [--scrub]`.
  Adds only a `class` label taken from an existing field; no ordinals.
- `<gateway>/` -- the record as the gateway kept it, the configuration used, the
  binary hash where a binary was downloaded, and `client-view/`: each tool call and
  the response the client received, so the record can be compared with what happened.
  The full capture, including start-up and `tools/list`, is on the capture branch.

Regenerate every JSONL file from these folders:

```sh
for g in agentgateway docker-mcp contextforge lasso bifrost; do
  python3 convert.py $g $g         > ../$g-live-full.jsonl
  python3 convert.py $g $g --scrub > ../$g-live-scrubbed.jsonl
done
```

## What was needed to make each one run

Stated because a capture that needed changes should say so. Run 1 is
`run-20260929T012350Z`, run 2 `run-20260929T012606Z`, both on the capture branch.

- **Docker MCP Gateway**: exited at start because `mcp/time` was not pinned to a
  digest; the capture passed `--verify-signatures=false` rather than pinning.
- **ContextForge**: rejects a server on 127.0.0.1 unless `SSRF_ALLOW_LOCALHOST=true`,
  and refused every permission to a token without `teams: null` and `is_admin`
  (run 2); this run mints the token with `create_jwt_token --admin`.
- **Lasso**: did not start with the current `mcp` SDK 2.x (run 1)
  (`ModuleNotFoundError: mcp.server.fastmcp`); pinned to `mcp<2`. Its flattened tool
  schemas make `read_text_file`'s optional `head`/`tail` required, so reads went
  through `read_multiple_files`.
- **Bifrost**: nothing failed. The config set `disable_auth_on_inference: true` and
  configured no admin authentication and no provider key.
- **agentgateway**: nothing. It listens on all interfaces (`binds` takes a port only);
  on a throwaway runner that does not matter.
