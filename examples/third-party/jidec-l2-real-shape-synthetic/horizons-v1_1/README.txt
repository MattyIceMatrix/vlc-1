jidec_l2_synthetic v1.1 (The HORIZONs Co., Ltd., 2026-11-28, MIT licence). SYNTHETIC: test keys from fixed seeds; no byte is output of the JIDEC ledger.

What changed from v1 (the archive of 2026-11-28, 2521c68a...):
- every nenrin-head-checkpoint-v2 record carries refused_complete_since, as named on vlc-1 PR #12:
  an integer beside production_count, from <= it <= to + 1, equal to from in every window but the first;
- variant partial_first: the first window counts refusals only from entry 3 (L2, refusals declared from 3);
- three variants where the field is wrong: in a later window, past to + 1, below from (each L1);
- plain_note: entry 4 is a Markdown note, bound by its sha256 and not read (L2; bind_only, EXT-034);
  plain_note_edited: the note's bytes changed with the claim left (L0).
The fourteen variants of v1 keep their names and expectations; their bytes change only by the new field.
jidec_l2_verify_v1_1.py grades the v1 trails exactly as v1 did (14 of 14 the same level and reasons).

Run:
  python3 -I jidec_l2_synth_v1_1.py --selftest
  python3 -I jidec_l2_verify_v1_1.py --selftest
  python3 -I jidec_l2_synth_v1_1.py --out out2      (rebuilds out/ byte for byte)
