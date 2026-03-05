# 42-iac-delivery-incident

Portfolio repo that demonstrates practical guardrails for:
- Infrastructure drift + fragile IaC automation
- Delivery friction (slow/flaky CI/CD + risky releases)
- Reliability under real on-call pressure (lower incident rate + faster MTTR)

## What breaks in real orgs (and why it hurts)
- **Drift & inconsistency:** changes happen outside IaC, environments diverge, and reviews stop being trustworthy.
- **Delivery friction:** pipelines become slow and flaky; releases turn into high-stress events with preventable rollbacks.
- **On-call pain:** missing runbooks and weak feedback loops increase incident frequency and MTTR.

This repository ships a small, deterministic validator + report generator (standard library only) that turns sanitized
environment snapshots into a human-readable risk report and enforceable validation gates.

## Architecture (inputs → checks → outputs → runbooks)
- **Inputs:** `examples/**.json` (declared vs live IaC snapshots, pipeline metadata, SLO/alerts, incident history)
- **Checks:** deterministic controls that map to the 3 pain points
- **Outputs:** `artifacts/report.md` (findings + guardrails + runbook pointers)
- **Runbooks:** `docs/runbooks/` (incident response and delivery operationalization)

More detail: `docs/architecture.md`.

## Quick start
```bash
make setup
make demo
```

## Demo
`make demo` generates:
- `artifacts/report.md` — findings + guardrails mapped to the 3 pain points

To enforce controls (CI-style gate) on the **passing** example set:
```bash
make setup
PYTHONPATH=src python3 -m portfolio_proof validate --examples examples/passing
```

To see the validator fail on the **failing** example set:
```bash
PYTHONPATH=src python3 -m portfolio_proof validate --examples examples/failing
```

## Security / secrets handling
- No secrets are required for the demo and nothing reads environment credentials.
- Generated outputs go to `artifacts/` (gitignored).
- The GitHub token workflow is intentionally out-of-scope for the demo CLI (see `docs/security.md`).
