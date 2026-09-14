# Independent verification — how to check this yourself

**Nothing is installed on your machine. Nothing is configured. Three clicks.**

This page exists because of this specification's own L5: a self-authored
transcript establishes nothing about its author. Every figure published by this
project was produced by the maintainer, on the maintainer's machine, with the
maintainer's harness. By the rules written here, that is a producer's
assertion, not evidence.

The only fix is other people.

---

## The three clicks

1. **Fork this repository.** Top right, "Fork".
2. In your fork, open the **Actions** tab. GitHub will ask you to enable
   workflows on a fork; say yes.
3. Select **"Independent verification"** in the left-hand list, then press
   **"Run workflow"**.

It takes a few minutes. When it finishes, open the run and download the
artefact named **`independent-verification-log`** at the bottom of the page.

**Send that file back as it is — pass or fail. Do not edit it.**

## What it runs

On a clean GitHub-hosted Ubuntu machine, from a fresh checkout:

- `selftest.sh` — the conformance self-test, including the negative cases
  (every published mutation must lower the level) and the trust-boundary cases
  (a generous adapter must not move the structural level);
- `coqc` over every development in `proofs/`, reporting the number of results
  and the counts of `Admitted` and `Axiom` for each.

It records the runner's OS, the Python, Rust and Coq versions, the commit it
checked, and who ran it.

## Why a fork rather than your laptop

Because the log is then produced by infrastructure that **neither you nor the
maintainer controls**, from a public commit, with the environment recorded. A
log from the maintainer's machine is a producer's assertion. A log from yours
is better. A log from a neutral runner, reproducible by anyone reading this, is
better still — and it is the only one of the three that a stranger can repeat.

## What a result does and does not establish

**Does:** that the published claims reproduce on a clean machine, from the
published source, with no local configuration — and what the counts actually
are.

**Does not:** this is **not an audit, not a certification, and not a security
review**. It establishes reproducibility, not correctness, not fitness for
purpose, and not the absence of defects. Anyone quoting it should say "an
independent run reproduced the published figures", never "independently
verified".

## A failure is more valuable than a pass

A project whose entire claim is that other people can check it, which does not
reproduce elsewhere, has a real defect — and the maintainer would rather learn
that from you than from a standards committee.

Failures are recorded in `FINDINGS-EXTERNAL.md` with the reporter's name,
unless the reporter prefers otherwise.

## If you would rather not fork

`docker run --rm -v "$PWD":/w -w /w ubuntu:24.04 bash -c \
  'apt-get update -qq && apt-get install -y -qq coq python3 >/dev/null && ./selftest.sh && for f in proofs/*.v; do coqc -Q proofs Sentinel "$f"; done'`

Same checks, on your machine, in a throwaway container. The fork route is
preferred because its log is public and repeatable by a third party.
