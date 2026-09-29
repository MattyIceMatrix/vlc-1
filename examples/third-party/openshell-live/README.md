# OpenShell live capture, 2026-09-29

What `adapters/nvidia-openshell-live.json` scores, and how it was made.

| File | What it is |
|---|---|
| `openshell-logs-raw.txt` | `openshell logs vlccap`, exactly as printed on the runner |
| `convert.py` | Line-for-line conversion to `../openshell-live-full.jsonl`; deterministic |
| `policy.yaml` | NVIDIA's `examples/sandbox-policy-quickstart/policy.yaml`, applied in phase 2. Copyright NVIDIA, Apache-2.0, header kept; redistributed unmodified |
| `install.sh.sha256` | SHA-256 of the OpenShell install script the runner used |

Produced by `.github/workflows/openshell-capture.yml` on branch
`capture/openshell-ocsf` (run `capture/run-20260929T002200Z`), on a
GitHub-hosted runner: OpenShell 0.1.2, Docker driver, one sandbox from
`docker.io/curlimages/curl:latest`. Phase 1 ran under OpenShell's default
policy, phase 2 under NVIDIA's quickstart policy. The same branch holds the
two earlier discovery runs, including the one showing that the process inside
the sandbox could not see any OpenShell log file.
