# Captures from before Corrigendum 2 (EXT-003)

These six files were recorded on 2026-09-12 by a Sentinel sensor whose end
marker counted framing records (COVERAGE, EPOCH, GAP) as produced. Corrigendum 2
(EXT-003) corrected the completeness identity to count event records only, as
SPEC VLC-L2-5 always said, and under the corrected checker these journals no
longer close it: they score structural L1.

They are kept, not edited. The count sits inside the hash chain, so correcting
it would break the binding; that is the property the specification exists to
protect, applied to the project's own evidence.

The files in the parent directory replace them. They were recorded on
2026-09-21 by the corrected sensor (octa-sentinel `5c7d8e0`) on a GitHub-hosted
Ubuntu runner rather than the maintainer's machine (octa-sentinel workflow
"Sensor re-capture", run 35657697524), and score structural L4, attested L5.

One of these files still does work: `selftest.sh` section 6 uses
`kernel-witness-honest-session.jsonl` from this directory as the witness below
structural L3 that VLC-L5-4 says may not corroborate (EXT-015).
