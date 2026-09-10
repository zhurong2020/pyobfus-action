#!/usr/bin/env python3
"""Driver for the pyobfus GitHub Action.

Why this exists rather than a plain `run: pyobfus --check ...` step:

1. **It removes the `|| true` footgun.** pyobfus exits 1 when it finds
   high-severity risks. In a hand-written step that kills the job *before* a
   later step can upload the SARIF, so the documented workaround is to append
   `|| true` -- which then silently discards real tool errors too. This driver
   always finishes writing its artifacts and outputs, and only then decides
   whether to fail, based on `fail-on`.

2. **It separates findings from tool failures.** pyobfus exits 1 for findings
   and 2 for a usage/tool error. `fail-on: never` suppresses the former and
   never the latter, so a typo'd path still fails your build.

3. It publishes counts as step outputs and writes a job-summary table, neither
   of which a raw `run:` step gives you.

Reads its configuration from INPUT_* environment variables set by action.yml.
"""

from __future__ import annotations

import json
import os
import shlex
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, NoReturn, Optional, Tuple

SEVERITIES = ("high", "medium", "low", "info")

# pyobfus's own exit codes. 0 and 1 are contract; anything else is a tool
# error (2 is Click's usage error) and must fail regardless of `fail-on`.
EXIT_CLEAN = 0
EXIT_FINDINGS = 1


def env(name: str, default: str = "") -> str:
    return os.environ.get(name, default).strip()


def env_bool(name: str) -> bool:
    return env(name).lower() in ("true", "1", "yes", "on")


def fail(message: str) -> NoReturn:
    print(f"::error::{message}", file=sys.stderr)
    sys.exit(1)


def write_outputs(pairs: Dict[str, Any]) -> None:
    """Publish step outputs. No-op when run outside Actions, which is what
    makes this script testable locally."""
    path = os.environ.get("GITHUB_OUTPUT")
    if not path:
        return
    with open(path, "a", encoding="utf-8") as handle:
        for key, value in pairs.items():
            handle.write(f"{key}={value}\n")


def write_summary(markdown: str) -> None:
    path = os.environ.get("GITHUB_STEP_SUMMARY")
    if not path:
        return
    with open(path, "a", encoding="utf-8") as handle:
        handle.write(markdown)


def resolve_python() -> str:
    return sys.executable or "python3"


def build_command() -> Tuple[List[str], str, str, str]:
    """Return (argv, mode, sarif_path, json_path)."""
    source = env("INPUT_SOURCE")
    if not source:
        fail("`source` is required.")

    mode = env("INPUT_MODE", "check").lower() or "check"
    if mode not in ("check", "build"):
        fail(f"`mode` must be 'check' or 'build', got {mode!r}.")

    argv = [resolve_python(), "-m", "pyobfus"]
    sarif_path = ""

    if mode == "check":
        argv += ["--check", source]
        sarif_path = env("INPUT_SARIF_FILE")
        if sarif_path:
            argv += ["--sarif", sarif_path]
        if env_bool("INPUT_OFFLINE"):
            argv.append("--offline")
    else:
        output = env("INPUT_OUTPUT")
        if not output:
            fail("`output` is required when mode is 'build'.")
        argv += [source, "-o", output]
        if env_bool("INPUT_VERIFY_SYNTAX"):
            argv.append("--verify-syntax")
        manifest = env("INPUT_PROVENANCE_MANIFEST")
        if manifest:
            argv += ["--provenance-manifest", manifest]

    config = env("INPUT_CONFIG")
    if config:
        argv += ["-c", config]
    preset = env("INPUT_PRESET")
    if preset:
        argv += ["--preset", preset]

    extra = env("INPUT_EXTRA_ARGS")
    if extra:
        argv += shlex.split(extra)

    argv.append("--json")
    json_path = env("INPUT_JSON_FILE") or "pyobfus-result.json"
    return argv, mode, sarif_path, json_path


def parse_payload(stdout: str) -> Optional[Dict[str, Any]]:
    """pyobfus prints one JSON object on stdout. A tool error prints a Click
    usage message instead, which is how a failure is told apart from findings.
    """
    text = stdout.strip()
    if not text:
        return None
    try:
        payload = json.loads(text)
    except ValueError:
        return None
    return payload if isinstance(payload, dict) else None


def counts_from(payload: Dict[str, Any]) -> Dict[str, int]:
    raw = payload.get("severity_counts")
    if not isinstance(raw, dict):
        return {level: 0 for level in SEVERITIES}
    return {level: int(raw.get(level, 0) or 0) for level in SEVERITIES}


def relative(path_value: str, root: Path) -> str:
    """Job summaries should not print the runner's absolute paths."""
    try:
        return Path(path_value).resolve().relative_to(root).as_posix()
    except (ValueError, OSError):
        return Path(path_value).name


def summarize(
    payload: Optional[Dict[str, Any]],
    mode: str,
    counts: Dict[str, int],
    version: str,
    exit_code: int,
) -> str:
    root = Path.cwd().resolve()
    lines = [f"## pyobfus {version or ''}".rstrip(), ""]

    if mode == "build":
        stats = (payload or {}).get("stats") or {}
        verification = (payload or {}).get("verification") or {}
        lines += [
            "| Metric | Value |",
            "| --- | --- |",
            "| Mode | build |",
            f"| Files processed | {stats.get('files_processed', 'n/a')} |",
            f"| Names obfuscated | {stats.get('total_names_obfuscated', 'n/a')} |",
        ]
        if verification:
            lines.append(f"| Syntax verified | {verification.get('syntax_valid')} |")
        lines.append("")
        return "\n".join(lines) + "\n"

    total = sum(counts.values())
    lines += [
        "| Severity | Count |",
        "| --- | --- |",
        f"| High | {counts['high']} |",
        f"| Medium | {counts['medium']} |",
        f"| Low | {counts['low']} |",
        f"| Info | {counts['info']} |",
        f"| **Total** | **{total}** |",
        "",
        f"Scanned {(payload or {}).get('files_scanned', 0)} file(s). "
        f"pyobfus exit code {exit_code}.",
        "",
    ]

    risks = (payload or {}).get("risks") or []
    if risks:
        lines += ["<details><summary>Findings</summary>", ""]
        lines += ["| Severity | Category | Location | Message |", "| --- | --- | --- | --- |"]
        for risk in risks[:50]:
            location = relative(str(risk.get("file", "")), root)
            line_no = risk.get("line")
            if line_no:
                location = f"{location}:{line_no}"
            message = str(risk.get("message", "")).replace("|", "\\|")
            lines.append(
                f"| {risk.get('severity', '')} | {risk.get('category', '')} "
                f"| `{location}` | {message} |"
            )
        if len(risks) > 50:
            lines.append(f"| … | | | {len(risks) - 50} more finding(s) not listed |")
        lines += ["", "</details>", ""]

    return "\n".join(lines) + "\n"


def installed_version() -> str:
    try:
        from importlib.metadata import version as dist_version

        return dist_version("pyobfus")
    except Exception:
        return ""


def main() -> int:
    argv, mode, sarif_path, json_path = build_command()

    print("::group::pyobfus command")
    print(" ".join(shlex.quote(part) for part in argv))
    print("::endgroup::")

    completed = subprocess.run(argv, capture_output=True, text=True)
    exit_code = completed.returncode
    payload = parse_payload(completed.stdout)

    if completed.stderr.strip():
        print(completed.stderr, file=sys.stderr)

    # A tool error: no parseable JSON, or an exit code outside the contract.
    # This always fails, and `fail-on: never` must not be able to hide it --
    # otherwise a typo'd path would look like a clean scan.
    if payload is None or exit_code not in (EXIT_CLEAN, EXIT_FINDINGS):
        if completed.stdout.strip():
            print(completed.stdout, file=sys.stderr)
        write_outputs({"exit-code": exit_code, "status": "error"})
        fail(
            f"pyobfus failed with exit code {exit_code} and produced no JSON result. "
            "This is a tool or configuration error, not a findings gate."
        )

    Path(json_path).parent.mkdir(parents=True, exist_ok=True)
    Path(json_path).write_text(json.dumps(payload, indent=2), encoding="utf-8")

    counts = counts_from(payload)
    total = sum(counts.values())
    version = installed_version()
    sarif_written = sarif_path if (sarif_path and Path(sarif_path).exists()) else ""

    # The two modes report file counts under different keys: `files_scanned` for
    # a check, `stats.files_processed` for a build. Reading only the former left
    # build runs reporting a flat 0.
    if mode == "build":
        files_touched = (payload.get("stats") or {}).get("files_processed", 0)
    else:
        files_touched = payload.get("files_scanned", 0)

    write_outputs(
        {
            "exit-code": exit_code,
            "status": "findings" if exit_code == EXIT_FINDINGS else "clean",
            "sarif-file": sarif_written,
            "json-file": json_path,
            "files-scanned": files_touched,
            "findings-total": total,
            "findings-high": counts["high"],
            "findings-medium": counts["medium"],
            "findings-low": counts["low"],
            "findings-info": counts["info"],
            "version": version,
        }
    )
    write_summary(summarize(payload, mode, counts, version, exit_code))

    if sarif_path and not sarif_written:
        print(f"::warning::SARIF was requested at {sarif_path} but no file was written.")

    fail_on = env("INPUT_FAIL_ON", "high").lower() or "high"
    if fail_on not in ("high", "any", "never"):
        fail(f"`fail-on` must be 'high', 'any' or 'never', got {fail_on!r}.")

    if fail_on == "never":
        return 0
    if fail_on == "any" and total > 0:
        print(f"::error::pyobfus reported {total} finding(s) and fail-on is 'any'.")
        return 1
    if fail_on == "high" and exit_code == EXIT_FINDINGS:
        print("::error::pyobfus reported findings that warrant blocking.")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
