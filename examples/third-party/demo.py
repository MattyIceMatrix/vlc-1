#!/usr/bin/env python3
"""demo.py -- rerun every case in THIRD-PARTY.md and write the results to DEMO.md.

Runs conformance.py on each sample with the adapter and any held head CI uses, and for
each pair (the log as captured, and the same log with records removed, cut or
resealed) reports which requirement results changed. AER-1 is not a log; its section
shows the saved harness output from each kit commit tested.

Usage, from the repository root:  python3 examples/third-party/demo.py
Standard library only. Writes examples/third-party/DEMO.md and nothing else.
"""
import json, os, subprocess, sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
T = "examples/third-party/"
IH = "04467b72e3231f1deb61e1e15741674e226e3aece0892800d7fc7ace2e7a108d"   # invinoveritas signed Nostr head
S65 = "13d1a8dad24d5b70a5e5b05fc3b7359b14fcfe1f56a1424d8454c371811f36b4"  # JIDEC n 65 Bitcoin-stamped marker
R1 = "d1d2ed1574b70efc82f33f01678111d11e0887d180463251eb52f387a9836519"   # Tessera size-3 checkpoint root
H6 = "8082a0520690ab287e22984de621e3739250545056d715c15e0e6d773ba7318e"   # Tessera size-6 checkpoint root

# (case, how it was obtained, what the pair shows, [(label, file, adapter, extra args)])
CASES = [
 ("agentgateway 1.5.0", "one live run on a GitHub-hosted runner, 2026-09-29",
  "the refused tool call removed", [("as captured", "agentgateway-live-full", "agentgateway-live", []),
                                    ("refused call removed", "agentgateway-live-scrubbed", "agentgateway-live", [])]),
 ("Docker MCP Gateway v0.44.1", "one live run, 2026-09-29", "the refused calls removed",
  [("as captured", "docker-mcp-live-full", "docker-mcp-live", []), ("refused calls removed", "docker-mcp-live-scrubbed", "docker-mcp-live", [])]),
 ("IBM ContextForge 1.0.11", "one live run, 2026-09-29", "the refused calls removed",
  [("as captured", "contextforge-live-full", "contextforge-live", []), ("refused calls removed", "contextforge-live-scrubbed", "contextforge-live", [])]),
 ("Lasso MCP Gateway 1.2.1", "one live run, 2026-09-29", "the refused call removed",
  [("as captured", "lasso-live-full", "lasso-live", []), ("refused call removed", "lasso-live-scrubbed", "lasso-live", [])]),
 ("Bifrost 2.2.3", "one live run, 2026-09-29", "the refused call removed",
  [("as captured", "bifrost-live-full", "bifrost-live", []), ("refused call removed", "bifrost-live-scrubbed", "bifrost-live", [])]),
 ("NVIDIA OpenShell 0.1.2", "one live run, one driver, 2026-09-29", "the six DENIED lines removed",
  [("as captured", "openshell-live-full", "nvidia-openshell-live", []), ("DENIED lines removed", "openshell-live-scrubbed", "nvidia-openshell-live", [])]),
 ("OpenAI Agents SDK 0.22.3", "one live run, mock model endpoint, 2026-09-30",
  "the guardrail-refused call removed, and 25 of 29 items dropped by a full queue",
  [("as captured", "openai-agents-live-full", "openai-agents-live", []), ("refused call removed", "openai-agents-live-scrubbed", "openai-agents-live", []),
   ("queue overflow, 25 of 29 dropped", "openai-agents-live-overflow", "openai-agents-live", [])]),
 ("OpenTelemetry GenAI spans", "one live run, mock model endpoint, 2026-09-30", "the refused call removed",
  [("as captured", "otel-genai-live-full", "otel-genai-live", []), ("refused call removed", "otel-genai-live-scrubbed", "otel-genai-live", [])]),
 ("Falco 0.45.0", "one live run per configuration, 2026-09-30",
  "a rule alert removed, and the default configuration that dropped 11694 syscalls with no drop alert",
  [("tuned, as captured", "falco-live-full", "falco-live", []), ("rule alert removed", "falco-live-scrubbed", "falco-live", []),
   ("default configuration", "falco-live-default", "falco-live", [])]),
 ("Trillian Tessera v1.0.4 (positive control)", "one live run, 2026-09-30", "one entry removed; then the full log against held checkpoints",
  [("as captured", "tessera-live-full", "tessera-live", []), ("one entry removed", "tessera-live-scrubbed", "tessera-live", []),
   ("full, against held size-3 and size-6 checkpoints", "tessera-live-full", "tessera-live", ["--expect-root", R1, "--expect-head", H6])]),
 ("invinoveritas verdict ledger (positive control)", "public API and Nostr relays, 2026-09-30",
  "the newest entry dropped, on the log alone and against the signed Nostr head",
  [("log alone", "invinoveritas-ledger-live-full", "invinoveritas-ledger-live", []),
   ("newest entry dropped, log alone", "invinoveritas-ledger-live-truncated", "invinoveritas-ledger-live", []),
   ("against the signed head", "invinoveritas-ledger-live-full", "invinoveritas-ledger-live", ["--expect-head", IH]),
   ("newest entry dropped, against the signed head", "invinoveritas-ledger-live-truncated", "invinoveritas-ledger-live", ["--expect-head", IH])]),
 ("JIDEC ledger, n 65 export (scored by its operator)", "live export, 2026-09-30",
  "the same export cut at n 64 and resealed consistently, against the Bitcoin-stamped n 65 head",
  [("log alone", "jidec-ledger-chained-n65", "jidec-ledger-chained", []),
   ("against the n 65 stamp", "jidec-ledger-chained-n65", "jidec-ledger-chained", ["--expect-head", S65]),
   ("cut at n 64 and resealed, log alone", "jidec-ledger-chained-n65-resealed-64", "jidec-ledger-chained", []),
   ("cut at n 64 and resealed, against the n 65 stamp", "jidec-ledger-chained-n65-resealed-64", "jidec-ledger-chained", ["--expect-head", S65])]),
 ("MCP tool calls (from public documentation)", "synthetic, shape-accurate", "the same session recorded by a host connected to one server",
  [("full session", "mcp-toolcall", "mcp-toolcall", []), ("partial host", "mcp-toolcall-partial-host", "mcp-toolcall", [])]),
 ("Fab equipment, SECS-II/GEM (from public documentation)", "synthetic, shape-accurate", "the same excursion under a sparse sampling plan",
  [("full trace", "fab-equipment-full", "fab-equipment-secsgem", []), ("sampled trace", "fab-equipment-sampled", "fab-equipment-secsgem", [])]),
 ("OpenTelemetry OTLP logs (from public documentation)", "synthetic, shape-accurate", "", [("sample", "otlp-logs", "otel-otlp-logs", [])]),
 ("Kubernetes audit (from public documentation)", "synthetic, shape-accurate", "", [("sample", "k8s-audit", "k8s-audit", [])]),
 ("Linux auditd (from public documentation)", "synthetic, shape-accurate", "", [("sample", "linux-auditd", "linux-auditd", [])]),
 ("AWS CloudTrail digests (from public documentation)", "synthetic, shape-accurate", "", [("sample", "cloudtrail-digests", "aws-cloudtrail-digest", [])]),
]


def run(f, adapter, extra):
    cmd = [sys.executable, "conformance.py", "--log", T + f + ".jsonl", "--adapter", "adapters/" + adapter + ".json", "--json"] + extra
    r = json.loads(subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True).stdout)
    req = {k: v["status"] for k, v in r["requirements"].items()}
    shown = "python3 conformance.py --log " + T + f + ".jsonl --adapter adapters/" + adapter + ".json" + "".join(
        " " + (a if a.startswith("--") else a[:12] + "…") for a in extra)
    return r["structural_level"], r["attested_level"], req, shown


def main():
    out = ["# Every case, rerun", "",
           "Generated by `examples/third-party/demo.py` from the files in this repository. Each",
           "case was first captured where its line says (live cases on GitHub-hosted runners;",
           "see `THIRD-PARTY.md`). Here each sample is scored again, and where a case has a",
           "second file with records removed, cut or resealed, the table shows whether the",
           "score noticed. **Same result** means the removal is invisible to a reader holding",
           "only that file; **caught** means a check that passed now fails.", "",
           "Rerun it yourself: `python3 examples/third-party/demo.py`", ""]
    for name, how, shows, runs in CASES:
        out += ["## " + name, "", "*" + how + "*" + ((". Pair: " + shows + ".") if shows else "."), "",
                "| file | structural | attested | failed requirements | compared with the first row |", "|---|---|---|---|---|"]
        base = None; cmds = []
        for label, f, ad, extra in runs:
            s, a, req, shown = run(f, ad, extra)
            failed = sorted(k for k, v in req.items() if v == "FAIL")
            if base is None:
                cmp_ = "—"; base = req
            else:
                ch = sorted(k for k in set(req) | set(base) if req.get(k) != base.get(k))
                real = [k for k in ch if req.get(k) and base.get(k)]
                skipped = len(ch) - len(real)
                cmp_ = "**same result**" if not ch else "**caught**: " * any(base.get(k) == "PASS" and req.get(k) == "FAIL" for k in real) + \
                    ", ".join(f"{k} {base.get(k)}→{req.get(k)}" for k in real) + \
                    (f" (and {skipped} later checks no longer reached)" if skipped else "")
            out.append(f"| {label} | L{s} | L{a} | {len(failed)} | {cmp_} |")
            cmds.append(shown)
        out += ["", "```sh"] + cmds + ["```", ""]
    out += ["## AER-1, IETF agent-receipt draft", "",
            "*Not a log: the draft's own reference verifier, run against the VLC-1 tamper cases",
            "(`aer1-07/chain_attacks.py`). The kit is not in this repository, so this section",
            "shows the saved output from each kit commit tested.* Details: `THIRD-PARTY.md`,",
            "*Cross-testing another draft's chain: AER-1*.", ""]
    for c, f in [("aff1330 (draft -07)", "results-kit-aff1330.txt"), ("e1430ec (draft -08)", "results-kit-e1430ec.txt"),
                 ("4edbcbb (fixes in)", "results-kit-4edbcbb.txt")]:
        p = os.path.join(ROOT, T, "aer1-07", f)
        if os.path.exists(p):
            last = [l for l in open(p).read().splitlines() if l.strip()][-1]
            out.append(f"- kit `{c}`: {last} ([output](aer1-07/{f}))")
    out.append("")
    open(os.path.join(ROOT, T, "DEMO.md"), "w").write("\n".join(out))
    print("wrote", T + "DEMO.md")


if __name__ == "__main__":
    main()
