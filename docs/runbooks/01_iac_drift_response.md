# Runbook: IaC drift response

## When to use
- A drift check reports declared vs live mismatches
- Environments behave differently despite “same code”

## Triage
1) Identify scope: which resources drifted and which environments are impacted.
2) Confirm source of change: IaC pipeline vs manual/hotfix vs automation outside Git.
3) Assess blast radius: network/security resources first, then stateful services.

## Containment
1) Pause risky automation for the affected scope (reduce further changes while investigating).
2) If the drift represents an emergency fix, capture it as a documented exception with an expiry date.

## Remediation
1) Reconcile: either revert live to declared, or update declared to match the intended live state.
2) Add/strengthen guardrails:
   - required tagging
   - version pinning
   - drift detection as a merge gate

## Validation
- Re-run `validate` on the updated snapshot and ensure drift is 0 for the target environment.

