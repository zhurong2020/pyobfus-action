# Architecture and compatibility

`pyobfus-action` is a thin composite CI wrapper. It owns workflow inputs,
outputs, summaries, and the distinction between findings and tool errors. It
does not own obfuscation, scanning, SARIF schemas, Pro transforms, or target
runtime code.

## Relationship to the main project

```text
GitHub workflow
    |
    +-- pyobfus-action@v1
            |
            +-- installs/invokes pyobfus builder
                    |
                    +-- writes scan reports or generated output
                                      |
                                      +-- runtime-backed Pro output imports
                                          pyobfus-runtime on the target
```

The Action is a separate repository because Marketplace requires `action.yml`
at the repository root, consumers fetch the Action repository through `uses:`,
and the moving `v1` tag must not collide with Core's release tags.

## Ownership

| Contract | Owner |
|---|---|
| Action inputs/outputs, job summary, exit gating | this repository |
| CLI options and JSON/SARIF content | `zhurong2020/pyobfus` |
| Pro builder behavior | `pyobfus_pro/` in the main repository |
| Code imported on a protected target | `pyobfus_runtime/` in the main repository |
| Runtime package release | PyPI `pyobfus-runtime`, independently versioned |

Do not work around a changed CLI contract by silently reimplementing it here.
Update the owning project, then adapt the wrapper with a real-contract test.

## Version contract

- Action tags (`v1`, `v1.0.1`) and pyobfus versions (`0.5.31`) are unrelated.
- `@v1` is a moving wrapper tag. Pin an exact Action tag or commit SHA when the
  wrapper itself must be immutable.
- `pyobfus-version` pins the builder installed by this Action. Omit it to use
  latest; pin it for reproducible CI.
- The current builder declares `pyobfus-runtime>=0.1,<1`. Runtime-backed
  generated artifacts must install a compatible runtime on the target.
- `install: false` transfers all builder/runtime environment responsibility to
  the calling workflow.

## Build and deployment boundary

The Action's `output` is generated source, not a wheel, container, or vendored
virtual environment. `--verify-syntax` proves that generated Python parses; it
does not prove that application dependencies are installed or that the
application behaves correctly.

For a runtime-backed Pro build:

1. retain the mapping/private diagnostic material outside the shipped output;
2. read the provenance manifest's `runtime_requirement` when present;
3. declare that runtime requirement in the target application/package;
4. install and test the application in a fresh target environment; and
5. do not install or ship the complete Pro builder merely to satisfy runtime
   imports.

## Documentation synchronization

When the main project changes repository boundaries, CLI/JSON contracts, or
runtime requirements, review this file, README inputs/examples, the fixture CI,
and the Action changelog. When this Action changes its public contract, update
the main project's `PROJECT_STRUCTURE.md`, `SUPPORT_MATRIX.md`, SARIF guide, and
distribution-channel record as applicable.
