# CI/CD templates

**GitLab:** include `gitlab-ci/aer1-verify.yml` and optionally set `AER1_RECEIPTS_DIR`.

**pre-commit:** add `pre-commit/.pre-commit-hooks.yaml` as a local hook or copy its entry into your repository configuration.

All paths are checked recursively for `*.json`. A valid directory exits green; one malformed or tampered receipt exits red. The test harness demonstrates both outcomes. In a pipeline UI, the green result appears as a passing check with `AER-1 receipts: N/N valid`; a failure prints each receipt path and violated rule.

```sh
python3 test/test_harness.py
```
