from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

from .types import Finding, ValidationSummary


_PAIN_POINT_TITLES: dict[str, str] = {
    "iac_automation": "Infrastructure drift + fragile automation",
    "ci_cd_delivery": "Delivery friction + risky releases",
    "reliability_incidents": "Reliability under on-call pressure",
}


def _md_escape(text: str) -> str:
    return text.replace("\n", " ").strip()


def render_report(summary: ValidationSummary, *, examples_dir: Path) -> str:
    by_pain: dict[str, list[Finding]] = {}
    for finding in summary.findings:
        by_pain.setdefault(finding.pain_point, []).append(finding)

    lines: list[str] = []
    lines.append("# Portfolio Proof Report")
    lines.append("")
    lines.append(f"**Input set:** `{examples_dir.as_posix()}`")
    lines.append("")
    lines.append("## Validation result")
    lines.append(f"- Passed: `{summary.passed}`")
    lines.append(f"- Exit code (validate): `{summary.exit_code}`")
    lines.append("")

    lines.append("## Pain points covered")
    for key in ("iac_automation", "ci_cd_delivery", "reliability_incidents"):
        title = _PAIN_POINT_TITLES.get(key, key)
        hi = sum(1 for f in by_pain.get(key, []) if f.severity in {"CRITICAL", "HIGH"})
        med = sum(1 for f in by_pain.get(key, []) if f.severity == "MEDIUM")
        low = sum(1 for f in by_pain.get(key, []) if f.severity == "LOW")
        lines.append(f"- **{title}:** {hi} high/critical, {med} medium, {low} low")
    lines.append("")

    lines.append("## Findings")
    if not summary.findings:
        lines.append("- No findings.")
        lines.append("")
    else:
        for finding in summary.findings:
            lines.append(f"### [{finding.severity}] {finding.code} — {_md_escape(finding.title)}")
            lines.append(f"- Pain point: `{finding.pain_point}`")
            lines.append(f"- Evidence: {_md_escape(finding.evidence)}")
            lines.append(f"- Recommendation: {_md_escape(finding.recommendation)}")
            if finding.runbooks:
                lines.append(f"- Runbooks: {', '.join(f'`{p}`' for p in finding.runbooks)}")
            lines.append("")

    lines.append("## Suggested guardrails (merge gates)")
    lines.append("- Block merges when IaC drift budget is exceeded.")
    lines.append("- Require immutable artifacts + mandatory tests before production deploy.")
    lines.append("- Tie paging to SLO burn and require postmortems for Sev1/Sev2.")
    lines.append("")

    lines.append("## Metrics (machine-friendly)")
    lines.append("```json")
    lines.append(json.dumps(summary.metrics, sort_keys=True, indent=2))
    lines.append("```")
    lines.append("")

    return "\n".join(lines)


def write_artifacts(summary: ValidationSummary, *, out_dir: Path, examples_dir: Path) -> dict[str, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    report_path = out_dir / "report.md"
    validation_path = out_dir / "validation.json"

    report_path.write_text(render_report(summary, examples_dir=examples_dir), encoding="utf-8")
    validation_path.write_text(
        json.dumps(
            {
                "passed": summary.passed,
                "exit_code": summary.exit_code,
                "metrics": summary.metrics,
                "findings": [asdict(f) for f in summary.findings],
            },
            sort_keys=True,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return {"report": report_path, "validation": validation_path}

