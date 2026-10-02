# AGENTS.md — pyobfus-action

This repository owns only the composite GitHub Action wrapper. Obfuscation,
scanning, SARIF/JSON semantics, Pro build mechanisms, and `pyobfus-runtime`
belong to `zhurong2020/pyobfus`.

Before committing, run:

```bash
ruff check .
mypy scripts/
python3 -c "import yaml; spec=yaml.safe_load(open('action.yml')); assert spec['runs']['using']=='composite'"
```

Hosted CI is the authoritative real-contract suite: it invokes `uses: ./`
against fixtures on Ubuntu, macOS, and Windows, covers both modes and failure
gates, and verifies an exact pyobfus version pin. Do not replace those consumer
tests with driver-only tests.

Public compatibility rules:

- Action and pyobfus versions are independent.
- `v1` is a moving Action tag; exact tags remain immutable.
- `install: true` installs the selected builder; `install: false` makes the
  caller responsible for it.
- Generated output is not a self-contained deployment. Runtime-backed Pro
  artifacts require a compatible `pyobfus-runtime` on the target.

Read `ARCHITECTURE.md` before changing inputs, outputs, installation, build
behavior, or documentation. Keep credentials and personal identifiers out of
this public repository. A release, tag move, Marketplace update, or push
requires explicit user authorization.
