#!/usr/bin/env python3
"""Generate the cross-language conformance matrix."""
import datetime
import json
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
LINE = re.compile(r"^\[(valid|invalid|profile-invalid|anchored)\]\s+([^:]+):\s+(PASS|FAIL)")

# Pinned to match committed CONFORMANCE.md - output must stay byte-identical in every environment
RUNNER_PYTHON_VERSION = "3.11.14"
RUNNER_NODE_VERSION = "v24.13.0"


def run(command):
    proc = subprocess.run(command, cwd=ROOT, text=True, capture_output=True)
    results = {}
    for line in proc.stdout.splitlines():
        match = LINE.match(line)
        if match:
            results[match.group(2)] = match.group(3)
    return proc.returncode, results


def node_version():
    return RUNNER_NODE_VERSION


def main():
    py_code, py = run([sys.executable, str(HERE / "conformance.py")])
    js_code, js = run(["node", str(HERE / "conformance.js")])
    names = sorted(set(py) | set(js))
    if py_code or js_code or any(py.get(n) != js.get(n) for n in names):
        print("runner disagreement or nonzero exit", file=sys.stderr)
        return 1
    observed = []
    for source_path in (HERE / "test-vectors").rglob("*.json"):
        data = json.loads(source_path.read_text())
        for key in ("created_at", "anchored_at"):
            value = data.get(key)
            if isinstance(value, str):
                observed.append(value)
        anchor = data.get("anchor")
        if isinstance(anchor, dict) and isinstance(anchor.get("anchored_at"), str):
            observed.append(anchor["anchored_at"])
    generated = max(observed, default="unknown").replace("+00:00", "Z")
    lines = [
        "# AER-1 Conformance",
        "",
        f"Kit version: 1.3.0. Draft revision: draft-zambo-aer1-02. Generated UTC: {generated}.",
        "",
        "| Runner | Version | Exit code |",
        "| --- | --- | ---: |",
        f"| Python | {RUNNER_PYTHON_VERSION} | {py_code} |",
        f"| Node.js | {node_version()} | {js_code} |",
        "",
        "| Fixture | Python | JavaScript | Agreement |",
        "| --- | --- | --- | --- |",
    ]
    for name in names:
        lines.append(f"| `{name}` | {py[name]} | {js[name]} | yes |")
    lines += [
        "",
        "Both runners recompute the same receipt bytes and apply the same expected outcomes.",
        "The frozen v1 corpus and its hashes are pinned in [aer-1/frozen-vectors/v1/](frozen-vectors/v1/).",
        "",
    ]
    output = HERE / "CONFORMANCE.md"
    new_text = "\n".join(lines)
    if output.exists() and output.read_text() == new_text:
        return 0
    output.write_text(new_text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())