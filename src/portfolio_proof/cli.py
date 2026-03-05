from __future__ import annotations

import argparse
from pathlib import Path
from typing import Sequence

from .checks import run_all_checks
from .io import InputError, load_inputs
from .reporting import write_artifacts


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="portfolio_proof", description="Deterministic guardrail checks + report.")
    sub = parser.add_subparsers(dest="command", required=True)

    p_report = sub.add_parser("report", help="Generate artifacts/report.md and artifacts/validation.json")
    p_report.add_argument("--examples", type=Path, default=Path("examples/failing"), help="Examples directory")
    p_report.add_argument("--out", type=Path, default=Path("artifacts"), help="Output directory (gitignored)")

    p_validate = sub.add_parser("validate", help="Exit non-zero on policy violations")
    p_validate.add_argument("--examples", type=Path, default=Path("examples/passing"), help="Examples directory")
    p_validate.add_argument("--out", type=Path, default=None, help="Optional output directory for validation.json")

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)

    try:
        inputs = load_inputs(args.examples)
    except InputError as exc:
        # Exit code 3 reserved for input/schema problems.
        print(f"ERROR: {exc}")
        return 3

    summary = run_all_checks(
        controls=inputs.controls,
        iac_declared=inputs.iac_declared,
        iac_live=inputs.iac_live,
        pipeline=inputs.pipeline,
        service=inputs.service,
        incidents=inputs.incidents,
        runbooks=inputs.runbooks,
    )

    if args.command == "report":
        paths = write_artifacts(summary, out_dir=args.out, examples_dir=inputs.examples_dir)
        print(f"Wrote {paths['report']}")
        return 0

    if args.command == "validate":
        if args.out is not None:
            write_artifacts(summary, out_dir=args.out, examples_dir=inputs.examples_dir)
        if summary.passed:
            print("PASS")
        else:
            print("FAIL")
        return summary.exit_code

    raise AssertionError(f"Unknown command: {args.command}")

