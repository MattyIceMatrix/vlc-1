#!/usr/bin/env python3
"""demo.py -- rerun every case in THIRD-PARTY.md and write the results to DEMO.md.

Runs conformance.py on each sample with the adapter and any held head CI uses, and for
each pair (the log as captured, and the same log with records removed, cut or
resealed) reports which requirement results changed. AER-1 is not a log; its section
shows the saved harness output from each kit commit tested.

Usage, from the repository root:  python3 examples/third-party/demo.py
Standard library only. Writes examples/third-party/DEMO.md and one animated SVG
terminal recording per case under examples/third-party/demo/, and nothing else.
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


W, LH, PAD, COLS = 960, 19, 16, 118
COL = {"cmd": "#e6edf3", "dim": "#8b949e", "del": "#ff7b72", "ok": "#3fb950", "bad": "#f85149",
       "out": "#c9d1d9", "head": "#d2a8ff", "warn": "#e3b341"}


def esc(t):
    return t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


SCENES = []


def svg(title, lines, path):
    SCENES.append({"title": title, "file": os.path.basename(path)[:-4], "lines": [list(x) for x in lines]})
    """lines: [(kind, text)]; each line fades in after the previous, holds, and the scene loops."""
    step, hold = 0.55, 6.0
    n = len(lines); total = n * step + hold
    h = PAD * 2 + 30 + n * LH
    css, body = [], []
    for i, (kind, text) in enumerate(lines):
        t0 = i * step / total * 100
        css.append(f"@keyframes k{i}{{0%,{t0:.2f}%{{opacity:0}}{t0 + 0.5:.2f}%,97%{{opacity:1}}100%{{opacity:0}}}}"
                   f".l{i}{{animation:k{i} {total:.2f}s linear infinite}}")
        text = text if len(text) <= COLS else text[:COLS - 1] + "…"
        body.append(f'<text class="l{i}" x="{PAD}" y="{PAD + 42 + i * LH}" fill="{COL[kind]}">{esc(text)}</text>')
    doc = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{h}" viewBox="0 0 {W} {h}" role="img">'
           f'<title>{esc(title)}</title><style>text{{font:13px ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;'
           f'white-space:pre}}{"".join(css)}</style>'
           f'<rect width="{W}" height="{h}" rx="8" fill="#0d1117" stroke="#30363d"/>'
           f'<circle cx="20" cy="18" r="5" fill="#ff5f57"/><circle cx="36" cy="18" r="5" fill="#febc2e"/>'
           f'<circle cx="52" cy="18" r="5" fill="#28c840"/>'
           f'<text x="72" y="22" fill="#8b949e">{esc(title)}</text>{"".join(body)}</svg>')
    open(path, "w").write(doc)


def slug(name):
    base = name.split(" (")[0].lower()
    out = "".join(c if c.isalnum() else "-" for c in base)
    while "--" in out:
        out = out.replace("--", "-")
    return out.strip("-")


def removed(a, b):
    """records in file a that are not in file b, in file order"""
    lb = set(open(os.path.join(ROOT, T, b + ".jsonl")).read().splitlines())
    return [l for l in open(os.path.join(ROOT, T, a + ".jsonl")).read().splitlines() if l.strip() and l not in lb]


def run(f, adapter, extra):
    cmd = [sys.executable, "conformance.py", "--log", T + f + ".jsonl", "--adapter", "adapters/" + adapter + ".json", "--json"] + extra
    r = json.loads(subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True).stdout)
    req = {k: v["status"] for k, v in r["requirements"].items()}
    run.first = next((f"{k} {v['note']}" for k, v in r["requirements"].items() if v["status"] == "FAIL"), "")
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
           "Rerun it yourself: `python3 examples/third-party/demo.py`. The recordings are",
           "rendered from the same output by `make_videos.py` (needs Pillow and ffmpeg).", ""]
    for name, how, shows, runs in CASES:
        out += ["## " + name, "", "*" + how + "*" + ((". Pair: " + shows + ".") if shows else "."), "",
                "| file | structural | attested | failed requirements | compared with the first row |", "|---|---|---|---|---|"]
        base = None; cmds = []; scene = []; first_file = runs[0][1]; shown_diff = {first_file}
        for label, f, ad, extra in runs:
            if f not in shown_diff and base is not None:
                shown_diff.add(f)
                gone = removed(first_file, f)
                added = removed(f, first_file)
                scene.append(("cmd", f"$ diff {first_file}.jsonl {f}.jsonl"))
                for l in gone[:2]:
                    scene.append(("del", "- " + l))
                if len(gone) > 2:
                    scene.append(("del", f"  … and {len(gone) - 2} more record(s) removed"))
                if added:
                    scene.append(("warn", f"+ {len(added)} record(s) present only in the second file"))
            elif base is None and len(runs) == 1:
                rec = next(l for l in open(os.path.join(ROOT, T, f + ".jsonl")).read().splitlines() if l.strip())
                scene.append(("cmd", f"$ head -1 {f}.jsonl"))
                scene.append(("out", rec))
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
            scene.append(("cmd", "$ " + shown.replace("examples/third-party/", "")))
            scene.append(("out", f"  structural L{s}   attested L{a}   {len(failed)} of {len(req)} requirements fail"))
            if base is req:
                scene.append(("dim", f"  first failure: {run.first}"))
            elif cmp_ == "**same result**" and f == first_file:
                scene.append(("dim", f"  same result as '{runs[0][0]}'"))
            elif cmp_ == "**same result**":
                scene.append(("bad", f"  SAME RESULT as '{runs[0][0]}': the change is invisible to this check"))
            else:
                plain = cmp_.replace("**", "")
                if plain.startswith("caught:"):
                    scene.append(("ok", "  CAUGHT:" + plain[len("caught:"):]))
                else:
                    scene.append(("head", "  changed: " + plain))
        os.makedirs(os.path.join(ROOT, T, "demo"), exist_ok=True)
        svg(name, scene, os.path.join(ROOT, T, "demo", slug(name) + ".svg"))
        i = out.index("## " + name) + 2
        out[i + 1:i + 1] = ["", f"![{name}: recorded run](demo/{slug(name)}.gif)", "",
                            f"[MP4](demo/{slug(name)}.mp4) · [SVG](demo/{slug(name)}.svg)"]
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
    scene = [("dim", "AER-1 reference verifier (Python), VLC-1 tamper cases, saved output per kit commit")]
    for c, f in [("aff1330", "results-kit-aff1330.txt"), ("4edbcbb", "results-kit-4edbcbb.txt")]:
        p = os.path.join(ROOT, T, "aer1-07", f)
        if not os.path.exists(p):
            continue
        scene.append(("cmd", f"$ python3 aer1-07/chain_attacks.py zambo@{c}/aer1-implementations/python"))
        for l in open(p).read().splitlines():
            if l.startswith("GAP") or "seq 1.0" in l:
                scene.append(("bad" if l.startswith("GAP") else "ok", l.rstrip()))
            elif " of 30 as expected" in l:
                scene.append(("head", l.strip()))
    svg("AER-1 cross-test", scene, os.path.join(ROOT, T, "demo", "aer-1.svg"))
    i = out.index("## AER-1, IETF agent-receipt draft") + 1
    out[i + 1:i + 1] = ["", "![AER-1: recorded runs](demo/aer-1.gif)", "", "[MP4](demo/aer-1.mp4) · [SVG](demo/aer-1.svg)"]
    out.append("")
    open(os.path.join(ROOT, T, "DEMO.md"), "w").write("\n".join(out))
    with open(os.path.join(ROOT, T, "demo", "scenes.json"), "w") as fh:
        json.dump(SCENES, fh, indent=1, ensure_ascii=False)
    print("wrote", T + "DEMO.md")


if __name__ == "__main__":
    main()
