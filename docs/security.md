# Security

## Controls in this repo
- **No secrets required:** demo runs entirely offline with sanitized JSON under `examples/`.
- **No secret printing:** the CLI never reads or prints `$GITHUB_TOKEN`.
- **Artifact hygiene:** generated content is written to `artifacts/` which is gitignored.
- **Fail closed:** `validate` exits non-zero on malformed inputs or policy violations.
- **Least privilege mindset:** if you extend this repo to integrate with APIs, use scoped tokens and avoid wide org access.

## What this repo intentionally does not do
- Store credentials or `.env` files in the repository.
- Call external services from the demo tool.
- Provide a full secrets management implementation (Vault/KMS/etc.).

## Suggested extensions (portfolio discussion)
- Add pre-commit secret scanning (e.g., gitleaks) in your real workflow.
- Integrate with CI to enforce `validate` on pull requests for infra/pipeline changes.

