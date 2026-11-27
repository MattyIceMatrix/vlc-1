# Corrections

A conformance checker's own defects are findings, and findings get published.
This file lists every bug that could have produced a WRONG GRADE on a surface
other people could reach, with its exposure window and who was affected.
(Divergences caught before the surface shipped live in commit messages and
the fuzzers' frozen vectors; they are not listed here because no one could
have received a wrong grade from them.)

## C-001 — live checker: `-0.0` slipped the jcs-nested float guard

- **Surface:** the live checker (web page and API), mechanism
  `sha256-chain-jcs-nested` only.
- **Window:** 2026-11-25 ≈19:51 UTC (mechanism first served, commit
  `2c91160a`) → 2026-11-27 ≈12:38 UTC (fix deployed).
- **Defect:** the spec's guarded JCS subset refuses all non-integer numbers
  as unrecomputable. The live core checked the *parsed* value, and
  ECMAScript parses `-0.0` to `-0`, where `Number.isInteger(-0)` is `true` —
  so a record carrying `-0.0` (or any `X.0` float spelling, which
  `JSON.parse` erases entirely) was graded instead of refused. A journal the
  reference checker fails on VLC-L1-1 could receive a live PASS.
- **Found by:** `tools/fuzz_differential_jcs.py`, case 53 of its first run
  (2026-11-27), written to extend generative fuzzing to this mechanism.
- **Fix:** the core now scans the raw line for float *syntax* before
  recomputing, the same approach as its big-integer scan. Frozen vector
  `jcs-nested-negzero-float-syntax`; the new fuzzer runs in CI on every push.
- **Affected results:**
  - **Signed verified reports: none.** Every signed report ever issued
    (registry in `VERIFIED-REPORTS.md`) was graded by the Python reference,
    which always refused floats; report 001 additionally covers a
    `sha256-canonical-fields` journal, a mechanism this bug never touched.
    Report 001 re-verified unchanged under the fixed code on 2026-11-27.
  - **Live grades:** only jcs-nested journals containing float spellings
    graded in the window could be wrong, and only toward PASS. The served
    jcs-nested examples contain no floats. If you graded a jcs-nested
    journal in the window, re-run it — the live page is current, or
    `pip install vlc-check` and grade offline.
