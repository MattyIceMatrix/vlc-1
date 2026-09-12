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
git init && git add -- . && git commit -m "VLC-1 1.1.1-draft"
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

`mint-doi.ps1` does all of this from PowerShell, including the new-version flow.
For a **first** publication use `-Go`; for a **subsequent version** use
`-NewVersionOf <record id of the latest published version>`, which keeps the
concept DOI and therefore leaves the README badge alone.

The manual route, if you would rather click:

1. Sign in to https://zenodo.org with GitHub.
2. In Zenodo's GitHub settings, flip this repository **on**.
3. Cut a release on GitHub: tag `v<version>-draft`, title "VLC-1 <version>-draft".
   The tag must match the `version` in `CITATION.cff`, which is also what
   `selftest.sh` §7 checks against `SPEC.md` and the string the checker prints.
4. Zenodo archives the tarball and assigns a DOI. `CITATION.cff` is already
   present, so the metadata comes across.
5. Put the **concept** DOI badge at the top of `README.md`. Do not put a
   version DOI in `COMMENT-prEN-18229.md` — it cites the concept DOI on
   purpose, so the comment does not go stale on the next mint. Record the new
   version DOI in `SPEC.md` Annex F instead.

A DOI is what turns "a GitHub repo" into something a standards committee document
can cite, and it costs nothing.

### Before you mint anything, in this order

A Zenodo record cannot be edited afterwards, so the five minutes here are the
cheapest in the process. Version **1.1.1-draft** exists because step 1 was
skipped once.

1. **Bump the version in all three places** — `SPEC.md`'s header table,
   `CITATION.cff`, and `VERSION` in `conformance.py`. Then run
   `bash selftest.sh`; §7 fails the whole suite if they disagree.
2. **Add the row to `SPEC.md` Annex F** for the version you are about to mint,
   with the version DOI left as *this text* until Zenodo gives you one.
3. **Read `CITATION.cff`'s abstract out loud.** It is the text that enters the
   permanent record, and it is the field that goes stale quietest.
4. **Rehearse:** `.\mint-doi.ps1 -Sandbox -Tag v<version>-draft -Go`. Free,
   against sandbox.zenodo.org, and it never touches the README.
5. Then the real one, passing `-NewVersionOf <the previous record id>` so the
   concept DOI is kept and the badge does not move.

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
