# Changelog — pyobfus-action

All notable changes to this action are documented here. Follows
[Keep a Changelog](https://keepachangelog.com/en/1.0.0/) and
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

Versioned independently of the `pyobfus` PyPI package. The action's `v1` is not
tied to a pyobfus major version; pin `pyobfus-version` if you need that.

## [Unreleased]

## [1.0.0] - 2026-09-10

### Added

- Initial release. A composite action that runs `pyobfus --check` or an
  obfuscated build in CI.

- **`check` mode** writes SARIF 2.1.0 for GitHub Code Scanning and a JSON
  result, and renders a per-severity findings table in the job summary.

- **`build` mode** produces obfuscated output, with optional `--verify-syntax`
  (in-memory compilation, no import, no execution, no `__pycache__`) and an
  optional local JSON provenance manifest.

- **`fail-on` separates findings from tool errors.** `high` (default) matches
  the CLI, `any` fails on any finding, `never` never fails on findings so a
  later step can upload the SARIF. A pyobfus tool error fails the step under
  every setting — the `|| true` workaround this replaces could not make that
  distinction, and silently turned a bad path into a clean-looking scan.

- Artifacts and step outputs are always written before the pass/fail decision,
  so an upload step still has a file to upload when the gate trips.

- Step outputs: `status`, `exit-code`, `sarif-file`, `json-file`,
  `files-scanned`, `findings-total`, per-severity counts, and the `version` of
  pyobfus that actually ran.

- `pyobfus-version` pins the installed version; `install: false` skips
  installation when an earlier step already provided it.

### Notes

- SARIF upload is deliberately left to `github/codeql-action/upload-sarif`.
  Bundling it would force `security-events: write` on consumers who only want
  the JSON.
- CI exercises the action against real fixtures on Ubuntu, macOS and Windows,
  including an assertion that `fail-on: never` still fails on a nonexistent
  path.
