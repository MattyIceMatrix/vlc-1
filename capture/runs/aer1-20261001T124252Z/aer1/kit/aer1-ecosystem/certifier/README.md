# AER-1 conformance certifier

1. Place your verifier behind a command that accepts one receipt path and exits 0 for PASS, 1 for FAIL.
2. Run `python3 certify.py --command "node verifier.js" --name my-verifier --out certification`.
3. Publish `certification/conformance-report.json` and the green/red `aer1-conformant.svg` only with the implementation version and input hashes.

The bundled `vectors/` contains the frozen 44-vector corpus and `fuzz-corpus/` contains 1,000 adversarial cases. The JSON report is HMAC-SHA256 signed; set `AER1_CERTIFIER_KEY` to a protected deployment key (the development fallback is only for local tests). `test_certifier.py` proves both a reference verifier and deliberately broken always-pass verifier are handled correctly. The command runs from the certifier directory; a module can be supplied with `--module package.verifier`.
