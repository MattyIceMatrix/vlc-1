SYNTHETIC JIDEC L2 trails, builder and verifier
HORIZON SHIELD (The HORIZONs Co., Ltd.), 2026-11-28, for vlc-1 PR #12

Everything here is synthetic: test keys from fixed seeds, no output of the JIDEC ledger.
Standard library only. Python 3.9 or later.

sha256 of each file:
acf174c66ec9f65cd75c548e9b15ffe48f7b7e475cb2438c526b645bf8ff8891  jidec_l2_synth.py
6a30d29cc8a6d23567ee12a49b8f0f2f1787964b873d9ba38accf7625568069d  jidec_l2_verify.py
ae3741216e2b85497aa85e40101fa526d2a6af00bb1a1ee77c5bb70bf29b2df2  run_vlc_bound.py
a4c19dbb88b0dc317932f555bf75a841a774df6cb1d72efbeca0e8c7d1503721  vlc_bound_run.txt
7202dccaf356c44569aafcaea9159322b7c92727bd47d0ef9de880c514d93e0b  verify_run.txt

How to run:
  python3 -I jidec_l2_synth.py --selftest
  python3 -I jidec_l2_synth.py --out <a new folder>      (rebuilds the fourteen trails; index.json carries each export's sha256)
  python3 jidec_l2_verify.py --selftest                 (needs jidec_l2_synth.py beside it)
  python3 -I jidec_l2_verify.py --export <folder>/<variant>/export.jsonl --operator-key <operator_public_key from operator_key.json> --refusals <folder>/<variant>
  python3 run_vlc_bound.py <vlc-1 checkout> <folder>      (the in-process wrapper behind the table on PR #12; conformance.py is not modified on disk)

vlc_bound_run.txt is the wrapper's run at vlc-1 344e12b; verify_run.txt is the verifier on the fourteen.

out/ holds the fourteen trails as built: out/<variant>/export.jsonl with the refusal lists of each window, out/index.json (each export's sha256) and out/operator_key.json.

Licence: MIT, the same as the HORIZON SHIELD repository.
