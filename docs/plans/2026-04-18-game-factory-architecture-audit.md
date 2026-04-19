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

The repo is still **mid-migration**, but the center of gravity is no longer the flash-crash demo.

Important migration wins already landed:

- stored `MaterialResearchPack` and `FrozenInitialWorld` artifacts are first-class and have committed anchor-case fixtures
- runtime can boot directly from a supplied `FrozenInitialWorld`
- generated actions now drive the live choice surface, with frozen-world action grammar preferred over legacy scenario actions
- action-focus / dominant-tension ranking now reads each frozen world's own `dimension_defs` thresholds instead of flash-crash-specific urgency constants
- ending resolution already comes from `FrozenInitialWorld.resolve_ending_band(...)`
- agent run-state / reaction-boundary schemas exist and are validated at runtime
- flash-crash is isolated as sample/regression content instead of package identity

The highest-leverage remaining cleanup is narrower now:

- `WorldState`, `STATE_KEYS`, and `AXIS_LABELS` are still fixed-schema runtime bridges
- `ActionCard` still survives underneath generated actions as a compatibility template layer
- agent reactions still bridge from legacy role-bucket logic before validation
- the no-argument CLI path still falls back to sample content for regression convenience

So the current transition state is:

> **the game-factory artifact flow is real, but a few legacy runtime bridges still need to be retired or demoted further**.

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
| `ScenarioDefinition` | Legacy scenario wrapper | **bridge temporarily** | Still useful as a compatibility adapter and sample-content carrier, but frozen worlds should remain the authoritative runtime contract. |
| `ScenarioBlueprint` | Worldgen output bridge | **bridge temporarily** | Acceptable while research/inspection/freeze flow is still being built. |
| `SeedEntity` | Shared entity card type | **keep for now** | Still useful across research/frozen-world/runtime, though it may later split into research-card vs runtime-agent seed if needed. |
| `AgentProfile` | Legacy per-agent runtime prompt profile | **bridge temporarily** | Agent run-state now exists, but profile generation still bridges prompt setup and should eventually be demoted further. |
| `AgentReaction` | Legacy reaction output snapshot | **bridge temporarily** | Runtime validation now exists, but the outward reaction shape is still a bridge around validated proposals/results. |
| `WorldState` | Fixed mutable runtime state with 12 baked-in axes | **replace** | This is the biggest remaining demo-shaped domain object. It hardcodes one worldview into the engine. |
| `WORLD_STATE_DIMENSION_KEYS` | Global fixed axis registry | **remove after migration** | Only exists because `WorldState` is fixed-schema. |
| `ActionCard` | Legacy action template/effect object with demo-specific delta fields | **replace** | No longer the player-facing action currency, but still survives as an internal compatibility template layer. |
| `TurnChoice` | Chosen runtime action wrapper | **refit mostly done** | It now carries `GeneratedAction`; remaining cleanup is removing residual legacy assumptions around the bridge layer. |
| `WorldReport` | End-of-run summary object | **keep/refit mostly done** | Structurally fine and already world-owned for ending resolution; remaining work is cleanup, not contract replacement. |
| `InitialWorldValidation` | Validation result | **keep** | Compatible with the research/frozen-world pipeline. |

### 2) `src/eventforge/engine.py`

| Symbol / area | Current role | Status | Why |
|---|---|---|---|
| `STATE_KEYS` | Global engine metric registry | **remove after migration** | Duplicates the fixed-schema problem from `WorldState`. |
| `AXIS_LABELS` | Global flash-crash-oriented labels | **replace** | Dimension labels belong to each frozen world. |
| `ENDING_BANDS` | Global ending labels | **already removed / retired from runtime contract** | Ending labels now resolve through each frozen world. |
| `action_tradeoff_profile(...)` | Bridge helper from compatibility templates into generated tradeoff metadata | **remove after migration** | Player-facing runtime now consumes `GeneratedAction`, but this helper still exists underneath the compatibility bridge. |
| `decision_focus_from_state(...)` | Urgency heuristic tied to fixed axes | **replace** | Should be driven by frozen-world dimension definitions and live world state, not hardcoded axis rules. |
| `format_tradeoff_suffix(...)` | Legacy tradeoff display helper | **refit** | Keep the UX idea, but base it on `GeneratedAction` explicit upside/downside metadata. |
| `CrisisGame.__init__` scenario boot path | Can boot from a supplied `FrozenInitialWorld`, with legacy scenario fallback still present | **bridge temporarily** | The frozen-world-first path exists; remaining cleanup is reducing dependence on the fallback path. |
| `available_actions()` | Returns `GeneratedAction`, still sometimes synthesized from legacy templates | **bridge temporarily** | Major migration win already landed; remaining work is deleting the underlying `ActionCard` bridge. |
| pre-turn event generation / secondary world rules | Strongly tuned to flash-crash dynamics | **replace/refactor** | Runtime world updates must stop assuming the sample world's metric meanings. |
| `_generate_agent_reactions(...)` and role-bucket helpers | Partly action-conditioned, but still dominated by narrow role buckets and fixed trust/control heuristics | **replace** | Core blocker for item 6. |
| report/ending resolution path | Resolves ending labels through the frozen world | **refit mostly done** | Remaining cleanup is around fixed-state scoring/report assumptions, not world ownership of ending labels. |

### 3) `src/eventforge/scenarios.py`

| Symbol | Current role | Status | Why |
|---|---|---|---|
| `FLASH_CRASH_SCENARIO` | Demo/sample scenario definition | **isolate as sample content** | Keep for regression and as an example frozen-world migration source. Do not let it define core engine interfaces. |
| `INITIAL_WORLD_STATE` | Demo world state fixture | **isolate as sample content** | Same as above. |
| `get_default_scenario()` | Sample-content fallback for no-argument play and regression coverage | **demote / keep temporarily** | Acceptable as a compatibility fallback, but should stay explicitly secondary to frozen-world-first flows. |

### 4) CLI and entrypoints (`src/eventforge/__main__.py`, `play.py`)

| Area | Current role | Status | Why |
|---|---|---|---|
| world-centric command flow (`research-case` / `freeze-world` / `inspect-world` / `play`) | Main game-factory CLI surface | **keep** | This is now the primary product-facing path. |
| no-argument sample fallback | Regression-friendly shortcut | **keep temporarily** | Acceptable only as a secondary compatibility path while the repo still carries sample content. |

### 5) Tests

| Area | Current role | Status | Why |
|---|---|---|---|
| `tests/test_game_factory_models.py` | New architecture bridge tests | **keep and extend** | Best current proof that the migration objects are real. |
| `tests/test_engine.py` | Mixed migration coverage | **keep and continue separating** | It now covers frozen-world precedence, generated actions, ending ownership, and remaining bridge behavior. |
| CLI tests | Frozen-world flow plus fallback coverage | **keep and extend** | The command router is now world-centric; remaining work is reducing fallback/demo emphasis where possible. |

---

## Concrete blockers to the approved todo sequence

This section maps the audit to the approved todo order.

### Todo 3 — research-pack dataclasses and serialization
**Prerequisite status:** landed for the current anchor-case flow.

What is already good:
- `MaterialResearchPack` exists.
- deterministic anchor-case `research-case` flows already persist reusable JSON artifacts without LLM credentials.

What still matters:
- enrich packs further only when a new case truly needs more research structure; do not reopen generic design churn here.

### Todo 4 — frozen-world dataclasses and serialization
**Prerequisite status:** landed for the current anchor-case flow.

What is already good:
- `FrozenInitialWorld`, `WorldEndingBand`, `WorldDimensionDef`, and `WorldActionGrammar` exist.
- `freeze-world` / `inspect-world` already treat frozen worlds as primary stored contracts.

What still matters:
- continue removing runtime assumptions that still depend on fixed `WorldState` bridges rather than fully world-local dimension semantics.

### Todo 5 — generated-action schema + action generation context
**Prerequisite status:** mostly landed; bridge cleanup remains.

Primary blocker:
- `ActionCard` still survives underneath generated actions as a compatibility template layer.

Required outcome:
- generated actions remain the runtime action currency
- `ActionCard` becomes sample-only bridge material or disappears

### Todo 6 — agent run-state / reaction schema in code
**Prerequisite status:** landed as a validated first-pass bridge; deeper cleanup remains.

Primary blocker:
- `engine.py` still derives reaction proposals from legacy role-bucket logic before passing them through the validator.

Required outcome:
- persistent per-agent run state remains explicit
- reaction proposals and validation boundaries are driven by the new schema, not demo role buckets

### Todo 7 — runtime loop consumes frozen worlds instead of implicit regeneration/demo assumptions
**Prerequisite status:** no longer the main execution blocker; the loop is live, but bridge cleanup remains.

Primary blockers:
- fixed-schema `WorldState` / `STATE_KEYS` / `AXIS_LABELS` still shape parts of runtime evaluation and display
- sample fallback behavior still exists for no-argument play
- some internal action/reaction bridge code still leans on legacy template semantics

---

## Replacement order: what should change first vs later

### Replace first
These changes unblock the rest of the roadmap and should happen before broad anchor-world work:

1. **fixed-schema runtime state cleanup**
   - reduce or remove `WorldState`, `STATE_KEYS`, and `AXIS_LABELS` so world-local dimensions own more of runtime semantics
2. **action bridge cleanup**
   - delete the remaining `ActionCard` compatibility layer underneath generated actions
3. **reaction bridge cleanup**
   - replace bucket-first proposal generation with a more world-local reaction path on top of the validated run-state contract
4. **sample fallback demotion**
   - keep flash-crash only as explicit sample/regression content, not the easiest accidental entry path

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

The architecture is no longer blocked by missing concepts; it is blocked by **a shrinking set of legacy runtime bridges**.

That means:

- **research-pack and frozen-world work should continue**
- **flash-crash content should stay only as explicit sample/regression content**
- but the next major implementation effort should keep moving execution authority away from:
  - `WorldState` fixed schema
  - `ActionCard`
  - bucket-first reaction proposal logic
  - sample-first fallback paths that are easier to reach than world-file flows

In short:

> the repo already contains the right replacement pieces; the next work is to retire or demote the remaining bridge layers until frozen worlds and world-local runtime contracts fully own play.
