from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable

from .types import Finding, ValidationSummary


def _as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def _get_required_tags(controls: dict[str, Any]) -> list[str]:
    tags = controls.get("required_tags", [])
    if not isinstance(tags, list) or not all(isinstance(x, str) for x in tags):
        return []
    return tags


def _iter_resources(snapshot: dict[str, Any]) -> Iterable[dict[str, Any]]:
    resources = snapshot.get("resources", [])
    if not isinstance(resources, list):
        return []
    for item in resources:
        if isinstance(item, dict):
            yield item


def _resource_index(snapshot: dict[str, Any]) -> dict[str, dict[str, Any]]:
    idx: dict[str, dict[str, Any]] = {}
    for res in _iter_resources(snapshot):
        rid = res.get("id")
        if isinstance(rid, str) and rid:
            idx[rid] = res
    return idx


def _check_iac_drift(inputs: dict[str, Any]) -> tuple[list[Finding], dict[str, Any]]:
    controls = inputs["controls"]
    declared = inputs["iac_declared"]
    live = inputs["iac_live"]

    findings: list[Finding] = []
    metrics: dict[str, Any] = {}

    required_tags = _get_required_tags(controls)
    require_pinned = bool(controls.get("iac", {}).get("require_pinned_versions", False))
    max_drift = int(controls.get("iac", {}).get("max_drift_resources", 0) or 0)

    declared_idx = _resource_index(declared)
    live_idx = _resource_index(live)

    drifted: list[str] = []
    missing: list[str] = []
    extra: list[str] = []
    missing_tags: list[str] = []
    unpinned: list[str] = []

    for rid, dres in sorted(declared_idx.items()):
        if rid not in live_idx:
            missing.append(rid)
            continue
        lres = live_idx[rid]
        if dres.get("config_hash") != lres.get("config_hash"):
            drifted.append(rid)

        tags = lres.get("tags", {})
        if isinstance(tags, dict):
            for tag in required_tags:
                if tag not in tags:
                    missing_tags.append(f"{rid}:{tag}")
        else:
            for tag in required_tags:
                missing_tags.append(f"{rid}:{tag}")

        if require_pinned and not bool(lres.get("pinned", False)):
            unpinned.append(rid)

    for rid in sorted(live_idx.keys()):
        if rid not in declared_idx:
            extra.append(rid)

    drift_count = len(drifted) + len(missing) + len(extra)
    metrics["iac_drift_resources"] = drift_count
    metrics["iac_missing_required_tags"] = len(missing_tags)
    metrics["iac_unpinned_versions"] = len(unpinned)

    if drifted:
        findings.append(
            Finding(
                code="IAC_DRIFT",
                severity="HIGH",
                pain_point="iac_automation",
                title="Declared vs live configuration drift detected",
                evidence=f"Drifted resources: {', '.join(drifted)}",
                recommendation="Detect drift continuously and block merges when drift is non-zero; reconcile via PRs.",
                runbooks=("docs/runbooks/01_iac_drift_response.md",),
            )
        )
    if missing or extra:
        details = []
        if missing:
            details.append(f"Missing in live: {', '.join(missing)}")
        if extra:
            details.append(f"Extra in live: {', '.join(extra)}")
        findings.append(
            Finding(
                code="IAC_INVENTORY_MISMATCH",
                severity="HIGH",
                pain_point="iac_automation",
                title="IaC inventory mismatch between declared and live",
                evidence="; ".join(details),
                recommendation="Treat the declared inventory as the source of truth and prevent out-of-band creation.",
                runbooks=("docs/runbooks/01_iac_drift_response.md",),
            )
        )
    if missing_tags:
        findings.append(
            Finding(
                code="IAC_TAGGING",
                severity="MEDIUM",
                pain_point="iac_automation",
                title="Required tags missing on live resources",
                evidence=f"Missing tags: {', '.join(missing_tags[:12])}"
                + (" …" if len(missing_tags) > 12 else ""),
                recommendation="Enforce tags via policy-as-code and fail infrastructure changes that omit ownership/env tags.",
                runbooks=("docs/runbooks/01_iac_drift_response.md",),
            )
        )
    if unpinned:
        findings.append(
            Finding(
                code="IAC_UNPINNED",
                severity="MEDIUM",
                pain_point="iac_automation",
                title="Unpinned versions increase drift and rollback risk",
                evidence=f"Unpinned resources: {', '.join(unpinned)}",
                recommendation="Pin versions for critical components and review upgrades explicitly via PR.",
                runbooks=("docs/runbooks/01_iac_drift_response.md",),
            )
        )
    if drift_count > max_drift:
        findings.append(
            Finding(
                code="IAC_DRIFT_BUDGET",
                severity="CRITICAL",
                pain_point="iac_automation",
                title="Drift budget exceeded",
                evidence=f"Drifted/missing/extra resources: {drift_count} > allowed {max_drift}",
                recommendation="Stop the line: reconcile drift before proceeding with further changes.",
                runbooks=("docs/runbooks/01_iac_drift_response.md",),
            )
        )

    return findings, metrics


def _pipeline_stage_names(pipeline: dict[str, Any]) -> list[str]:
    stages = pipeline.get("stages", [])
    if not isinstance(stages, list):
        return []
    names: list[str] = []
    for stage in stages:
        if isinstance(stage, dict) and isinstance(stage.get("name"), str):
            names.append(stage["name"])
    return names


def _prod_stage(pipeline: dict[str, Any]) -> dict[str, Any] | None:
    stages = pipeline.get("stages", [])
    if not isinstance(stages, list):
        return None
    for stage in stages:
        if not isinstance(stage, dict):
            continue
        if stage.get("environment") == "prod":
            return stage
    return None


def _check_pipeline(inputs: dict[str, Any]) -> tuple[list[Finding], dict[str, Any]]:
    controls = inputs["controls"]
    pipeline = inputs["pipeline"]

    findings: list[Finding] = []
    metrics: dict[str, Any] = {}

    pipeline_controls = controls.get("pipeline", {}) if isinstance(controls.get("pipeline", {}), dict) else {}
    required_stages = [
        x for x in _as_list(pipeline_controls.get("required_test_stages", [])) if isinstance(x, str)
    ]
    require_prod_approvals = bool(pipeline_controls.get("require_prod_approvals", False))
    require_immutable_artifacts = bool(pipeline_controls.get("require_immutable_artifacts", False))
    prod_requires_strategy = bool(pipeline_controls.get("prod_requires_strategy", False))
    allowed_strategies = [
        x for x in _as_list(pipeline_controls.get("allowed_strategies", [])) if isinstance(x, str)
    ]

    stage_names = _pipeline_stage_names(pipeline)
    missing_required = [s for s in required_stages if s not in stage_names]

    artifact = pipeline.get("artifact", {}) if isinstance(pipeline.get("artifact", {}), dict) else {}
    immutable = bool(artifact.get("immutable", False))

    prod = _prod_stage(pipeline)
    prod_approvals = int(prod.get("approvals_required", 0) or 0) if isinstance(prod, dict) else 0
    prod_strategy = prod.get("strategy") if isinstance(prod, dict) else None
    rollback_plan = prod.get("rollback_plan") if isinstance(prod, dict) else None

    observations = pipeline.get("observations", {}) if isinstance(pipeline.get("observations", {}), dict) else {}
    p95_minutes = observations.get("p95_minutes")
    flake_rate = observations.get("flake_rate")

    if isinstance(p95_minutes, (int, float)):
        metrics["pipeline_p95_minutes"] = float(p95_minutes)
    if isinstance(flake_rate, (int, float)):
        metrics["pipeline_flake_rate"] = float(flake_rate)

    if missing_required:
        findings.append(
            Finding(
                code="PIPELINE_MISSING_TESTS",
                severity="HIGH",
                pain_point="ci_cd_delivery",
                title="Pipeline missing required test stages",
                evidence=f"Missing stages: {', '.join(missing_required)}",
                recommendation="Make tests mandatory gates before production deploy; add fast smoke coverage to reduce rollbacks.",
                runbooks=("docs/runbooks/02_release_guardrails.md",),
            )
        )

    if require_immutable_artifacts and not immutable:
        findings.append(
            Finding(
                code="PIPELINE_MUTABLE_ARTIFACTS",
                severity="HIGH",
                pain_point="ci_cd_delivery",
                title="Artifacts are not immutable (build once, deploy many)",
                evidence="pipeline.artifact.immutable is false",
                recommendation="Build a single artifact per commit and promote the same artifact across environments.",
                runbooks=("docs/runbooks/02_release_guardrails.md",),
            )
        )

    if require_prod_approvals and prod_approvals <= 0:
        findings.append(
            Finding(
                code="PIPELINE_NO_APPROVALS",
                severity="HIGH",
                pain_point="ci_cd_delivery",
                title="Production deploy lacks approvals",
                evidence=f"approvals_required={prod_approvals}",
                recommendation="Require peer approval (and record it) for production deployments.",
                runbooks=("docs/runbooks/02_release_guardrails.md",),
            )
        )

    if prod_requires_strategy:
        if not isinstance(prod_strategy, str) or not prod_strategy:
            findings.append(
                Finding(
                    code="PIPELINE_NO_STRATEGY",
                    severity="MEDIUM",
                    pain_point="ci_cd_delivery",
                    title="No rollout strategy defined for production",
                    evidence="No strategy set for prod stage",
                    recommendation="Adopt a safer rollout strategy (canary/blue-green) for high-risk services.",
                    runbooks=("docs/runbooks/02_release_guardrails.md",),
                )
            )
        elif allowed_strategies and prod_strategy not in allowed_strategies:
            findings.append(
                Finding(
                    code="PIPELINE_BAD_STRATEGY",
                    severity="MEDIUM",
                    pain_point="ci_cd_delivery",
                    title="Rollout strategy not in allowed set",
                    evidence=f"strategy={prod_strategy}; allowed={', '.join(allowed_strategies)}",
                    recommendation="Standardize supported strategies and document rollback expectations per strategy.",
                    runbooks=("docs/runbooks/02_release_guardrails.md",),
                )
            )

    if rollback_plan not in {"automatic", "manual"}:
        findings.append(
            Finding(
                code="PIPELINE_ROLLBACK_UNCLEAR",
                severity="MEDIUM",
                pain_point="ci_cd_delivery",
                title="Rollback plan is unclear",
                evidence=f"rollback_plan={rollback_plan!r}",
                recommendation="Document and test rollback paths; prefer automatic rollback for canary/blue-green.",
                runbooks=("docs/runbooks/02_release_guardrails.md",),
            )
        )

    if isinstance(p95_minutes, (int, float)) and float(p95_minutes) > 30:
        findings.append(
            Finding(
                code="PIPELINE_SLOW",
                severity="LOW",
                pain_point="ci_cd_delivery",
                title="Pipeline is slow (high p95)",
                evidence=f"p95_minutes={p95_minutes}",
                recommendation="Use caching, parallelism, and smaller test scopes to keep lead time low.",
                runbooks=("docs/runbooks/02_release_guardrails.md",),
            )
        )

    if isinstance(flake_rate, (int, float)) and float(flake_rate) >= 0.1:
        findings.append(
            Finding(
                code="PIPELINE_FLAKY",
                severity="MEDIUM",
                pain_point="ci_cd_delivery",
                title="Pipeline flakiness increases delivery friction and risk",
                evidence=f"flake_rate={flake_rate}",
                recommendation="Quarantine flaky tests, add retries only as a temporary measure, and track flake rate as a KPI.",
                runbooks=("docs/runbooks/02_release_guardrails.md",),
            )
        )

    return findings, metrics


def _runbook_index(runbooks: dict[str, Any]) -> set[str]:
    rb = runbooks.get("runbooks", [])
    if not isinstance(rb, list):
        return set()
    ids: set[str] = set()
    for item in rb:
        if isinstance(item, dict) and isinstance(item.get("id"), str):
            ids.add(item["id"])
    return ids


def _check_reliability(inputs: dict[str, Any]) -> tuple[list[Finding], dict[str, Any]]:
    controls = inputs["controls"]
    service = inputs["service"]
    incidents = inputs["incidents"]
    runbooks = inputs["runbooks"]

    findings: list[Finding] = []
    metrics: dict[str, Any] = {}

    rel_controls = controls.get("reliability", {}) if isinstance(controls.get("reliability", {}), dict) else {}
    require_slo = bool(rel_controls.get("require_slo", False))
    max_mttr = int(rel_controls.get("max_mttr_minutes", 0) or 0)
    require_postmortem = bool(rel_controls.get("require_postmortem_for_sev1_2", False))
    require_runbook = bool(rel_controls.get("require_runbook_for_service", False))

    slo = service.get("slo") if isinstance(service.get("slo"), dict) else None
    availability_target = None
    if isinstance(slo, dict):
        availability_target = slo.get("availability_target")
        if isinstance(availability_target, (int, float)):
            metrics["slo_availability_target"] = float(availability_target)

    if require_slo and slo is None:
        findings.append(
            Finding(
                code="SLO_MISSING",
                severity="HIGH",
                pain_point="reliability_incidents",
                title="Service SLO is missing",
                evidence="service.slo is missing",
                recommendation="Define an availability SLO and tie paging to error-budget burn alerts.",
                runbooks=("docs/runbooks/03_incident_boring.md",),
            )
        )
    elif isinstance(availability_target, (int, float)) and float(availability_target) < 0.995:
        findings.append(
            Finding(
                code="SLO_WEAK",
                severity="MEDIUM",
                pain_point="reliability_incidents",
                title="SLO target is low for a critical API",
                evidence=f"availability_target={availability_target}",
                recommendation="Raise the availability target or narrow the SLO scope and improve alerting quality.",
                runbooks=("docs/runbooks/03_incident_boring.md",),
            )
        )

    incident_list = incidents.get("incidents", [])
    if not isinstance(incident_list, list):
        incident_list = []

    durations: list[int] = []
    sev12_missing_postmortem: list[str] = []
    for inc in incident_list:
        if not isinstance(inc, dict):
            continue
        dur = inc.get("duration_minutes")
        if isinstance(dur, int) and dur >= 0:
            durations.append(dur)
        sev = inc.get("severity")
        pm = inc.get("postmortem_complete")
        if require_postmortem and isinstance(sev, int) and sev in {1, 2} and not bool(pm):
            iid = inc.get("id")
            if isinstance(iid, str):
                sev12_missing_postmortem.append(iid)

    avg_mttr = (sum(durations) / len(durations)) if durations else 0.0
    metrics["incident_count"] = len(durations)
    metrics["incident_avg_mttr_minutes"] = round(float(avg_mttr), 2)

    if max_mttr and avg_mttr > max_mttr:
        findings.append(
            Finding(
                code="MTTR_HIGH",
                severity="HIGH",
                pain_point="reliability_incidents",
                title="Mean time to restore exceeds target",
                evidence=f"avg_mttr_minutes={round(avg_mttr,2)} > allowed {max_mttr}",
                recommendation="Improve detection and rollback readiness; tighten runbooks and practice incident response.",
                runbooks=("docs/runbooks/03_incident_boring.md",),
            )
        )

    if sev12_missing_postmortem:
        findings.append(
            Finding(
                code="POSTMORTEM_MISSING",
                severity="HIGH",
                pain_point="reliability_incidents",
                title="Postmortems missing for Sev1/Sev2 incidents",
                evidence=f"Incidents without postmortem: {', '.join(sev12_missing_postmortem)}",
                recommendation="Require blameless postmortems within 48 hours and track follow-up actions to completion.",
                runbooks=("docs/runbooks/03_incident_boring.md",),
            )
        )

    runbook_id = service.get("runbook_id")
    rb_ids = _runbook_index(runbooks)
    if require_runbook:
        if not isinstance(runbook_id, str) or not runbook_id:
            findings.append(
                Finding(
                    code="RUNBOOK_UNSET",
                    severity="MEDIUM",
                    pain_point="reliability_incidents",
                    title="Service has no runbook reference",
                    evidence="service.runbook_id is missing",
                    recommendation="Link every paged service to a runbook and validate it exists.",
                    runbooks=("docs/runbooks/03_incident_boring.md",),
                )
            )
        elif runbook_id not in rb_ids:
            findings.append(
                Finding(
                    code="RUNBOOK_MISSING",
                    severity="HIGH",
                    pain_point="reliability_incidents",
                    title="Referenced runbook does not exist in the runbook index",
                    evidence=f"runbook_id={runbook_id}",
                    recommendation="Create the missing runbook and keep the runbook registry in sync with services.",
                    runbooks=("docs/runbooks/03_incident_boring.md",),
                )
            )

    return findings, metrics


def run_all_checks(*, controls: dict[str, Any], iac_declared: dict[str, Any], iac_live: dict[str, Any], pipeline: dict[str, Any], service: dict[str, Any], incidents: dict[str, Any], runbooks: dict[str, Any]) -> ValidationSummary:
    inputs = {
        "controls": controls,
        "iac_declared": iac_declared,
        "iac_live": iac_live,
        "pipeline": pipeline,
        "service": service,
        "incidents": incidents,
        "runbooks": runbooks,
    }

    findings: list[Finding] = []
    metrics: dict[str, Any] = {"pain_points": ["iac_automation", "ci_cd_delivery", "reliability_incidents"]}

    iac_findings, iac_metrics = _check_iac_drift(inputs)
    pipe_findings, pipe_metrics = _check_pipeline(inputs)
    rel_findings, rel_metrics = _check_reliability(inputs)

    findings.extend(iac_findings)
    findings.extend(pipe_findings)
    findings.extend(rel_findings)

    metrics.update(iac_metrics)
    metrics.update(pipe_metrics)
    metrics.update(rel_metrics)

    findings_sorted = tuple(sorted(findings, key=lambda f: (f.pain_point, f.severity, f.code, f.title)))

    # Exit codes:
    # - 0: passed
    # - 2: policy violations present
    passed = not any(f.severity in {"CRITICAL", "HIGH", "MEDIUM"} for f in findings_sorted)
    exit_code = 0 if passed else 2
    return ValidationSummary(passed=passed, exit_code=exit_code, findings=findings_sorted, metrics=metrics)

