# Releasing: the operator's clicks, in order

*Written 2026-11-25. Everything below is a manual operator action by design —
no automation creates releases or publishes packages on its own.*

## 1. Tag v1.0.0 and v1 (≈1 minute)

GitHub → this repo → **Releases** → **Draft a new release** →
Choose a tag: type `v1.0.0` → *Create new tag on publish* → target `main` →
title `v1.0.0 — live checker, signed reports, CI distribution` → publish.
Then once more with tag `v1` (same commit) — that's the moving-major tag CI
users pin (`uses: MattyIceMatrix/vlc-1@v1`).

Publishing the `v1.0.0` release also fires `pypi-publish.yml` (step 2 makes
it actually reach PyPI).

## 2. PyPI Trusted Publishing (≈3 minutes, once)

pypi.org → log in → **Your projects → Publishing** → *Add a new pending
publisher*:
- PyPI project name: `vlc-check`
- Owner: `MattyIceMatrix` · Repository: `vlc-1`
- Workflow: `pypi-publish.yml` · Environment: `pypi`

Then GitHub → repo **Settings → Environments** → create environment `pypi`
(no secrets needed — Trusted Publishing is token-free OIDC).
From then on, every published release ships `pip install vlc-check`
automatically, after the workflow's own install-and-grade sanity check.

## 3. GitHub Marketplace listing (≈2 minutes, once)

The release page for a repo with a root `action.yml` shows **Publish this
Action to the GitHub Marketplace** — tick it while drafting the v1.0.0
release (branding icon/color are already set in `action.yml`).

Suggested listing text:

> **VLC-1 conformance check** — Grade your AI system's logs for
> completeness on every push. The reference checker for the VLC-1 spec
> (CC0): verifies that delivered + declared-lost == produced under a hash
> chain, so a log that silently dropped records can't pass review. Stdlib
> Python, no dependencies, three lines of workflow. Levels L1–L5; exit
> codes fail the job when the level you `expect:` isn't demonstrated.
> Live demo: https://vlc-1.moorematthew131.workers.dev/checker.html

Categories: *Continuous integration*, *Security*.

## 4. After any release

`selftest.sh` and the parity/fuzz/sweep workflows must be green on the
tagged commit — they were at tagging time if the badge row is green. The
published wheel is the reference checker itself; nothing else ships.
