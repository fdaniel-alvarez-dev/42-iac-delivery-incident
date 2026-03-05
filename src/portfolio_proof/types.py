from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable


Severity = str
PainPoint = str


@dataclass(frozen=True)
class Finding:
    code: str
    severity: Severity
    pain_point: PainPoint
    title: str
    evidence: str
    recommendation: str
    runbooks: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class ValidationSummary:
    passed: bool
    exit_code: int
    findings: tuple[Finding, ...]
    metrics: dict[str, Any]

    def by_severity(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for finding in self.findings:
            counts[finding.severity] = counts.get(finding.severity, 0) + 1
        return counts

    def high_impact(self) -> Iterable[Finding]:
        for finding in self.findings:
            if finding.severity in {"CRITICAL", "HIGH"}:
                yield finding

