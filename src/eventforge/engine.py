from __future__ import annotations

import random
import re
from dataclasses import replace
from typing import Iterable

from .domain import (
    ActionCard,
    AgentMemoryEntry,
    AgentProfile,
    AgentReaction,
    AgentReactionContext,
    AgentReactionProposal,
    AgentReactionResult,
    AgentRelationshipState,
    AgentRunState,
    FrozenInitialWorld,
    ScenarioDefinition,
    TurnChoice,
    TurnResolution,
    TurnSituation,
    WorldEvent,
    WorldReport,
    WorldState,
)
from .llm import OpenAICompatibleLLM
from .scenarios import get_default_scenario

STATE_KEYS = (
    "credibility",
    "treasury",
    "pressure",
    "price",
    "liquidity",
    "sell_pressure",
    "volatility",
    "community_panic",
    "rumor_level",
    "narrative_control",
    "exchange_trust",
    "control",
)

AXIS_LABELS = {
    "credibility": "信誉",
    "treasury": "国库",
    "pressure": "压力",
    "price": "币价",
    "liquidity": "流动性",
    "sell_pressure": "抛压",
    "volatility": "波动",
    "community_panic": "社区恐慌",
    "rumor_level": "传言",
    "narrative_control": "叙事控制",
    "exchange_trust": "交易所信任",
    "control": "控制权",
}

IMPACT_MODEL = {
    "tiny": 2,
    "light": 4,
    "medium": 6,
    "heavy": 10,
    "major": 14,
    "extreme": 18,
}


def impact(level: str, direction: int = 1, scale: int = 1) -> int:
    return IMPACT_MODEL[level] * direction * scale


def action_impact_profile(action: ActionCard) -> dict[str, int | str]:
    impact_cost = (
        max(0, action.public_pressure)
        + max(0, -action.narrative_shift)
        + max(0, -(action.exchange_shift + action.exchange_trust_shift))
        + max(0, -action.liquidity_shift)
        + max(0, -action.treasury_shift)
        + max(0, -action.control_shift)
        + max(0, action.volatility_shift)
        + max(0, -action.kol_trust_shift)
        + max(0, -action.whale_trust_shift)
    )
    if impact_cost <= 6:
        impact_tier = "low"
    elif impact_cost <= 14:
        impact_tier = "medium"
    elif impact_cost <= 24:
        impact_tier = "high"
    else:
        impact_tier = "extreme"
    return {"impact_cost": impact_cost, "impact_tier": impact_tier}


def action_tradeoff_profile(action: ActionCard) -> dict[str, list[str]]:
    upside_axes: list[str] = []
    downside_axes: list[str] = []

    if action.narrative_shift > 0:
        upside_axes.append("narrative_control")
    elif action.narrative_shift < 0:
        downside_axes.append("narrative_control")

    exchange_delta = action.exchange_shift + action.exchange_trust_shift
    if exchange_delta > 0:
        upside_axes.append("exchange_trust")
    elif exchange_delta < 0:
        downside_axes.append("exchange_trust")

    if action.liquidity_shift > 0:
        upside_axes.append("liquidity")
    elif action.liquidity_shift < 0:
        downside_axes.append("liquidity")

    if action.treasury_shift > 0:
        upside_axes.append("treasury")
    elif action.treasury_shift < 0:
        downside_axes.append("treasury")

    if action.control_shift > 0:
        upside_axes.append("control")
    elif action.control_shift < 0:
        downside_axes.append("control")

    if action.volatility_shift < 0:
        upside_axes.append("volatility")
    elif action.volatility_shift > 0:
        downside_axes.append("volatility")

    if action.kol_trust_shift > 0:
        upside_axes.append("rumor_level")
    elif action.kol_trust_shift < 0:
        downside_axes.append("rumor_level")

    if action.whale_trust_shift > 0:
        upside_axes.append("sell_pressure")
    elif action.whale_trust_shift < 0:
        downside_axes.append("sell_pressure")

    if action.public_pressure > 0:
        downside_axes.append("pressure")
    elif action.public_pressure < 0:
        upside_axes.append("pressure")

    if not upside_axes:
        upside_axes.append("control")
    if not downside_axes:
        downside_axes.append("pressure")

    return {
        "upside_axes": list(dict.fromkeys(upside_axes)),
        "downside_axes": list(dict.fromkeys(downside_axes)),
    }


def decision_focus_from_state(state: WorldState) -> list[dict[str, int | str]]:
    focus_candidates = [
        {"axis": "control", "urgency": max(0, 60 - state.control), "desired_direction": "up"},
        {"axis": "narrative_control", "urgency": max(0, 70 - state.narrative_control), "desired_direction": "up"},
        {"axis": "exchange_trust", "urgency": max(0, 75 - state.exchange_trust), "desired_direction": "up"},
        {"axis": "liquidity", "urgency": max(0, 65 - state.liquidity), "desired_direction": "up"},
        {"axis": "price", "urgency": max(0, 55 - state.price), "desired_direction": "up"},
        {"axis": "community_panic", "urgency": max(0, state.community_panic - 45), "desired_direction": "down"},
        {"axis": "rumor_level", "urgency": max(0, state.rumor_level - 40), "desired_direction": "down"},
        {"axis": "sell_pressure", "urgency": max(0, state.sell_pressure - 40), "desired_direction": "down"},
        {"axis": "volatility", "urgency": max(0, state.volatility - 45), "desired_direction": "down"},
        {"axis": "pressure", "urgency": max(0, state.pressure - 55), "desired_direction": "down"},
        {"axis": "treasury", "urgency": max(0, 35 - state.treasury), "desired_direction": "up"},
    ]
    focus_candidates.sort(key=lambda item: int(item["urgency"]), reverse=True)
    return [item for item in focus_candidates if int(item["urgency"]) > 0][:4]


def format_tradeoff_suffix(action: ActionCard) -> str:
    tradeoff = action_tradeoff_profile(action)
    upside = "/".join(AXIS_LABELS.get(axis, axis) for axis in tradeoff["upside_axes"][:2])
    downside = "/".join(AXIS_LABELS.get(axis, axis) for axis in tradeoff["downside_axes"][:2])
    return f"（+{upside} / -{downside}）"


def _default_action_tag(cost_types: tuple[str, ...]) -> str:
    valid_tags = {"public", "private", "finance", "legal", "delay"}
    for cost_type in cost_types:
        if cost_type in valid_tags:
            return cost_type
    return "public"


def _apply_dimension_to_action_shift(shifts: dict[str, int], dimension_key: str, *, magnitude: int, upside: bool) -> None:
    signed = magnitude if upside else -magnitude
    if dimension_key == "pressure":
        shifts["public_pressure"] += -signed
    elif dimension_key == "narrative_control":
        shifts["narrative_shift"] += signed
    elif dimension_key == "exchange_trust":
        shifts["exchange_trust_shift"] += signed
    elif dimension_key == "liquidity":
        shifts["liquidity_shift"] += signed
    elif dimension_key == "treasury":
        shifts["treasury_shift"] += signed
    elif dimension_key == "control":
        shifts["control_shift"] += signed
    elif dimension_key == "volatility":
        shifts["volatility_shift"] += -signed
    elif dimension_key == "rumor_level":
        shifts["kol_trust_shift"] += signed
    elif dimension_key == "sell_pressure":
        shifts["whale_trust_shift"] += signed
    elif dimension_key == "credibility":
        shifts["narrative_shift"] += max(1, signed // 2) if signed > 0 else min(-1, signed // 2)
        shifts["exchange_shift"] += max(1, signed // 2) if signed > 0 else min(-1, signed // 2)
    elif dimension_key == "community_panic":
        shifts["public_pressure"] += -signed
        shifts["volatility_shift"] += -(signed // 2)
    elif dimension_key == "price":
        shifts["liquidity_shift"] += max(1, signed // 2) if signed > 0 else min(-1, signed // 2)
        shifts["control_shift"] += max(1, signed // 2) if signed > 0 else min(-1, signed // 2)


def synthesize_action_templates_from_frozen_world(frozen_world: FrozenInitialWorld) -> tuple[ActionCard, ...]:
    grammar = frozen_world.action_grammar
    if grammar is None:
        return ()
    templates: list[ActionCard] = []
    for rule in grammar.rules:
        shifts = {
            "public_pressure": 0,
            "narrative_shift": 0,
            "exchange_shift": 0,
            "liquidity_shift": 0,
            "treasury_shift": 0,
            "control_shift": 0,
            "volatility_shift": 0,
            "kol_trust_shift": 0,
            "whale_trust_shift": 0,
            "exchange_trust_shift": 0,
        }
        for dimension_key in rule.preferred_upside_dimensions[: max(1, rule.minimum_upside_count)]:
            _apply_dimension_to_action_shift(shifts, dimension_key, magnitude=6, upside=True)
        for dimension_key in rule.likely_downside_dimensions[: max(1, rule.minimum_downside_count)]:
            _apply_dimension_to_action_shift(shifts, dimension_key, magnitude=5, upside=False)
        templates.append(
            ActionCard(
                id=rule.key,
                label=rule.label,
                description=rule.description,
                tag=_default_action_tag(rule.allowed_cost_types),
                public_pressure=shifts["public_pressure"],
                narrative_shift=shifts["narrative_shift"],
                exchange_shift=shifts["exchange_shift"],
                liquidity_shift=shifts["liquidity_shift"],
                treasury_shift=shifts["treasury_shift"],
                control_shift=shifts["control_shift"],
                volatility_shift=shifts["volatility_shift"],
                kol_trust_shift=shifts["kol_trust_shift"],
                whale_trust_shift=shifts["whale_trust_shift"],
                exchange_trust_shift=shifts["exchange_trust_shift"],
                unlocks_truth="audit" in rule.tags or "disclosure" in rule.tags,
            )
        )
    return tuple(templates)


ENDING_BANDS = (
    {
        "min_score": 85,
        "id": "phoenix-recovery",
        "title": "凤凰回升",
        "description": "你不只是止血，还把世界状态拉回到高信任、高控制、低恐慌的强势修复区。",
    },
    {
        "min_score": 70,
        "id": "hard-won-stability",
        "title": "艰难稳盘",
        "description": "大局被你稳住了，核心结构恢复健康，但仍带着可见代价与后续修复任务。",
    },
    {
        "min_score": 55,
        "id": "fragile-truce",
        "title": "脆弱停火",
        "description": "最坏情况暂时没发生，但系统仍处在脆弱均衡，稍有失手就会再度恶化。",
    },
    {
        "min_score": 35,
        "id": "pyrrhic-survival",
        "title": "惨胜续命",
        "description": "你勉强保住局面的一部分，但代价巨大，世界状态已经留下明显结构性损伤。",
    },
    {
        "min_score": 0,
        "id": "unraveling-collapse",
        "title": "失控崩解",
        "description": "关键指标全面恶化，叙事、信任与市场结构同时失守，系统进入崩解态。",
    },
)


def validate_agent_reaction_proposal(
    *,
    context: AgentReactionContext,
    proposal: AgentReactionProposal,
    known_entities: set[str],
) -> tuple[AgentRunState, AgentReactionResult]:
    boundaries = context.boundaries
    axis_defs = {axis.key: axis for axis in boundaries.scalar_axes}
    applied_scalar_deltas: dict[str, int] = {}
    next_scalar_state = dict(context.acting_agent.scalar_state)
    for axis_key, raw_delta in proposal.scalar_deltas.items():
        axis_def = axis_defs.get(axis_key)
        if axis_def is None:
            continue
        bounded_delta = max(-axis_def.max_delta_per_turn, min(axis_def.max_delta_per_turn, int(raw_delta)))
        current_value = next_scalar_state.get(axis_key, axis_def.min_value)
        next_value = max(axis_def.min_value, min(axis_def.max_value, current_value + bounded_delta))
        applied_scalar_deltas[axis_key] = next_value - current_value
        next_scalar_state[axis_key] = next_value

    relationship_index = {relationship.target_entity_id: relationship for relationship in context.acting_agent.relationships}
    applied_relationship_deltas: dict[str, dict[str, int]] = {}
    next_relationships: list[AgentRelationshipState] = list(context.acting_agent.relationships)
    relationship_fields = ("alignment", "strain", "dependency", "visibility")
    for target_id, delta_map in list(proposal.relationship_deltas.items())[: boundaries.max_relationship_updates_per_reaction]:
        if target_id not in known_entities:
            continue
        base = relationship_index.get(target_id, AgentRelationshipState(target_entity_id=target_id, alignment=50, strain=50, dependency=50, visibility=50))
        current_values = {
            "alignment": base.alignment,
            "strain": base.strain,
            "dependency": base.dependency,
            "visibility": base.visibility,
        }
        applied_for_target: dict[str, int] = {}
        updated_values = dict(current_values)
        for field_name, raw_delta in delta_map.items():
            if field_name not in relationship_fields:
                continue
            bounded_delta = max(-boundaries.max_relationship_delta_per_turn, min(boundaries.max_relationship_delta_per_turn, int(raw_delta)))
            next_value = max(0, min(100, current_values[field_name] + bounded_delta))
            applied_for_target[field_name] = next_value - current_values[field_name]
            updated_values[field_name] = next_value
        if not applied_for_target:
            continue
        applied_relationship_deltas[target_id] = applied_for_target
        updated_relationship = AgentRelationshipState(target_entity_id=target_id, **updated_values)
        if target_id in relationship_index:
            next_relationships = [updated_relationship if relationship.target_entity_id == target_id else relationship for relationship in next_relationships]
        else:
            next_relationships.append(updated_relationship)

    known_dimensions = set(context.current_dimensions)
    applied_dimension_impacts: dict[str, int] = {}
    for dimension_key, raw_delta in list(proposal.dimension_impacts.items())[: boundaries.max_dimension_impacts_per_reaction]:
        if dimension_key not in known_dimensions:
            continue
        applied_dimension_impacts[dimension_key] = max(
            -boundaries.max_dimension_delta_per_reaction,
            min(boundaries.max_dimension_delta_per_reaction, int(raw_delta)),
        )

    allowed_hooks = set(boundaries.allowed_hook_tags)
    max_hooks = max(0, boundaries.max_hooks_per_reaction)
    triggered_hooks: list[str] = []
    if max_hooks > 0:
        for hook_tag in proposal.follow_on_hooks:
            if hook_tag not in allowed_hooks or hook_tag in triggered_hooks:
                continue
            triggered_hooks.append(hook_tag)
            if len(triggered_hooks) >= max_hooks:
                break

    salience = min(100, max(0, sum(abs(delta) for delta in applied_scalar_deltas.values())))
    valence = max(-100, min(100, sum(applied_dimension_impacts.values()) - sum(abs(delta) for delta in applied_relationship_deltas.get(next(iter(applied_relationship_deltas), ""), {}).values())))
    memory_entry = AgentMemoryEntry(
        turn_index=context.turn_index,
        action_id=context.chosen_action_id,
        summary=proposal.summary,
        salience=salience,
        valence=valence,
    )
    memory_limit = max(0, boundaries.memory_limit)
    next_memories = (*context.acting_agent.memories, memory_entry)[-memory_limit:] if memory_limit > 0 else ()
    next_triggered_hooks = tuple(dict.fromkeys((*context.acting_agent.triggered_hooks, *triggered_hooks)))

    updated_state = AgentRunState(
        agent_id=context.acting_agent.agent_id,
        agent_name=context.acting_agent.agent_name,
        role=context.acting_agent.role,
        stance=proposal.stance,
        current_objective=proposal.updated_objective,
        scalar_state=next_scalar_state,
        relationships=tuple(next_relationships),
        memories=tuple(next_memories),
        triggered_hooks=next_triggered_hooks,
    )
    result = AgentReactionResult(
        agent_id=updated_state.agent_id,
        agent_name=updated_state.agent_name,
        role=updated_state.role,
        summary=proposal.summary,
        stance=updated_state.stance,
        objective=updated_state.current_objective,
        applied_scalar_deltas=applied_scalar_deltas,
        applied_relationship_deltas=applied_relationship_deltas,
        applied_dimension_impacts=applied_dimension_impacts,
        triggered_hooks=tuple(triggered_hooks),
    )
    return updated_state, result


class CrisisGame:
    def __init__(
        self,
        scenario: ScenarioDefinition | None = None,
        *,
        frozen_world: FrozenInitialWorld | None = None,
        turns: int = 6,
        seed: int = 42,
        llm_client: OpenAICompatibleLLM | None = None,
    ) -> None:
        if scenario is None and frozen_world is None:
            scenario = get_default_scenario()
        self.scenario = scenario
        self.seed = seed
        self.random = random.Random(seed)
        self.llm = llm_client or OpenAICompatibleLLM()
        self.frozen_world = frozen_world or scenario.to_frozen_world()
        self.action_templates = tuple(getattr(scenario, "actions", ())) or synthesize_action_templates_from_frozen_world(self.frozen_world)
        self.state = self.frozen_world.instantiate_state(turns_total=turns)
        self.initial_state = self.snapshot_state()
        self.agent_profiles = [
            self.llm.generate_agent_profile(
                entity=entity,
                scenario_title=self.frozen_world.title,
                world_truth=self.frozen_world.truth,
            )
            for entity in self.frozen_world.entities
        ]
        self.agent_run_states = {profile.id: self._build_initial_agent_run_state(profile) for profile in self.agent_profiles}
        self.agent_reaction_results: list[AgentReactionResult] = []
        self.history: list[TurnResolution] = []
        self.pending_event: WorldEvent | None = None
        self.pending_actions: tuple[ActionCard, ...] | None = None

    def snapshot_state(self) -> dict[str, int]:
        return {key: getattr(self.state, key) for key in STATE_KEYS}

    def _build_initial_agent_run_state(self, profile: AgentProfile) -> AgentRunState:
        public_alignment = max(0, min(100, profile.trust_in_player))
        pressure_load = max(0, min(100, 100 - profile.trust_in_player))
        escalation_drive = max(0, min(100, 100 - profile.trust_in_player))
        return AgentRunState(
            agent_id=profile.id,
            agent_name=profile.name,
            role=profile.role,
            stance=profile.stance,
            current_objective=profile.public_goal,
            scalar_state={
                "trust_in_player": profile.trust_in_player,
                "pressure_load": pressure_load,
                "escalation_drive": escalation_drive,
                "public_alignment": public_alignment,
            },
        )

    def begin_turn(self) -> WorldEvent:
        if self.pending_event is not None:
            return self.pending_event
        actor = self._pick_event_actor()
        event = self._generate_pre_turn_event(actor)
        self._apply_delta(event.state_delta)
        self.pending_event = event
        return event

    def available_actions(self) -> tuple[ActionCard, ...]:
        if self.pending_actions is not None:
            return self.pending_actions
        template_pool = list(self.action_templates)
        if self.state.treasury < 20:
            template_pool = [a for a in template_pool if a.id != "buyback"]
        if "wallet_frozen" in self.state.flags:
            template_pool = [a for a in template_pool if a.id != "freeze_wallet"]
        templates = []
        decision_focus = decision_focus_from_state(self.state)
        for action in template_pool:
            profile = action_impact_profile(action)
            tradeoff = action_tradeoff_profile(action)
            templates.append(
                {
                    "id": action.id,
                    "label": action.label,
                    "description": action.description,
                    "impact_cost": profile["impact_cost"],
                    "impact_tier": profile["impact_tier"],
                    "upside_axes": tradeoff["upside_axes"],
                    "downside_axes": tradeoff["downside_axes"],
                }
            )
        action_context = self.frozen_world.build_action_generation_context(
            state=self.state,
            situation=TurnSituation(
                turn_index=self.state.turn_index,
                turns_total=self.state.turns_total,
                selected_player_role=self.frozen_world.player_role,
                objective=self.frozen_world.objective,
                dominant_tensions=tuple(item["axis"] for item in decision_focus[:3]),
                urgent_dimensions=(),
                unstable_dimensions=(),
                recent_action_summaries=tuple(resolution.action_label for resolution in self.history[-2:]),
            ),
        )
        generated = self.llm.generate_turn_actions(
            scenario_title=self.frozen_world.title,
            player_role=self.frozen_world.player_role,
            player_objective=self.frozen_world.objective,
            state_summary=self._state_summary(),
            decision_focus=decision_focus,
            available_templates=templates,
            action_context=action_context,
        )
        template_map = {action.id: action for action in template_pool}
        constrained_ids = self._constrain_generated_action_ids(
            template_pool=template_pool,
            generated_ids=[item["template_id"] for item in generated],
        )
        generated_map = {item["template_id"]: item for item in generated if item["template_id"] in constrained_ids}
        actions: list[ActionCard] = []
        for template_id in constrained_ids:
            base = template_map[template_id]
            item = generated_map.get(
                template_id,
                {"label": base.label, "description": base.description},
            )
            actions.append(
                ActionCard(
                    id=base.id,
                    label=item["label"],
                    description=self._normalize_action_description(base=base, description=item["description"]),
                    tag=base.tag,
                    public_pressure=base.public_pressure,
                    narrative_shift=base.narrative_shift,
                    exchange_shift=base.exchange_shift,
                    liquidity_shift=base.liquidity_shift,
                    treasury_shift=base.treasury_shift,
                    control_shift=base.control_shift,
                    volatility_shift=base.volatility_shift,
                    kol_trust_shift=base.kol_trust_shift,
                    whale_trust_shift=base.whale_trust_shift,
                    exchange_trust_shift=base.exchange_trust_shift,
                    unlocks_truth=base.unlocks_truth,
                )
            )
        if len(actions) < 2:
            raise ValueError("LLM-generated actions must include at least two valid choices")
        self.pending_actions = tuple(actions)
        return self.pending_actions

    def _normalize_action_description(self, *, base: ActionCard, description: str) -> str:
        clean = description.strip()
        suffix = format_tradeoff_suffix(base)
        if suffix in clean:
            return clean
        if re.search(r"（[^）]*\+[^）]*-[^）]*）\s*$", clean):
            return clean
        return f"{clean} {suffix}".strip()

    def _constrain_generated_action_ids(self, *, template_pool: list[ActionCard], generated_ids: list[str]) -> list[str]:
        template_map = {action.id: action for action in template_pool}
        ordered_ids: list[str] = []
        for template_id in generated_ids:
            if template_id in template_map and template_id not in ordered_ids:
                ordered_ids.append(template_id)

        selected: list[str] = []
        selected_tiers: list[str] = []

        def add_candidate(candidate_id: str) -> bool:
            if candidate_id in selected:
                return False
            tier = str(action_impact_profile(template_map[candidate_id])["impact_tier"])
            if tier == "extreme" and selected_tiers.count("extreme") >= 1:
                return False
            selected.append(candidate_id)
            selected_tiers.append(tier)
            return True

        for required_tier in ("low", "medium"):
            preferred = next(
                (
                    template_id
                    for template_id in ordered_ids
                    if str(action_impact_profile(template_map[template_id])["impact_tier"]) == required_tier
                ),
                None,
            )
            fallback = next(
                (
                    action.id
                    for action in template_pool
                    if str(action_impact_profile(action)["impact_tier"]) == required_tier and action.id not in selected
                ),
                None,
            )
            if preferred is not None:
                add_candidate(preferred)
            elif fallback is not None:
                add_candidate(fallback)

        for candidate_id in ordered_ids:
            if len(selected) >= 4:
                break
            add_candidate(candidate_id)

        for action in template_pool:
            if len(selected) >= 4:
                break
            add_candidate(action.id)

        return selected[:4]

    def auto_choose_action(self) -> TurnChoice:
        scored = []
        for action in self.available_actions():
            score = self._score_action(action)
            scored.append((score, action))
        _, action = max(scored, key=lambda item: item[0])
        return TurnChoice(action=action, reason="Auto player chooses the highest control-preserving move.")

    def apply_choice(self, choice: TurnChoice) -> TurnResolution:
        pre_turn_event = self.begin_turn()
        action = choice.action
        self.state.turn_index += 1
        self._apply_action_base_effects(action)
        reactions = self._generate_agent_reactions(action)
        for reaction in reactions:
            self._apply_delta(reaction.state_delta)
        self._apply_secondary_world_rules(action, reactions)
        self.state.clamp()

        narrative = self.llm.narrate_turn(
            turn_number=self.state.turn_index,
            action_label=action.label,
            player_objective=self.frozen_world.objective,
            state_summary=self._state_summary(),
            agent_profiles=self.agent_profiles,
        )
        bullets = tuple(self._build_bullets(action, pre_turn_event, reactions))
        snapshot = self._frozen_state_snapshot()
        resolution = TurnResolution(
            turn_number=self.state.turn_index,
            action_id=action.id,
            action_label=action.label,
            narrative=narrative,
            bullet_points=bullets,
            state_snapshot=snapshot,
            pre_turn_event=pre_turn_event,
            agent_reactions=tuple(reactions),
        )
        self.history.append(resolution)
        self.pending_event = None
        self.pending_actions = None
        return resolution

    def build_world_report(self) -> WorldReport:
        final_state = self.snapshot_state()
        diff = {key: final_state[key] - self.initial_state[key] for key in STATE_KEYS}
        timeline = self.timeline_lines()
        summary, share_text = self.llm.summarize_world_state(
            scenario_title=self.frozen_world.title,
            player_role=self.frozen_world.player_role,
            initial_state=self.initial_state,
            final_state=final_state,
            diff=diff,
            timeline=timeline,
        )
        ending = self._build_ending_from_state(final_state)
        timeline_markdown = self.timeline_markdown()
        return WorldReport(
            initial_state=self.initial_state,
            final_state=final_state,
            diff=diff,
            summary=summary,
            share_text=share_text,
            timeline_markdown=timeline_markdown,
            ending_score=int(ending["ending_score"]),
            ending_id=str(ending["ending_id"]),
            ending_title=str(ending["ending_title"]),
            ending_description=str(ending["ending_description"]),
        )

    def _build_ending_from_state(self, state: dict[str, int]) -> dict[str, int | str]:
        positive_score = (
            state["credibility"]
            + state["price"]
            + state["liquidity"]
            + state["narrative_control"]
            + state["exchange_trust"]
            + state["control"]
            + (100 - state["sell_pressure"])
            + (100 - state["volatility"])
            + (100 - state["community_panic"])
            + (100 - state["rumor_level"])
        )
        negative_drag = state["pressure"] + max(0, 40 - state["treasury"]) * 2
        ending_score = max(0, min(100, (positive_score - negative_drag) // 8))
        band = next(item for item in ENDING_BANDS if ending_score >= int(item["min_score"]))
        return {
            "ending_score": ending_score,
            "ending_id": str(band["id"]),
            "ending_title": str(band["title"]),
            "ending_description": str(band["description"]),
        }

    def timeline_lines(self) -> list[str]:
        lines: list[str] = []
        for resolution in self.history:
            pre = resolution.pre_turn_event
            if pre is not None:
                lines.append(f"Turn {resolution.turn_number} pre-event: {pre.actor_name} -> {pre.headline}")
            lines.append(f"Turn {resolution.turn_number} player: {resolution.action_label}")
            for reaction in resolution.agent_reactions:
                lines.append(f"Turn {resolution.turn_number} reaction: {reaction.actor_name} -> {reaction.summary}")
        return lines

    def timeline_markdown(self) -> str:
        lines = ["# Timeline", "", "## turns"]
        for resolution in self.history:
            lines.append(f"### Turn {resolution.turn_number}")
            if resolution.pre_turn_event is not None:
                lines.append(f"- Pre-turn: {resolution.pre_turn_event.actor_name} / {resolution.pre_turn_event.headline}")
                lines.append(f"- Event: {resolution.pre_turn_event.summary}")
            lines.append(f"- Player action: {resolution.action_label}")
            for reaction in resolution.agent_reactions:
                lines.append(f"- {reaction.actor_name}: {reaction.summary}")
            lines.append("")
        return "\n".join(lines)

    def _frozen_state_snapshot(self) -> WorldState:
        return WorldState(
            turn_index=self.state.turn_index,
            turns_total=self.state.turns_total,
            credibility=self.state.credibility,
            treasury=self.state.treasury,
            pressure=self.state.pressure,
            price=self.state.price,
            liquidity=self.state.liquidity,
            sell_pressure=self.state.sell_pressure,
            volatility=self.state.volatility,
            community_panic=self.state.community_panic,
            rumor_level=self.state.rumor_level,
            narrative_control=self.state.narrative_control,
            exchange_trust=self.state.exchange_trust,
            control=self.state.control,
            truth_public=self.state.truth_public,
            flags=set(self.state.flags),
        )

    def _score_action(self, action: ActionCard) -> int:
        emergency_weight = 20 if self.state.exchange_trust < 45 else 0
        panic_weight = 20 if self.state.community_panic > 65 else 0
        treasury_penalty = 18 if self.state.treasury < 30 and action.treasury_shift < 0 else 0
        score = (
            action.control_shift * 5
            + action.narrative_shift * 4
            + (action.exchange_shift + action.exchange_trust_shift) * 4
            + action.liquidity_shift * 3
            - action.public_pressure * 2
            - max(0, action.volatility_shift) * 2
            - treasury_penalty
            + (action.exchange_trust_shift if emergency_weight else 0)
            + (action.narrative_shift if panic_weight else 0)
        )
        tradeoff = action_tradeoff_profile(action)
        focus_weights = {item["axis"]: int(item["urgency"]) for item in decision_focus_from_state(self.state)}
        for axis, urgency in focus_weights.items():
            if axis in tradeoff["upside_axes"]:
                score += urgency // 2
            if axis in tradeoff["downside_axes"]:
                score -= urgency // 2
        if self.state.truth_public and action.id == "shift_blame":
            score -= 80
        return score

    def _pick_event_actor(self) -> AgentProfile:
        weighted = []
        for agent in self.agent_profiles:
            role_bucket = _role_bucket(agent.role, agent.name, agent.public_goal, agent.pressure_point)
            urgency = max(1, 100 - agent.trust_in_player)
            if role_bucket == "community":
                urgency += self.state.community_panic // 2
            elif role_bucket == "whale":
                urgency += self.state.sell_pressure // 2
            elif role_bucket == "kol":
                urgency += self.state.rumor_level // 2
            elif role_bucket == "exchange":
                urgency += max(0, 60 - self.state.exchange_trust)
            elif role_bucket == "market_maker":
                urgency += max(0, 60 - self.state.liquidity)
            weighted.append((urgency + agent.influence, agent))
        total = sum(weight for weight, _ in weighted)
        pick = self.random.randint(1, total)
        cursor = 0
        for weight, agent in weighted:
            cursor += weight
            if pick <= cursor:
                return agent
        return weighted[-1][1]

    def _generate_pre_turn_event(self, actor: AgentProfile) -> WorldEvent:
        role_bucket = _role_bucket(actor.role, actor.name, actor.public_goal, actor.pressure_point)
        if role_bucket == "kol":
            if actor.trust_in_player < 40:
                return WorldEvent(
                    headline=f"{actor.name} 发出新的质疑贴",
                    summary=f"{actor.name} 公开追问异常钱包和做市撤单之间的关系，舆论热度再次升高。",
                    severity=72,
                    actor_id=actor.id,
                    actor_name=actor.name,
                    state_delta={"rumor_level": impact("medium"), "pressure": impact("light") + 1, "community_panic": impact("light")},
                )
            return WorldEvent(
                headline=f"{actor.name} 暂缓开火",
                summary=f"{actor.name} 表示先等更多证据，暂时没有继续升级攻击。",
                severity=38,
                actor_id=actor.id,
                actor_name=actor.name,
                state_delta={"rumor_level": -impact("light"), "narrative_control": impact("tiny")},
            )
        if role_bucket == "whale":
            if actor.trust_in_player < 45:
                return WorldEvent(
                    headline=f"{actor.name} 再次减仓",
                    summary=f"{actor.name} 在盘口脆弱时继续减仓，价格和恐慌同步承压。",
                    severity=76,
                    actor_id=actor.id,
                    actor_name=actor.name,
                    state_delta={"price": -(impact("light") + 1), "sell_pressure": impact("heavy"), "community_panic": impact("light") + 1},
                )
            return WorldEvent(
                headline=f"{actor.name} 暂停抛售",
                summary=f"{actor.name} 暂时停止继续卖出，市场获得一点喘息空间。",
                severity=34,
                actor_id=actor.id,
                actor_name=actor.name,
                state_delta={"sell_pressure": -impact("medium"), "price": impact("tiny")},
            )
        if role_bucket == "market_maker":
            if actor.trust_in_player < 45:
                return WorldEvent(
                    headline=f"{actor.name} 缩窄挂单深度",
                    summary=f"{actor.name} 为了自保继续降低盘口深度，流动性变得更脆弱。",
                    severity=68,
                    actor_id=actor.id,
                    actor_name=actor.name,
                    state_delta={"liquidity": -impact("medium") - 2, "volatility": impact("medium"), "pressure": impact("light")},
                )
            return WorldEvent(
                headline=f"{actor.name} 补回部分挂单",
                summary=f"{actor.name} 回补了一部分关键挂单，价格波动略有缓和。",
                severity=40,
                actor_id=actor.id,
                actor_name=actor.name,
                state_delta={"liquidity": impact("medium"), "volatility": -impact("light")},
            )
        if role_bucket == "community":
            if actor.trust_in_player >= 55:
                return WorldEvent(
                    headline=f"{actor.name} 在社区稳群",
                    summary=f"{actor.name} 把讨论组织成 FAQ 和时间线，帮助你争取时间。",
                    severity=35,
                    actor_id=actor.id,
                    actor_name=actor.name,
                    state_delta={"community_panic": -impact("medium"), "narrative_control": impact("light")},
                )
            return WorldEvent(
                headline=f"{actor.name} 顶不住社区质问",
                summary=f"{actor.name} 开始要求你给更完整解释，群体情绪明显变差。",
                severity=61,
                actor_id=actor.id,
                actor_name=actor.name,
                state_delta={"community_panic": impact("medium") + 1, "pressure": impact("light")},
            )
        if role_bucket == "exchange":
            if actor.trust_in_player < 50 or self.state.exchange_trust < 50:
                return WorldEvent(
                    headline=f"{actor.name} 催交补充材料",
                    summary=f"{actor.name} 要求你在更短时间内提供完整证据，否则将升级风险处置。",
                    severity=74,
                    actor_id=actor.id,
                    actor_name=actor.name,
                    state_delta={"pressure": impact("medium") + 2, "exchange_trust": -(impact("light") + 1), "control": -impact("tiny")},
                )
            return WorldEvent(
                headline=f"{actor.name} 暂缓进一步风控动作",
                summary=f"{actor.name} 认可你目前的配合度，暂时没有追加限制。",
                severity=32,
                actor_id=actor.id,
                actor_name=actor.name,
                state_delta={"exchange_trust": impact("tiny") + 1, "pressure": -impact("tiny")},
            )
        return WorldEvent(
            headline="市场继续波动",
            summary="市场仍然高度敏感。",
            severity=50,
            actor_id=actor.id,
            actor_name=actor.name,
            state_delta={"pressure": 2},
        )

    def _apply_action_base_effects(self, action: ActionCard) -> None:
        self._apply_delta(
            {
                "pressure": action.public_pressure,
                "narrative_control": action.narrative_shift,
                "exchange_trust": action.exchange_shift + action.exchange_trust_shift,
                "liquidity": action.liquidity_shift,
                "treasury": action.treasury_shift,
                "control": action.control_shift,
                "volatility": action.volatility_shift,
            }
        )
        if action.unlocks_truth:
            self.state.truth_public = True
        if action.id == "freeze_wallet":
            self.state.flags.add("wallet_frozen")

    def _generate_agent_reactions(self, action: ActionCard) -> list[AgentReaction]:
        reactions: list[AgentReaction] = []
        reaction_results: list[AgentReactionResult] = []
        updated_profiles: list[AgentProfile] = []
        known_entities = {agent.id for agent in self.agent_profiles}
        relevant_entities = tuple(entity.id for entity in self.frozen_world.entities)
        for agent in self.agent_profiles:
            trust_delta, state_delta, summary = self._agent_reaction_payload(agent, action)
            trust = max(0, min(100, agent.trust_in_player + trust_delta))
            stance = _derive_stance(agent.role, trust, self.state)
            updated_profiles.append(replace(agent, trust_in_player=trust, stance=stance))

            run_state = self.agent_run_states.get(agent.id, self._build_initial_agent_run_state(agent))
            proposal = AgentReactionProposal(
                summary=summary,
                stance=stance,
                updated_objective=run_state.current_objective,
                scalar_deltas={
                    "trust_in_player": trust_delta,
                    "pressure_load": max(-12, min(12, state_delta.get("pressure", 0))),
                    "escalation_drive": max(-12, min(12, state_delta.get("control", 0) * -1 + state_delta.get("pressure", 0))),
                    "public_alignment": max(-12, min(12, state_delta.get("narrative_control", 0) + state_delta.get("exchange_trust", 0))),
                },
                relationship_deltas={},
                dimension_impacts={key: value for key, value in state_delta.items() if key in self.state.to_dimension_map()},
                follow_on_hooks=("institutional_freeze",) if action.id == "freeze_wallet" and _role_bucket(agent.role) == "exchange" else (),
            )
            context = AgentReactionContext(
                world_id=self.frozen_world.world_id,
                world_title=self.frozen_world.title,
                turn_index=self.state.turn_index,
                turns_total=self.state.turns_total,
                player_role=self.frozen_world.player_role,
                player_objective=self.frozen_world.objective,
                chosen_action_id=action.id,
                chosen_action_label=action.label,
                chosen_action_summary=action.description,
                current_dimensions=self.state.to_dimension_map(),
                urgent_dimensions=(),
                unstable_dimensions=(),
                dominant_tensions=tuple(item["axis"] for item in decision_focus_from_state(self.state)[:3]),
                acting_agent=run_state,
                relevant_entities=relevant_entities,
                recent_turn_summaries=tuple(resolution.action_label for resolution in self.history[-2:]),
                boundaries=self.frozen_world.reaction_boundaries,
            )
            updated_run_state, result = validate_agent_reaction_proposal(
                context=context,
                proposal=proposal,
                known_entities=known_entities,
            )
            self.agent_run_states[agent.id] = updated_run_state
            reaction_results.append(result)
            reactions.append(
                AgentReaction(
                    actor_id=agent.id,
                    actor_name=agent.name,
                    role=agent.role,
                    summary=summary,
                    stance=stance,
                    trust_after=trust,
                    state_delta=state_delta,
                )
            )
        self.agent_profiles = updated_profiles
        self.agent_reaction_results = reaction_results
        return reactions

    def _agent_reaction_payload(self, agent: AgentProfile, action: ActionCard) -> tuple[int, dict[str, int], str]:
        role_bucket = _role_bucket(agent.role, agent.name, agent.public_goal, agent.pressure_point)
        if role_bucket == "kol":
            if action.id == "shift_blame":
                if self.state.truth_public:
                    return -16, {"rumor_level": 6, "narrative_control": -4, "pressure": 4}, f"{agent.name} 认为你在已公开部分真相后仍试图甩锅，开始组织新一轮负面叙事。"
                return -4, {"rumor_level": 2, "narrative_control": 3}, f"{agent.name} 半信半疑地转发你的外部攻击说法，但仍保留质疑空间。"
            if action.id == "private_kol":
                return 18, {"rumor_level": -5, "narrative_control": 4}, f"{agent.name} 暂时放缓攻击节奏，开始把焦点放到更多证据上。"
            if action.id in {"statement", "ama"}:
                return 8, {"rumor_level": -3, "narrative_control": 3}, f"{agent.name} 承认你至少愿意正面回应，但还会继续审视细节。"
            return 0, {"rumor_level": 1}, f"{agent.name} 继续观察你的下一步动作。"
        if role_bucket == "whale":
            if action.id == "buyback":
                return 12, {"sell_pressure": -9, "price": 5}, f"{agent.name} 判断你愿意拿真金白银托底，暂时停止继续砸盘。"
            if action.id in {"statement", "freeze_wallet"}:
                return 6, {"sell_pressure": -4, "price": 2}, f"{agent.name} 认为风险略有下降，减缓了抛售节奏。"
            if action.id == "silent":
                return -12, {"sell_pressure": 8, "price": -4}, f"{agent.name} 把你的沉默理解成危险信号，继续减仓。"
            return 0, {"sell_pressure": 1}, f"{agent.name} 仍在按风控模型谨慎调整仓位。"
        if role_bucket == "market_maker":
            if action.id == "pressure_mm":
                return 10, {"liquidity": 9, "volatility": -5}, f"{agent.name} 被迫回补部分挂单，盘口短暂变厚。"
            if action.id == "shift_blame":
                return -8, {"liquidity": -4, "pressure": 2}, f"{agent.name} 感到你可能把责任推给自己，于是进一步缩手自保。"
            if action.id == "freeze_wallet":
                return 3, {"liquidity": 2}, f"{agent.name} 认为你至少在做止血动作，因此暂时没有继续撤离。"
            return 0, {"volatility": 1}, f"{agent.name} 继续以极其保守的方式维持盘口。"
        if role_bucket == "community":
            if action.id in {"ama", "statement"}:
                return 10, {"community_panic": -6, "narrative_control": 4}, f"{agent.name} 开始帮你整理话术和 FAQ，社区情绪略有回稳。"
            if action.id == "buyback":
                return 6, {"community_panic": -4}, f"{agent.name} 把回购解读为你没有跑路打算，开始安抚群成员。"
            if action.id == "silent":
                return -10, {"community_panic": 7, "pressure": 3}, f"{agent.name} 顶不住群体质问，开始公开向你施压。"
            return 2, {"community_panic": -1}, f"{agent.name} 继续观察，但愿意先给你一点时间。"
        if role_bucket == "exchange":
            if action.id == "freeze_wallet":
                return 18, {"exchange_trust": 10, "control": 2}, f"{agent.name} 认可你给出的可执行止血动作，暂时不升级风控。"
            if action.id in {"statement", "ama"}:
                return 6, {"exchange_trust": 4}, f"{agent.name} 认为你在配合，但仍要求更完整证据。"
            if action.id == "shift_blame":
                return -14, {"exchange_trust": -10, "control": -4, "pressure": 4}, f"{agent.name} 觉得你在转移责任，开始准备更严厉的风险动作。"
            if action.id == "silent":
                return -12, {"exchange_trust": -8, "pressure": 5}, f"{agent.name} 把沉默解读为重大不确定性，进一步收紧容忍度。"
            return 1, {"exchange_trust": 1}, f"{agent.name} 暂时记下你的动作，但还没有完全放心。"
        return 0, {}, f"{agent.name} 没有明显反应。"

    def _apply_secondary_world_rules(self, action: ActionCard, reactions: list[AgentReaction]) -> None:
        avg_trust = sum(agent.trust_in_player for agent in self.agent_profiles) // len(self.agent_profiles)
        influencer_support = sum(agent.influence for agent in self.agent_profiles if agent.trust_in_player >= 55)
        influencer_hostility = sum(agent.influence for agent in self.agent_profiles if agent.trust_in_player <= 35)
        self._apply_delta(
            {
                "credibility": (avg_trust - 45) // 5,
                "community_panic": max(0, 55 - avg_trust) // 5,
                "rumor_level": max(0, influencer_hostility - influencer_support) // 20,
                "sell_pressure": max(0, self.state.community_panic - self.state.narrative_control) // 10,
                "exchange_trust": max(0, avg_trust - 50) // 8,
                "control": max(0, self.state.narrative_control - self.state.rumor_level) // 12,
                "pressure": 5,
            }
        )
        if action.id == "buyback" and self.state.treasury < 20:
            self._apply_delta({"pressure": 4, "credibility": -2})
        if self.state.exchange_trust < 25:
            self.state.flags.add("delisting_risk")
            self._apply_delta({"control": -10})
        if self.state.price < 25:
            self._apply_delta({"community_panic": 8, "pressure": 6})
        if any(_role_bucket(reaction.role) == "exchange" and reaction.trust_after < 30 for reaction in reactions):
            self.state.flags.add("exchange_hostile")
        self._apply_anomaly_rules()
        self.state.clamp()

    def _apply_anomaly_rules(self) -> None:
        if self.state.pressure >= 85:
            self.state.flags.add("pressure_breakdown")
            self._apply_delta({"control": -6, "credibility": -3, "community_panic": 4})
        if self.state.volatility >= 90:
            self.state.flags.add("volatility_spike")
            self._apply_delta({"price": -4, "community_panic": 4})
        if self.state.community_panic >= 90:
            self.state.flags.add("panic_cascade")
            self._apply_delta({"sell_pressure": 6, "control": -4})

    def _apply_delta(self, delta: dict[str, int]) -> None:
        for key, value in delta.items():
            setattr(self.state, key, getattr(self.state, key) + value)
        self.state.clamp()

    def _state_summary(self) -> dict[str, int]:
        return {
            "credibility": self.state.credibility,
            "control": self.state.control,
            "price": self.state.price,
            "liquidity": self.state.liquidity,
            "community_panic": self.state.community_panic,
            "rumor_level": self.state.rumor_level,
            "exchange_trust": self.state.exchange_trust,
        }

    def _build_bullets(self, action: ActionCard, pre_turn_event: WorldEvent, reactions: list[AgentReaction]) -> Iterable[str]:
        yield f"回合前事件：{pre_turn_event.actor_name} / {pre_turn_event.headline}"
        yield f"控制权 {self.state.control} / 100"
        yield f"叙事控制 {self.state.narrative_control} / 100"
        yield f"社区恐慌 {self.state.community_panic} / 100"
        yield f"交易所信任 {self.state.exchange_trust} / 100"
        for reaction in reactions[:3]:
            yield f"{reaction.actor_name}：{reaction.summary}"
        if "delisting_risk" in self.state.flags:
            yield "⚠️ 交易所下架风险正在逼近"
        if "pressure_breakdown" in self.state.flags:
            yield "⚠️ 压力异常：团队进入高压失稳状态，控制权和信誉开始额外受损"
        if "volatility_spike" in self.state.flags:
            yield "⚠️ 波动异常：盘口出现额外失稳，价格承压"
        if "panic_cascade" in self.state.flags:
            yield "⚠️ 恐慌异常：社区进入踩踏传播，抛压进一步放大"
        if action.id == "buyback" and self.state.treasury < 20:
            yield "⚠️ 国库资金已经很危险"


def _derive_stance(role: str, trust: int, state: WorldState) -> str:
    role_bucket = _role_bucket(role)
    if role_bucket == "exchange":
        if trust >= 60 and state.exchange_trust >= 55:
            return "暂时配合，但要求更多证据"
        if trust <= 35:
            return "准备切割项目"
        return "谨慎观望"
    if role_bucket == "kol":
        if trust >= 55:
            return "开始转向中立甚至帮你说话"
        if trust <= 30:
            return "持续放大负面叙事"
        return "仍在试探你"
    if role_bucket == "whale":
        if trust >= 55 and state.liquidity >= 50:
            return "考虑停止砸盘"
        if trust <= 35:
            return "准备继续出货"
        return "继续观望"
    if role_bucket == "community":
        if trust >= 60:
            return "愿意帮你稳住群体情绪"
        if trust <= 30:
            return "开始怀疑你就是问题本身"
        return "还在等你给更多解释"
    if role_bucket == "market_maker":
        if trust >= 60:
            return "可以短暂配合恢复挂单"
        if trust <= 30:
            return "优先保护自己，不愿背锅"
        return "摇摆不定"
    return "中立"


def _role_bucket(role: str, *signals: str) -> str:
    text = " ".join(part for part in (role, *signals) if part).lower()
    zh_text = " ".join(part for part in (role, *signals) if part)
    if any(token in text for token in ("kol", "media", "journalist", "reporter", "influencer")) or any(token in zh_text for token in ("媒体", "记者", "自媒体", "话题账号", "kol", "大v")):
        return "kol"
    if any(token in text for token in ("whale", "fund", "holder", "investor", "parent", "alumni")) or any(token in zh_text for token in ("鲸鱼", "基金", "投资人", "持有人", "家长", "校友", "公众")):
        return "whale"
    if any(token in text for token in ("market maker", "maker", "liquidity", "dealer")) or any(token in zh_text for token in ("做市", "流动性", "盘口")):
        return "market_maker"
    if any(token in text for token in ("exchange", "platform", "school", "university", "institution", "regulator", "department", "committee")) or any(token in zh_text for token in ("校方", "学校", "大学", "平台", "机构", "监管", "部门", "体系", "官方")):
        return "exchange"
    if any(token in text for token in ("community", "student", "user", "public", "audience", "group")) or any(token in zh_text for token in ("学生", "用户", "社区", "人群", "群体", "网民")):
        return "community"
    return "community"


def build_game(
    *,
    turns: int = 6,
    seed: int = 42,
    llm_client: OpenAICompatibleLLM | None = None,
    scenario: ScenarioDefinition | None = None,
    frozen_world: FrozenInitialWorld | None = None,
) -> CrisisGame:
    return CrisisGame(scenario=scenario, frozen_world=frozen_world, turns=turns, seed=seed, llm_client=llm_client)


def run_auto_game(
    *,
    turns: int = 6,
    seed: int = 42,
    llm_client: OpenAICompatibleLLM | None = None,
    scenario: ScenarioDefinition | None = None,
    frozen_world: FrozenInitialWorld | None = None,
) -> tuple[CrisisGame, WorldReport]:
    game = build_game(turns=turns, seed=seed, llm_client=llm_client, scenario=scenario, frozen_world=frozen_world)
    while game.state.turn_index < game.state.turns_total:
        game.begin_turn()
        game.apply_choice(game.auto_choose_action())
    return game, game.build_world_report()
