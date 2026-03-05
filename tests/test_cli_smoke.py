from __future__ import annotations

import os
import subprocess
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def run_cli(*args: str, cwd: Path) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(REPO_ROOT / "src")
    return subprocess.run(
        ["python3", "-m", "portfolio_proof", *args],
        cwd=str(cwd),
        env=env,
        text=True,
        capture_output=True,
    )


class TestCliSmoke(unittest.TestCase):
    def test_validate_passing_examples_exits_zero(self) -> None:
        result = run_cli("validate", "--examples", "examples/passing", cwd=REPO_ROOT)
        self.assertEqual(result.returncode, 0, msg=result.stdout + "\n" + result.stderr)
        self.assertIn("PASS", result.stdout)

    def test_validate_failing_examples_exits_two(self) -> None:
        result = run_cli("validate", "--examples", "examples/failing", cwd=REPO_ROOT)
        self.assertEqual(result.returncode, 2, msg=result.stdout + "\n" + result.stderr)
        self.assertIn("FAIL", result.stdout)

    def test_report_generates_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp) / "artifacts"
            result = run_cli(
                "report",
                "--examples",
                "examples/failing",
                "--out",
                str(out_dir),
                cwd=REPO_ROOT,
            )
            self.assertEqual(result.returncode, 0, msg=result.stdout + "\n" + result.stderr)
            self.assertTrue((out_dir / "report.md").exists())
            self.assertTrue((out_dir / "validation.json").exists())

