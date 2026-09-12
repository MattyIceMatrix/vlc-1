# Publishing this repository

Claude cannot push to GitHub from the sessions that built this, so these are the
commands for a human to run. Everything in this directory is intended to be
public; the kernel sensor is deliberately not here.

## 1. Check what you are about to publish

```sh
./selftest.sh                       # must print SELFTEST PASS
grep -rn "moorematthew131" . | cut -d: -f1 | sort -u   # the contact address, on purpose
```

The sample logs under `examples/reference-impl/` are real captures from a
throwaway container. They contain file paths (`/usr/lib/python3.11/...`),
process ids and session ids, and no credentials, hostnames or personal data.
Read one before publishing if you want to be sure — they are plain JSON lines.

## 2. Push

Use `push-to-github.sh`, which sits one level up — beside this directory, not
inside it, because it handles **both** repositories: this public one and the
private tree next to it.

```sh
./push-to-github.sh            # dry run — prints what it would do, changes nothing

./push-to-github.sh \
    --public-remote  git@github.com:<you>/vlc-1.git \
    --private-remote git@github.com:<you>/octa-sentinel.git \
    --push
```

Before it commits anything it checks the public tree against a list of private
paths (the sensor, the policy engine, the rest of the proof estate, the OCTA
review material), scans both trees for credential-shaped strings, runs this
repository's own self-test, and — using `gh` — confirms the private remote is
genuinely a private repository. Any one of those failing stops the whole run
with nothing committed.

Doing it by hand instead:

```sh
git init && git add -- . && git commit -m "VLC-1 1.0-draft"
git branch -M main
git remote add origin git@github.com:<you>/vlc-1.git
git push -u origin main
```

Suggested repository description:

> A vendor-neutral specification and conformance suite for proving an AI audit
> log is complete — not just tamper-evident. Six levels, a checker you can run
> against any log, and a machine-checked proof that each level is necessary.

Topics: `ai-governance` `audit-logging` `eu-ai-act` `formal-verification`
`observability` `compliance` `coq`

If the description is already set from an earlier release, update it — the
scheme has six levels, not five:

```sh
gh repo edit <you>/vlc-1 --description "A vendor-neutral specification and conformance suite for proving an AI audit log is complete, not just tamper-evident. Six levels, a checker that reports separately what it recomputed and what it relayed, and a machine-checked proof that each level is necessary."
```

## 3. Mint a DOI — do this, it is the step that matters

1. Sign in to https://zenodo.org with GitHub.
2. In Zenodo's GitHub settings, flip this repository **on**.
3. Cut a release on GitHub: tag `v1.0-draft`, title "VLC-1 1.0-draft".
4. Zenodo archives the tarball and assigns a DOI. `CITATION.cff` is already
   present, so the metadata comes across.
5. Put the DOI badge at the top of `README.md` and into
   `COMMENT-prEN-18229.md` before filing anything.

A DOI is what turns "a GitHub repo" into something a standards committee document
can cite, and it costs nothing.

## 4. Turn on CI

`.github/workflows/ci.yml` runs the self-test, regenerates the worked examples
from their generator, scores the third-party formats, and compiles the Coq
development while asserting that every theorem reports "Closed under the global
context". It needs no secrets. A green badge on the README is worth more than a
paragraph of the README.

## 5. What is deliberately not here

The kernel sensor, the policy engine, the classifier and the object tier stay
private. What is published is the **specification, the checker, the proof and the
reconciler** — the parts that are worth more to everyone if they are free, and
the parts a standards body would need to be able to adopt.

That line is stated in the README so nobody has to guess where it falls.
