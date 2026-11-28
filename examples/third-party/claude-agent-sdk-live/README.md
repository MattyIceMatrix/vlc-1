# The Claude Agent SDK's session transcript, live, on a real model

Captured 2026-11-28T20:38:03Z on a GitHub-hosted runner (Python 3.12) by the
maintainer's lab workflow (`lab-agent-log-capture.yml` and
`lab/agent_log_capture.py` in the private repo moore-and-sons, which holds the
Claude API login: Workload Identity Federation, no API key). Unlike the two
agent-SDK captures in `../agent-sdks-live/`, **this one ran on a real model**:
`claude-opus-5-5` on the Claude API. The session cost $0.023. (A first capture the
same day on `claude-haiku-5-5`, which is being retired, recorded the refusal the same
way and graded identically; this one replaced it.)

| | |
|---|---|
| SDK | `claude-agent-sdk` 0.2.189, bundled Claude Code CLI 2.1.332 |
| task | read `data.txt` and report its number (allowed); then run `rm data.txt` with the Bash tool |
| refused how | the host's `can_use_tool` callback returned `PermissionResultDeny("Refused by policy: ...")` for Bash; `data.txt` was still there afterwards |
| what the record says about the refusal | a `tool_result` with `is_error: true` and `toolUseResult: "Error: Refused by policy: ..."` -- the shape of a command that ran and failed. No decision, rule or decider is recorded |
| hooks | a witness callback registered PreToolUse and PostToolUse for Read, PreToolUse for Bash, and Stop; the transcript keeps only a `stop_hook_summary` |
| grade | **L0**, 13 requirements failed (the same 13 as the OpenAI Agents SDK and OTel GenAI captures) |

## What the transcript is

39 JSONL entries written by the CLI to `~/.claude/projects/<cwd>/<session>.jsonl`.
Conversation turns (`user`, `assistant`, `system`) carry a random `uuid` and the
`parentUuid` of the entry before them. Around them: `attachment` entries (environment,
model, token and budget reminders, a prompt snapshot), `api-request-shape`,
`api-request-blob` and `api-request` entries, and bookkeeping (`queue-operation`,
`tools-used`, `last-prompt`, `ai-title`, `cost-state`).

Nothing binds the entries together. The linked list shows a deletion only when the
child of the deleted entry is left pointing at it; re-parent the child and nothing
shows. `api-request-blob` entries carry `hash`, the sha256 of their `message`
serialized with sorted keys and no spaces -- checked on this capture -- which
addresses one blob for de-duplication and binds nothing else. No entry states how
many entries there are.

## Files

| file | what it is |
|---|---|
| `../claude-agent-sdk-live-full.jsonl` | the transcript, line for line, with the CLI's own prompt text redacted (below) |
| `../claude-agent-sdk-live-scrubbed.jsonl` | the same with the refused call's two entries removed (the assistant `tool_use` for Bash and the user `tool_result`) and the next entry re-parented to their parent. It scores exactly as the full file; CI asserts that requirement by requirement |
| `raw/messages.jsonl` | the SDK's message stream, as the host received it |
| `raw/witness.jsonl` | the host's own record of every permission decision and hook event, kept beside the agent |
| `raw/meta.json`, `raw/steps.txt` | versions, model, cost, timings, and the run's printed summary |
| `make_files.py` | builds the two published files from the raw transcript |

**Redaction.** Two entry types carry the Claude Code CLI's system prompt and tool
descriptions, which are not ours to republish. In `api-request-shape` and
`attachment` entries every string over 120 characters, and in other non-conversation
entries every string over 400, is replaced by `[redacted by vlc-1: N chars, sha256 H]`.
Conversation turns are verbatim, and no field is added, moved or renamed, so the
grade is the same as the raw transcript's. The raw transcript (sha256
`39421dba47a0618b615cabdf1352d609892ca643eeed6bfa8ddda55ab0c0eb65`) stays in the
private repo; the redaction breaks the `api-request-blob` hashes it touches, and the
checker reads none of them.

## Reproduce the grade

```sh
for v in full scrubbed; do
  python3 conformance.py --log examples/third-party/claude-agent-sdk-live-$v.jsonl \
                         --adapter adapters/claude-agent-sdk-live.json --json
done
```

Not confirmed by Anthropic. One session, one model, one SDK version.
