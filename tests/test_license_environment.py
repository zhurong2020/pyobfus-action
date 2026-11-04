"""Regression coverage for the wrapper's secret boundary and error gating."""

from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

DRIVER = Path(__file__).resolve().parents[1] / "scripts" / "run_pyobfus.py"
SPEC = importlib.util.spec_from_file_location("action_driver", DRIVER)
assert SPEC is not None and SPEC.loader is not None
driver = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(driver)


class LicenseEnvironmentTests(unittest.TestCase):
    """Exercise main so argv, reports, outputs and summaries are inspected."""

    def exercise(self, supplied: dict[str, str], *, denied: bool = False) -> dict[str, str]:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            settings = {
                "INPUT_SOURCE": "fixture.py",
                "INPUT_MODE": "build",
                "INPUT_OUTPUT": "out.py",
                "INPUT_JSON_FILE": str(root / "result.json"),
                "INPUT_FAIL_ON": "never",
                "GITHUB_OUTPUT": str(root / "outputs.txt"),
                "GITHUB_STEP_SUMMARY": str(root / "summary.md"),
                **supplied,
            }
            payload = {"status": "error"} if denied else {
                "status": "success", "stats": {"files_processed": 1}
            }
            completed = subprocess.CompletedProcess([], 1 if denied else 0, json.dumps(payload), "")
            stdout, stderr = io.StringIO(), io.StringIO()
            with (
                patch.dict(os.environ, settings, clear=True),
                patch.object(driver.subprocess, "run", return_value=completed) as child,
                patch.object(driver, "installed_version", return_value="0.12.0"),
                contextlib.redirect_stdout(stdout),
                contextlib.redirect_stderr(stderr),
            ):
                if denied:
                    with self.assertRaises(SystemExit) as failure:
                        driver.main()
                    self.assertEqual(failure.exception.code, 1)
                else:
                    self.assertEqual(driver.main(), 0)
                self.assertEqual(dict(os.environ), settings)
            call = child.call_args
            self.assertIsNotNone(call)
            self.assertNotIn("INPUT_LICENSE_KEY", call.kwargs["env"])
            surfaces = stdout.getvalue() + stderr.getvalue() + str(call.args[0])
            for file in root.iterdir():
                surfaces += file.read_text()
            for key in ("INPUT_LICENSE_KEY", "PYOBFUS_LICENSE_KEY"):
                secret = supplied.get(key, "").strip()
                if secret:
                    self.assertNotIn(secret, surfaces)
            if denied:
                self.assertIn("status=error", (root / "outputs.txt").read_text())
                self.assertFalse((root / "result.json").exists())
            return call.kwargs["env"]

    def test_explicit_input_overrides_inherited_key(self) -> None:
        child = self.exercise(
            {"INPUT_LICENSE_KEY": " input-secret ", "PYOBFUS_LICENSE_KEY": "env-secret"}
        )
        self.assertEqual(child["PYOBFUS_LICENSE_KEY"], "input-secret")

    def test_empty_input_preserves_inherited_key(self) -> None:
        child = self.exercise({"INPUT_LICENSE_KEY": " \n", "PYOBFUS_LICENSE_KEY": "env-secret"})
        self.assertEqual(child["PYOBFUS_LICENSE_KEY"], "env-secret")

    def test_no_license_is_added_for_community(self) -> None:
        child = self.exercise({"INPUT_LICENSE_KEY": ""})
        self.assertNotIn("PYOBFUS_LICENSE_KEY", child)

    def test_structured_entitlement_error_is_not_suppressed(self) -> None:
        self.exercise({"INPUT_LICENSE_KEY": "input-secret"}, denied=True)


if __name__ == "__main__":
    unittest.main()
