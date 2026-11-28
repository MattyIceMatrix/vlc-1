"""Build the published files of the Claude Agent SDK capture from its transcript.

The raw transcript stays in the private repo that ran the capture (its sha256 is in
README.md). Two kinds of entry carry the Claude Code CLI's own system prompt and
tool descriptions, which are not ours to republish. In the entries that carry them
(type api-request-shape and attachment) any string longer than 120 characters, and
in every other entry that is not a conversation turn any string longer than 400, is
replaced by "[redacted by vlc-1: N chars, sha256 H]". Conversation turns (type
user / assistant / system) are kept verbatim. No field is added, moved or renamed.

  claude-agent-sdk-live-full.jsonl      the redacted transcript, line for line
  claude-agent-sdk-live-scrubbed.jsonl  the same with the refused Bash call's two
                                        entries removed and the next entry
                                        re-parented to their parent, as a careful
                                        editor would

Usage: python3 make_files.py RAW_TRANSCRIPT.jsonl   (writes next to examples/third-party/)
Blast radius: reads the file named; writes the two files above.
"""
import hashlib
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.dirname(HERE)
TURNS = {"user", "assistant", "system"}
PROMPT_CARRIERS = {"api-request-shape", "attachment"}


def redact(v, limit):
    if isinstance(v, str) and len(v) > limit:
        h = hashlib.sha256(v.encode("utf-8")).hexdigest()
        return f"[redacted by vlc-1: {len(v)} chars, sha256 {h}]"
    if isinstance(v, dict):
        return {k: redact(x, limit) for k, x in v.items()}
    if isinstance(v, list):
        return [redact(x, limit) for x in v]
    return v


def dump(rows, name):
    with open(os.path.join(OUT, name), "w", encoding="utf-8", newline="\n") as f:
        for o in rows:
            f.write(json.dumps(o, ensure_ascii=False, separators=(",", ":")) + "\n")


def main(path):
    rows = [json.loads(l) for l in open(path, encoding="utf-8") if l.strip()]
    full = [o if o.get("type") in TURNS
            else redact(o, 120 if o.get("type") in PROMPT_CARRIERS else 400) for o in rows]
    dump(full, "claude-agent-sdk-live-full.jsonl")

    # the refused call: the assistant entry whose tool_use is Bash, and the user
    # entry carrying its tool_result
    def blocks(o):
        c = (o.get("message") or {}).get("content")
        return c if isinstance(c, list) else []
    call = next(o for o in full if o.get("type") == "assistant"
                and any(b.get("type") == "tool_use" and b.get("name") == "Bash" for b in blocks(o)))
    tid = next(b["id"] for b in blocks(call) if b.get("type") == "tool_use")
    res = next(o for o in full if o.get("type") == "user"
               and any(b.get("tool_use_id") == tid for b in blocks(o)))
    gone = {call["uuid"], res["uuid"]}
    scrub = []
    for o in full:
        if o.get("uuid") in gone:
            continue
        if o.get("parentUuid") == res["uuid"]:
            o = dict(o, parentUuid=call["parentUuid"])
        scrub.append(o)
    dump(scrub, "claude-agent-sdk-live-scrubbed.jsonl")
    print(f"full {len(full)} lines, scrubbed {len(scrub)} lines (removed {sorted(u[:8] for u in gone)})")


if __name__ == "__main__":
    main(sys.argv[1])
