# Game Factory Architecture Audit — Replace vs Isolate Map

> Item advanced in this pass: **Todo 2 — audit current flash-crash/demo-shaped domain objects and map what must be replaced vs isolated**.
>
> This document is implementation-grounded. It is not a product-ideation draft. It records the current code surface in `slice-of-life`, identifies which objects are still demo-shaped, and assigns each one to one of four buckets:
>
> - **replace now** — blocks the research-pack -> frozen-world -> runtime architecture
> - **bridge/keep temporarily** — acceptable transitional compatibility layer
> - **isolate as sample/regression content** — keep, but move out of architecture center
> - **remove after migration** — legacy helper that should disappear once runtime no longer depends on the demo schema

## Target architecture reminder

The approved architecture is:

1. **research pack** — web-grounded case facts, entities, stances, disputes, relationships, candidate roles
2. **frozen world** — immutable stored world artifact with dimensions, selectable roles, action grammar, ending bands, thresholds
3. **runtime** — loads a frozen world, asks the player to choose role + turns, generates tradeoff actions, evolves agents under bounded validation
4. **ending synthesis** — world-local deterministic ending band + run-local narrative ending text

The architectural rule is:

> **flash-crash remains content, not the engine contract**.

---

## Audit summary

The repo is **mid-migration**, not fully demo-bound anymore.

Good news already landed:

- `MaterialResearchPack`, `FrozenInitialWorld`, `WorldDimensionDef`, `WorldActionGrammar`, `ActionGenerationContext`, `GeneratedAction`, and `WorldEndingBand` now exist in `src/eventforge/domain.py`.
- `ScenarioDefinition.to_material_research_pack(...)` and `.to_frozen_world(...)` already provide a bridge from legacy scenarios into the new artifacts.
- `FrozenInitialWorld.build_action_generation_context(...)` already provides a runtime bridge from frozen world + live state into structured action-generation input.
- tests for these bridge artifacts already exist and pass.

But the runtime center is still demo-shaped:

- `CrisisGame` still boots from `ScenarioDefinition` + `ActionCard` instead of a stored `FrozenInitialWorld`
- `WorldState` is still a fixed flash-crash metric schema
- `ActionCard` still encodes crypto/demo-specific effect fields
- `engine.py` still contains global metric labels, ending bands, action heuristics, and role-bucket reaction logic that assume the flash-crash worldview
- `FLASH_CRASH_SCENARIO` still acts like the default product entrypoint rather than a sample world pack

So the repo is currently in this transition state:

> **new architecture objects exist, but old runtime assumptions still dominate execution**.

---

## Replace / isolate map by symbol

### 1) `src/eventforge/domain.py`

| Symbol | Current role | Status | Why |
|---|---|---|---|
| `MaterialResearchPack` | Research-layer artifact | **keep** | Correct target-layer object for item 3. |
| `FrozenInitialWorld` | Frozen-world artifact | **keep** | Correct target-layer object for item 4 and runtime handoff. |
| `WorldDimensionDef` | World-local dimension metadata | **keep** | Core to frozen-world semantics. |
| `WorldActionGrammar` / `ActionGenerationRule` / `ActionCostType` | World-authored action grammar | **keep** | Core to generated-action architecture. |
| `ActionGenerationContext` / `GeneratedAction` / `TurnSituation` | Runtime action-generation contract | **keep** | Core to item 5. |
| `WorldEndingBand` | World-local ending model | **keep** | Core to item 12; already replaces global ending constants conceptually. |
| `ScenarioDefinition` | Legacy scenario wrapper | **bridge temporarily** | Useful only as a migration adapter from old sample content to new artifacts. Runtime should stop depending on it directly. |
| `ScenarioBlueprint` | Worldgen output bridge | **bridge temporarily** | Acceptable while research/inspection/freeze flow is still being built. |
| `SeedEntity` | Shared entity card type | **keep for now** | Still useful across research/frozen-world/runtime, though it may later split into research-card vs runtime-agent seed if needed. |
| `AgentProfile` | Legacy per-agent runtime prompt profile | **bridge temporarily** | Acceptable until item 6 introduces explicit agent run-state / reaction schema in code. |
| `AgentReaction` | Legacy reaction output snapshot | **bridge temporarily** | Can survive briefly, but should eventually be aligned to the world-authored agent evolution schema. |
| `WorldState` | Fixed mutable runtime state with 12 baked-in axes | **replace** | This is the biggest remaining demo-shaped domain object. It hardcodes one worldview into the engine. |
| `WORLD_STATE_DIMENSION_KEYS` | Global fixed axis registry | **remove after migration** | Only exists because `WorldState` is fixed-schema. |
| `ActionCard` | Legacy action template/effect object with demo-specific delta fields | **replace** | Blocks generic action generation because its fields encode one crisis genre. |
| `TurnChoice` | Chosen `ActionCard` wrapper | **replace or refit** | Runtime should choose/generated-action instances, not legacy demo cards. |
| `WorldReport` | End-of-run summary object | **keep/refit** | Structurally fine, but should derive ending labels from the frozen world, not global engine constants. |
| `InitialWorldValidation` | Validation result | **keep** | Compatible with the research/frozen-world pipeline. |

### 2) `src/eventforge/engine.py`

| Symbol / area | Current role | Status | Why |
|---|---|---|---|
| `STATE_KEYS` | Global engine metric registry | **remove after migration** | Duplicates the fixed-schema problem from `WorldState`. |
| `AXIS_LABELS` | Global flash-crash-oriented labels | **replace** | Dimension labels belong to each frozen world. |
| `ENDING_BANDS` | Global ending labels | **remove after migration** | Ending labels must be world-local. |
| `action_tradeoff_profile(...)` | Infers tradeoff from `ActionCard` delta fields | **replace** | Works only because action semantics are globally hardcoded. Runtime should consume explicit generated-action upside/downside fields. |
| `decision_focus_from_state(...)` | Urgency heuristic tied to fixed axes | **replace** | Should be driven by frozen-world dimension definitions and live world state, not hardcoded axis rules. |
| `format_tradeoff_suffix(...)` | Legacy tradeoff display helper | **refit** | Keep the UX idea, but base it on `GeneratedAction` explicit upside/downside metadata. |
| `CrisisGame.__init__` scenario boot path | Starts from `ScenarioDefinition`, copies `initial_world`, synthesizes `frozen_world` as secondary | **replace** | Runtime should load a `FrozenInitialWorld` first-class and instantiate mutable run state from it. |
| `available_actions()` | Samples/rewrites legacy `ActionCard` templates | **replace** | Core blocker for item 5 and item 7. |
| pre-turn event generation / secondary world rules | Strongly tuned to flash-crash dynamics | **replace/refactor** | Runtime world updates must stop assuming the sample world's metric meanings. |
| `_generate_agent_reactions(...)` and role-bucket helpers | Partly action-conditioned, but still dominated by narrow role buckets and fixed trust/control heuristics | **replace** | Core blocker for item 6. |
| report/ending resolution path | Still carries legacy global-engine worldview | **replace/refit** | Must resolve labels through `FrozenInitialWorld.resolve_ending_band(...)`. |

### 3) `src/eventforge/scenarios.py`

| Symbol | Current role | Status | Why |
|---|---|---|---|
| `FLASH_CRASH_SCENARIO` | Demo/sample scenario definition | **isolate as sample content** | Keep for regression and as an example frozen-world migration source. Do not let it define core engine interfaces. |
| `INITIAL_WORLD_STATE` | Demo world state fixture | **isolate as sample content** | Same as above. |
| `get_default_scenario()` | Default app entry | **replace** | Product flow should become research case -> inspect/freeze/select role/select turns/play. A hardcoded default scenario should not be the product center. |

### 4) CLI and entrypoints (`src/eventforge/__main__.py`, `play.py`)

| Area | Current role | Status | Why |
|---|---|---|---|
| demo-centric play entry | Assumes one default scenario/demo flow | **replace** | Blocks item 13. CLI must become world-centric rather than sample-centric. |
| sample-friendly fallback behavior | Useful for smoke tests | **keep temporarily** | Acceptable only as a regression mode after the main flow becomes frozen-world-first. |

### 5) Tests

| Area | Current role | Status | Why |
|---|---|---|---|
| `tests/test_game_factory_models.py` | New architecture bridge tests | **keep and extend** | Best current proof that the migration objects are real. |
| `tests/test_engine.py` | Legacy runtime behavior tests | **split** | Keep sample-regression coverage, but stop treating demo behavior as the architecture contract. |
| CLI/demo tests | Mixed | **refactor later** | Should follow the CLI redesign once world-centric flow lands. |

---

## Concrete blockers to the approved todo sequence

This section maps the audit to the approved todo order.

### Todo 3 — research-pack dataclasses and serialization
**Prerequisite status:** mostly unblocked.

What is already good:
- `MaterialResearchPack` exists.

What still matters:
- serialization should target the research pack directly rather than depending on `ScenarioDefinition` as the only creation path.

### Todo 4 — frozen-world dataclasses and serialization
**Prerequisite status:** mostly unblocked.

What is already good:
- `FrozenInitialWorld`, `WorldEndingBand`, `WorldDimensionDef`, and `WorldActionGrammar` exist.

What still matters:
- persistence should treat frozen worlds as primary artifacts, not as a derivative hidden behind `ScenarioDefinition`.

### Todo 5 — generated-action schema + action generation context
**Prerequisite status:** partially unblocked, but legacy runtime still fights it.

Primary blocker:
- `ActionCard` remains the live runtime action currency.

Required outcome:
- generated actions become the runtime action currency
- `ActionCard` becomes sample-only bridge material or disappears

### Todo 6 — agent run-state / reaction schema in code
**Prerequisite status:** design unblocked, runtime integration still blocked.

Primary blocker:
- `engine.py` still uses bucket-first trust/stance updates attached to legacy `AgentProfile` and `ActionCard` flows.

Required outcome:
- persistent per-agent run state becomes explicit
- reaction proposals and validation boundaries are driven by the new schema, not demo role buckets

### Todo 7 — runtime loop consumes frozen worlds instead of implicit regeneration/demo assumptions
**Prerequisite status:** currently the main execution blocker.

Primary blockers:
- `CrisisGame` starts from `ScenarioDefinition`
- mutable state still centers on fixed `WorldState`
- action selection still centers on `ActionCard`
- endings/reporting still retain global-engine assumptions

---

## Replacement order: what should change first vs later

### Replace first
These changes unblock the rest of the roadmap and should happen before broad anchor-world work:

1. **runtime entry contract**
   - replace `ScenarioDefinition`-first runtime boot with `FrozenInitialWorld`-first boot
2. **runtime action currency**
   - replace `ActionCard` in the live turn loop with the generated-action schema
3. **agent evolution state**
   - replace bucket-first reaction updates with explicit run-state + validated bounded updates
4. **ending resolution path**
   - remove global ending band dependence in `engine.py`

### Keep as compatibility bridges for now
These are acceptable until the corresponding roadmap item lands:

1. `ScenarioDefinition.to_material_research_pack(...)`
2. `ScenarioDefinition.to_frozen_world(...)`
3. `ScenarioBlueprint`
4. `SeedEntity`
5. sample-world conversion helpers that synthesize a default frozen-world action grammar from legacy actions

### Isolate as sample/regression only
These should survive, but in a clearly demoted role:

1. `FLASH_CRASH_SCENARIO`
2. flash-crash-specific action IDs and texts
3. flash-crash-specific tests, as regression fixtures
4. any CLI demo mode explicitly labeled as sample/regression

### Remove after migration
These should disappear once runtime no longer depends on demo-shaped globals:

1. `WORLD_STATE_DIMENSION_KEYS`
2. `STATE_KEYS`
3. engine-global `AXIS_LABELS`
4. engine-global `ENDING_BANDS`
5. all `ActionCard`-specific impact inference helpers that only exist to reinterpret hardcoded demo deltas

---

## Minimal migration contract for the next coding passes

To keep the refactor coherent, the next implementation passes should preserve these boundaries:

### Boundary 1 — research output must be inspectable without runtime
A research pack should be serializable, reviewable, and reusable before any gameplay starts.

### Boundary 2 — frozen world must be loadable without regeneration
A stored frozen world must contain enough information to start a run later without re-running worldgen implicitly.

### Boundary 3 — runtime must not require flash-crash metric names
The runtime may temporarily adapt the legacy `WorldState`, but new code should treat dimension definitions and dimension maps as the real contract.

### Boundary 4 — every runtime action must carry explicit upside and downside
No fallback to “description-only action cards” as the engine contract.

### Boundary 5 — agent freedom must be bounded by schema validation
No return to a fixed reaction table; no unbounded freeform jumps either.

---

## Final judgment

The architecture is no longer blocked by missing concepts; it is blocked by **legacy runtime center-of-gravity**.

That means:

- **research-pack and frozen-world work should continue**
- **flash-crash content should stay**
- but the next major implementation effort must move execution authority away from:
  - `WorldState` fixed schema
  - `ActionCard`
  - `ScenarioDefinition` as the runtime entry contract
  - `engine.py` global endings/axis heuristics/role buckets

In short:

> the repo already contains the right replacement pieces; the next work is to make runtime obey them and demote the old demo objects to bridge/sample status.
