# Security Policy

## Reporting a vulnerability

Report privately through
[GitHub Security Advisories](https://github.com/zhurong2020/pyobfus-action/security/advisories/new).
Please do not open a public issue for an unfixed vulnerability.

Expect an acknowledgement within 7 days and an assessment within 30.

Vulnerabilities in the **pyobfus obfuscator itself** belong in the
[pyobfus repository](https://github.com/zhurong2020/pyobfus/security/policy),
not here. This repository covers only the action wrapper.

## What this action does with your code

- It installs pyobfus from PyPI and runs it on the runner.
- It does not upload your source, mappings or configuration, or send telemetry.
  It writes a findings table (up to 50 rows, including severity, category,
  `file:line` and message) to the GitHub job summary, which GitHub retains with
  the workflow run. SARIF reaches Code Scanning only if a later step uploads it.
- In check mode, `offline: true` skips the dependency advisory's public PyPI
  lookups. It does not disable package installation or online Pro CI license
  verification. See Core's [CI licensing guide](https://pyobfus.readthedocs.io/en/latest/CI_LICENSING/)
  and [network guide](https://pyobfus.readthedocs.io/en/latest/NETWORK_BEHAVIOR/)
  for dependency-name and license-data requests.

## Handling of mapping files

A mapping file is the de-obfuscation key for your build. If you generate one in
CI, treat it as a secret:

- keep it out of the artifact you ship,
- do not upload it as a public workflow artifact,
- store it where only the people who need to debug production can read it.

The action never writes a mapping unless you ask for one via `extra-args`.

## Supply chain

- Third-party actions used by this repository's own workflows are pinned to
  commit SHAs.
- The action is a composite action: `action.yml` plus one Python script. There
  is no bundled binary and no build step between the source you can read and
  what runs on your runner.
- Pin `pyobfus-version` to an exact version for reproducible builds. With
  `install: true`, a value installs `pyobfus==<input>`; an empty input runs plain
  `pip install pyobfus`, without `--upgrade`. In a fresh environment this
  resolves to the latest release compatible with the runner's Python and
  configured package index; an already installed version may be retained.
