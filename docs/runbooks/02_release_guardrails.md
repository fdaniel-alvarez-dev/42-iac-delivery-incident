# Runbook: Release guardrails and rollback readiness

## When to use
- Release failures, repeated rollbacks, or “Friday deploy” fear
- Pipeline is slow/flaky and teams work around it

## Guardrails to enforce
1) Production deploy requires approvals (and is auditable).
2) Tests are required before deploy (unit + at least one integration smoke stage).
3) Artifacts are immutable (build once, deploy many).
4) Rollback is defined and tested (timeboxed).
5) Safer rollout strategy exists (canary or blue/green) for high-risk services.

## Operational steps
1) Define promotion rules per environment.
2) Add a rollback checklist and verify it during game days.
3) Track delivery KPIs: lead time, change failure rate, mean time to restore.

