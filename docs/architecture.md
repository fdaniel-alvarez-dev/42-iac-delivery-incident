# Architecture

## Purpose
This repo is a deterministic proof that converts sanitized operational snapshots into:
- a **risk report** (for humans)
- a **validation gate** (for CI)

It demonstrates three common pain points:
1) Infrastructure drift and fragile automation
2) Delivery friction and risky releases
3) Reliability under real on-call pressure

## Data flow
1) Read inputs from an examples directory (JSON, standard library only).
2) Run checks against a small set of explicit controls.
3) Emit artifacts:
   - `report.md` (human-readable)
   - `validation.json` (machine-readable summary)

## Threat model notes (lightweight)
- **Secrets exposure:** outputs must never include tokens/credentials; inputs are sanitized and stored under `examples/`.
- **Supply chain:** no runtime dependency downloads; standard library only.
- **Auditability:** deterministic checks + stable report structure enables review and CI gating.
- **Tampering:** treat example inputs as untrusted; the CLI validates schemas and fails closed on malformed data.

## Out of scope
- Running Terraform/Ansible/Chef for real
- Connecting to cloud APIs or CI providers
- Producing a complete governance framework

