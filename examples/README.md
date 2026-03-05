# Examples

The demo CLI reads sanitized JSON snapshots from `examples/`.

- `examples/passing/`: passes `validate` (CI gate style).
- `examples/failing/`: intentionally violates key controls to demonstrate how the report surfaces risk.

Inputs are intentionally simplified and provider-agnostic: the point is to make the guardrails reviewable and repeatable.

