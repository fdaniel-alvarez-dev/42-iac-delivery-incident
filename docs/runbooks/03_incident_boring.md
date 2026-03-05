# Runbook: Make incidents boring (reduce MTTR)

## When to use
- On-call pages are noisy
- Incidents recur without clear learning loops

## Principles
- Prefer actionable alerts tied to SLOs.
- Standardize severity and escalation.
- Capture learning via postmortems and follow-up actions.

## Immediate response
1) Stabilize service (rollback/feature flag/scale) before deep analysis.
2) Use a standard incident timeline: detect → mitigate → recover → learn.
3) Assign roles: incident commander, communications, operations.

## After action
1) Write a blameless postmortem within 48 hours.
2) Record root cause and corrective actions with owners and deadlines.
3) Update runbooks and alerts; re-run validation gates on updated configs.

