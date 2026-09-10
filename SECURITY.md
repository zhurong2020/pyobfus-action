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
- It does **not** transmit your source, findings, mappings or configuration
  anywhere. There is no telemetry.
- With `offline: true`, pyobfus makes no network calls at all. Otherwise its
  dependency advisory queries public PyPI metadata.

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
- Pin `pyobfus-version` for reproducible builds; by default the latest release
  is installed.
