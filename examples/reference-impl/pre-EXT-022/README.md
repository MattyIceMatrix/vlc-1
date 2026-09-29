# Reference journals before EXT-022 (kept unedited)

Captured by the sensor before its HEAD record was chained. Under 1.4.1-draft
they score L0 (L1 with an independently held head): HEAD sat outside the
chain, so its counts and the tail could be changed without recomputing a hash.
They are kept byte-for-byte, not rewritten, as the record of what was
published. Replaced in the parent folder by captures from the fixed sensor
(octa-sentinel `269b176`, 2026-09-29), which chain HEAD and score structural
L4 / attested L5. Score these with `adapters/observer.json` from 1.4.1-draft or
earlier (end marker `self_bound: false`, `head_field: "h"`).
