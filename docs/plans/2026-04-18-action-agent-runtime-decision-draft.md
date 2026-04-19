# Agent Run-State / Reaction Schema — Runtime Contract

> Item advanced in this pass: **Todo 1 — finalize Agent Run-State / Reaction Schema defining `方向自由，边界受控` agent evolution and runtime validation boundaries**.

This document is no longer a product-ideation draft. It records the runtime contract now implemented in `src/eventforge/domain.py` and `src/eventforge/engine.py`, and it defines how agent evolution stays generative without reverting to fixed reaction tables.

## Goal

Make agent evolution:

- **direction free** — reactions depend on the chosen action, live world state, agent role, and recent history
- **boundary controlled** — runtime validates every proposed update against world-authored caps before it mutates state

The engine should never hardcode “role X must always react with outcome Y.”
It should instead persist agent state, accept bounded proposals, and clamp everything that exceeds the world contract.

---

## Core rule

> **LLM or bridge logic may propose agent change freely; only validated change may enter runtime state.**

That rule applies whether the proposal comes from:

1. the current bridge from legacy reaction logic, or
2. a future world-local generative reaction prompt.

---

## Runtime schema

## 1. `AgentStateAxisDef`

Defines one bounded scalar axis for runtime agent state.

Current fields:

- `key`
- `label`
- `description`
- `min_value`
- `max_value`
- `max_delta_per_turn`

### Current baseline axes

The default migration boundary uses four scalar axes:

- `trust_in_player`
- `pressure_load`
- `escalation_drive`
- `public_alignment`

These are intentionally cross-world enough to bridge the old engine, but still bounded explicitly per world via `reaction_boundaries`.

## 2. `AgentRelationshipState`

Stores one agent’s current relationship to another entity.

Current bounded fields:

- `alignment`
- `strain`
- `dependency`
- `visibility`

All relationship values are normalized to `0..100`.

## 3. `AgentMemoryEntry`

Stores one persistent memory slice from a prior turn.

Current fields:

- `turn_index`
- `action_id`
- `summary`
- `salience`
- `valence`

This keeps run continuity explicit instead of hiding it inside prompt-only context.

## 4. `AgentRunState`

Persistent per-run state for one agent.

Current fields:

- `agent_id`
- `agent_name`
- `role`
- `stance`
- `current_objective`
- `scalar_state`
- `relationships`
- `memories`
- `triggered_hooks`

### Contract

`AgentRunState` is the authoritative mutable runtime memory for agent evolution.
It is the object that survives across turns.

## 5. `AgentReactionBoundaries`

World-authored validation envelope attached to `FrozenInitialWorld`.

Current fields:

- `scalar_axes`
- `max_relationship_delta_per_turn`
- `max_dimension_impacts_per_reaction`
- `max_dimension_delta_per_reaction`
- `max_relationship_updates_per_reaction`
- `max_hooks_per_reaction`
- `memory_limit`
- `allowed_hook_tags`

### Meaning

This is the explicit implementation of **边界受控**.
The world owns these caps, not the generic engine.

## 6. `AgentReactionContext`

Structured input passed into reaction generation / validation.

Current fields include:

- world identity and title
- turn index and turn count
- player role and objective
- chosen action id / label / summary
- current dimensions
- urgent / unstable dimensions
- dominant tensions
- acting agent run state
- relevant entities
- recent turn summaries
- active `AgentReactionBoundaries`

### Contract

Reaction logic must be conditioned on **this turn’s real situation**, not on a global canned lookup table.

## 7. `AgentReactionProposal`

Untrusted proposed update.

Current fields:

- `summary`
- `stance`
- `updated_objective`
- `scalar_deltas`
- `relationship_deltas`
- `dimension_impacts`
- `follow_on_hooks`

### Important distinction

A proposal is **not** runtime truth.
It is only candidate output waiting for validation.

## 8. `AgentReactionResult`

Validated applied outcome.

Current fields:

- `agent_id`
- `agent_name`
- `role`
- `summary`
- `stance`
- `objective`
- `applied_scalar_deltas`
- `applied_relationship_deltas`
- `applied_dimension_impacts`
- `triggered_hooks`

This is the post-validation record used by the runtime loop and reporting.

---

## Validation pipeline

The validator is `validate_agent_reaction_proposal(...)` in `src/eventforge/engine.py`.

Validation order is deliberate and should remain stable:

1. **ignore unknown scalar axes**
2. **clamp scalar deltas by each axis’s `max_delta_per_turn`**
3. **clamp resulting scalar values to axis min/max**
4. **ignore unknown relationship targets**
5. **ignore unknown relationship fields**
6. **limit relationship updates to `max_relationship_updates_per_reaction`**
7. **clamp relationship deltas by `max_relationship_delta_per_turn`**
8. **clamp relationship values to `0..100`**
9. **ignore unknown world dimensions**
10. **limit dimension impacts to `max_dimension_impacts_per_reaction`**
11. **clamp dimension deltas by `max_dimension_delta_per_reaction`**
12. **ignore disallowed hook tags**
13. **dedupe hooks and enforce `max_hooks_per_reaction`**
14. **append one memory entry for the turn**
15. **trim memories to `memory_limit`**
16. **persist the validated `AgentRunState` and emit `AgentReactionResult`**

This ordering matters because it guarantees invalid proposal surface area is removed before any persistent state is written.

---

## Zero-cap semantics

Zero and negative caps are treated as hard disables, not soft suggestions.

### Current enforced behavior

- if `max_hooks_per_reaction <= 0`, no hooks are emitted
- if `memory_limit <= 0`, no memories are retained

This behavior has regression coverage because an earlier boundary bug could accidentally keep hooks or memories alive under zero caps.

---

## Runtime bridge policy

This migration pass does **not** require fully autonomous agent prompting yet.

Current bridge behavior:

1. existing reaction logic still produces the first-pass reaction shape
2. runtime converts that legacy output into an `AgentReactionProposal`
3. validator clamps and filters the proposal
4. runtime persists `agent_run_states`
5. downstream callers still receive the old reaction-facing output where needed

This is intentional.
It gives us explicit persistent state and validation boundaries first, before replacing the whole reaction generator.

---

## What this schema prevents

This contract is specifically designed to block the old failure modes:

- **fixed reaction tables** — blocked because reactions now flow through per-turn context + run state
- **unbounded improvisation** — blocked because proposals are not trusted and must be clamped
- **mystery state jumps** — blocked because applied deltas are explicit in `AgentReactionResult`
- **demo-world leakage** — reduced because boundaries live on each frozen world rather than in one global reaction table

---

## What remains intentionally flexible

The schema leaves room for future world-local sophistication without changing the contract:

- worlds can add richer scalar axes later
- worlds can vary allowed hook tags
- reaction prompts can become fully world-authored later
- relationship targeting can become more selective per world
- memory scoring can evolve without changing payload shape

That is the correct interpretation of **方向自由，边界受控**:

- free in proposal direction
- bounded in mutation surface
- explicit in persistence
- world-owned in limits

---

## Serialization contract

All runtime agent schema objects above support payload round-trip serialization in `src/eventforge/domain.py`.

This matters because:

1. `FrozenInitialWorld` must be a portable artifact
2. `reaction_boundaries` must survive JSON persistence
3. future saved-run / replay flows will need stable agent-state payloads

The current test suite already covers:

- `AgentRunState` payload round-trips
- `AgentReactionBoundaries` payload round-trips
- frozen-world serialization including `reaction_boundaries`
- validator clamping / unknown-field filtering
- zero-cap hook and memory behavior
- runtime bridge updates to `agent_run_states`

---

## Approved implementation boundary for the next passes

With this schema finalized, later work should follow these rules:

1. **Todo 5 / 7 runtime work must read world-owned boundaries from `FrozenInitialWorld`**
2. **future reaction prompts must output `AgentReactionProposal`-compatible payloads**
3. **no new direct state mutation path should bypass the validator**
4. **world-specific volatility belongs in `reaction_boundaries`, not engine globals**
5. **legacy reaction code is a migration bridge only, not the long-term architecture**

---

## Bottom line

The project now has a concrete agent runtime contract:

- persistent per-agent run state
- explicit world-owned reaction boundaries
- proposal vs validated-result separation
- deterministic runtime clamping
- memory and hook caps with tested zero-cap semantics

That is the current implementation-grounded answer to the product rule:

> **agent evolution is direction free, boundary controlled.**
