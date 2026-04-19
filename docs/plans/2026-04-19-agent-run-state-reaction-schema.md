# Agent Run-State / Reaction Schema

> **For Hermes:** This document is now the source of truth for approved todo item **1** (`finalize Agent Run-State / Reaction Schema`) and the implementation contract for todo item **6**.

**Goal:** Define a runtime model that lets agents evolve freely per run while keeping evolution inside explicit, testable world-authored boundaries.

**Architecture:** Runtime stores a persistent per-agent state vector plus relationship state and short memory. Each turn, runtime builds a reaction context from the frozen world, current dimensions, player action, and recent history. The model may propose any direction of change, but the engine clamps, validates, and rejects updates that violate the world's declared bounds.

**Tech Stack:** Python 3.11 dataclasses, frozen-world JSON artifacts, OpenAI-compatible generation, pytest.

---

## Decision Summary

This project should use **constrained generative evolution**.

That means:

1. **No fixed reaction table**
   - the engine must not hardcode `role X always reacts with branch Y`
2. **Direction free**
   - the model may move an agent toward support, hostility, hesitation, opportunism, withdrawal, or escalation depending on the exact run context
3. **Boundary controlled**
   - the engine must validate all proposed changes against explicit world-authored limits before applying them
4. **World-local semantics**
   - the frozen world defines the meaningful axes, relationship surfaces, volatility caps, trigger hooks, and abnormal thresholds for that world
5. **Persistent run state**
   - agents do not only emit one-off flavor text; they accumulate state, relationship drift, and short memory across turns

This keeps the product aligned with the rule:

```text
agent evolution = free direction + controlled boundaries
```

---

## What Must Be Runtime-Stateful

A frozen world is immutable. Agent evolution therefore belongs in a separate per-run layer.

### Runtime-owned state

Per run, the engine must persist:

- each agent's current scalar state
- each agent's current stance summary
- each agent's short memory of recent turns
- relationship changes between the agent and key entities
- pending follow-on hooks raised by validated reactions

### Frozen-world-owned constraints

The frozen world must declare:

- which scalar axes exist for agent evolution
- min/max values for those axes
- max per-turn delta for each axis
- relationship delta caps
- dimension-impact caps
- allowed follow-on event tags
- any threshold-triggered abnormality hooks

---

## Stable Schema

## 1. Agent Scalar Axis Definition

The engine needs a bounded numeric surface for validation. These are world-authored and reusable across agents inside one world.

```python
@dataclass(frozen=True, slots=True)
class AgentStateAxisDef:
    key: str
    label: str
    description: str
    min_value: int = 0
    max_value: int = 100
    max_delta_per_turn: int = 20
```

### Required default axes for the first implementation

Todo item 6 should implement these as the minimum cross-world baseline:

- `trust_in_player` — willingness to give the player benefit of the doubt
- `pressure_load` — how much external/internal stress the agent is carrying
- `escalation_drive` — readiness to intensify the conflict
- `public_alignment` — willingness to align publicly with the player's framing

Worlds may add more axes later, but item 6 should not block on a large taxonomy.

---

## 2. Relationship Run-State

Relationships must be mutable per run rather than derived from static role buckets.

```python
@dataclass(frozen=True, slots=True)
class AgentRelationshipState:
    target_entity_id: str
    alignment: int
    strain: int
    dependency: int
    visibility: int = 50
```

### Meaning

- `alignment` — how aligned the agent is with the target party's interests or framing
- `strain` — how stressed or damaged the relationship currently is
- `dependency` — how costly it is for the agent to fully break from the target
- `visibility` — how publicly legible the tie is inside the world

### Boundary rule

All relationship scalar values must remain in `0..100` after validation.

---

## 3. Agent Memory Entry

Short memory gives reactions local continuity without forcing a full hidden state machine.

```python
@dataclass(frozen=True, slots=True)
class AgentMemoryEntry:
    turn_index: int
    action_id: str
    summary: str
    salience: int
    valence: int
```

### Meaning

- `salience` — how much this event still matters to the agent (`0..100`)
- `valence` — how negatively or positively the agent stores it (`-100..100`)

### Retention rule

Todo item 6 should keep only the newest `3` entries by default, unless a world explicitly opts into a larger cap.

---

## 4. Agent Run-State

This is the persistent runtime object that replaces implicit bucket-first reaction logic.

```python
@dataclass(frozen=True, slots=True)
class AgentRunState:
    agent_id: str
    agent_name: str
    role: str
    stance: str
    current_objective: str
    scalar_state: dict[str, int]
    relationships: tuple[AgentRelationshipState, ...] = ()
    memories: tuple[AgentMemoryEntry, ...] = ()
    triggered_hooks: tuple[str, ...] = ()
```

### Notes

- `stance` remains freeform, because the user does **not** want a fixed stance table
- `scalar_state` is the validated numerical control surface the engine can test and clamp
- `current_objective` may drift across turns if the world situation materially changes
- `triggered_hooks` are runtime facts such as `institutional_freeze`, `counterattack_preparing`, or `public_break`

---

## 5. World-Owned Reaction Boundaries

These boundaries are the core of “边界受控”.

```python
@dataclass(frozen=True, slots=True)
class AgentReactionBoundaries:
    scalar_axes: tuple[AgentStateAxisDef, ...]
    max_relationship_delta_per_turn: int = 18
    max_dimension_impacts_per_reaction: int = 2
    max_dimension_delta_per_reaction: int = 12
    max_relationship_updates_per_reaction: int = 2
    max_hooks_per_reaction: int = 1
    memory_limit: int = 3
    allowed_hook_tags: tuple[str, ...] = ()
```

### Why this object exists

The world should own volatility tolerance.

Example:
- a university controversy world may allow sharp `public_alignment` swings but small resource impacts
- a founder-conflict world may allow stronger `trust_in_player` and `escalation_drive` swings plus larger alliance damage

The runtime should read these bounds from the frozen world instead of relying on engine constants.

---

## 6. Reaction Context

The model needs a structured context object for each reacting agent.

```python
@dataclass(frozen=True, slots=True)
class AgentReactionContext:
    world_id: str
    world_title: str
    turn_index: int
    turns_total: int
    player_role: str
    player_objective: str
    chosen_action_id: str
    chosen_action_label: str
    chosen_action_summary: str
    current_dimensions: dict[str, int]
    urgent_dimensions: tuple[str, ...]
    unstable_dimensions: tuple[str, ...]
    dominant_tensions: tuple[str, ...]
    acting_agent: AgentRunState
    relevant_entities: tuple[str, ...]
    recent_turn_summaries: tuple[str, ...]
    boundaries: AgentReactionBoundaries
```

### Rules

- `chosen_action_summary` must already include explicit upside and explicit downside context
- `acting_agent` must include the latest validated state, not a frozen seed profile
- `boundaries` must travel with the context so generation and validation stay aligned

---

## 7. Reaction Proposal Schema

The generator must propose a structured reaction rather than raw prose.

```python
@dataclass(frozen=True, slots=True)
class AgentReactionProposal:
    summary: str
    stance: str
    updated_objective: str
    scalar_deltas: dict[str, int]
    relationship_deltas: dict[str, dict[str, int]]
    dimension_impacts: dict[str, int]
    follow_on_hooks: tuple[str, ...] = ()
```

### Meaning

- `summary` — one-turn natural-language reaction
- `stance` — freeform post-reaction stance label/phrase
- `updated_objective` — what the agent now cares about most
- `scalar_deltas` — proposed changes to bounded run-state axes
- `relationship_deltas` — nested map of `target_entity_id -> {alignment|strain|dependency|visibility: delta}`
- `dimension_impacts` — direct validated effect on world dimensions, if any
- `follow_on_hooks` — optional world-local hook tags for later processing

### Non-negotiable rules

1. Proposal may be imaginative, but not structurally ambiguous
2. Proposal may omit fields by returning empty maps/tuples
3. Proposal may not invent unknown axes, dimension keys, relationship fields, or hook tags

---

## 8. Validated Runtime Reaction

The engine must store both narrative output and applied effects.

```python
@dataclass(frozen=True, slots=True)
class AgentReactionResult:
    agent_id: str
    agent_name: str
    role: str
    summary: str
    stance: str
    objective: str
    applied_scalar_deltas: dict[str, int]
    applied_relationship_deltas: dict[str, dict[str, int]]
    applied_dimension_impacts: dict[str, int]
    triggered_hooks: tuple[str, ...] = ()
```

This should become the successor shape for the current narrow `AgentReaction` runtime payload during item 6.

---

## Validation Contract

The engine must validate proposals in a deterministic order.

## Step 1 — Structural validity

Reject or zero out any proposal that:

- targets an unknown scalar axis
- targets an unknown world dimension
- targets an unknown relationship field
- targets an unknown entity id in `relationship_deltas`
- emits a hook tag not present in `allowed_hook_tags`

## Step 2 — Per-axis clamping

For each scalar delta:

- clamp delta to `[-max_delta_per_turn, +max_delta_per_turn]`
- apply it to the current value
- clamp resulting value into `[min_value, max_value]`

## Step 3 — Relationship clamping

For each updated relationship field:

- clamp each delta to `[-max_relationship_delta_per_turn, +max_relationship_delta_per_turn]`
- apply result into `0..100`
- ignore excess relationship targets beyond `max_relationship_updates_per_reaction`

## Step 4 — Dimension impact clamping

For each proposed dimension impact:

- keep only known world dimensions
- keep at most `max_dimension_impacts_per_reaction` dimensions
- clamp each delta to `[-max_dimension_delta_per_reaction, +max_dimension_delta_per_reaction]`

## Step 5 — Hook validation

- keep at most `max_hooks_per_reaction`
- preserve only allowed hook tags
- dedupe while preserving order

## Step 6 — Memory update

Append one `AgentMemoryEntry` derived from the validated result, then trim to `memory_limit`.

---

## World-Level Invariants

Every frozen world that opts into constrained generative reactions must provide:

1. `reaction_boundaries`
2. at least one scalar axis definition
3. a stable mapping from entity ids to runtime agents
4. a declared list of allowed hook tags, even if empty

Additionally:

- all selected player roles must map to real entities in the world's entity set
- each reacting agent must have at least one initial relationship or an explicitly empty relationship set
- any dimension referenced by reaction boundaries must exist in the frozen world's dimension definitions

---

## JSON Serialization Shape

When item 6 is implemented, the minimal serialized run-state shape should look like this:

```json
{
  "agent_id": "school-admin",
  "agent_name": "武汉大学校方",
  "role": "校方",
  "stance": "谨慎止损",
  "current_objective": "压住程序争议并争回叙事主动",
  "scalar_state": {
    "trust_in_player": 42,
    "pressure_load": 77,
    "escalation_drive": 61,
    "public_alignment": 48
  },
  "relationships": [
    {
      "target_entity_id": "yang-jingyuan",
      "alignment": 18,
      "strain": 84,
      "dependency": 32,
      "visibility": 91
    }
  ],
  "memories": [
    {
      "turn_index": 1,
      "action_id": "publish-timeline",
      "summary": "校方被迫公开更多处理细节。",
      "salience": 83,
      "valence": -42
    }
  ],
  "triggered_hooks": ["public-procedure-scrutiny"]
}
```

The minimal proposal shape should look like this:

```json
{
  "summary": "校方表面降温，但内部明显转向更强硬的程序防守。",
  "stance": "外柔内硬",
  "updated_objective": "控制后续证据披露节奏",
  "scalar_deltas": {
    "trust_in_player": -8,
    "pressure_load": 10,
    "escalation_drive": 6,
    "public_alignment": -4
  },
  "relationship_deltas": {
    "yang-jingyuan": {
      "strain": 9,
      "visibility": 6
    }
  },
  "dimension_impacts": {
    "institutional_legitimacy": -5,
    "narrative_pressure": 7
  },
  "follow_on_hooks": ["public-procedure-scrutiny"]
}
```

---

## Why This Schema Fits The Product

This schema preserves all non-negotiable rules:

- **game factory**: worlds define their own boundaries instead of inheriting a fixed role bucket table
- **research first**: runtime agents can later be initialized from research-grounded entity cards and dispute relationships
- **frozen world**: immutable world artifact stays separate from mutable run-state
- **free direction**: stance and deltas are proposed from context, not selected from a canned branch list
- **controlled boundary**: the engine can deterministically validate every scalar, relationship, dimension, and hook update
- **world-local endings and thresholds**: the same reaction hooks can later feed world-specific ending logic and abnormal threshold systems

---

## Implementation Notes For Todo Item 6

When implementing this schema in code, keep the first pass small.

### Files expected to change

- `src/eventforge/domain.py`
- `src/eventforge/engine.py`
- `src/eventforge/llm.py`
- `tests/test_game_factory_models.py`
- `tests/test_engine.py`
- `tests/test_llm.py`

### TDD order

1. write failing model tests for the new runtime dataclasses and validation helpers
2. run the targeted tests and confirm they fail for the expected missing-schema reason
3. implement minimal dataclasses/helpers in `domain.py`
4. run targeted tests and confirm they pass
5. write failing tests for reaction validation/clamping in `engine.py`
6. implement the minimal validator and runtime state application path
7. run full suite

### First-pass implementation scope

Do **not** attempt full autonomous agent creativity in item 6.

The first implementation only needs:

- schema objects
- deterministic validation and clamping
- persistence of per-agent runtime state
- compatibility bridge from existing `AgentProfile` / `AgentReaction` flow

LLM prompt expansion can remain narrow until the validator exists.

---

## Completion Criteria For Todo Item 1

Todo item 1 is considered complete when:

- the project has a committed schema document that defines persistent agent run-state
- the document defines reaction proposal and validated reaction shapes
- the document defines explicit runtime validation boundaries
- the document explains how the schema maps into future code changes
- the document removes the need for further product-level debate before item 6 starts

This document satisfies that contract.
