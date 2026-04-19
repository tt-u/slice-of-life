from __future__ import annotations

import re
from dataclasses import replace

from .domain import (
    InitialWorldValidation,
    MaterialSeedInspection,
    ScenarioBlueprint,
    ScenarioDefinition,
    ScenarioRoleComparisonCard,
    ScenarioRoleOverviewCard,
    ScenarioViewpointCard,
    SeedEntity,
    WorldState,
    default_world_dimension_defs,
    dimension_driven_world_action_grammar,
)
from .llm import OpenAICompatibleLLM

SUPPORTED_ROLES = ("kol", "whale", "market_maker", "community", "exchange")
MAX_ENTITY_CAP = 24
DEFAULT_ENTITY_CAP = 12
POLARIZED_GROUP_RE = re.compile(r"^(支持|反对)(?P<subject>.+?)(?:的)?(?:声音|群体|阵营|人群)$")
INSTITUTION_ROLE_SUFFIX_RE = re.compile(r"(?P<base>.+?)(?:核心决策者|核心负责人|主要负责人|决策者)$")
PERSON_ROLE_SUFFIX_RE = re.compile(r"(?P<base>.+?)(?:本人)$")
INSTITUTION_TOKENS = (
    "校方",
    "学校",
    "平台",
    "公司",
    "港口",
    "州政府",
    "地方政府",
    "政府",
    "航运集团",
    "集团",
    "品牌",
    "品牌方",
    "俱乐部",
    "交易所",
    "项目方",
    "院方",
    "节目组",
)
INSPECTION_METRIC_KEYS = ("control", "pressure", "credibility", "narrative_control")
INSPECTION_METRIC_LABELS = {
    "control": "控制权",
    "pressure": "压力",
    "credibility": "公信力",
    "narrative_control": "叙事控制",
}
INSPECTION_FOCUS_WEIGHTS = {
    "control": 1.0,
    "pressure": 1.0,
    "credibility": 1.05,
    "narrative_control": 0.75,
}
EMBATTLED_STANCE_TOKENS = ("embattled", "under fire", "targeted", "isolated", "被动", "承压", "围攻")
STABILIZING_STANCE_TOKENS = ("stable", "steady", "defensive", "稳态", "防守")


def validate_initial_world_state(state: WorldState) -> InitialWorldValidation:
    reasons: list[str] = []
    if not 20 <= state.control <= 80:
        reasons.append("control_out_of_band")
    if not 15 <= state.exchange_trust <= 85:
        reasons.append("exchange_trust_out_of_band")
    if not 15 <= state.narrative_control <= 85:
        reasons.append("narrative_control_out_of_band")
    if not 15 <= state.liquidity <= 85:
        reasons.append("liquidity_out_of_band")
    if not 10 <= state.treasury <= 90:
        reasons.append("treasury_out_of_band")
    if not 15 <= state.price <= 85:
        reasons.append("price_out_of_band")
    if not 20 <= state.credibility <= 85:
        reasons.append("credibility_out_of_band")
    if state.pressure < 20:
        reasons.append("pressure_too_low")

    danger_metrics = sum(
        [
            state.pressure >= 55,
            state.community_panic >= 55,
            state.rumor_level >= 55,
            state.sell_pressure >= 55,
            state.volatility >= 55,
        ]
    )
    if danger_metrics < 2:
        reasons.append("not_enough_danger")

    recovery_levers = sum(
        [
            state.control >= 35,
            state.treasury >= 25,
            state.exchange_trust >= 30,
            state.narrative_control >= 30,
            state.credibility >= 30,
        ]
    )
    if recovery_levers < 2:
        reasons.append("not_enough_recovery")

    return InitialWorldValidation(is_playable=not reasons, reasons=tuple(reasons))


def repair_initial_world_state(state: WorldState) -> WorldState:
    repaired = replace(state)
    repaired.clamp()

    repaired.control = max(20, min(80, repaired.control))
    repaired.exchange_trust = max(15, min(85, repaired.exchange_trust))
    repaired.narrative_control = max(15, min(85, repaired.narrative_control))
    repaired.liquidity = max(15, min(85, repaired.liquidity))
    repaired.treasury = max(10, min(90, repaired.treasury))
    repaired.price = max(15, min(85, repaired.price))
    repaired.credibility = max(20, min(85, repaired.credibility))
    repaired.pressure = max(20, repaired.pressure)

    danger_fields = [
        "pressure",
        "community_panic",
        "rumor_level",
        "sell_pressure",
        "volatility",
    ]
    if sum(getattr(repaired, field) >= 55 for field in danger_fields) < 2:
        repaired.pressure = max(repaired.pressure, 58)
        repaired.community_panic = max(repaired.community_panic, 60)

    recovery_fields = [
        "control",
        "treasury",
        "exchange_trust",
        "narrative_control",
        "credibility",
    ]
    if sum(getattr(repaired, field) >= 35 if field in {"control", "treasury"} else getattr(repaired, field) >= 30 for field in recovery_fields) < 2:
        repaired.control = max(repaired.control, 38)
        repaired.exchange_trust = max(repaired.exchange_trust, 34)
        repaired.narrative_control = max(repaired.narrative_control, 34)

    repaired.clamp()
    return repaired


def build_scenario_from_material(
    *,
    source_material: str,
    llm_client: OpenAICompatibleLLM,
    entity_cap: int = DEFAULT_ENTITY_CAP,
    selected_player_role: str | None = None,
) -> ScenarioDefinition:
    material = source_material.strip()
    if not material:
        raise ValueError("source_material must not be empty")

    normalized_cap = max(3, min(entity_cap, MAX_ENTITY_CAP))
    blueprint = llm_client.generate_scenario_blueprint(
        source_material=material,
        entity_cap=normalized_cap,
        selected_player_role=selected_player_role,
    )
    entities = _normalize_entities(blueprint.entities, normalized_cap)
    if len(entities) < 3:
        entities = _backfill_entities(entities, normalized_cap)

    resolved_player_role = _resolve_player_role(blueprint.player_role, selected_player_role)
    calibration_roles = _normalize_playable_roles(
        blueprint.playable_roles,
        fallback_role=resolved_player_role,
    )
    playable_roles = _normalize_playable_roles(
        blueprint.playable_roles,
        fallback_role=resolved_player_role,
        preferred_role=resolved_player_role,
    )
    entities = _prioritize_entities_for_viewpoint(
        entities,
        player_role=resolved_player_role,
        playable_roles=playable_roles,
    )
    initial_world = repair_initial_world_state(blueprint.initial_world)
    initial_world = _calibrate_initial_world_for_viewpoint(
        initial_world,
        entities,
        resolved_player_role,
        playable_roles=calibration_roles,
    )
    opening_event = replace(
        blueprint.opening_event,
        severity=_opening_event_severity(initial_world),
    )
    dimension_defs = default_world_dimension_defs(initial_world.to_dimension_map())
    action_grammar = dimension_driven_world_action_grammar(
        initial_world.to_dimension_map(),
        dimension_defs,
        player_role=resolved_player_role,
        objective=blueprint.objective,
    )
    return ScenarioDefinition(
        id=_slugify(blueprint.title) or "generated-scenario",
        title=blueprint.title,
        premise=blueprint.premise,
        player_role=resolved_player_role,
        player_secret=blueprint.player_secret,
        objective=blueprint.objective,
        opponent=blueprint.opponent,
        audience=blueprint.audience,
        truth=blueprint.truth,
        opening_event=opening_event,
        seed_entities=entities,
        actions=(),
        initial_world=initial_world,
        playable_roles=playable_roles,
        action_grammar=action_grammar,
    )


def inspect_material_seed(
    *,
    source_material: str,
    llm_client: OpenAICompatibleLLM,
    entity_cap: int = DEFAULT_ENTITY_CAP,
    selected_player_role: str | None = None,
) -> MaterialSeedInspection:
    scout = build_scenario_from_material(
        source_material=source_material,
        llm_client=llm_client,
        entity_cap=entity_cap,
        selected_player_role=None,
    )
    selected_role = _normalize_player_role(selected_player_role) if selected_player_role else None
    roles = _ordered_roles(scout.playable_roles, selected_role=selected_role)
    scenarios: list[ScenarioDefinition] = []
    for role in roles:
        if role == scout.player_role:
            scenario = scout
        else:
            scenario = build_scenario_from_material(
                source_material=source_material,
                llm_client=llm_client,
                entity_cap=entity_cap,
                selected_player_role=role,
            )
        scenarios.append(scenario)

    baseline = scenarios[0]
    baseline_metrics = {key: getattr(baseline.initial_world, key) for key in INSPECTION_METRIC_KEYS}
    baseline_summary = _summarize_inspection_metrics(baseline_metrics)
    viewpoint_cards = tuple(
        _build_viewpoint_card(
            scenario,
            baseline_metrics=baseline_metrics,
            selected_role=selected_role,
            baseline_role=baseline.player_role,
        )
        for scenario in scenarios
    )
    comparison_card = max(
        (card for card in viewpoint_cards if not card.is_baseline),
        key=lambda card: card.contrast_score,
        default=None,
    )
    selected_card = next((card for card in viewpoint_cards if card.is_selected), viewpoint_cards[0] if viewpoint_cards else None)
    role_overview_cards = tuple(
        _build_role_overview_card(card, is_comparison=bool(comparison_card and card.role == comparison_card.role))
        for card in viewpoint_cards
    )
    selected_overview_card = next(
        (card for card in role_overview_cards if selected_card is not None and card.role == selected_card.role),
        None,
    )
    comparison_overview_card = next(
        (card for card in role_overview_cards if comparison_card is not None and card.role == comparison_card.role),
        None,
    )
    selected_role_comparisons = _build_selected_role_comparisons(
        viewpoint_cards,
        reference_role=selected_card.role if selected_card is not None else baseline.player_role,
        primary_role=comparison_card.role if comparison_card is not None else None,
    )
    primary_selected_role_comparison = next((card for card in selected_role_comparisons if card.is_primary), None)
    pairwise_role_comparisons = _build_pairwise_role_comparisons(
        viewpoint_cards,
        selected_role=selected_card.role if selected_card is not None else baseline.player_role,
        primary_role=comparison_card.role if comparison_card is not None else None,
    )
    role_overview = tuple(_role_overview_line(card) for card in role_overview_cards)
    selected_summary = (
        f"{selected_card.role}：{selected_card.relationship_summary} / {selected_card.summary}"
        if selected_card is not None
        else ""
    )
    comparison_summary = (
        f"{comparison_card.role}：{comparison_card.relationship_summary} / {comparison_card.delta_summary}"
        if comparison_card is not None and comparison_card.contrast_score > 0
        else ""
    )
    comparison_focus = _summarize_focus_metrics(comparison_card.metric_deltas, comparison_card.focus_metrics) if comparison_card else "无显著差异"
    comparison_focus_count = len(comparison_card.focus_metrics) if comparison_card else 0
    comparison_role = comparison_card.role if comparison_card and comparison_card.contrast_score > 0 else None
    comparison_focus_metrics = comparison_card.focus_metrics if comparison_card and comparison_card.contrast_score > 0 else ()
    return MaterialSeedInspection(
        title=scout.title,
        playable_roles=roles,
        selected_role=selected_role,
        baseline_role=baseline.player_role,
        baseline_summary=baseline_summary,
        selected_summary=selected_summary,
        comparison_summary=comparison_summary,
        role_overview=role_overview,
        role_overview_cards=role_overview_cards,
        comparison_role=comparison_role,
        comparison_focus=comparison_focus,
        comparison_focus_metrics=comparison_focus_metrics,
        comparison_focus_count=comparison_focus_count,
        viewpoints=viewpoint_cards,
        selected_viewpoint=selected_card,
        comparison_viewpoint=comparison_card,
        selected_overview_card=selected_overview_card,
        comparison_overview_card=comparison_overview_card,
        selected_role_comparisons=selected_role_comparisons,
        primary_selected_role_comparison=primary_selected_role_comparison,
        pairwise_role_comparisons=pairwise_role_comparisons,
    )


def _normalize_entities(entities: tuple[SeedEntity, ...], entity_cap: int) -> tuple[SeedEntity, ...]:
    merged_entities = _merge_polarized_community_entities(entities)
    normalized: list[SeedEntity] = []
    seen_ids: set[str] = set()
    for entity in merged_entities:
        entity_id = _slugify(entity.id or entity.name)
        if not entity_id:
            entity_id = f"entity-{len(normalized) + 1}"
        if entity_id in seen_ids:
            continue
        normalized.append(
            SeedEntity(
                id=entity_id,
                name=entity.name.strip() or entity_id,
                role=entity.role.strip() or "相关方",
                public_goal=entity.public_goal.strip() or "stabilize their position",
                pressure_point=entity.pressure_point.strip() or "public scrutiny",
                starting_trust=max(0, min(100, entity.starting_trust)),
                influence=max(0, min(100, entity.influence)),
                stance=entity.stance.strip() or "watching",
                details=entity.details.strip() or entity.public_goal.strip() or entity.name.strip(),
            )
        )
        seen_ids.add(entity_id)
        if len(normalized) >= entity_cap:
            break
    return tuple(normalized)


def _merge_polarized_community_entities(entities: tuple[SeedEntity, ...]) -> tuple[SeedEntity, ...]:
    grouped: dict[str, list[SeedEntity]] = {}
    passthrough: list[SeedEntity] = []
    for entity in entities:
        subject = _polarized_subject(entity)
        if subject:
            grouped.setdefault(subject, []).append(entity)
        else:
            passthrough.append(entity)

    merged: list[SeedEntity] = list(passthrough)
    for subject, members in grouped.items():
        if len(members) == 1:
            merged.append(_neutralize_polarized_entity(members[0], subject))
            continue
        merged.append(_merge_entity_group(subject, members))
    return tuple(merged)


def _polarized_subject(entity: SeedEntity) -> str | None:
    match = POLARIZED_GROUP_RE.match(entity.name.strip())
    if not match:
        return None
    return match.group("subject").strip()


def _neutralize_polarized_entity(entity: SeedEntity, subject: str) -> SeedEntity:
    topic = _event_topic(subject)
    return SeedEntity(
        id=entity.id,
        name=f"围绕{topic}的相关人群",
        role=entity.role,
        public_goal="争夺事件解释权",
        pressure_point=entity.pressure_point,
        starting_trust=entity.starting_trust,
        influence=entity.influence,
        stance="split",
        details=f"围绕{topic}的人群内部存在不同立场，包括支持、反对与观望声音。{entity.details.strip()}".strip(),
    )


def _merge_entity_group(subject: str, members: list[SeedEntity]) -> SeedEntity:
    topic = _event_topic(subject)
    base_id = _slugify(subject) or _slugify("-".join(member.id for member in members)) or "community-group"
    pressure_points = sorted({member.pressure_point.strip() for member in members if member.pressure_point.strip()})
    detail_parts = [member.details.strip() for member in members if member.details.strip()]
    merged_role = members[0].role.strip() or "相关人群"
    return SeedEntity(
        id=f"group-{base_id}",
        name=f"围绕{topic}的相关人群",
        role=merged_role,
        public_goal="争夺事件解释权",
        pressure_point=" / ".join(pressure_points) or "public scrutiny",
        starting_trust=sum(member.starting_trust for member in members) // len(members),
        influence=max(member.influence for member in members),
        stance="split",
        details=(
            f"围绕{topic}的人群内部存在不同立场，包括支持、反对与观望声音。"
            + (" ".join(detail_parts) if detail_parts else "")
        ).strip(),
    )


def _event_topic(subject: str) -> str:
    subject = subject.strip()
    if subject.endswith(("事件", "风波", "争议", "案")):
        return subject
    return f"{subject}事件"


def _resolve_player_role(blueprint_role: str, selected_player_role: str | None) -> str:
    selected = _normalize_player_role(selected_player_role) if selected_player_role else ""
    if selected:
        return selected
    return _normalize_player_role(blueprint_role)


def _ordered_roles(playable_roles: tuple[str, ...], *, selected_role: str | None = None) -> tuple[str, ...]:
    ordered: list[str] = []
    if selected_role:
        ordered.append(selected_role)
    for role in playable_roles:
        clean = _normalize_player_role(role)
        if clean and clean not in ordered:
            ordered.append(clean)
    return tuple(ordered)


def _find_viewpoint_entity(entities: tuple[SeedEntity, ...], player_role: str) -> SeedEntity | None:
    for entity in entities:
        if _entity_matches_role(entity, player_role):
            return entity
    return None


def _find_primary_counterpart(
    entities: tuple[SeedEntity, ...],
    player_entity: SeedEntity,
    *,
    playable_roles: tuple[str, ...] = (),
) -> SeedEntity | None:
    selectable_roles = {_normalize_player_role(role) for role in playable_roles if _normalize_player_role(role)}
    selectable_roles.discard(_normalize_player_role(player_entity.role))
    candidates = [entity for entity in entities if entity.id != player_entity.id]
    if selectable_roles:
        matching = [entity for entity in candidates if any(_entity_matches_role(entity, role) for role in selectable_roles)]
        if matching:
            candidates = matching
    if not candidates:
        return None
    return max(candidates, key=lambda entity: (entity.influence, -entity.starting_trust, entity.name))


def _fallback_counterpart_role(playable_roles: tuple[str, ...], *, player_role: str) -> str | None:
    normalized_player = _normalize_player_role(player_role)
    for role in playable_roles:
        clean = _normalize_player_role(role)
        if clean and clean != normalized_player:
            return clean
    return None


def _find_counterpart_for_role_without_player_entity(
    entities: tuple[SeedEntity, ...],
    *,
    player_role: str,
    playable_roles: tuple[str, ...] = (),
) -> SeedEntity | None:
    normalized_player = _normalize_player_role(player_role)
    candidates: list[SeedEntity] = []
    for role in playable_roles:
        clean = _normalize_player_role(role)
        if not clean or clean == normalized_player:
            continue
        matched = [entity for entity in entities if _entity_matches_role(entity, clean)]
        if matched:
            candidates.extend(matched)
    if not candidates:
        return None
    unique_candidates = {entity.id: entity for entity in candidates}
    return max(unique_candidates.values(), key=lambda entity: (entity.influence, -entity.starting_trust, entity.name))


def _prioritize_entities_for_viewpoint(
    entities: tuple[SeedEntity, ...],
    *,
    player_role: str,
    playable_roles: tuple[str, ...] = (),
) -> tuple[SeedEntity, ...]:
    player_entity = _find_viewpoint_entity(entities, player_role)
    if player_entity is None:
        return entities
    normalized_roles = tuple(_normalize_player_role(role) for role in playable_roles if _normalize_player_role(role))
    has_multiple_viewpoints = len(dict.fromkeys(normalized_roles)) > 1
    counterpart = _find_primary_counterpart(entities, player_entity, playable_roles=playable_roles) if has_multiple_viewpoints else None
    prioritized = [player_entity]
    if counterpart is not None and counterpart.id != player_entity.id:
        prioritized.append(counterpart)
    prioritized_ids = {entity.id for entity in prioritized}
    prioritized.extend(entity for entity in entities if entity.id not in prioritized_ids)
    return tuple(prioritized)


def _conflict_role_direction(player_role: str, counterpart_role: str) -> int:
    left = _normalize_player_role(player_role)
    right = _normalize_player_role(counterpart_role)
    if not left or not right or left == right:
        return 0
    return 1 if left < right else -1


def _stance_bias_value(stance: str) -> int:
    normalized = stance.strip().lower()
    if any(token in normalized for token in EMBATTLED_STANCE_TOKENS):
        return 2
    if any(token in normalized for token in STABILIZING_STANCE_TOKENS):
        return -1
    return 0


def _relationship_summary(*, player_entity: str, player_role: str, counterpart: str, counterpart_role: str) -> str:
    return f"{player_entity}（{player_role}） ↔ {counterpart}（{counterpart_role}）"


def _build_role_overview_card(card: ScenarioViewpointCard, *, is_comparison: bool = False) -> ScenarioRoleOverviewCard:
    overview_metrics = {key: card.metrics[key] for key in INSPECTION_METRIC_KEYS}
    return ScenarioRoleOverviewCard(
        role=card.role,
        metrics=overview_metrics,
        summary=card.summary,
        relationship_summary=card.relationship_summary,
        delta_summary=card.delta_summary,
        contrast_score=card.contrast_score,
        focus_metrics=card.focus_metrics,
        primary_counterpart=card.primary_counterpart,
        primary_counterpart_role=card.primary_counterpart_role,
        player_entity_resolved=card.player_entity_resolved,
        primary_counterpart_resolved=card.primary_counterpart_resolved,
        is_selected=card.is_selected,
        is_baseline=card.is_baseline,
        is_comparison=is_comparison,
    )


def _role_overview_tags(card: ScenarioRoleOverviewCard) -> str:
    tags: list[str] = []
    if card.is_selected:
        tags.append("selected")
    if card.is_baseline:
        tags.append("baseline")
    if card.is_comparison:
        tags.append("comparison")
    return "".join(f"[{tag}]" for tag in tags)


def _role_overview_line(card: ScenarioRoleOverviewCard) -> str:
    focus = "基准视角" if card.contrast_score == 0 else card.delta_summary
    return f"{card.role}：{card.relationship_summary} / {focus}"


def _role_overview_matrix_line(card: ScenarioRoleOverviewCard) -> str:
    tags = _role_overview_tags(card)
    focus = "基准视角" if card.contrast_score == 0 else card.delta_summary
    metrics = " / ".join(f"{INSPECTION_METRIC_LABELS[key]} {card.metrics[key]}" for key in INSPECTION_METRIC_KEYS)
    prefix = f"{tags} " if tags else ""
    return f"{prefix}{card.role} | {metrics} | {focus} | {card.relationship_summary}"


def _build_selected_role_comparisons(
    viewpoint_cards: tuple[ScenarioViewpointCard, ...],
    *,
    reference_role: str,
    primary_role: str | None,
) -> tuple[ScenarioRoleComparisonCard, ...]:
    normalized_reference = _normalize_player_role(reference_role)
    normalized_primary = _normalize_player_role(primary_role) if primary_role else ""
    reference_card = next((card for card in viewpoint_cards if _normalize_player_role(card.role) == normalized_reference), None)
    comparisons: list[ScenarioRoleComparisonCard] = []
    for card in viewpoint_cards:
        if _normalize_player_role(card.role) == normalized_reference:
            continue
        comparisons.append(
            _build_role_comparison_card(
                reference_card,
                card,
                is_primary=bool(normalized_primary and _normalize_player_role(card.role) == normalized_primary),
            )
        )
    comparisons.sort(key=lambda item: (not item.is_primary, -item.contrast_score, item.compared_role))
    return tuple(comparisons)


def _build_pairwise_role_comparisons(
    viewpoint_cards: tuple[ScenarioViewpointCard, ...],
    *,
    selected_role: str,
    primary_role: str | None,
) -> tuple[ScenarioRoleComparisonCard, ...]:
    normalized_selected = _normalize_player_role(selected_role)
    normalized_primary = _normalize_player_role(primary_role) if primary_role else ""
    comparisons: list[ScenarioRoleComparisonCard] = []
    for index, reference_card in enumerate(viewpoint_cards):
        for compared_card in viewpoint_cards[index + 1 :]:
            comparisons.append(
                _build_role_comparison_card(
                    reference_card,
                    compared_card,
                    is_primary=bool(
                        normalized_primary
                        and _normalize_player_role(reference_card.role) == normalized_selected
                        and _normalize_player_role(compared_card.role) == normalized_primary
                    ),
                )
            )
    if comparisons and any(card.is_primary for card in comparisons):
        comparisons.sort(key=lambda item: (not item.is_primary,))
    return tuple(comparisons)


def _build_role_comparison_card(
    reference_card: ScenarioViewpointCard | None,
    compared_card: ScenarioViewpointCard,
    *,
    is_primary: bool,
) -> ScenarioRoleComparisonCard:
    if reference_card is None:
        metric_deltas = {key: 0 for key in INSPECTION_METRIC_KEYS}
        reference_role = ""
        reference_summary = ""
        reference_metrics: dict[str, int] = {}
        reference_relationship_summary = ""
    else:
        metric_deltas = {
            key: compared_card.metrics[key] - reference_card.metrics[key]
            for key in INSPECTION_METRIC_KEYS
        }
        reference_role = reference_card.role
        reference_summary = reference_card.summary
        reference_metrics = dict(reference_card.metrics)
        reference_relationship_summary = reference_card.relationship_summary
    focus_metrics = _focus_metrics(metric_deltas)
    return ScenarioRoleComparisonCard(
        reference_role=reference_role,
        reference_summary=reference_summary,
        reference_metrics=reference_metrics,
        reference_relationship_summary=reference_relationship_summary,
        compared_role=compared_card.role,
        compared_summary=compared_card.summary,
        compared_metrics=dict(compared_card.metrics),
        metric_deltas=metric_deltas,
        delta_summary=_summarize_focus_metrics(metric_deltas, focus_metrics),
        contrast_score=_contrast_score(metric_deltas),
        focus_metrics=focus_metrics,
        compared_relationship_summary=compared_card.relationship_summary,
        is_primary=is_primary,
    )


def _summarize_inspection_metrics(metrics: dict[str, int]) -> str:
    return (
        f"控制权 {metrics['control']} / 压力 {metrics['pressure']} / "
        f"公信力 {metrics['credibility']} / 叙事控制 {metrics['narrative_control']}"
    )


def _focus_metrics(metric_deltas: dict[str, int]) -> tuple[str, ...]:
    ranked = sorted(
        (
            (key, abs(metric_deltas[key]) * INSPECTION_FOCUS_WEIGHTS.get(key, 1.0), abs(metric_deltas[key]), index)
            for index, key in enumerate(INSPECTION_METRIC_KEYS)
            if metric_deltas[key] != 0
        ),
        key=lambda item: (-item[1], -item[2], item[3]),
    )
    return tuple(key for key, _, _, _ in ranked[:3])


def _contrast_score(metric_deltas: dict[str, int]) -> int:
    return sum(abs(metric_deltas[key]) for key in INSPECTION_METRIC_KEYS)


def _summarize_focus_metrics(metric_deltas: dict[str, int], focus_metrics: tuple[str, ...]) -> str:
    if not focus_metrics:
        return "无显著差异"
    parts = [f"{INSPECTION_METRIC_LABELS[key]} {metric_deltas[key]:+d}" for key in focus_metrics]
    return " / ".join(parts)


def _calibrate_initial_world_for_viewpoint(
    state: WorldState,
    entities: tuple[SeedEntity, ...],
    player_role: str,
    *,
    playable_roles: tuple[str, ...] = (),
) -> WorldState:
    player_entity = _find_viewpoint_entity(entities, player_role)
    if player_entity is None:
        return _calibrate_initial_world_without_player_entity(
            state,
            player_role=player_role,
            playable_roles=playable_roles,
        )

    others = [entity for entity in entities if entity.id != player_entity.id]
    avg_other_trust = sum(entity.starting_trust for entity in others) / len(others) if others else player_entity.starting_trust
    avg_other_influence = sum(entity.influence for entity in others) / len(others) if others else player_entity.influence
    trust_gap = player_entity.starting_trust - avg_other_trust
    influence_gap = player_entity.influence - avg_other_influence
    stance_text = player_entity.stance.strip().lower()
    counterpart = _find_primary_counterpart(entities, player_entity, playable_roles=playable_roles)

    adjusted = replace(state)
    adjusted.control += round(influence_gap / 4)
    adjusted.credibility += round(trust_gap / 3)
    adjusted.narrative_control += round((player_entity.influence - 50) / 5)
    adjusted.pressure -= round(trust_gap / 3)
    adjusted.community_panic -= round(trust_gap / 4)
    adjusted.rumor_level -= round(trust_gap / 5)
    adjusted.treasury += round(influence_gap / 10)
    adjusted.liquidity += round(influence_gap / 9)

    if any(token in stance_text for token in EMBATTLED_STANCE_TOKENS):
        adjusted.control -= 8
        adjusted.pressure += 6
        adjusted.community_panic += 4
        adjusted.treasury -= 3
        adjusted.liquidity -= 4
    elif any(token in stance_text for token in STABILIZING_STANCE_TOKENS):
        adjusted.control += 3
        adjusted.pressure -= 2
        adjusted.treasury += 2
        adjusted.liquidity += 2

    if counterpart is not None:
        conflict_gap = player_entity.influence - counterpart.influence
        trust_vs_counterpart = player_entity.starting_trust - counterpart.starting_trust
        contest_intensity = max(4, round((counterpart.influence + abs(trust_vs_counterpart)) / 12))
        player_stance_bias = _stance_bias_value(player_entity.stance)
        counterpart_stance_bias = _stance_bias_value(counterpart.stance)
        relative_stance_bias = player_stance_bias - counterpart_stance_bias
        adjusted.pressure += max(0, round((-conflict_gap) / 6))
        adjusted.community_panic += max(0, round((-trust_vs_counterpart) / 8))
        adjusted.rumor_level += max(0, round((counterpart.influence - player_entity.influence) / 7))
        adjusted.control += round(conflict_gap / 5)
        adjusted.credibility += round(trust_vs_counterpart / 4)
        adjusted.narrative_control += round((player_entity.influence - counterpart.influence) / 5)
        adjusted.liquidity += round(conflict_gap / 10)
        adjusted.pressure += relative_stance_bias * 3
        adjusted.community_panic += relative_stance_bias * 2
        adjusted.rumor_level += max(0, relative_stance_bias)
        adjusted.narrative_control += relative_stance_bias * 3
        adjusted.control -= relative_stance_bias * 3
        adjusted.credibility -= relative_stance_bias * 2

        player_is_institution = _looks_institutional(player_entity)
        counterpart_is_institution = _looks_institutional(counterpart)
        if player_is_institution and not counterpart_is_institution:
            adjusted.control += contest_intensity + 2
            adjusted.exchange_trust += contest_intensity
            adjusted.narrative_control -= max(2, contest_intensity // 2)
            adjusted.community_panic -= max(1, contest_intensity // 2)
            adjusted.treasury += contest_intensity
            adjusted.liquidity += max(2, contest_intensity // 2 + 1)
        elif counterpart_is_institution and not player_is_institution:
            adjusted.control -= contest_intensity + 2
            adjusted.exchange_trust -= max(1, contest_intensity // 2)
            adjusted.narrative_control += contest_intensity
            adjusted.community_panic += max(2, contest_intensity // 2)
            adjusted.rumor_level += max(1, contest_intensity // 2)
            adjusted.treasury -= contest_intensity
            adjusted.liquidity -= max(2, contest_intensity // 2 + 1)
        elif abs(conflict_gap) <= 1 and abs(trust_vs_counterpart) <= 1:
            role_direction = _conflict_role_direction(player_entity.role, counterpart.role)
            adjusted.control += 5 * role_direction
            adjusted.credibility += 4 * role_direction
            adjusted.pressure -= 4 * role_direction
            adjusted.community_panic -= 3 * role_direction
            adjusted.narrative_control += 5 * role_direction

    adjusted.control += round(influence_gap / 6)
    adjusted.pressure -= round(influence_gap / 8)
    adjusted.clamp()
    return repair_initial_world_state(adjusted)


def _calibrate_initial_world_without_player_entity(
    state: WorldState,
    *,
    player_role: str,
    playable_roles: tuple[str, ...] = (),
) -> WorldState:
    normalized_player = _normalize_player_role(player_role)
    normalized_roles = []
    for role in playable_roles:
        clean = _normalize_player_role(role)
        if clean and clean not in normalized_roles:
            normalized_roles.append(clean)
    if normalized_player and normalized_player not in normalized_roles:
        normalized_roles.append(normalized_player)
    if len(normalized_roles) < 2:
        return state

    role_index = normalized_roles.index(normalized_player) if normalized_player in normalized_roles else 0
    center = (len(normalized_roles) - 1) / 2
    direction = 1 if role_index < center else -1 if role_index > center else 0
    if direction == 0:
        return state

    adjusted = replace(state)
    adjusted.control += 6 * direction
    adjusted.credibility += 4 * direction
    adjusted.pressure -= 6 * direction
    adjusted.community_panic -= 4 * direction
    adjusted.narrative_control += 5 * direction
    adjusted.exchange_trust += 3 * direction
    adjusted.treasury += 2 * direction
    adjusted.liquidity += 2 * direction
    adjusted.clamp()
    return repair_initial_world_state(adjusted)


def _build_viewpoint_card(
    scenario: ScenarioDefinition,
    *,
    baseline_metrics: dict[str, int],
    selected_role: str | None,
    baseline_role: str,
) -> ScenarioViewpointCard:
    metrics = {key: getattr(scenario.initial_world, key) for key in INSPECTION_METRIC_KEYS}
    summary = _summarize_inspection_metrics(metrics)
    key_entities = tuple(entity.name for entity in scenario.seed_entities[:3])
    player_entity = _find_viewpoint_entity(scenario.seed_entities, scenario.player_role)
    counterpart = (
        _find_primary_counterpart(scenario.seed_entities, player_entity, playable_roles=scenario.playable_roles)
        if player_entity
        else _find_counterpart_for_role_without_player_entity(
            scenario.seed_entities,
            player_role=scenario.player_role,
            playable_roles=scenario.playable_roles,
        )
    )
    metric_deltas = {key: metrics[key] - baseline_metrics[key] for key in INSPECTION_METRIC_KEYS}
    contrast_score = _contrast_score(metric_deltas)
    focus_metrics = _focus_metrics(metric_deltas)
    delta_summary = _summarize_focus_metrics(metric_deltas, focus_metrics)
    normalized_role = _normalize_player_role(scenario.player_role)
    normalized_baseline = _normalize_player_role(baseline_role)
    normalized_selected = _normalize_player_role(selected_role) if selected_role else normalized_baseline
    fallback_counterpart_role = _fallback_counterpart_role(scenario.playable_roles, player_role=scenario.player_role)
    counterpart_name = counterpart.name if counterpart else (fallback_counterpart_role or "无明显对位")
    counterpart_role = counterpart.role if counterpart else (fallback_counterpart_role or "无明显对位")
    relationship_summary = _relationship_summary(
        player_entity=player_entity.name if player_entity else scenario.player_role,
        player_role=player_entity.role if player_entity else scenario.player_role,
        counterpart=counterpart_name,
        counterpart_role=counterpart_role,
    )
    return ScenarioViewpointCard(
        role=scenario.player_role,
        summary=summary,
        metrics=metrics,
        metric_deltas=metric_deltas,
        delta_summary=delta_summary,
        contrast_score=contrast_score,
        focus_metrics=focus_metrics,
        key_entities=key_entities,
        player_entity=player_entity.name if player_entity else scenario.player_role,
        player_entity_role=player_entity.role if player_entity else scenario.player_role,
        player_entity_resolved=player_entity is not None,
        primary_counterpart=counterpart_name,
        primary_counterpart_role=counterpart_role,
        primary_counterpart_resolved=counterpart is not None,
        relationship_summary=relationship_summary,
        opening_headline=scenario.opening_event.headline,
        is_selected=bool(normalized_selected and normalized_role == normalized_selected),
        is_baseline=normalized_role == normalized_baseline,
    )


def _normalize_player_role(player_role: str) -> str:
    role = player_role.strip()
    person_match = PERSON_ROLE_SUFFIX_RE.match(role)
    if person_match:
        normalized_person = person_match.group("base").strip()
        if normalized_person:
            role = normalized_person
    match = INSTITUTION_ROLE_SUFFIX_RE.match(role)
    if not match:
        return _compact_institution_role(role)
    base = match.group("base").strip()
    if any(token in base for token in INSTITUTION_TOKENS):
        return _compact_institution_role(base)
    return _compact_institution_role(role)


def _compact_institution_role(role: str) -> str:
    clean = role.strip()
    if not clean:
        return clean
    for token in sorted(INSTITUTION_TOKENS, key=len, reverse=True):
        idx = clean.find(token)
        if idx == -1:
            continue
        prefix = clean[: idx + len(token)].strip()
        if prefix:
            return prefix
    return clean


def _entity_matches_role(entity: SeedEntity, role: str) -> bool:
    normalized_role = _normalize_player_role(role)
    if not normalized_role:
        return False
    candidates = {
        entity.name.strip(),
        entity.role.strip(),
        _normalize_player_role(entity.name),
        _normalize_player_role(entity.role),
    }
    if normalized_role in candidates:
        return True
    if len(normalized_role) < 2:
        return False
    for candidate in candidates:
        if candidate and (normalized_role in candidate or candidate in normalized_role):
            return True
    return False


def _looks_institutional(entity: SeedEntity) -> bool:
    haystack = f"{entity.role} {entity.name}".strip()
    return any(token in haystack for token in INSTITUTION_TOKENS)


def _normalize_playable_roles(
    playable_roles: tuple[str, ...],
    *,
    fallback_role: str,
    preferred_role: str | None = None,
) -> tuple[str, ...]:
    raw_roles = playable_roles or (fallback_role,)
    normalized: list[str] = []
    preferred = _normalize_player_role(preferred_role) if preferred_role else ""
    if preferred:
        normalized.append(preferred)
    for role in raw_roles:
        clean = _normalize_player_role(role)
        if clean and clean not in normalized:
            normalized.append(clean)
    fallback = _normalize_player_role(fallback_role)
    if fallback and fallback not in normalized:
        normalized.append(fallback)
    return tuple(normalized or (fallback,))


def _backfill_entities(existing: tuple[SeedEntity, ...], entity_cap: int) -> tuple[SeedEntity, ...]:
    existing_roles = {entity.role for entity in existing}
    seed_pool = [
        SeedEntity(
            id=f"fallback-{role}",
            name=f"{role.title()} Watcher",
            role=role,
            public_goal="protect their own downside",
            pressure_point="being blamed for the crisis",
            starting_trust=35,
            influence=55,
            stance="watching",
            details="auto-generated fallback entity",
        )
        for role in SUPPORTED_ROLES
        if role not in existing_roles
    ]
    merged = list(existing)
    for entity in seed_pool:
        merged.append(entity)
        if len(merged) >= min(entity_cap, 5):
            break
    return tuple(merged)


def _fallback_role(name: str, details: str) -> str:
    haystack = f"{name} {details}".lower()
    if any(word in haystack for word in ("exchange", "platform", "listing")):
        return "exchange"
    if any(word in haystack for word in ("community", "user", "customer")):
        return "community"
    if any(word in haystack for word in ("market maker", "maker", "liquidity")):
        return "market_maker"
    if any(word in haystack for word in ("fund", "investor", "whale", "holder")):
        return "whale"
    return "kol"


def _opening_event_severity(state: WorldState) -> int:
    severity = (
        state.pressure
        + state.community_panic
        + state.rumor_level
        + state.sell_pressure
        + state.volatility
        + (100 - state.control)
    ) // 6
    return max(35, min(95, severity))


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug
