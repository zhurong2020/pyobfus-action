# pyobfus GitHub Action

[![Marketplace](https://img.shields.io/badge/GitHub%20Marketplace-pyobfus%20scan%20and%20build-blue?logo=github)](https://github.com/marketplace/actions/pyobfus-scan-and-build)
[![CI](https://github.com/zhurong2020/pyobfus-action/actions/workflows/ci.yml/badge.svg)](https://github.com/zhurong2020/pyobfus-action/actions/workflows/ci.yml)
[![License](https://img.shields.io/badge/license-Apache--2.0-green.svg)](LICENSE)

Run [pyobfus](https://github.com/zhurong2020/pyobfus)'s pre-flight risk scan or
an obfuscated build in CI. Findings go to GitHub Code Scanning as SARIF and to
the job summary as a table, and the step's pass/fail behaviour is something you
choose rather than something you work around.

```yaml
- uses: actions/setup-python@v5
  with:
    python-version: "3.12"

- uses: zhurong2020/pyobfus-action@v1
  with:
    source: src/
```

That scans `src/`, writes `pyobfus.sarif` and `pyobfus-result.json`, prints a
findings table in the job summary, and fails the step if pyobfus reports
high-severity risks.

## Why not just `run: pyobfus --check`

You can, and for a simple gate you should. This action exists for the case where
you also want the SARIF uploaded.

pyobfus exits `1` when it finds high-severity risks. In a hand-written step that
kills the job **before** your upload step runs, so the usual fix is `|| true`:

```yaml
# The footgun this action removes
- run: pyobfus --check src/ --sarif pyobfus.sarif || true
- uses: github/codeql-action/upload-sarif@v3
  with:
    sarif_file: pyobfus.sarif
```

`|| true` swallows real tool errors too. A typo in the path, a broken config, a
crash — all of them now look exactly like a clean scan, and the upload step
quietly uploads nothing.

This action separates the two. Artifacts and outputs are always written first,
and only then does it decide whether to fail:

- **findings** are gated by `fail-on`, which you set
- **tool errors** always fail the step, even with `fail-on: never`

## Upload to Code Scanning

```yaml
permissions:
  contents: read
  security-events: write   # required to upload SARIF

jobs:
  preflight:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v5
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"

      - id: scan
        uses: zhurong2020/pyobfus-action@v1
        with:
          source: src/
          fail-on: never        # let the upload happen first

      - uses: github/codeql-action/upload-sarif@v3
        with:
          sarif_file: ${{ steps.scan.outputs.sarif-file }}
          category: pyobfus-preflight

      - name: Gate on the result after uploading
        if: steps.scan.outputs.findings-high != '0'
        run: exit 1
```

The action deliberately does **not** upload the SARIF itself. Doing so would
force `security-events: write` on every consumer, including the ones who only
want the JSON. Composing with `upload-sarif` keeps that permission yours to
grant.

> Uploading to Code Scanning on a **private** repository requires GitHub
> Advanced Security. The scan and its JSON work regardless.

## Build obfuscated output

```yaml
- uses: zhurong2020/pyobfus-action@v1
  with:
    source: src/
    mode: build
    output: dist/
    verify-syntax: "true"
    provenance-manifest: provenance.json
```

`verify-syntax` compiles every generated file in memory after the build. It
never imports or executes your project and writes no `__pycache__`, so it
proves the output parses, not that it behaves.

The mapping file is your de-obfuscation key. If you produce one with
`extra-args: --save-mapping mapping.json`, treat it as a secret: keep it out of
the shipped artifact, and out of any public workflow artifact.

### Build output is not a self-contained deployment

This action invokes the pyobfus **builder**; it does not vendor Python package
dependencies into `output`. Community output normally has no pyobfus runtime
dependency. Pro artifacts that use runtime-backed protection import the
separately published `pyobfus-runtime` package on the target machine.

The current builder declares `pyobfus-runtime>=0.1,<1`, so the default
`install: true` step installs a compatible runtime on the build runner. That
does not place the package inside `dist/`. Declare/install the same runtime
requirement in the environment or application package that will execute the
generated artifact. Target machines need neither the Pro builder nor a build
licence.

With `install: false`, this action installs nothing: the workflow owns both the
builder and compatible runtime setup. A provenance manifest records
`runtime_requirement` when a build needs it; use that fact as deployment input,
not as evidence that the dependency was bundled.

## Inputs

| Input | Default | Description |
| --- | --- | --- |
| `source` | *(required)* | Path to scan or obfuscate. |
| `mode` | `check` | `check` runs the risk scan, `build` produces obfuscated output. |
| `output` | | Output path. Required when `mode: build`. |
| `fail-on` | `high` | `high` fails when pyobfus exits non-zero, `any` fails on any finding, `never` never fails on findings. Tool errors always fail. |
| `sarif-file` | `pyobfus.sarif` | Where to write SARIF 2.1.0. Empty string disables it. |
| `json-file` | `pyobfus-result.json` | Where to save the JSON result. |
| `config` | | Path to a `pyobfus.yaml`. Omit for auto-discovery. |
| `preset` | | `fastapi`, `django`, `flask`, `pydantic`, `click`, `sqlalchemy`, `ml`, … |
| `offline` | `false` | Skip the PyPI lookups behind the dependency advisory. Recommended on hermetic runners. |
| `verify-syntax` | `false` | `mode: build` only. Compile generated files in memory. |
| `provenance-manifest` | | `mode: build` only. Path for a local JSON provenance manifest. |
| `extra-args` | | Raw extra CLI arguments. No validation; an escape hatch. |
| `pyobfus-version` | *(latest)* | Pin a version, e.g. `0.5.23`, for reproducible CI. |
| `install` | `true` | Set `false` if an earlier step already installed pyobfus. |
| `working-directory` | `.` | Directory to run in. |

## Outputs

| Output | Description |
| --- | --- |
| `status` | `clean`, `findings`, or `error`. |
| `exit-code` | pyobfus's own exit code. |
| `sarif-file` | Path to the written SARIF, empty if none. |
| `json-file` | Path to the saved JSON result. |
| `files-scanned` | Files scanned (`check`) or processed (`build`). |
| `findings-total` | Findings across all severities. |
| `findings-high` / `findings-medium` / `findings-low` / `findings-info` | Per-severity counts. |
| `version` | The pyobfus version that actually ran. |

## Requirements

Python must be on `PATH`. GitHub-hosted runners have it; use
`actions/setup-python` first if you need a specific version. Works on
`ubuntu-*`, `macos-*` and `windows-*` runners, all three covered by this repo's
CI.

The action installs pyobfus with `pip` unless you set `install: false`. Pin
`pyobfus-version` if you want your CI reproducible.

pyobfus Core, `pyobfus-runtime`, and this Action are independently versioned.
`@v1` selects the current compatible Action wrapper, not pyobfus 1.x. By
default the wrapper installs the latest pyobfus release; set
`pyobfus-version` to an exact version for reproducible behavior. See
[Architecture and compatibility](ARCHITECTURE.md) for ownership, deployment,
and update rules.

## Why you can trust this action

Not a badge, things you can check yourself:

- It is a **composite action**, not a container. `action.yml` and
  `scripts/run_pyobfus.py` are the entire implementation — about 300 readable
  lines, no bundled binaries and no build step between source and what runs.
- **No network access beyond PyPI.** The action installs pyobfus and runs it.
  Set `offline: true` and pyobfus makes no network calls at all.
- **Nothing is sent anywhere.** Your source, findings and mappings stay on the
  runner. There is no telemetry.
- Third-party actions in this repo's own CI are **pinned to commit SHAs**.
- The CI here uses the action against real fixtures, including a test asserting
  that `fail-on: never` still fails on a bad path — the exact behaviour the
  `|| true` pattern gets wrong.

## Versioning

Released as `v1` (a moving major tag) plus exact tags like `v1.0.0`. Pin
whichever suits your risk tolerance; `@v1` gets fixes, an exact tag gets
nothing without your say-so.

## Licence

Apache-2.0, same as pyobfus Core. Pro features require a licence from the
[pyobfus project](https://github.com/zhurong2020/pyobfus); this action can run
them but does not include or provide one.
