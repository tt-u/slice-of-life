# Planning / Architecture Notes Index

This directory now mixes three kinds of documents:

1. **active implementation contracts** — still describe the current code and should be updated when behavior changes
2. **implementation-grounded audits** — useful reference for migration order and legacy cleanup
3. **historical plans** — kept for provenance, but no longer authoritative

## Active implementation contracts

- [`2026-04-19-generated-action-runtime-contract.md`](./2026-04-19-generated-action-runtime-contract.md)
  - current generated-action bridge contract and remaining migration boundaries
- [`2026-04-19-agent-run-state-reaction-schema.md`](./2026-04-19-agent-run-state-reaction-schema.md)
  - current agent run-state / reaction boundary contract
- [`2026-04-18-game-factory-architecture-audit.md`](./2026-04-18-game-factory-architecture-audit.md)
  - replace / bridge / isolate map for the game-factory migration

## Historical plans kept for context only

These documents captured earlier planning passes and can still be useful for rationale, but they should not be treated as the source of truth without checking the active contracts above:

- `2026-04-18-action-agent-runtime-decision-draft.md`
- `2026-04-18-multi-role-seed-iteration.md`
- `2026-04-18-initial-world-generator.md`
- `2026-04-18-flash-crash-demo.md`

## Obsolete local drafts

The following draft topics were intentionally consolidated instead of being committed as standalone plans:

- action-generation schema draft → landed as `2026-04-19-generated-action-runtime-contract.md`
- game-factory reset plan → absorbed by the repo `README.md` plus the architecture audit
- web-grounded seed ingestion plan → absorbed by the repo `README.md`, anchor-case CLI flow, and the architecture audit

## Maintenance rule

When a plan becomes implementation-grounded, prefer updating an active contract or this index instead of adding another free-floating draft. Keep the repo's durable docs small, current, and explicit about what is authoritative.
