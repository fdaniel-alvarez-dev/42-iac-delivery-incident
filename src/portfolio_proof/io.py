from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


class InputError(Exception):
    pass


@dataclass(frozen=True)
class Inputs:
    examples_dir: Path
    controls: dict[str, Any]
    iac_declared: dict[str, Any]
    iac_live: dict[str, Any]
    pipeline: dict[str, Any]
    service: dict[str, Any]
    incidents: dict[str, Any]
    runbooks: dict[str, Any]


def _read_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise InputError(f"Missing required input file: {path}") from exc
    except json.JSONDecodeError as exc:
        raise InputError(f"Invalid JSON in {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise InputError(f"Expected a JSON object in {path}")
    return data


def load_inputs(examples_dir: Path) -> Inputs:
    examples_dir = examples_dir.resolve()
    if not examples_dir.exists():
        raise InputError(f"Examples directory does not exist: {examples_dir}")
    if not examples_dir.is_dir():
        raise InputError(f"Examples path is not a directory: {examples_dir}")

    controls = _read_json(examples_dir / "controls.json")
    iac_declared = _read_json(examples_dir / "iac_declared.json")
    iac_live = _read_json(examples_dir / "iac_live.json")
    pipeline = _read_json(examples_dir / "pipeline.json")
    service = _read_json(examples_dir / "service.json")
    incidents = _read_json(examples_dir / "incidents.json")
    runbooks = _read_json(examples_dir / "runbooks.json")

    return Inputs(
        examples_dir=examples_dir,
        controls=controls,
        iac_declared=iac_declared,
        iac_live=iac_live,
        pipeline=pipeline,
        service=service,
        incidents=incidents,
        runbooks=runbooks,
    )

