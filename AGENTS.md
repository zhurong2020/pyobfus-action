# AGENTS.md — pyobfus-action

Guide for AI coding agents (and humans) working **on** this repository. To
*use* the Action in a workflow, read [`README.md`](README.md) (inputs, outputs,
examples) and the main project's
[CI licensing guide](https://pyobfus.readthedocs.io/en/latest/CI_LICENSING/).

This repository owns only the composite GitHub Action wrapper: inputs, outputs,
the job summary and exit gating. Obfuscation, scanning, SARIF/JSON semantics,
Pro build mechanisms, licence verification and `pyobfus-runtime` belong to
[`zhurong2020/pyobfus`](https://github.com/zhurong2020/pyobfus). Read
[`ARCHITECTURE.md`](ARCHITECTURE.md) before changing inputs, outputs,
installation, build behavior or documentation.

## Setup

Work from the WSL checkout under `~/projects/pyobfus-action`; OneDrive copies
are backups only. Enable the hooks once per clone (they block personal
identifiers and credential shapes; each scan has its own bypass variable):

```bash
git config core.hooksPath .githooks
```

## Before committing

Mirror the `lint` job in `.github/workflows/ci.yml` (Python 3.12, pinned tools):

```bash
python3.12 -m venv .venv && . .venv/bin/activate
pip install "ruff==0.15.7" "mypy==1.19.1" pyyaml
ruff check .
mypy scripts/
python -m unittest discover -s tests -v   # driver secret boundary and structured errors
```

The `lint` job also asserts the Marketplace fields of `action.yml` (composite
runs, branding icon/color, name, description under 125 characters, required
inputs). Run that block locally when you touch `action.yml`.

Hosted CI is the authoritative real-contract suite: it invokes `uses: ./`
against fixtures on Ubuntu, macOS and Windows, covers both modes and failure
gates, CI licence input fail-closed behavior and an exact pyobfus version pin.
Do not replace those consumer tests with driver-only tests.

## Invariants

- **Findings vs tool errors.** Findings follow `fail-on`, and a findings
  failure happens after the report artifacts are written. A tool error (no
  parseable JSON, an exit code other than 0 or 1, or a structured
  `status: error`) fails the step even with `fail-on: never`.
- **Licence secret boundary.** `license-key` reaches Core only as
  `PYOBFUS_LICENSE_KEY` in the CLI child's environment. Never put it in argv,
  output JSON, Action outputs, the job summary or logs. An empty input keeps an
  inherited `PYOBFUS_LICENSE_KEY`. Tests use synthetic invalid values only.
- **Ownership.** Do not reimplement a changed Core CLI/JSON contract here;
  change Core first, then adapt the wrapper with a real-contract test.
- **Versions.** Action and pyobfus versions are independent. `v1` is a moving
  tag; exact tags (`v1.1.0`) are immutable. `pyobfus-version` pins the builder.
- **Install.** `install: true` installs the selected builder; `install: false`
  makes the caller responsible for builder and runtime.
- **Output is not a deployment.** Generated output is source, not a wheel or
  environment. Runtime-backed Pro artifacts need a compatible
  `pyobfus-runtime` on the target.
- **Marketplace limits.** CI asserts the description stays under 125
  characters and the branding fields are valid. The Marketplace also rejects a
  listing name that collides with an existing GitHub user name (hence
  "pyobfus scan and build"); that is checked only at publish time, not by CI.

## Changing the public contract

When inputs, outputs, gating or install behavior change: update `README.md`
(inputs table and examples), `ARCHITECTURE.md`, `CHANGELOG.md` and the fixture
CI in the same PR, then follow "Documentation synchronization" in
`ARCHITECTURE.md` for the main project's records.

This is a public repository: keep credentials, customer data and personal
identifiers out of code, commits and docs. A release, tag move (including
`v1`), Marketplace update or push requires explicit maintainer authorization.
