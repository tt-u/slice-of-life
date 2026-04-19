# Generated Action Runtime Contract

> Item advanced in this pass: land the earlier action-generation draft as an implementation-grounded contract instead of leaving an untracked planning note.

This document records the **current** action-generation runtime contract in `src/eventforge/domain.py` and `src/eventforge/engine.py`.

It is intentionally not a greenfield design draft. It describes the migration state that now exists:

- frozen worlds own `WorldActionGrammar`
- runtime turn context is serialized as `TurnSituation` + `ActionGenerationContext`
- runtime-facing menu choices are `GeneratedAction`
- the current engine still uses a **legacy `ActionCard` bridge** to synthesize effect metadata and menu constraints

## Goal

Keep the product rule intact:

```text
turn choices come from world-local grammar + current situation
and every choice must contain an explicit upside and explicit downside
```

## Current schema in `domain.py`

### `ActionCostType`
World-local action cost vocabulary.

Current fields:
- `key`
- `label`
- `description`

### `ActionGenerationRule`
One world-authored rule describing what kinds of tradeoff actions may be generated.

Current fields:
- `key`
- `label`
- `description`
- `trigger_dimensions`
- `preferred_upside_dimensions`
- `likely_downside_dimensions`
- `allowed_cost_types`
- `minimum_upside_count`
- `minimum_downside_count`
- `max_upside_count`
- `max_downside_count`
- `intensity_range`
- `tags`

### `WorldActionGrammar`
Frozen-world action grammar attached to `FrozenInitialWorld`.

Current fields:
- `rules`
- `cost_types`
- `forbidden_pairs`
- `forbidden_tags`
- `required_tradeoff`
- `menu_size`
- `low_commitment_slots`
- `medium_commitment_slots`
- `high_commitment_slots`

### `TurnSituation`
Structured live-turn summary passed into generation.

Current fields:
- `turn_index`
- `turns_total`
- `selected_player_role`
- `objective`
- `dominant_tensions`
- `urgent_dimensions`
- `unstable_dimensions`
- `recent_action_summaries`

### `ActionGenerationContext`
Serialized action-generation input combining world metadata and live state.

Current fields:
- `world_title`
- `player_role`
- `dimensions`
- `dimension_defs`
- `situation`
- `action_grammar`

### `GeneratedAction`
Runtime action currency returned by `CrisisGame.available_actions()`.

Current fields:
- `id`
- `label`
- `description`
- `rationale`
- `upside_dimensions`
- `downside_dimensions`
- `upside_magnitude`
- `downside_magnitude`
- `cost_types`
- `affected_entities`
- `commitment_tier`
- `tags`

### Current enforced invariants

`GeneratedAction.__post_init__()` currently enforces:

1. at least one upside dimension
2. at least one downside dimension
3. no overlap between upside and downside dimensions

That is the minimum hard guarantee behind the tradeoff rule.

## Current runtime flow in `engine.py`

`CrisisGame.available_actions()` now works in this order:

1. start from the runtime template pool
2. apply lightweight live gating (`treasury < 20`, `wallet_frozen`, etc.)
3. build a structured `ActionGenerationContext` from `self.frozen_world`
4. ask the LLM for turn actions using:
   - world title
   - player role
   - player objective
   - state summary
   - decision focus
   - available templates
   - structured action context
5. constrain returned template ids into a valid menu
6. convert each allowed choice into a `GeneratedAction`
7. cache the generated menu for the current turn

## Important bridge reality

The runtime surface is already `GeneratedAction`, but the bridge is not complete yet.

Today `_build_generated_action(...)` still derives several fields from legacy `ActionCard` helpers:

- upside/downside axes come from `action_tradeoff_profile(base)`
- commitment tier comes from legacy impact tier mapping
- magnitude defaults are synthesized (`6` upside, `5` downside)
- `cost_types` and some tags still come from the base template
- the tradeoff suffix formatter still operates on legacy action templates

This is acceptable as a migration bridge, but it is **not** the desired end state.

## Current menu-shape constraints

The current runtime guarantees these practical menu rules before returning actions:

- duplicate template ids are removed
- at least one low-commitment action is preferred
- at least one medium-commitment action is preferred
- no more than one extreme/high-risk template is kept
- fewer than two valid actions is treated as an error

This keeps menu spread bounded even while the engine still bridges through legacy templates.

## Current text-normalization rule

`_normalize_action_description(...)` preserves already-good explicit Chinese tradeoff suffixes.

Current behavior:
- if the exact canonical suffix is already present, keep it
- if the description already ends with an explicit `（+... / -...）` pattern, keep it
- otherwise append the canonical suffix

This prevents duplicate tradeoff tails from live LLM output.

## Architecture boundary that remains

The repo has crossed an important boundary:

> `GeneratedAction` is now the runtime-facing action object.

But the engine has **not** crossed the full migration boundary yet:

> legacy `ActionCard` still acts as the hidden effect/template substrate underneath generated actions.

That means the next action-generation refactors should preserve this order:

1. keep `GeneratedAction` as the runtime/menu/reporting currency
2. move world-authored effect semantics into frozen-world-owned metadata
3. stop deriving runtime tradeoffs from flash-crash-era `ActionCard` helpers
4. make tradeoff formatting and scoring consume `GeneratedAction` directly

## Non-negotiable product rules

Any future refactor should preserve these constraints:

1. **no global action list as architecture contract**
2. **world-local grammar owns action shape**
3. **every action must expose explicit upside and downside**
4. **runtime may allow freer wording, but validation must stay structured**
5. **flash-crash action semantics remain bridge/sample content, not the permanent engine contract**

## Source files to update when this changes

If action-generation behavior changes, update this document together with:

- `src/eventforge/domain.py`
- `src/eventforge/engine.py`
- `docs/plans/2026-04-18-game-factory-architecture-audit.md`
- `README.md` if the user-facing flow changes
