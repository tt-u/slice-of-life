# Planning / Architecture Notes Index

This directory now keeps only the docs that still matter during active development:

1. **active implementation contracts** — update these when behavior changes
2. **one implementation-grounded audit** — tracks remaining migration tails and cleanup priorities

## Active implementation contracts

- [`2026-04-19-generated-action-runtime-contract.md`](./2026-04-19-generated-action-runtime-contract.md)
  - generated-action runtime contract and remaining bridge boundaries
- [`2026-04-19-agent-run-state-reaction-schema.md`](./2026-04-19-agent-run-state-reaction-schema.md)
  - agent run-state / reaction-boundary contract
- [`2026-04-18-game-factory-architecture-audit.md`](./2026-04-18-game-factory-architecture-audit.md)
  - current replace / bridge / isolate map and the highest-leverage remaining migration tails

## Consolidated / removed draft topics

The repo no longer keeps free-floating draft plans once their content is either implemented or absorbed into authoritative docs.

- action-generation schema draft → landed as `2026-04-19-generated-action-runtime-contract.md`
- agent runtime decision draft → landed as `2026-04-19-agent-run-state-reaction-schema.md`
- game-factory reset plan → absorbed by the repo `README.md` plus the architecture audit
- web-grounded seed ingestion plan → absorbed by the repo `README.md`, anchor-case CLI flow, and the architecture audit
- early multi-role / initial-world / flash-crash planning notes → removed after their relevant behavior and constraints were either implemented or superseded

## Maintenance rule

When a plan becomes implementation-grounded, update an active contract or this index instead of leaving another stale draft in the repo. Keep the durable docs small, current, and explicit about what is authoritative.
