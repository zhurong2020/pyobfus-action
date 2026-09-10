# Contributing

## Local development

The action is `action.yml` plus `scripts/run_pyobfus.py`. The driver reads
`INPUT_*` environment variables and writes to `GITHUB_OUTPUT` /
`GITHUB_STEP_SUMMARY`, both of which are no-ops when unset — so you can run it
directly:

```bash
python -m venv .venv && . .venv/bin/activate
pip install pyobfus ruff mypy pyyaml

INPUT_SOURCE=tests/fixtures/risky_project \
INPUT_FAIL_ON=never \
INPUT_OFFLINE=true \
python scripts/run_pyobfus.py
```

Set `GITHUB_OUTPUT=/tmp/out.txt` to inspect the step outputs it would publish.

## Before opening a pull request

```bash
ruff check scripts/
mypy --ignore-missing-imports scripts/
```

CI runs those plus the action itself against the fixtures in `tests/fixtures/`
on Ubuntu, macOS and Windows. Add a fixture and a CI assertion for any
behaviour change — the tests use `uses: ./` so they exercise the action the way
a consumer does, not the driver in isolation.

## Enable the pre-commit guard

```bash
git config core.hooksPath .githooks
```

It blocks personal identifiers and credential shapes from entering this public
repository.

## Scope

This repository is the CI wrapper. Changes to obfuscation behaviour, presets,
the risk scanner or SARIF content belong in
[pyobfus](https://github.com/zhurong2020/pyobfus).
