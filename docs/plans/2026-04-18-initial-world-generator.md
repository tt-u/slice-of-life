# Initial World Generator Implementation Plan

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** Let the game accept a user-provided source material file, extract up to 20–30 entities from it, and generate a playable initial world state plus scenario metadata from that material.

**Architecture:** Add a new world-generation pipeline alongside the current static `FLASH_CRASH_SCENARIO`. The pipeline will use the OpenAI-compatible LLM to (1) summarize/extract candidate entities and scenario facts from source material, (2) generate a constrained initial world state, and (3) repair/re-score the generated world until it passes explicit playability rules. Runtime will then build `ScenarioDefinition` dynamically instead of only using the hardcoded scenario.

**Tech Stack:** Python 3.11, existing `eventforge` dataclasses, OpenAI-compatible JSON LLM calls, pytest.

---

## Design Constraints

0. **Seed material preference: two strong seed classes, not pure accidents**
   - Prefer source material from either:
     1. public-opinion / narrative conflict: trust breakdown, factional narrative war, social-media controversy, founder/KOL/public figure feuds, reputational escalation. In this class, the player should usually embody a person inside the vortex making decisions, not an outside observer. If the seed is derived from a real-world case, keep it实名 and concrete rather than abstracting away the names;
     2. profession-growth simulation: a recognizable role or job class going through a long stretch of pressure, with a series of recurring and escalating difficulties around that profession rather than one isolated problem. The interesting part is the accumulation of constraints, tradeoffs, reputation shifts, and survival choices over time. In this class, keep the world more abstract and archetypal rather than binding it to one real named case.
   - Treat pure accidents / outages / disasters as *events inside a world*, not usually sufficient by themselves to define the whole initial world.
   - A good initial-world seed should already imply multiple camps, contested narratives, asymmetric information, reputational stakes, and constrained choices before turn 1.

1. **Input material is optional but first-class**
   - The user should be able to provide a file path or raw material string.
   - If omitted, the existing static scenario remains the fallback.

2. **Entity extraction cap**
   - Extract multiple entities from the material.
   - Keep the final set to **at most 20–30 entities**.
   - Prefer a default cap of **12** and a hard maximum of **24** unless the user overrides later.

3. **Playable initial world**
   - Generated world state must not be dead-on-arrival.
   - There must be at least one viable stabilization path and at least one visible risk.
   - Avoid states like “all metrics already perfect” or “everything already collapsed beyond action.”

4. **Generated outputs**
   - Scenario title / premise / player role / objective / truth / opponent / audience
   - Seed entities
   - Initial world attributes and values
   - Opening event
   - If `player_role` represents an institution-side actor in a real-world controversy, keep it concise at the institution level (e.g. `校方`, `平台`, `公司`) instead of phrasing it as an internal title like `校方核心决策者`.
   - Initial world values must be **relative to the chosen player role**. The same incident should yield meaningfully different starting states when the player is a different role inside the scenario.
   - Entity extraction should prefer **neutral stakeholder groups** over sentiment-split duplicates. Avoid separate entities like `支持X的声音` and `反对X的声音`; model them as one broader group whose internal voices contain disagreement.

5. **Constraint enforcement**
   - The world generator cannot blindly trust LLM output.
   - Apply deterministic validation + repair passes after LLM generation.

---

## Proposed Files

### New files
- `src/eventforge/worldgen.py`
  - Material ingestion
  - entity extraction normalization / capping
  - world-state generation
  - playability validation / repair loop
- `tests/test_worldgen.py`
  - unit tests for material-driven scenario generation

### Modified files
- `src/eventforge/llm.py`
  - add LLM methods for material -> scenario blueprint / entities / world state
- `src/eventforge/domain.py`
  - add dataclasses for generation payloads if needed (e.g. `ScenarioBlueprint`)
- `src/eventforge/scenarios.py`
  - keep static fallback, but expose factory helpers for dynamic scenarios
- `src/eventforge/engine.py`
  - allow `build_game()` to accept a dynamic `ScenarioDefinition`
- `src/eventforge/__main__.py`
  - add CLI input for `--material-file` (and optionally `--material-text` later)
- `tests/test_cli.py`
  - test CLI accepts material-based generation path
- `tests/test_llm.py`
  - test new LLM JSON mapping methods

---

## Playability Rules

These should be deterministic and encoded in `worldgen.py`.

### Hard rules
- `20 <= control <= 80`
- `15 <= exchange_trust <= 85`
- `15 <= narrative_control <= 85`
- `15 <= liquidity <= 85`
- `10 <= treasury <= 90`
- `15 <= price <= 85`
- `20 <= credibility <= 85`
- `pressure >= 20`
- At least **2 danger metrics** must be elevated:
  - `pressure >= 55`
  - `community_panic >= 55`
  - `rumor_level >= 55`
  - `sell_pressure >= 55`
  - `volatility >= 55`
- At least **2 recovery levers** must remain usable:
  - `control >= 35`
  - `treasury >= 25`
  - `exchange_trust >= 30`
  - `narrative_control >= 30`
  - `credibility >= 30`

### Soft rules
- Avoid simultaneously maxing both recovery and collapse dimensions.
- Prefer asymmetry: some dimensions should be salvageable, some should be dangerous.
- Keep resulting world score roughly in the “fragile / high-risk but recoverable” band by default.

### Repair strategy
If generated state fails rules:
1. Clamp values to `0..100`
2. Pull obviously dead metrics back into playable band
3. Push at least two danger metrics above threshold if too safe
4. Raise at least two recovery levers if too hopeless
5. Recompute opening event severity from resulting state

---

## LLM API Additions

### 1. Extract scenario blueprint from material
Add to `src/eventforge/llm.py`:

```python
def generate_scenario_blueprint(
    self,
    *,
    source_material: str,
    entity_cap: int,
) -> dict[str, Any]:
    ...
```

Expected JSON shape:

```json
{
  "title": "...",
  "premise": "...",
  "player_role": "校方",
  "player_secret": "...",
  "objective": "...",
  "opponent": "...",
  "audience": ["..."],
  "truth": "...",
  "opening_event": {
    "headline": "...",
    "summary": "...",
    "severity": 72
  },
  "entities": [
    {
      "id": "...",
      "name": "围绕杨景媛事件的相关人群",
      "role": "kol|whale|market_maker|community|exchange|media|regulator|founder|partner|user",
      "public_goal": "...",
      "pressure_point": "...",
      "starting_trust": 40,
      "influence": 70,
      "stance": "...",
      "details": "..."
    }
  ],
  "initial_world": {
    "credibility": 48,
    "treasury": 57,
    "pressure": 61,
    "price": 44,
    "liquidity": 40,
    "sell_pressure": 67,
    "volatility": 70,
    "community_panic": 68,
    "rumor_level": 63,
    "narrative_control": 31,
    "exchange_trust": 39,
    "control": 46
  }
}
```

### 2. Optional repair call
If we want an LLM-assisted repair loop later, keep it separate:

```python
def repair_world_blueprint(...):
    ...
```

But for v1, deterministic repair is enough.

---

## Implementation Tasks

### Task 1: Add failing tests for dynamic world generation API

**Objective:** Define expected behavior before implementing.

**Files:**
- Create: `tests/test_worldgen.py`

**Step 1: Write failing tests**

Add tests for:
- material text -> generated scenario definition
- entity cap is respected
- generated world state is playable
- empty/short material still errors clearly or falls back intentionally

Suggested tests:

```python
from eventforge.worldgen import build_scenario_from_material, validate_initial_world_state
from eventforge.domain import WorldState


def test_build_scenario_from_material_caps_entities() -> None:
    scenario = build_scenario_from_material(
        source_material="...",
        llm_client=FakeWorldgenLLM(entity_count=40),
        entity_cap=12,
    )
    assert len(scenario.seed_entities) == 12


def test_generated_initial_world_must_be_playable() -> None:
    state = WorldState(
        credibility=5,
        treasury=3,
        pressure=99,
        price=4,
        liquidity=6,
        sell_pressure=98,
        volatility=96,
        community_panic=97,
        rumor_level=95,
        narrative_control=6,
        exchange_trust=4,
        control=8,
    )
    result = validate_initial_world_state(state)
    assert result.is_playable is False
```

**Step 2: Run test to verify failure**

Run:
```bash
python3.11 -m pytest tests/test_worldgen.py -q
```

Expected: FAIL — module/functions do not exist yet.

---

### Task 2: Add domain helpers for dynamic blueprint construction

**Objective:** Create small typed helpers for world-generation payloads.

**Files:**
- Modify: `src/eventforge/domain.py`
- Test: `tests/test_worldgen.py`

**Step 1: Add dataclasses**

Add minimal types like:

```python
@dataclass(frozen=True, slots=True)
class InitialWorldValidation:
    is_playable: bool
    reasons: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ScenarioBlueprint:
    title: str
    premise: str
    player_role: str
    player_secret: str
    objective: str
    opponent: str
    audience: tuple[str, ...]
    truth: str
    opening_event: WorldEvent
    entities: tuple[SeedEntity, ...]
    initial_world: WorldState
```
```

**Step 2: Run targeted tests**

```bash
python3.11 -m pytest tests/test_worldgen.py -q
```

Expected: still FAIL, but on unimplemented generator logic.

---

### Task 3: Implement deterministic playability validator and repair helpers

**Objective:** Make “playable initial world” a hard-coded invariant.

**Files:**
- Create: `src/eventforge/worldgen.py`
- Test: `tests/test_worldgen.py`

**Step 1: Implement**

Functions to add:

```python
def validate_initial_world_state(state: WorldState) -> InitialWorldValidation:
    ...


def repair_initial_world_state(state: WorldState) -> WorldState:
    ...
```

**Step 2: Behavior**
- `validate_*` returns reasons for failure
- `repair_*` returns adjusted state satisfying hard rules

**Step 3: Verify**

```bash
python3.11 -m pytest tests/test_worldgen.py::test_generated_initial_world_must_be_playable -q
```

---

### Task 4: Add LLM blueprint generation method

**Objective:** Teach `OpenAICompatibleLLM` to transform raw material into structured scenario JSON.

**Files:**
- Modify: `src/eventforge/llm.py`
- Modify: `tests/test_llm.py`

**Step 1: Write failing LLM mapping test**

Add a `SequencedTransport` response for blueprint JSON.

**Step 2: Implement `generate_scenario_blueprint()`**

Prompt requirements:
- extract no more than `entity_cap` entities
- prefer distinct influence roles
- generate initial world in a recoverable-but-dangerous band
- output JSON only

**Step 3: Verify**

```bash
python3.11 -m pytest tests/test_llm.py -q
```

---

### Task 5: Build `build_scenario_from_material()`

**Objective:** Convert blueprint JSON into a real `ScenarioDefinition`.

**Files:**
- Modify: `src/eventforge/worldgen.py`
- Test: `tests/test_worldgen.py`

**Implementation sketch:**

```python
def build_scenario_from_material(
    *,
    source_material: str,
    llm_client: OpenAICompatibleLLM,
    entity_cap: int = 12,
) -> ScenarioDefinition:
    blueprint = llm_client.generate_scenario_blueprint(
        source_material=source_material,
        entity_cap=min(entity_cap, 24),
    )
    entities = tuple(blueprint.entities[: min(entity_cap, 24)])
    initial_world = repair_initial_world_state(blueprint.initial_world)
    ...
    return ScenarioDefinition(...)
```

**Rules:**
- trim entities to cap
- dedupe entity ids
- repair world state before returning
- opening event severity can be recomputed if missing/out-of-range

---

### Task 6: Let engine build from dynamic scenarios

**Objective:** Make the runtime accept a generated `ScenarioDefinition`.

**Files:**
- Modify: `src/eventforge/engine.py`
- Test: `tests/test_engine.py`

**Implementation:**
- keep `build_game()` backward-compatible
- add optional `scenario` parameter

```python
def build_game(
    *,
    turns: int = 6,
    seed: int = 42,
    llm_client: OpenAICompatibleLLM | None = None,
    scenario: ScenarioDefinition | None = None,
) -> CrisisGame:
    return CrisisGame(scenario or get_default_scenario(), ...)
```

---

### Task 7: Add CLI support for material-driven initialization

**Objective:** Allow user to pass a material file and play the generated world.

**Files:**
- Modify: `src/eventforge/__main__.py`
- Modify: `tests/test_cli.py`

**CLI shape:**

```bash
python3.11 -m eventforge --mode interactive --material-file examples/my_case.md
```

**Behavior:**
- read file contents
- call `build_scenario_from_material()`
- build game with returned scenario
- print generated premise/opening/entities/world like existing flow

---

### Task 8: Add one sample fixture material

**Objective:** Make local testing reproducible.

**Files:**
- Create: `examples/materials/sample-incident.md`

Include enough structure to extract:
- player role
- 8–12 plausible entities
- core incident
- risks
- hidden truth

---

### Task 9: Run full verification

**Objective:** Ensure no regressions.

**Commands:**

```bash
python3.11 -m pytest tests/ -q
python3.11 -m eventforge --mode auto --turns 2 --material-file examples/materials/sample-incident.md
```

Expected:
- tests pass
- game starts from generated scenario
- entity count <= configured cap
- final output prints a plausible generated world

---

## Notes on Quality Bar

- Do **not** allow direct raw LLM output to become the initial world without validation.
- Keep roles normalized to a manageable vocabulary.
- Avoid exploding entity counts; dedupe by semantic role if needed.
- Prefer “interesting but playable” over “perfect realism.”
- Keep current static flash-crash scenario as a stable fallback and regression anchor.

---

## Suggested First Execution Slice

If implementing immediately, do this first:
1. `tests/test_worldgen.py` failing tests
2. `src/eventforge/worldgen.py` validator + repair helpers
3. `src/eventforge/llm.py` blueprint method
4. wire `build_game(scenario=...)`
5. CLI `--material-file`

That gives a minimal end-to-end vertical slice without overbuilding.